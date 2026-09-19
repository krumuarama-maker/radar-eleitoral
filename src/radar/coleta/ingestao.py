"""Ingestão — do que o coletor trouxe para dentro do banco.

É a peça que faltava entre coleta e análise, e a mais delicada do sistema: é
aqui que documentos soltos viram um *processo*, e é a partir do processo que as
regras conseguem enxergar divergência entre fases.

Três decisões que moldam tudo:

**Versão, nunca sobrescrita.** Documento cujo conteúdo mudou vira versão nova.
Edital retificado não apaga o anterior — e a existência da retificação é, por si,
um sinal.

**Vínculo com procedência declarada.** Toda ligação entre processo e documento
registra COMO foi feita: por identificador da fonte ou por heurística. Regra que
depende de vínculo heurístico produz achado mais fraco, e isso só é possível
porque a procedência está gravada.

**O órgão é quem licita, não o município.** Cada CNPJ vira um órgão próprio.
Sem isso, o fracionamento entre Prefeitura, Câmara e fundos fica invisível — que
é justamente o achado mais valioso de um radar municipal.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from radar.coleta.base import ItemColetado, ResultadoColeta

log = logging.getLogger(__name__)


@dataclass(slots=True)
class BalancoIngestao:
    documentos_novos: int = 0
    versoes_novas: int = 0
    ja_conhecidos: int = 0
    processos_novos: int = 0
    processos_atualizados: int = 0
    orgaos_descobertos: list[str] = field(default_factory=list)
    entidades_novas: int = 0
    participacoes: int = 0
    erros: list[str] = field(default_factory=list)


class Ingestor:
    """Grava o resultado de uma coleta. Idempotente: reexecutar não duplica."""

    def __init__(self, con: sqlite3.Connection, municipio_ibge: str) -> None:
        self.con = con
        self.con.row_factory = sqlite3.Row
        self.municipio_ibge = municipio_ibge
        self._municipio_id = self._exigir_municipio()

    def _exigir_municipio(self) -> int:
        linha = self.con.execute(
            "SELECT id FROM municipio WHERE codigo_ibge = ?", (self.municipio_ibge,)
        ).fetchone()
        if not linha:
            raise ValueError(
                f"município {self.municipio_ibge} não cadastrado. "
                "Rode `radar municipio` antes de ingerir."
            )
        return int(linha[0])

    # -- entrada principal -------------------------------------------------

    def ingerir(
        self, resultado: ResultadoColeta, coleta_id: int | None = None
    ) -> BalancoIngestao:
        b = BalancoIngestao()
        fonte_id = self._fonte_id(resultado.fonte_chave)

        for item in resultado.itens:
            try:
                if item.tipo_documento == "contratacao_pncp":
                    self._ingerir_contratacao_pncp(item, fonte_id, coleta_id, b)
                else:
                    self._ingerir_anexo(item, fonte_id, coleta_id, b)
            except Exception as exc:  # um item ruim não interrompe a ingestão
                b.erros.append(f"{item.url_origem}: {type(exc).__name__}: {exc}")
                log.exception("falha ingerindo %s", item.url_origem)
        return b

    # -- contratação (registro estruturado do PNCP) ------------------------

    def _ingerir_contratacao_pncp(
        self, item: ItemColetado, fonte_id: int, coleta_id: int | None, b: BalancoIngestao
    ) -> None:
        bruto = json.loads(item.conteudo.decode("utf-8"))
        meta = item.metadados

        orgao_id = self._orgao(
            cnpj=str(meta.get("cnpj_orgao") or ""),
            nome=str((bruto.get("orgaoEntidade") or {}).get("razaoSocial") or ""),
            balanco=b,
        )

        processo_id = self._processo(bruto, meta, orgao_id, b)

        # O próprio JSON é documento preservado. Sem isso, achado gerado a partir
        # de dado estruturado não teria onde se ancorar (ver `ancorar()`).
        doc_id, _ = self._documento_e_versao(
            item,
            fonte_id,
            coleta_id,
            orgao_id,
            b,
            tipo="registro_contratacao",
            titulo=item.titulo,
        )
        self._vincular(processo_id, doc_id, "registro_contratacao", "identificador", 1.0)

        self._participantes(bruto, processo_id, b)

    def _processo(
        self,
        bruto: dict[str, Any],
        meta: dict[str, Any],
        orgao_id: int | None,
        b: BalancoIngestao,
    ) -> int:
        numero = str(bruto.get("numeroCompra") or meta.get("sequencial") or "")
        ano = int(bruto.get("anoCompra") or 0) or None
        tipo = self._tipo_processo(int(meta.get("modalidade") or 0))
        modalidade = self._nome_modalidade(int(meta.get("modalidade") or 0))

        existente = self.con.execute(
            "SELECT id FROM processo WHERE municipio_id=? AND tipo=? AND numero=?"
            "   AND exercicio IS ? AND orgao_id IS ?",
            (self._municipio_id, tipo, numero, ano, orgao_id),
        ).fetchone()

        campos = {
            "modalidade": modalidade,
            "objeto": bruto.get("objetoCompra"),
            "regime_juridico": self._regime(bruto),
            "valor_estimado": bruto.get("valorTotalEstimado"),
            "valor_homologado": bruto.get("valorTotalHomologado"),
            "data_publicacao": _iso(
                meta.get("data_publicacao") or bruto.get("dataPublicacaoPncp")
            ),
            "data_abertura": _iso(bruto.get("dataAberturaProposta")),
            "situacao": bruto.get("situacaoCompraNome"),
        }

        if existente:
            self.con.execute(
                "UPDATE processo SET modalidade=?, objeto=?, regime_juridico=?,"
                " valor_estimado=?, valor_homologado=?, data_publicacao=?,"
                " data_abertura=?, situacao=?, atualizado_em=datetime('now')"
                " WHERE id=?",
                (*campos.values(), existente[0]),
            )
            b.processos_atualizados += 1
            return int(existente[0])

        cur = self.con.execute(
            "INSERT INTO processo (municipio_id, orgao_id, tipo, numero, exercicio,"
            " modalidade, objeto, regime_juridico, valor_estimado, valor_homologado,"
            " data_publicacao, data_abertura, situacao)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (self._municipio_id, orgao_id, tipo, numero, ano, *campos.values()),
        )
        b.processos_novos += 1
        return int(cur.lastrowid or 0)

    def _regime(self, bruto: dict[str, Any]) -> str:
        """Qual lei regia o ato.

        O PNCP nasceu com a Lei 14.133 e traz `amparoLegal`. Quando o campo vem,
        ele manda; quando não vem, fica `indeterminado` — e regra que depende de
        regime devolve NAO_APLICAVEL em vez de presumir a lei nova, que é o erro
        que a regra R4 existe para impedir.
        """
        amparo = str((bruto.get("amparoLegal") or {}).get("nome") or "").lower()
        if "14.133" in amparo or "14133" in amparo:
            return "lei_14133"
        if "8.666" in amparo or "8666" in amparo:
            return "lei_8666"
        if "10.520" in amparo or "10520" in amparo:
            return "lei_10520"
        return "indeterminado"

    def _participantes(
        self, bruto: dict[str, Any], processo_id: int, b: BalancoIngestao
    ) -> None:
        """Registra quem participou, quando o PNCP informa.

        Ausência aqui NÃO é ausência de disputa — pode ser que a consulta não
        traga resultados, ou que o certame ainda esteja aberto. Por isso a R002
        devolve SEM_DADOS quando não encontra participante, em vez de apontar
        licitação com proposta única.
        """
        for chave in ("resultados", "resultadoCompra", "fornecedores"):
            registros = bruto.get(chave)
            if isinstance(registros, list) and registros:
                for r in registros:
                    cnpj = _digitos(str(r.get("niFornecedor") or r.get("cnpj") or ""))
                    if not cnpj:
                        continue
                    ent_id = self._entidade(
                        cnpj,
                        str(r.get("nomeRazaoSocialFornecedor") or r.get("razaoSocial") or ""),
                        b,
                    )
                    papel = (
                        "vencedor"
                        if r.get("situacaoCompraItemResultadoNome")
                        in (None, "Homologado", "Adjudicado")
                        else "licitante"
                    )
                    self.con.execute(
                        "INSERT OR IGNORE INTO participacao"
                        " (processo_id, entidade_id, papel, valor_proposta)"
                        " VALUES (?,?,?,?)",
                        (
                            processo_id,
                            ent_id,
                            papel,
                            r.get("valorTotalHomologado") or r.get("valorUnitarioHomologado"),
                        ),
                    )
                    b.participacoes += 1
                return

    # -- anexos (PDF do edital, termo de referência, etc.) -----------------

    def _ingerir_anexo(
        self, item: ItemColetado, fonte_id: int, coleta_id: int | None, b: BalancoIngestao
    ) -> None:
        contratacao = str(item.metadados.get("contratacao") or "")
        processo_id = None
        vinculo = "heuristica"
        confianca = 0.5

        if contratacao:
            linha = self.con.execute(
                "SELECT p.id FROM processo p"
                "  JOIN processo_documento pd ON pd.processo_id = p.id"
                "  JOIN documento d ON d.id = pd.documento_id"
                " WHERE d.identificador_externo = ? LIMIT 1",
                (contratacao,),
            ).fetchone()
            if linha:
                processo_id = int(linha[0])
                vinculo = "identificador"
                confianca = 1.0

        doc_id, _ = self._documento_e_versao(
            item,
            fonte_id,
            coleta_id,
            orgao_id=None,
            balanco=b,
            tipo=item.tipo_documento,
            titulo=item.titulo,
        )
        if processo_id:
            self._vincular(processo_id, doc_id, item.tipo_documento, vinculo, confianca)

    # -- documento e versão ------------------------------------------------

    def _documento_e_versao(
        self,
        item: ItemColetado,
        fonte_id: int,
        coleta_id: int | None,
        orgao_id: int | None,
        balanco: BalancoIngestao,
        tipo: str,
        titulo: str | None,
    ) -> tuple[int, int]:
        ident = item.identificador_externo or item.url_origem

        linha = self.con.execute(
            "SELECT id FROM documento WHERE fonte_id=? AND identificador_externo=? AND tipo=?",
            (fonte_id, ident, tipo),
        ).fetchone()

        if linha:
            doc_id = int(linha[0])
        else:
            cur = self.con.execute(
                "INSERT INTO documento (municipio_id, orgao_id, fonte_id, tipo, titulo,"
                " numero, exercicio, identificador_externo, url_origem, primeira_coleta)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    self._municipio_id,
                    orgao_id,
                    fonte_id,
                    tipo,
                    titulo,
                    item.numero,
                    item.exercicio,
                    ident,
                    item.url_origem,
                    item.coletado_em.isoformat(),
                ),
            )
            doc_id = int(cur.lastrowid or 0)
            balanco.documentos_novos += 1

        return doc_id, self._versao(doc_id, item, coleta_id, balanco)

    def _versao(
        self, doc_id: int, item: ItemColetado, coleta_id: int | None, balanco: BalancoIngestao
    ) -> int:
        sha = item.sha256
        igual = self.con.execute(
            "SELECT id FROM documento_versao WHERE documento_id=? AND sha256=?",
            (doc_id, sha),
        ).fetchone()
        if igual:
            balanco.ja_conhecidos += 1
            return int(igual[0])

        anterior = self.con.execute(
            "SELECT MAX(versao) FROM documento_versao WHERE documento_id=?", (doc_id,)
        ).fetchone()[0]
        nova = int(anterior or 0) + 1

        # Conteúdo mudou num documento já conhecido: é retificação, e o fato de
        # ter havido retificação importa tanto quanto o novo conteúdo.
        resumo = None
        if anterior:
            resumo = (
                f"conteúdo alterado em relação à versão {anterior}: "
                f"{len(item.conteudo)} bytes coletados em "
                f"{item.coletado_em.date().isoformat()}. "
                "A versão anterior permanece arquivada."
            )

        cur = self.con.execute(
            "INSERT INTO documento_versao (documento_id, versao, sha256, tamanho_bytes,"
            " mime, caminho_arquivo, coletado_em, coleta_id, http_headers,"
            " substitui_versao, diff_resumo) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                doc_id,
                nova,
                sha,
                len(item.conteudo),
                item.http_headers.get("content-type"),
                self._caminho(item),
                item.coletado_em.isoformat(),
                coleta_id,
                json.dumps(dict(item.http_headers), ensure_ascii=False),
                anterior,
                resumo,
            ),
        )
        balanco.versoes_novas += 1
        return int(cur.lastrowid or 0)

    def _caminho(self, item: ItemColetado) -> str:
        return str(
            Path("dados/originais")
            / self.municipio_ibge
            / item.coletado_em.strftime("%Y/%m")
            / f"{item.sha256}{item.extensao}"
        )

    # -- auxiliares --------------------------------------------------------

    def _vincular(
        self, processo_id: int, doc_id: int, papel: str, origem: str, confianca: float
    ) -> None:
        self.con.execute(
            "INSERT OR IGNORE INTO processo_documento"
            " (processo_id, documento_id, papel, vinculo_origem, confianca)"
            " VALUES (?,?,?,?,?)",
            (processo_id, doc_id, papel, origem, confianca),
        )

    def _orgao(self, cnpj: str, nome: str, balanco: BalancoIngestao) -> int | None:
        """Cada CNPJ é um ente que licita sozinho.

        Descobrir um órgão novo é informação: é a Câmara ou um fundo que o
        mapeamento inicial não conhecia, e é entre eles que o fracionamento de
        despesa se dispersa.
        """
        cnpj = _digitos(cnpj)
        if not cnpj:
            return None

        linha = self.con.execute(
            "SELECT id FROM orgao WHERE municipio_id=? AND REPLACE(REPLACE(REPLACE("
            "COALESCE(cnpj,''),'.',''),'/',''),'-','') = ?",
            (self._municipio_id, cnpj),
        ).fetchone()
        if linha:
            return int(linha[0])

        tipo = _classificar_orgao(nome)
        cur = self.con.execute(
            "INSERT INTO orgao (municipio_id, nome, cnpj, tipo) VALUES (?,?,?,?)",
            (self._municipio_id, nome or f"Órgão CNPJ {cnpj}", cnpj, tipo),
        )
        balanco.orgaos_descobertos.append(f"{cnpj} — {nome or '(sem nome)'} [{tipo}]")
        return int(cur.lastrowid or 0)

    def _entidade(self, cnpj: str, razao: str, balanco: BalancoIngestao) -> int:
        linha = self.con.execute(
            "SELECT id FROM entidade WHERE documento_fiscal=?", (cnpj,)
        ).fetchone()
        if linha:
            return int(linha[0])
        cur = self.con.execute(
            "INSERT INTO entidade (tipo, documento_fiscal, razao_social) VALUES (?,?,?)",
            ("pj" if len(cnpj) == 14 else "pf", cnpj, razao or None),
        )
        balanco.entidades_novas += 1
        return int(cur.lastrowid or 0)

    def _fonte_id(self, chave: str) -> int:
        linha = self.con.execute("SELECT id FROM fonte WHERE chave=?", (chave,)).fetchone()
        if linha:
            return int(linha[0])
        cur = self.con.execute(
            "INSERT INTO fonte (municipio_id, chave, nome, url_base, tipo, coletor)"
            " VALUES (?,?,?,?,?,?)",
            (self._municipio_id, chave, chave, "", "api", f"radar.coleta.{chave}"),
        )
        return int(cur.lastrowid or 0)

    @staticmethod
    def _tipo_processo(modalidade: int) -> str:
        return {8: "dispensa", 9: "inexigibilidade", 12: "credenciamento"}.get(
            modalidade, "licitacao"
        )

    @staticmethod
    def _nome_modalidade(codigo: int) -> str:
        return {
            1: "leilao_eletronico",
            2: "dialogo_competitivo",
            3: "concurso",
            4: "concorrencia_eletronica",
            5: "concorrencia_presencial",
            6: "pregao_eletronico",
            7: "pregao_presencial",
            8: "dispensa",
            9: "inexigibilidade",
            10: "manifestacao_interesse",
            11: "pre_qualificacao",
            12: "credenciamento",
        }.get(codigo, "indeterminada")


# -- funções livres ---------------------------------------------------------


def _digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def _iso(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        return None


def _classificar_orgao(nome: str) -> str:
    n = (nome or "").lower()
    if "camara" in n or "câmara" in n:
        return "camara"
    if "fundo" in n:
        return "fundo"
    if "consorcio" in n or "consórcio" in n:
        return "consorcio"
    if "autarquia" in n or "instituto" in n or "servico autonomo" in n:
        return "autarquia"
    return "prefeitura"
