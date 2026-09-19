"""Executor — roda o catálogo de regras sobre o que foi coletado.

Duas responsabilidades, e a segunda é a que importa mais:

1. Montar o `Contexto` de cada processo a partir do banco e rodar as regras.
2. **Registrar toda execução**, inclusive as que não geraram achado e as que não
   puderam rodar.

O item 2 é o que sustenta o relatório de cobertura. Sem ele não há como
responder "por que este processo nunca foi apontado?" — e a resposta honesta
pode ser "porque a regra nunca rodou nele", o que é muito diferente de "porque
está tudo certo".
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any

from radar.achados.modelo import Ficha
from radar.analise.deterministico.base import (
    REGISTRO,
    Contexto,
    Desfecho,
    Regra,
    Resultado,
)
from radar.analise.normas import BaseNormas

log = logging.getLogger(__name__)


@dataclass(slots=True)
class Balanco:
    """O que aconteceu numa execução completa.

    `sem_dados` e `nao_aplicavel` aparecem lado a lado com `achados` de
    propósito: um número alto ali significa que o radar está cego em boa parte
    do que examinou, e isso precisa ser tão visível quanto os achados.
    """

    processos: int = 0
    regras: int = 0
    achados: int = 0
    limpos: int = 0
    sem_dados: int = 0
    nao_aplicavel: int = 0
    erros: int = 0
    fichas: list[Ficha] | None = None
    faltantes: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.fichas is None:
            self.fichas = []
        if self.faltantes is None:
            self.faltantes = {}

    @property
    def executadas(self) -> int:
        return self.achados + self.limpos + self.sem_dados + self.nao_aplicavel + self.erros

    @property
    def cobertura(self) -> float:
        """Fração das execuções em que a regra de fato conseguiu olhar.

        Não é medida de regularidade do município. É medida de quanto o radar
        enxergou — e serve para dizer, no painel, o quanto ele ainda não viu.
        """
        util = self.achados + self.limpos
        return util / self.executadas if self.executadas else 0.0


class Executor:
    def __init__(self, conexao: sqlite3.Connection, normas: BaseNormas) -> None:
        self.con = conexao
        self.con.row_factory = sqlite3.Row
        self.normas = normas

    # -- montagem do contexto ---------------------------------------------

    def processos(self, municipio_ibge: str, exercicio: int | None = None) -> list[sqlite3.Row]:
        sql = (
            "SELECT p.* FROM processo p JOIN municipio m ON m.id = p.municipio_id"
            " WHERE m.codigo_ibge = ?"
        )
        params: list[Any] = [municipio_ibge]
        if exercicio:
            sql += " AND p.exercicio = ?"
            params.append(exercicio)
        return list(self.con.execute(sql + " ORDER BY p.exercicio DESC, p.numero", params))

    def contexto(self, processo: sqlite3.Row, municipio_ibge: str) -> Contexto:
        # Traz a versão mais recente de cada documento, com hash e id. Sem isso
        # as regras não têm onde ancorar o achado, e um achado sem âncora não
        # pode existir (regra R1).
        documentos = [
            dict(r)
            for r in self.con.execute(
                "SELECT d.*, pd.papel, pd.vinculo_origem, pd.confianca,"
                "       v.id AS documento_versao_id, v.sha256, v.versao"
                "  FROM processo_documento pd"
                "  JOIN documento d ON d.id = pd.documento_id"
                "  LEFT JOIN documento_versao v ON v.documento_id = d.id"
                "   AND v.versao = (SELECT MAX(versao) FROM documento_versao"
                "                    WHERE documento_id = d.id)"
                " WHERE pd.processo_id = ?",
                (processo["id"],),
            )
        ]
        participantes = [
            dict(r)
            for r in self.con.execute(
                "SELECT pa.*, e.documento_fiscal, e.razao_social, e.capital_social,"
                "       e.data_abertura, e.cnae_principal, e.situacao_cadastral"
                "  FROM participacao pa"
                "  JOIN entidade e ON e.id = pa.entidade_id"
                " WHERE pa.processo_id = ?",
                (processo["id"],),
            )
        ]
        return Contexto(
            processo=dict(processo),
            documentos=documentos,
            participantes=participantes,
            normas=self.normas,
            municipio_ibge=municipio_ibge,
            extras=self._extras(processo),
        )

    def _extras(self, processo: sqlite3.Row) -> dict[str, Any]:
        """Dados que algumas regras pedem e que não estão no processo.

        Regra que precisa de algo daqui e não o encontra devolve SEM_DADOS — a
        chave ausente é a diferença entre "não há sanção" e "não consultei a
        base de sanções". Por isso `sancoes` só é preenchido quando a tabela tem
        conteúdo: uma lista vazia mentiria.
        """
        extras: dict[str, Any] = {}

        if self.con.execute("SELECT 1 FROM sancao LIMIT 1").fetchone():
            extras["sancoes"] = [
                dict(r)
                for r in self.con.execute(
                    "SELECT s.*, e.documento_fiscal FROM sancao s"
                    "  JOIN entidade e ON e.id = s.entidade_id"
                )
            ]

        # Demais contratações do mesmo município e exercício, para as regras que
        # comparam um processo com a série (fracionamento, concentração, rodízio).
        extras["contratacoes_do_municipio"] = [
            dict(r)
            for r in self.con.execute(
                "SELECT p.id, p.numero, p.tipo, p.modalidade, p.objeto, p.exercicio,"
                "       p.valor_estimado, p.valor_contratado, p.data_publicacao,"
                "       p.orgao_id, o.nome AS orgao_nome, o.cnpj AS orgao_cnpj"
                "  FROM processo p LEFT JOIN orgao o ON o.id = p.orgao_id"
                " WHERE p.municipio_id = ? AND p.exercicio = ? AND p.id != ?",
                (processo["municipio_id"], processo["exercicio"], processo["id"]),
            )
        ]
        return extras

    # -- execução ----------------------------------------------------------

    def executar(
        self,
        municipio_ibge: str,
        exercicio: int | None = None,
        regras: list[Regra] | None = None,
        persistir: bool = True,
    ) -> Balanco:
        alvo = regras if regras is not None else list(REGISTRO)
        processos = self.processos(municipio_ibge, exercicio)
        b = Balanco(processos=len(processos), regras=len(alvo))

        if not processos:
            log.warning(
                "nenhum processo para %s — rodar as regras sobre banco vazio "
                "produziria 'nada encontrado', que não é a mesma coisa que 'nada errado'",
                municipio_ibge,
            )
            return b

        for linha in processos:
            ctx = self.contexto(linha, municipio_ibge)
            for regra in alvo:
                r = regra.executar(ctx)
                self._contabilizar(b, r)
                if persistir:
                    self._registrar(regra, ctx, r)
                if r.desfecho is Desfecho.ACHADO:
                    assert b.fichas is not None
                    b.fichas.extend(r.fichas)
                    if persistir:
                        for ficha in r.fichas:
                            self.gravar_ficha(ficha)
        return b

    def _contabilizar(self, b: Balanco, r: Resultado) -> None:
        match r.desfecho:
            case Desfecho.ACHADO:
                b.achados += len(r.fichas)
            case Desfecho.LIMPO:
                b.limpos += 1
            case Desfecho.SEM_DADOS:
                b.sem_dados += 1
                assert b.faltantes is not None
                for campo in r.dados_faltantes or ["(não especificado)"]:
                    b.faltantes[campo] = b.faltantes.get(campo, 0) + 1
            case Desfecho.NAO_APLICAVEL:
                b.nao_aplicavel += 1
            case Desfecho.ERRO:
                b.erros += 1
                log.error("regra falhou: %s", r.motivo)

    def _registrar(self, regra: Regra, ctx: Contexto, r: Resultado) -> None:
        rid = self._id_regra(regra)
        self.con.execute(
            "INSERT INTO execucao_regra"
            " (regra_id, processo_id, resultado, motivo, versao_regra, duracao_ms)"
            " VALUES (?,?,?,?,?,?)",
            (
                rid,
                ctx.processo.get("id"),
                r.desfecho.value,
                r.motivo or None,
                regra.versao,
                r.duracao_ms,
            ),
        )

    def _id_regra(self, regra: Regra) -> int:
        linha = self.con.execute(
            "SELECT id FROM regra WHERE codigo = ?", (regra.codigo,)
        ).fetchone()
        if linha:
            return int(linha[0])
        cur = self.con.execute(
            "INSERT INTO regra (codigo, nome, categoria, natureza, descricao,"
            " requisitos_dados, severidade_base, versao, fonte_metodologica)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (
                regra.codigo,
                regra.nome,
                regra.categoria,
                "deterministica",
                regra.descricao,
                repr(list(regra.requisitos)),
                regra.severidade_base.value,
                regra.versao,
                regra.fonte_metodologica,
            ),
        )
        return int(cur.lastrowid or 0)

    # -- persistência de achados ------------------------------------------

    def gravar_ficha(self, ficha: Ficha) -> int | None:
        """Grava a ficha e suas evidências. Idempotente pela impressão digital.

        A gravação de `achado` e de `achado_evidencia` acontece na mesma
        transação: um achado sem evidência no banco violaria a regra R1 e ficaria
        barrado pelo trigger na primeira mudança de status — melhor não existir.
        """
        digital = ficha.impressao_digital()
        ja = self.con.execute(
            "SELECT id FROM achado WHERE codigo = ?", (f"{ficha.codigo}#{digital}",)
        ).fetchone()
        if ja:
            return int(ja[0])

        mid = self.con.execute(
            "SELECT id FROM municipio WHERE codigo_ibge = ?",
            (ficha.municipio_codigo_ibge,),
        ).fetchone()
        if not mid:
            log.error("município %s não cadastrado", ficha.municipio_codigo_ibge)
            return None

        cur = self.con.execute(
            "INSERT INTO achado (codigo, municipio_id, processo_id, titulo,"
            " fatos_documentais, hipoteses, lacunas, consequencia_possivel,"
            " hipotese_alternativa, gravidade, forca_evidencia, urgencia,"
            " prazo_limite, regime_aplicavel, origem, status)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                f"{ficha.codigo}#{digital}",
                mid[0],
                ficha.processo_id,
                ficha.titulo,
                "\n".join(ficha.fatos_documentais),
                "\n".join(ficha.hipoteses) or None,
                "\n".join(ficha.lacunas),
                ficha.consequencia_possivel,
                ficha.hipotese_alternativa,
                ficha.gravidade.value,
                ficha.forca_evidencia.value,
                ficha.urgencia.value,
                ficha.prazo_limite.isoformat() if ficha.prazo_limite else None,
                ficha.regime_aplicavel.value,
                ficha.origem.value,
                ficha.status.value,
            ),
        )
        aid = int(cur.lastrowid or 0)
        for i, ev in enumerate(ficha.evidencias):
            self.con.execute(
                "INSERT INTO achado_evidencia"
                " (achado_id, documento_versao_id, pagina, trecho, observacao, ordem)"
                " VALUES (?,?,?,?,?,?)",
                (aid, ev.documento_versao_id, ev.pagina, ev.trecho, ev.observacao, i),
            )
        return aid


def data_hoje() -> date:
    return date.today()
