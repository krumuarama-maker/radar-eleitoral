"""R002 — proposta única em modalidade competitiva.

O indicador mais usado e mais robusto da literatura de contratações públicas, e
o mais barato de calcular: basta contar licitantes.

Ele não acusa ninguém. Uma licitação com um só participante pode ter objeto
muito específico, mercado local concentrado, ou simplesmente pouco interesse.
O que ele faz é apontar onde olhar — e, quando o padrão se repete no mesmo
órgão com o mesmo vencedor, aí a série começa a dizer alguma coisa que o caso
isolado não diz.

Por isso a gravidade nasce baixa e sobe conforme o contexto: valor alto e
repetição são o que separam "aconteceu" de "acontece sempre".
"""

from __future__ import annotations

from radar.achados.modelo import (
    Evidencia,
    Ficha,
    ForcaEvidencia,
    Gravidade,
    Origem,
    Urgencia,
)
from radar.analise.deterministico.base import (
    REGISTRO,
    Contexto,
    Regra,
    Resultado,
    ancorar,
)

#: Modalidades em que se espera disputa. Dispensa e inexigibilidade ficam de
#: fora porque nelas a ausência de concorrência é o pressuposto, não o desvio —
#: apontá-las aqui seria ruído garantido.
MODALIDADES_COMPETITIVAS = {
    "pregao_eletronico",
    "pregao_presencial",
    "concorrencia",
    "concorrencia_eletronica",
    "concorrencia_presencial",
    "tomada_de_precos",
    "convite",
    "leilao_eletronico",
    "concurso",
    "dialogo_competitivo",
}

PAPEIS_DE_DISPUTA = {"licitante", "vencedor", "desclassificado", "inabilitado", "desistente"}


def formatar_reais(v: float) -> str:
    """Formata no padrão brasileiro: R$ 1.200.000,00.

    Aplicada só ao número, nunca à frase inteira — trocar os separadores de uma
    string que já contém pontuação corrompe o texto ao redor.
    """
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class R002PropostaUnica(Regra):
    codigo = "R002"
    nome = "Proposta única em modalidade competitiva"
    categoria = "competicao"
    descricao = (
        "Aponta licitação competitiva que recebeu proposta de um único licitante. "
        "Indício de restrição à competitividade, não prova dela."
    )
    severidade_base = Gravidade.BAIXA
    fonte_metodologica = (
        "Open Contracting Partnership — Cardinal R018; indicador padrão em "
        "metodologias de red flags de contratação pública."
    )
    requisitos = ("modalidade",)

    def avaliar(self, ctx: Contexto) -> Resultado:
        modalidade = str(ctx.processo.get("modalidade") or "").lower()
        if modalidade not in MODALIDADES_COMPETITIVAS:
            return Resultado.nao_aplicavel(
                f"modalidade '{modalidade}' não pressupõe disputa entre licitantes; "
                "em dispensa e inexigibilidade a ausência de concorrência é o "
                "pressuposto legal, não o desvio"
            )

        disputantes: set[str] = {
            str(p["documento_fiscal"])
            for p in ctx.participantes
            if p.get("papel") in PAPEIS_DE_DISPUTA and p.get("documento_fiscal")
        }

        if not disputantes:
            # Nenhum participante registrado. Pode ser licitação deserta (achado
            # de outro tipo) ou ata de sessão não coletada. Não dá para saber, e
            # chutar aqui produziria acusação a partir de falha de coleta.
            return Resultado.sem_dados(
                "nenhum participante registrado para este processo — pode ser "
                "licitação deserta ou ata de sessão ainda não coletada; sem a ata "
                "não há como distinguir os dois casos",
                ["participacao"],
            )

        if len(disputantes) > 1:
            return Resultado.limpo()

        evidencias = ancorar(ctx, ("ata_sessao", "ata", "edital"))
        if not evidencias:
            return Resultado.sem_dados(
                "nenhum documento preservado vinculado a este processo — o fato "
                "existe no registro estruturado, mas sem documento arquivado não há "
                "onde ancorar o achado, e achado sem âncora não é apresentável",
                ["documento_versao"],
            )

        return Resultado.achado(self._ficha(ctx, next(iter(disputantes)), evidencias))

    # -- montagem ---------------------------------------------------------

    def _ficha(self, ctx: Contexto, cnpj_unico: str, evidencias: list[Evidencia]) -> Ficha:
        p = ctx.processo
        unico = next(
            (x for x in ctx.participantes if x.get("documento_fiscal") == cnpj_unico), {}
        )
        razao = unico.get("razao_social") or cnpj_unico
        valor = (
            p.get("valor_contratado") or p.get("valor_homologado") or p.get("valor_estimado")
        )

        repeticoes = self._repeticoes(ctx, cnpj_unico)
        gravidade, forca = self._calibrar(valor, repeticoes)

        fatos = [
            f"O processo {p.get('numero')}/{p.get('exercicio')}, modalidade "
            f"{p.get('modalidade')}, registra um único participante: "
            f"{razao} (CNPJ {cnpj_unico}).",
        ]
        if valor:
            fatos.append(f"O valor registrado para o processo é de {formatar_reais(valor)}.")
        if repeticoes:
            fatos.append(
                f"No mesmo exercício, o radar localizou {len(repeticoes)} outro(s) "
                f"processo(s) do mesmo órgão em que {razao} também foi o único "
                f"participante: {', '.join(repeticoes[:5])}."
            )

        hipoteses = [
            "A ausência de concorrentes pode decorrer de exigências do edital que "
            "restringiram o universo de participantes."
        ]
        if repeticoes:
            hipoteses.append(
                "A repetição do padrão no mesmo órgão sugere condição estrutural, "
                "e não coincidência de um certame isolado."
            )

        return Ficha(
            codigo=f"{ctx.municipio_ibge}-{self.codigo}-{p.get('id', '?')}",
            titulo=f"Licitação competitiva com um único participante "
            f"({p.get('numero')}/{p.get('exercicio')})",
            fatos_documentais=fatos,
            hipoteses=hipoteses,
            hipotese_alternativa=(
                "Objeto de mercado naturalmente concentrado, valor pouco atrativo, "
                "localização remota ou prazo de execução apertado explicam proposta "
                "única sem qualquer irregularidade. A comparação com certames "
                "semelhantes de municípios vizinhos é o que separa as hipóteses."
            ),
            lacunas=[
                "Ler as exigências de habilitação e qualificação técnica do edital "
                "para avaliar se restringiram a participação.",
                "Verificar se houve impugnação ou pedido de esclarecimento no certame.",
                "Comparar com licitações do mesmo objeto em municípios da região.",
            ],
            consequencia_possivel=(
                "Sem disputa, o preço contratado não foi testado pelo mercado."
            ),
            evidencias=evidencias,
            gravidade=gravidade,
            forca_evidencia=forca,
            urgencia=Urgencia.ACOMPANHAR,
            origem=Origem.DETERMINISTICA,
            municipio_codigo_ibge=ctx.municipio_ibge,
            regime_aplicavel=ctx.regime,
            processo_id=p.get("id"),
            regra_codigo=self.codigo,
            metadados={"cnpj_unico": cnpj_unico, "repeticoes": repeticoes},
        )

    def _repeticoes(self, ctx: Contexto, cnpj: str) -> list[str]:
        """Outros processos do mesmo órgão com o mesmo participante solitário.

        Depende de o executor ter carregado a série do município; sem ela a
        regra segue funcionando, só sem o agravante.
        """
        outros = ctx.extras.get("contratacoes_do_municipio") or []
        marcados: list[str] = []
        for o in outros:
            if o.get("orgao_id") != ctx.processo.get("orgao_id"):
                continue
            if cnpj in str(o.get("_participantes_unicos") or ""):
                marcados.append(f"{o.get('numero')}/{o.get('exercicio')}")
        return marcados

    def _calibrar(
        self, valor: float | None, repeticoes: list[str]
    ) -> tuple[Gravidade, ForcaEvidencia]:
        """Contar licitantes é exato; interpretar o número, não.

        A contagem sustenta o fato com força total. A gravidade sobe com valor e
        com repetição, porque é a série — não o caso isolado — que indica
        condição estrutural.
        """
        forca = ForcaEvidencia.FORTE  # o número de participantes é conferível
        if repeticoes:
            return Gravidade.MEDIA, forca
        if valor and valor >= 500_000:
            return Gravidade.MEDIA, forca
        return Gravidade.BAIXA, forca


REGRA = REGISTRO.registrar(R002PropostaUnica())
