"""R001 — contratação de empresa com sanção vigente impeditiva.

A melhor razão entre sinal e esforço de todo o catálogo. Não depende de
interpretação, de perícia nem de leitura de cláusula: ou o CNPJ do contratado
está num cadastro oficial de sanção com vigência abrangendo a data do ato, ou
não está. Um join.

Por isso mesmo é a primeira regra a implementar num radar novo: entrega achado
verificável na primeira semana e calibra o pipeline inteiro.

Cuidado que a regra embute, e que separa achado bom de vexame:

1. **Nem toda sanção impede contratar.** Advertência e multa não impedem.
   Impedem: suspensão, impedimento e declaração de inidoneidade — e cada uma com
   alcance diferente (órgão, ente federativo, toda a Administração). A regra
   trata alcance como campo de dados, não como suposição.
2. **A sanção tem que estar vigente NA DATA DO ATO**, não hoje. Empresa
   sancionada depois de assinar o contrato não cometeu irregularidade ao assinar.
3. **Filial e matriz têm CNPJ diferente**, e o alcance da sanção sobre as demais
   unidades da mesma raiz é questão controvertida. A regra aponta o fato
   (coincidência de raiz) e marca a evidência como moderada, deixando a
   qualificação jurídica para quem revisa.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from radar.achados.modelo import (
    Evidencia,
    Ficha,
    ForcaEvidencia,
    Gravidade,
    Origem,
    Urgencia,
)
from radar.analise.deterministico.base import REGISTRO, Contexto, Regra, Resultado

#: Sanções que impedem participar de licitação ou contratar. Advertência e multa
#: ficam de fora: são punitivas, não impeditivas. Confundi-las gera apontamento
#: que a Procuradoria derruba na primeira linha da resposta.
TIPOS_IMPEDITIVOS = {
    "suspensao_temporaria",
    "impedimento_de_licitar",
    "declaracao_de_inidoneidade",
    "proibicao_de_contratar",
}

CADASTROS = {
    "ceis": "Cadastro de Empresas Inidôneas e Suspensas (CGU)",
    "cnep": "Cadastro Nacional de Empresas Punidas (CGU)",
    "cepim": "Cadastro de Entidades Privadas Sem Fins Lucrativos Impedidas (CGU)",
    "tce_pr": "Cadastro de sancionados do TCE-PR",
}


class R001ContratadoSancionado(Regra):
    codigo = "R001"
    nome = "Contratação de empresa com sanção impeditiva vigente"
    categoria = "integridade"
    descricao = (
        "Verifica se algum contratado ou vencedor tinha, na data do ato, sanção "
        "vigente que impedisse licitar ou contratar com a Administração."
    )
    severidade_base = Gravidade.ALTA
    fonte_metodologica = (
        "CGU — Banco de Sanções (CEIS/CNEP/CEPIM); trilha padrão de auditoria de "
        "contratações, presente nos manuais de fiscalização de tribunais de contas."
    )
    requisitos = ()  # a data vem de data_referencia, com tratamento próprio

    def avaliar(self, ctx: Contexto) -> Resultado:
        data_ato = ctx.data_referencia
        if data_ato is None:
            return Resultado.sem_dados(
                "processo sem data de publicação, abertura ou assinatura — sem data "
                "não há como saber se a sanção estava vigente no momento do ato",
                ["data_publicacao", "data_abertura", "data_assinatura"],
            )

        vencedores = [
            p for p in ctx.participantes if p.get("papel") in ("vencedor", "contratado")
        ]
        if not vencedores:
            return Resultado.nao_aplicavel(
                "processo sem vencedor ou contratado registrado — nada a checar "
                "(pode ser licitação ainda em curso, deserta ou fracassada)"
            )

        sancoes_disponiveis = ctx.extras.get("sancoes")
        if sancoes_disponiveis is None:
            # Diferença que importa: não é "empresa limpa", é "não olhei".
            return Resultado.sem_dados(
                "base de sanções não carregada nesta execução; sem ela a regra "
                "não pode afirmar ausência de sanção",
                ["sancoes"],
            )

        fichas: list[Ficha] = []
        for venc in vencedores:
            for sancao in self._sancoes_aplicaveis(venc, sancoes_disponiveis, data_ato):
                fichas.append(self._montar_ficha(ctx, venc, sancao, data_ato))

        return Resultado.achado(*fichas) if fichas else Resultado.limpo()

    # -- núcleo -----------------------------------------------------------

    def _sancoes_aplicaveis(
        self, participante: dict[str, Any], sancoes: list[dict[str, Any]], data_ato: date
    ) -> list[dict[str, Any]]:
        cnpj = so_digitos(participante.get("documento_fiscal", ""))
        if len(cnpj) != 14:
            return []
        raiz = cnpj[:8]

        aplicaveis: list[dict[str, Any]] = []
        for s in sancoes:
            if s.get("tipo") not in TIPOS_IMPEDITIVOS:
                continue
            if not vigente_em(s, data_ato):
                continue
            alvo = so_digitos(s.get("documento_fiscal", ""))
            if alvo == cnpj:
                aplicaveis.append({**s, "_coincidencia": "cnpj_exato"})
            elif alvo[:8] == raiz:
                # Mesma raiz, unidade diferente. Fato relevante, qualificação
                # jurídica controvertida — evidência entra como moderada.
                aplicaveis.append({**s, "_coincidencia": "mesma_raiz_cnpj"})
        return aplicaveis

    def _montar_ficha(
        self, ctx: Contexto, venc: dict[str, Any], sancao: dict[str, Any], data_ato: date
    ) -> Ficha:
        exato = sancao["_coincidencia"] == "cnpj_exato"
        cadastro = CADASTROS.get(sancao.get("cadastro", ""), sancao.get("cadastro", "?"))
        razao = venc.get("razao_social") or venc.get("documento_fiscal")

        fatos = [
            f"{razao} (CNPJ {venc.get('documento_fiscal')}) consta como "
            f"{venc.get('papel')} no processo {ctx.processo.get('numero')}, "
            f"com data de referência {data_ato.isoformat()}.",
            f"O {cadastro} registra, para o CNPJ {sancao.get('documento_fiscal')}, "
            f"sanção do tipo '{sancao.get('tipo')}' aplicada por "
            f"{sancao.get('orgao_sancionador', 'órgão não informado')}, "
            f"com vigência de {sancao.get('data_inicio')} a "
            f"{sancao.get('data_fim') or 'sem termo final informado'}.",
        ]

        if exato:
            hipoteses = [
                "A empresa pode ter sido contratada apesar de sanção que impedia "
                "sua participação na data do ato."
            ]
            alternativa = (
                "O alcance da sanção pode estar restrito ao órgão ou ao ente que a "
                "aplicou, não alcançando este município; e o cadastro pode registrar "
                "com atraso decisão judicial que suspendeu seus efeitos. Ambas as "
                "hipóteses precisam ser descartadas antes de qualquer encaminhamento."
            )
            forca = ForcaEvidencia.FORTE
        else:
            hipoteses = [
                "Há coincidência de raiz de CNPJ entre o contratado e empresa "
                "sancionada, o que sugere pertencerem ao mesmo grupo econômico."
            ]
            alternativa = (
                "Matriz e filial têm personalidades e CNPJs distintos, e a extensão "
                "da sanção às demais unidades é questão jurídica controvertida. "
                "A coincidência de raiz, isolada, não demonstra impedimento."
            )
            forca = ForcaEvidencia.MODERADA

        return Ficha(
            codigo=f"{ctx.municipio_ibge}-{self.codigo}-{ctx.processo.get('id', '?')}-"
            f"{so_digitos(venc.get('documento_fiscal', ''))[:8]}",
            titulo=(
                f"Contratado com registro de sanção impeditiva vigente em {cadastro}"
                if exato
                else "Contratado com raiz de CNPJ coincidente com empresa sancionada"
            ),
            fatos_documentais=fatos,
            hipoteses=hipoteses,
            hipotese_alternativa=alternativa,
            lacunas=[
                "Confirmar o alcance territorial e subjetivo da sanção "
                "(órgão, ente federativo ou toda a Administração Pública).",
                "Verificar se havia decisão judicial suspendendo os efeitos da "
                "sanção na data do ato.",
                f"Confirmar a situação do cadastro na data de {data_ato.isoformat()}, "
                "e não apenas na data da coleta.",
            ],
            consequencia_possivel=(
                "Se a sanção alcançava este município, a contratação foi firmada com "
                "empresa impedida, o que compromete a validade do ato."
            ),
            evidencias=[
                Evidencia(
                    documento_versao_id=int(sancao.get("documento_versao_id", 0)),
                    sha256_versao=str(sancao.get("sha256", "0" * 64)),
                    url_origem=str(sancao.get("fonte_url", "")),
                    observacao=f"registro de sanção coletado em {sancao.get('coletado_em')}",
                )
            ],
            gravidade=Gravidade.ALTA if exato else Gravidade.MEDIA,
            forca_evidencia=forca,
            urgencia=Urgencia.ACOMPANHAR,
            origem=Origem.DETERMINISTICA,
            municipio_codigo_ibge=ctx.municipio_ibge,
            regime_aplicavel=ctx.regime,
            processo_id=ctx.processo.get("id"),
            regra_codigo=self.codigo,
        )


# -- auxiliares -------------------------------------------------------------


def so_digitos(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


def vigente_em(sancao: dict[str, Any], quando: date) -> bool:
    """A sanção alcançava a data do ato?

    Sanção sem data de início é tratada como NÃO vigente: é dado incompleto, e
    presumir vigência a favor da acusação é exatamente o viés que este projeto
    combate.
    """

    def d(v: Any) -> date | None:
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v)[:10])
        except (ValueError, TypeError):
            return None

    inicio = d(sancao.get("data_inicio"))
    if inicio is None or quando < inicio:
        return False
    fim = d(sancao.get("data_fim"))
    return fim is None or quando <= fim


REGRA = REGISTRO.registrar(R001ContratadoSancionado())
