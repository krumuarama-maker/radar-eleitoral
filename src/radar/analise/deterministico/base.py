"""Motor de verificações determinísticas.

Uma verificação determinística é aquela cuja resposta se calcula: soma, data,
prazo, contagem, cruzamento de identificador. Ela não pergunta a um modelo o que
sabe fazer sozinha, e o resultado é sempre o mesmo para a mesma entrada.

O desenho central aqui é o tipo de retorno. Uma regra devolve UM de quatro
estados, nunca `None`:

    ACHADO         — encontrou, e traz a ficha
    LIMPO          — rodou e não encontrou nada
    NAO_APLICAVEL  — não deveria rodar neste caso (e diz por quê)
    SEM_DADOS      — deveria rodar, mas falta insumo (e diz o que falta)

A diferença entre LIMPO e SEM_DADOS é a diferença entre "está correto" e
"não fui capaz de olhar". Sistemas de fiscalização que colapsam esses dois
estados mentem para o usuário — e é essa mentira que faz alguém protocolar uma
denúncia dizendo que um documento não foi publicado quando, na verdade, o
raspador é que não soube achá-lo.
"""

from __future__ import annotations

import abc
import enum
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from radar.achados.modelo import Ficha, Gravidade, RegimeJuridico


class Desfecho(enum.StrEnum):
    ACHADO = "achado"
    LIMPO = "limpo"
    NAO_APLICAVEL = "nao_aplicavel"
    SEM_DADOS = "sem_dados"
    ERRO = "erro"


@dataclass(slots=True)
class Resultado:
    desfecho: Desfecho
    fichas: list[Ficha] = field(default_factory=list)
    motivo: str = ""
    dados_faltantes: list[str] = field(default_factory=list)
    duracao_ms: int = 0

    def __post_init__(self) -> None:
        if self.desfecho is Desfecho.ACHADO and not self.fichas:
            raise ValueError("Desfecho ACHADO sem ficha anexada")
        if self.desfecho in (Desfecho.NAO_APLICAVEL, Desfecho.SEM_DADOS) and not self.motivo:
            raise ValueError(
                f"Desfecho {self.desfecho} exige motivo explícito. "
                "'Não rodou' sem explicação é buraco de cobertura invisível."
            )

    # atalhos de construção
    @classmethod
    def achado(cls, *fichas: Ficha) -> Resultado:
        return cls(Desfecho.ACHADO, list(fichas))

    @classmethod
    def limpo(cls) -> Resultado:
        return cls(Desfecho.LIMPO)

    @classmethod
    def nao_aplicavel(cls, motivo: str) -> Resultado:
        return cls(Desfecho.NAO_APLICAVEL, motivo=motivo)

    @classmethod
    def sem_dados(cls, motivo: str, faltantes: Sequence[str] = ()) -> Resultado:
        return cls(Desfecho.SEM_DADOS, motivo=motivo, dados_faltantes=list(faltantes))


class BaseNormativa(Protocol):
    """Acesso à norma vigente numa data — regra R4 de AGENTS.md.

    Regra jamais lê limite legal de constante no código. Ela pergunta à base
    normativa qual era o valor NAQUELA data. O limite de dispensa mudou várias
    vezes por decreto de atualização; um contrato de 2022 julgado pelo limite de
    2026 gera apontamento falso que a Prefeitura derruba em uma linha.
    """

    def obter(self, chave: str, em: date) -> Any: ...
    def valor(self, chave: str, em: date) -> float | None: ...


@dataclass(slots=True)
class Contexto:
    """Tudo que uma regra pode consultar.

    `processo` e `documentos` são dicionários simples vindos do banco, de
    propósito: a regra deve ser testável com um dict literal em fixture, sem
    subir banco nenhum.
    """

    processo: dict[str, Any]
    documentos: list[dict[str, Any]]
    participantes: list[dict[str, Any]]
    normas: BaseNormativa
    municipio_ibge: str
    extras: dict[str, Any] = field(default_factory=dict)

    @property
    def regime(self) -> RegimeJuridico:
        bruto = self.processo.get("regime_juridico")
        try:
            return RegimeJuridico(bruto) if bruto else RegimeJuridico.INDETERMINADO
        except ValueError:
            return RegimeJuridico.INDETERMINADO

    @property
    def data_referencia(self) -> date | None:
        """Data que define qual norma se aplica.

        Prioriza a publicação do edital: é o marco que fixa o regime jurídico da
        contratação. Sem ela, a regra que depende de norma deve devolver SEM_DADOS.
        """
        for campo in ("data_publicacao", "data_abertura", "data_assinatura"):
            if bruto := self.processo.get(campo):
                if isinstance(bruto, date):
                    return bruto
                try:
                    return date.fromisoformat(str(bruto)[:10])
                except ValueError:
                    continue
        return None

    def documentos_por_papel(self, papel: str) -> list[dict[str, Any]]:
        return [d for d in self.documentos if d.get("papel") == papel]


class Regra(abc.ABC):
    """Uma verificação. Um arquivo, uma regra, um teste."""

    codigo: str  # 'R001'
    nome: str
    categoria: str  # licitacao|contrato|pagamento|engenharia|...
    descricao: str
    severidade_base: Gravidade = Gravidade.MEDIA
    versao: str = "1.0.0"
    #: De onde veio a trilha de auditoria (TCU, CGU, OCDE, TCE-PR...). Importa:
    #: um achado lastreado em metodologia publicada de órgão de controle é bem
    #: mais difícil de descartar como implicância pessoal.
    fonte_metodologica: str = ""
    #: Regimes em que a regra faz sentido. Vazio = todos.
    regimes_aplicaveis: tuple[RegimeJuridico, ...] = ()
    #: Campos do processo sem os quais a regra não roda.
    requisitos: tuple[str, ...] = ()

    @abc.abstractmethod
    def avaliar(self, ctx: Contexto) -> Resultado:
        """Implementação da verificação."""

    # -- execução com as travas comuns ------------------------------------

    def executar(self, ctx: Contexto) -> Resultado:
        inicio = time.monotonic()
        try:
            if self.regimes_aplicaveis and ctx.regime not in self.regimes_aplicaveis:
                r = Resultado.nao_aplicavel(
                    f"regra vale para {[x.value for x in self.regimes_aplicaveis]}; "
                    f"processo está sob {ctx.regime.value}"
                )
            elif faltam := [c for c in self.requisitos if not ctx.processo.get(c)]:
                r = Resultado.sem_dados(
                    f"faltam campos obrigatórios no processo: {', '.join(faltam)}",
                    faltam,
                )
            else:
                r = self.avaliar(ctx)
        except Exception as exc:
            r = Resultado(Desfecho.ERRO, motivo=f"{type(exc).__name__}: {exc}")
        r.duracao_ms = int((time.monotonic() - inicio) * 1000)
        return r


class RegistroRegras:
    """Catálogo das regras conhecidas."""

    def __init__(self) -> None:
        self._regras: dict[str, Regra] = {}

    def registrar(self, regra: Regra) -> Regra:
        if regra.codigo in self._regras:
            raise ValueError(f"código de regra duplicado: {regra.codigo}")
        self._regras[regra.codigo] = regra
        return regra

    def __iter__(self) -> Iterator[Regra]:
        return iter(sorted(self._regras.values(), key=lambda r: r.codigo))

    def __len__(self) -> int:
        return len(self._regras)

    def por_categoria(self, categoria: str) -> list[Regra]:
        return [r for r in self if r.categoria == categoria]

    def obter(self, codigo: str) -> Regra:
        return self._regras[codigo]


REGISTRO = RegistroRegras()
