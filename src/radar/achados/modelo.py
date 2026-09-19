"""Ficha de evidência — o contrato central do Radar.

Nenhum achado circula neste sistema fora deste formato. As validações abaixo
implementam, em código, as regras R1 e R2 de AGENTS.md: um achado sem âncora
documental, ou que confunda fato com hipótese, não chega a existir.

A escolha de levantar exceção (em vez de avisar) é deliberada. Um achado mal
formado que vaza para uma minuta endereçada ao Tribunal de Contas custa mais
caro que um processo que quebra.
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, ClassVar


class Gravidade(enum.StrEnum):
    """Quão sério seria o fato SE a hipótese proceder."""

    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    INDETERMINADA = "indeterminada"


class ForcaEvidencia(enum.StrEnum):
    """Quão bem o documento sustenta a afirmação.

    Separada de Gravidade de propósito. Confundir as duas é o erro que
    transforma fiscalização em acusação: "é gravíssimo" não quer dizer
    "está provado".
    """

    FRACA = "fraca"  # um indício, compatível com várias explicações
    MODERADA = "moderada"  # documento sustenta, mas falta contexto
    FORTE = "forte"  # o documento diz literalmente, e é conferível


class Urgencia(enum.StrEnum):
    SEM_PRAZO = "sem_prazo"
    ACOMPANHAR = "acompanhar"
    PRAZO_CORRENDO = "prazo_correndo"  # ex.: edital ainda impugnável
    IMEDIATA = "imediata"


class Origem(enum.StrEnum):
    DETERMINISTICA = "deterministica"
    IA = "ia"
    MISTA = "mista"
    MANUAL = "manual"


class StatusAchado(enum.StrEnum):
    NOVO = "novo"
    EM_REVISAO_ADVERSARIAL = "em_revisao_adversarial"
    AGUARDANDO_REVISAO_HUMANA = "aguardando_revisao_humana"
    APROVADO = "aprovado"
    IMPROCEDENTE = "improcedente"
    ARQUIVADO = "arquivado"
    CORRIGIDO_PELO_MUNICIPIO = "corrigido_pelo_municipio"
    ENCAMINHADO = "encaminhado"


class RegimeJuridico(enum.StrEnum):
    """Qual lei regia o fato. Regra R4: nunca se presume o regime atual."""

    LEI_8666 = "lei_8666"
    LEI_14133 = "lei_14133"
    LEI_10520_PREGAO = "lei_10520"
    RDC_12462 = "rdc_12462"
    LEI_13303_ESTATAIS = "lei_13303"
    INDETERMINADO = "indeterminado"


# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Evidencia:
    """Âncora de um fato em um documento preservado.

    `sha256_versao` é o que permite a alguém, meses depois, pegar o arquivo
    guardado, conferir o hash e ler exatamente o mesmo trecho.
    """

    documento_versao_id: int
    sha256_versao: str
    url_origem: str
    pagina: int | None = None
    trecho: str | None = None
    observacao: str | None = None

    def __post_init__(self) -> None:
        if not self.sha256_versao or len(self.sha256_versao) != 64:
            raise ValueError(
                "Evidencia exige sha256 de 64 caracteres da versão preservada; "
                f"recebido: {self.sha256_versao!r}"
            )
        if not self.url_origem:
            raise ValueError("Evidencia exige url_origem — de onde o documento veio")


@dataclass(frozen=True, slots=True)
class FundamentoNormativo:
    """Dispositivo legal com vigência conferida.

    `texto_conferido` guarda o texto literal que foi efetivamente recuperado de
    `normas/`. Se estiver vazio, o fundamento não entra em minuta — é a trava
    contra citação inventada (AGENTS.md, seção 7).
    """

    chave_norma: str
    diploma: str
    dispositivo: str
    texto_conferido: str
    url_oficial: str
    vigencia_inicio: date
    vigencia_fim: date | None
    explicacao_aplicacao: str

    def __post_init__(self) -> None:
        if not self.texto_conferido.strip():
            raise ValueError(
                f"{self.diploma} {self.dispositivo}: fundamento sem texto conferido não "
                "pode ser usado. Carregue a norma em normas/ antes de citá-la."
            )
        if not self.explicacao_aplicacao.strip():
            raise ValueError(
                "Citar dispositivo sem explicar por que ele se aplica a ESTE fato "
                "não é fundamentação — é decoração."
            )

    def vigente_em(self, quando: date) -> bool:
        if quando < self.vigencia_inicio:
            return False
        return self.vigencia_fim is None or quando <= self.vigencia_fim


@dataclass(slots=True)
class Ficha:
    """A ficha de evidência completa."""

    codigo: str
    titulo: str

    # --- os três campos que a regra R2 obriga a manter separados ---
    fatos_documentais: list[str]
    hipoteses: list[str]
    lacunas: list[str]

    evidencias: list[Evidencia]

    gravidade: Gravidade
    forca_evidencia: ForcaEvidencia
    urgencia: Urgencia
    origem: Origem

    municipio_codigo_ibge: str
    regime_aplicavel: RegimeJuridico = RegimeJuridico.INDETERMINADO

    fundamentos: list[FundamentoNormativo] = field(default_factory=list)
    consequencia_possivel: str | None = None
    hipotese_alternativa: str | None = None

    processo_id: int | None = None
    regra_codigo: str | None = None
    prazo_limite: date | None = None
    status: StatusAchado = StatusAchado.NOVO
    criado_em: datetime = field(default_factory=datetime.now)
    metadados: dict[str, Any] = field(default_factory=dict)

    # -- validação ---------------------------------------------------------

    def __post_init__(self) -> None:
        if not self.evidencias:
            raise ValueError(
                f"[{self.codigo}] Regra R1: achado sem evidência ancorada não existe. "
                "Se você não consegue apontar documento e página, você não tem um achado — "
                "tem uma suspeita, e suspeita se registra em `lacunas`."
            )
        if not self.fatos_documentais:
            raise ValueError(
                f"[{self.codigo}] Regra R2: todo achado precisa de ao menos um fato "
                "documental. Se só há leitura interpretativa, o achado nasce de hipótese "
                "e ainda não é apresentável."
            )
        if not self.lacunas:
            raise ValueError(
                f"[{self.codigo}] Regra R2: `lacunas` vazio é quase sempre sinal de "
                "análise apressada. Se realmente nada falta verificar, escreva isso "
                "explicitamente: ['nenhuma lacuna identificada — ver parecer X']."
            )
        self._validar_fatos_nao_sao_hipoteses()
        self._validar_coerencia_gravidade()

    _MARCAS_DE_HIPOTESE: ClassVar[tuple[str, ...]] = (
        "provavelmente",
        "possivelmente",
        "indica que",
        "sugere que",
        "aparenta",
        "parece",
        "pode ter",
        "teria sido",
        "supostamente",
        "presume-se",
        "tudo leva a crer",
        "é evidente que",
        "claramente houve",
    )

    def _validar_fatos_nao_sao_hipoteses(self) -> None:
        """Impede que interpretação se disfarce de fato.

        Esta checagem é grosseira de propósito: ela não tem como julgar semântica,
        mas pega a forma mais comum do erro, que é o analista escrever
        "o edital provavelmente direcionou a disputa" dentro de `fatos_documentais`.
        """
        for fato in self.fatos_documentais:
            baixo = fato.lower()
            for marca in self._MARCAS_DE_HIPOTESE:
                if marca in baixo:
                    raise ValueError(
                        f"[{self.codigo}] '{marca}' aparece em fatos_documentais: "
                        f"{fato!r}\n"
                        "Fato documental descreve o que está escrito no documento. "
                        "Leitura, inferência e juízo vão em `hipoteses`."
                    )

    def _validar_coerencia_gravidade(self) -> None:
        """Gravidade alta com evidência fraca precisa de hipótese alternativa.

        É exatamente a combinação que produz acusação injusta: o fato parece
        grave, a prova é rala, e ninguém procurou a explicação inocente.
        """
        if (
            self.gravidade is Gravidade.ALTA
            and self.forca_evidencia is ForcaEvidencia.FRACA
            and not self.hipotese_alternativa
        ):
            raise ValueError(
                f"[{self.codigo}] Gravidade alta + evidência fraca exige "
                "`hipotese_alternativa` preenchida pela revisão adversarial. "
                "Um achado nessa faixa é o que mais facilmente vira injustiça."
            )

    # -- utilidades --------------------------------------------------------

    @property
    def apta_a_revisao_humana(self) -> bool:
        """Só passa quem tem fundamento vigente na data do fato."""
        if not self.fundamentos:
            return False
        if self.hipotese_alternativa is None:
            return False
        return all(f.texto_conferido.strip() for f in self.fundamentos)

    def impressao_digital(self) -> str:
        """Identidade estável do achado, para não duplicar entre execuções."""
        base = "|".join(
            [
                self.regra_codigo or "manual",
                str(self.processo_id or ""),
                *sorted(e.sha256_versao for e in self.evidencias),
            ]
        )
        return hashlib.sha256(base.encode()).hexdigest()[:16]

    def para_json(self) -> str:
        def encoder(o: Any) -> Any:
            if isinstance(o, (date, datetime)):
                return o.isoformat()
            if isinstance(o, enum.Enum):
                return o.value
            raise TypeError(type(o))

        return json.dumps(asdict(self), ensure_ascii=False, indent=2, default=encoder)

    def resumo_humano(self) -> str:
        """Texto curto para o painel — nunca para envio externo."""
        linhas = [
            f"## {self.codigo} — {self.titulo}",
            f"gravidade: {self.gravidade} · evidência: {self.forca_evidencia} "
            f"· urgência: {self.urgencia} · regime: {self.regime_aplicavel}",
            "",
            "**Fatos documentais**",
            *(f"- {f}" for f in self.fatos_documentais),
        ]
        if self.hipoteses:
            linhas += [
                "",
                "**Hipóteses (leitura, não fato)**",
                *(f"- {h}" for h in self.hipoteses),
            ]
        if self.hipotese_alternativa:
            linhas += [
                "",
                "**Explicação alternativa considerada**",
                f"- {self.hipotese_alternativa}",
            ]
        linhas += ["", "**Lacunas**", *(f"- {lac}" for lac in self.lacunas)]
        linhas += ["", "**Evidências**"]
        for e in self.evidencias:
            pag = f", p. {e.pagina}" if e.pagina else ""
            linhas.append(f"- doc {e.sha256_versao[:12]}…{pag} — {e.url_origem}")
        if self.fundamentos:
            linhas += ["", "**Fundamento**"]
            for f in self.fundamentos:
                linhas.append(f"- {f.diploma}, {f.dispositivo}: {f.explicacao_aplicacao}")
        return "\n".join(linhas)
