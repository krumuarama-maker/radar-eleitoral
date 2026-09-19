"""Carregador da base normativa — implementa a regra R4 de AGENTS.md.

Duas garantias, e só elas justificam este módulo existir:

1. **Vigência.** `obter(chave, em=data)` devolve a redação que valia NAQUELA
   data, não a atual. Um contrato de 2021 é julgado pela lei de 2021.

2. **Conferência.** Dispositivo com `conferido.status: pendente` não vira
   `FundamentoNormativo`. `fundamento()` levanta exceção. É a trava que impede
   uma minuta de sair citando artigo que ninguém abriu.

A segunda garantia parece exagerada até a primeira vez que alguém protocola uma
representação citando dispositivo revogado. Aí ela parece barata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from radar.achados.modelo import FundamentoNormativo


class NormaNaoConferida(RuntimeError):
    """Tentou citar dispositivo cujo texto ninguém abriu na fonte oficial."""


class NormaNaoVigente(RuntimeError):
    """O dispositivo existe, mas não valia na data do fato."""


class NormaInexistente(KeyError):
    pass


@dataclass(frozen=True, slots=True)
class Dispositivo:
    chave: str
    diploma: str
    dispositivo: str
    ementa: str
    texto_literal: str
    url_oficial: str
    vigencia_inicio: date
    vigencia_fim: date | None
    conferido: bool
    conferido_por: str | None
    conferido_em: date | None
    parametros: dict[str, Any]
    observacao: str | None
    bloqueia: list[str]

    def vigente_em(self, quando: date) -> bool:
        if quando < self.vigencia_inicio:
            return False
        return self.vigencia_fim is None or quando <= self.vigencia_fim


class BaseNormas:
    """Índice das normas em `normas/`, consultável por chave e por data."""

    def __init__(self, raiz: Path | str = "normas") -> None:
        self.raiz = Path(raiz)
        self._por_chave: dict[str, list[Dispositivo]] = {}
        self._carregar()

    def _carregar(self) -> None:
        for arquivo in sorted(self.raiz.rglob("*.yaml")):
            dados = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
            diploma = dados.get("diploma", arquivo.stem)
            url_diploma = dados.get("url_oficial", "")
            for d in dados.get("dispositivos", []):
                conf = d.get("conferido") or {}
                disp = Dispositivo(
                    chave=d["chave"],
                    diploma=diploma,
                    dispositivo=d.get("dispositivo", ""),
                    ementa=d.get("ementa", ""),
                    texto_literal=(d.get("texto_literal") or "").strip(),
                    url_oficial=d.get("url_oficial") or url_diploma,
                    vigencia_inicio=_data(d["vigencia_inicio"]),
                    vigencia_fim=_data(d.get("vigencia_fim")),
                    conferido=(conf.get("status") == "conferido"),
                    conferido_por=conf.get("por"),
                    conferido_em=_data(conf.get("em")),
                    parametros=d.get("parametros") or {},
                    observacao=d.get("observacao"),
                    bloqueia=d.get("bloqueia") or [],
                )
                self._por_chave.setdefault(disp.chave, []).append(disp)

        # Ordena por vigência para que a busca por data pegue a redação certa.
        for lista in self._por_chave.values():
            lista.sort(key=lambda x: x.vigencia_inicio)

    # -- consulta ----------------------------------------------------------

    def obter(self, chave: str, em: date) -> Dispositivo:
        """A redação vigente naquela data. Não a atual."""
        candidatos = self._por_chave.get(chave)
        if not candidatos:
            raise NormaInexistente(
                f"dispositivo '{chave}' não existe em {self.raiz}/. "
                "Carregue-o antes de qualquer regra depender dele."
            )
        for d in candidatos:
            if d.vigente_em(em):
                return d
        vigencias = ", ".join(
            f"{d.vigencia_inicio}→{d.vigencia_fim or 'hoje'}" for d in candidatos
        )
        raise NormaNaoVigente(
            f"'{chave}' não estava vigente em {em}. Redações conhecidas: {vigencias}. "
            "Verifique se há redação anterior ainda não carregada — aplicar a regra "
            "de hoje a fato de ontem é o erro que a regra R4 existe para impedir."
        )

    def valor(self, chave: str, em: date, parametro: str | None = None) -> Any:
        """Um parâmetro numérico (prazo, limite, percentual) vigente na data.

        Regra de análise nunca guarda esses números. Ela pergunta aqui.
        """
        d = self.obter(chave, em)
        if not d.parametros:
            raise NormaNaoConferida(
                f"'{chave}' não tem parâmetros carregados. "
                + (" ".join(d.bloqueia) if d.bloqueia else
                   "Levante-os na fonte oficial antes de usar a regra que depende deles.")
            )
        if parametro is None:
            if len(d.parametros) != 1:
                raise ValueError(
                    f"'{chave}' tem {len(d.parametros)} parâmetros "
                    f"({', '.join(d.parametros)}); diga qual você quer."
                )
            return next(iter(d.parametros.values()))
        if parametro not in d.parametros:
            raise NormaNaoConferida(
                f"'{chave}' não carrega o parâmetro '{parametro}' na redação "
                f"vigente em {em}. Disponíveis: {', '.join(d.parametros) or 'nenhum'}."
            )
        return d.parametros[parametro]

    def fundamento(self, chave: str, em: date, explicacao: str) -> FundamentoNormativo:
        """Converte em fundamento citável. **Só se conferido.**

        É aqui que a base normativa encosta na peça que vai para fora. Por isso
        é aqui que a trava tem que estar.
        """
        d = self.obter(chave, em)
        if not d.conferido:
            raise NormaNaoConferida(
                f"{d.diploma}, {d.dispositivo} ('{chave}') está com "
                "conferido.status = pendente.\n"
                f"Abra {d.url_oficial}, copie o texto literal para normas/ e marque "
                "como conferido. Até lá este dispositivo não entra em peça alguma."
            )
        if not d.texto_literal:
            raise NormaNaoConferida(
                f"'{chave}' está marcado como conferido mas tem texto_literal vazio. "
                "Uma das duas informações está errada — resolva antes de citar."
            )
        return FundamentoNormativo(
            chave_norma=d.chave,
            diploma=d.diploma,
            dispositivo=d.dispositivo,
            texto_conferido=d.texto_literal,
            url_oficial=d.url_oficial,
            vigencia_inicio=d.vigencia_inicio,
            vigencia_fim=d.vigencia_fim,
            explicacao_aplicacao=explicacao,
        )

    # -- diagnóstico -------------------------------------------------------

    def pendentes(self) -> list[Dispositivo]:
        """O que ainda trava peças. Aparece no painel e em `make cobertura`."""
        return [d for lista in self._por_chave.values() for d in lista if not d.conferido]

    def __len__(self) -> int:
        return sum(len(v) for v in self._por_chave.values())


def _data(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])
