"""R003 — fracionamento de despesa entre órgãos do município.

A regra mais valiosa de um radar municipal, e a que quase nenhum painel oficial
implementa, porque exige olhar o município inteiro e não um CNPJ de cada vez.

O fracionamento clássico não se esconde dentro da Prefeitura. Ele se esconde
**entre os entes**: três compras do mesmo objeto, no mesmo trimestre, uma pela
Prefeitura, uma pelo Fundo Municipal de Saúde e uma pela Câmara, cada uma
confortavelmente abaixo do limite de dispensa. Isoladas, todas regulares.
Somadas, uma licitação que deveria ter acontecido e não aconteceu.

Três cuidados que separam este apontamento de uma acusação temerária:

1. **O limite vem de `normas/`, com a vigência da data do fato.** Ele foi
   atualizado por decreto mais de uma vez desde 2021. Enquanto o valor não for
   conferido na fonte oficial, a regra devolve SEM_DADOS em vez de chutar.
2. **A semelhança de objeto é explicável.** Nada de escore opaco: a regra usa
   sobreposição de termos significativos, declara o limiar e **lista na ficha
   quais processos ela juntou e por quê**. Quem revisa precisa poder discordar
   do agrupamento.
3. **Objeto parecido não é objeto idêntico.** "Medicamentos" e "material médico
   hospitalar" se parecem e são mercados distintos. Por isso a força da
   evidência nunca passa de moderada quando o agrupamento é heurístico.
"""

from __future__ import annotations

import re
import unicodedata
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
from radar.analise.deterministico.base import (
    REGISTRO,
    Contexto,
    Regra,
    Resultado,
    ancorar,
)
from radar.analise.normas import NormaInexistente, NormaNaoConferida, NormaNaoVigente

#: Palavras sem poder discriminante em objeto de licitação. Sem removê-las,
#: "aquisição de material" casa com "aquisição de serviços" e a regra vira ruído.
VAZIAS = {
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "para",
    "com",
    "em",
    "a",
    "o",
    "as",
    "os",
    "por",
    "ao",
    "aos",
    "na",
    "no",
    "nas",
    "nos",
    "um",
    "uma",
    "que",
    "sob",
    "aquisicao",
    "contratacao",
    "prestacao",
    "fornecimento",
    "servico",
    "servicos",
    "empresa",
    "eventual",
    "futura",
    "destinado",
    "destinados",
    "atender",
    "necessidades",
    "municipio",
    "municipal",
    "secretaria",
    "fundo",
    "diversos",
    "diversas",
    "objeto",
    "referente",
    "conforme",
    "demanda",
    "uso",
    "visando",
}

#: Fração de termos significativos em comum para considerar o mesmo objeto.
#: Valor conservador de propósito: é melhor deixar passar um fracionamento real
#: do que juntar dois objetos distintos e acusar alguém por engano.
LIMIAR_SEMELHANCA = 0.6

#: Objetos contratados com meses de distância não caracterizam a mesma despesa
#: fracionada. A janela é declarada aqui, e não escondida na consulta, porque
#: ela é uma escolha metodológica que quem revisa precisa poder contestar.
#: CONFERIR: a janela que a CGU adota na sua trilha ainda não foi levantada.
JANELA_DIAS = 180


class R003Fracionamento(Regra):
    codigo = "R003"
    nome = "Indício de fracionamento de despesa entre órgãos do município"
    categoria = "fracionamento"
    descricao = (
        "Soma contratações diretas de objeto semelhante feitas por quaisquer órgãos "
        "do mesmo município dentro de uma janela de tempo, e compara com o limite "
        "de dispensa vigente na data."
    )
    severidade_base = Gravidade.MEDIA
    fonte_metodologica = (
        "Trilha de auditoria de contratações diretas (CGU); catálogo FRAC-01 a "
        "FRAC-04 em config/catalogo-verificacoes.yaml."
    )
    requisitos = ("tipo",)

    #: Qual limite consultar, conforme a natureza do objeto.
    CHAVE_OBRAS = "lei_14133_art_75_limite_dispensa_obras"
    CHAVE_COMPRAS = "lei_14133_art_75_limite_dispensa_compras"

    def avaliar(self, ctx: Contexto) -> Resultado:
        if str(ctx.processo.get("tipo") or "").lower() != "dispensa":
            return Resultado.nao_aplicavel(
                f"regra vale para contratação direta por dispensa; este processo é "
                f"'{ctx.processo.get('tipo')}'"
            )

        data_ref = ctx.data_referencia
        if data_ref is None:
            return Resultado.sem_dados(
                "processo sem data — o limite de dispensa mudou por decreto mais de "
                "uma vez, e sem a data não há como saber qual valia",
                ["data_publicacao", "data_assinatura"],
            )

        chave = self._chave_limite(ctx)
        try:
            limite = float(ctx.normas.valor(chave, data_ref))
        except (NormaNaoConferida, NormaNaoVigente, NormaInexistente, TypeError) as exc:
            return Resultado.sem_dados(
                f"limite de dispensa indisponível para {data_ref}: {exc}",
                [chave],
            )

        irmaos = self._agrupar(ctx, data_ref)
        valor_proprio = _num(
            ctx.processo.get("valor_contratado") or ctx.processo.get("valor_estimado")
        )
        soma = valor_proprio + sum(_num(o.get("_valor")) for o in irmaos)

        if not irmaos:
            return Resultado.limpo()
        if soma <= limite:
            return Resultado.limpo()

        evidencias = ancorar(ctx)
        if not evidencias:
            return Resultado.sem_dados(
                "nenhum documento preservado vinculado a este processo — a soma "
                "acima do limite existe no registro estruturado, mas sem documento "
                "arquivado o apontamento não tem onde se ancorar",
                ["documento_versao"],
            )

        return Resultado.achado(
            self._ficha(ctx, irmaos, valor_proprio, soma, limite, data_ref, chave, evidencias)
        )

    # -- agrupamento ------------------------------------------------------

    def _chave_limite(self, ctx: Contexto) -> str:
        objeto = normalizar(str(ctx.processo.get("objeto") or ""))
        engenharia = {
            "obra",
            "obras",
            "engenharia",
            "pavimentacao",
            "construcao",
            "reforma",
            "ampliacao",
            "drenagem",
            "recapeamento",
        }
        return self.CHAVE_OBRAS if engenharia & set(objeto.split()) else self.CHAVE_COMPRAS

    def _agrupar(self, ctx: Contexto, data_ref: date) -> list[dict[str, Any]]:
        """Demais dispensas de objeto semelhante, de QUALQUER órgão do município."""
        meu_objeto = termos(str(ctx.processo.get("objeto") or ""))
        if not meu_objeto:
            return []

        encontrados: list[dict[str, Any]] = []
        for outro in ctx.extras.get("contratacoes_do_municipio") or []:
            if str(outro.get("tipo") or "").lower() != "dispensa":
                continue
            data_outro = _data(outro.get("data_publicacao"))
            if data_outro is None or abs((data_outro - data_ref).days) > JANELA_DIAS:
                continue
            sem = semelhanca(meu_objeto, termos(str(outro.get("objeto") or "")))
            if sem < LIMIAR_SEMELHANCA:
                continue
            encontrados.append(
                {
                    **outro,
                    "_semelhanca": round(sem, 2),
                    "_valor": outro.get("valor_contratado") or outro.get("valor_estimado"),
                }
            )
        return sorted(encontrados, key=lambda x: -float(x["_semelhanca"]))

    # -- ficha ------------------------------------------------------------

    def _ficha(
        self,
        ctx: Contexto,
        irmaos: list[dict[str, Any]],
        valor_proprio: float,
        soma: float,
        limite: float,
        data_ref: date,
        chave_norma: str,
        evidencias: list[Evidencia],
    ) -> Ficha:
        p = ctx.processo
        orgaos = {str(o.get("orgao_nome") or o.get("orgao_id")) for o in irmaos}
        orgaos.add(str(p.get("orgao_nome") or p.get("orgao_id")))
        entre_orgaos = len(orgaos) > 1

        fatos = [
            f"O processo {p.get('numero')}/{p.get('exercicio')}, dispensa de licitação "
            f"publicada em {data_ref.isoformat()}, tem objeto "
            f'"{str(p.get("objeto") or "")[:120]}" e valor de {reais(valor_proprio)}.',
            f"No mesmo município, dentro de {JANELA_DIAS} dias, o radar localizou "
            f"{len(irmaos)} outra(s) dispensa(s) de objeto semelhante:",
        ]
        for o in irmaos[:10]:
            fatos.append(
                f"  · {o.get('numero')}/{o.get('exercicio')} — "
                f"{o.get('orgao_nome') or 'órgão não identificado'} — "
                f"{reais(_num(o.get('_valor')))} — "
                f'"{str(o.get("objeto") or "")[:90]}" '
                f"(sobreposição de termos: {o['_semelhanca']})"
            )
        fatos.append(
            f"A soma dos valores é {reais(soma)}, contra limite de dispensa de "
            f"{reais(limite)} aplicável em {data_ref.isoformat()}."
        )

        hipoteses = [
            "As contratações podem constituir uma única despesa, dividida em parcelas "
            "que individualmente dispensam licitação."
        ]
        if entre_orgaos:
            hipoteses.append(
                f"As contratações foram feitas por {len(orgaos)} órgãos distintos do "
                "mesmo município, o que dispersa a despesa entre CNPJs diferentes e a "
                "torna invisível a quem consolida apenas um deles."
            )

        return Ficha(
            codigo=f"{ctx.municipio_ibge}-{self.codigo}-{p.get('id', '?')}",
            titulo=(
                "Dispensas de objeto semelhante somam acima do limite"
                + (" (entre órgãos distintos do município)" if entre_orgaos else "")
            ),
            fatos_documentais=fatos,
            hipoteses=hipoteses,
            hipotese_alternativa=(
                "Objetos que o agrupamento tratou como semelhantes podem ser "
                "mercados distintos — 'medicamentos' e 'material médico hospitalar' "
                "compartilham termos e não se substituem. Demandas imprevisíveis "
                "surgidas em momentos diferentes também justificam contratações "
                "separadas. E órgãos com autonomia orçamentária própria não estão, "
                "por si, obrigados a licitar em conjunto. Conferir objeto a objeto "
                "antes de qualquer encaminhamento."
            ),
            lacunas=[
                "Conferir, item a item, se os objetos agrupados são efetivamente o "
                "mesmo objeto — o agrupamento aqui é por semelhança de termos, "
                f"com limiar de {LIMIAR_SEMELHANCA}.",
                "Verificar a justificativa de cada dispensa nos respectivos processos.",
                f"Confirmar que o limite de {reais(limite)} era o vigente em "
                f"{data_ref.isoformat()} — o valor é atualizado por decreto.",
                f"A janela de {JANELA_DIAS} dias é escolha metodológica deste radar; "
                "a janela adotada pelos órgãos de controle ainda não foi levantada.",
            ],
            consequencia_possivel=(
                "Se as contratações constituem uma única despesa, a licitação que "
                "deveria ter ocorrido não ocorreu, e a disputa de preços não aconteceu."
            ),
            evidencias=evidencias,
            gravidade=Gravidade.ALTA if entre_orgaos and soma > limite * 2 else Gravidade.MEDIA,
            # Nunca acima de moderada: o agrupamento é heurístico, e é honesto
            # dizer isso na própria ficha em vez de deixar quem revisa descobrir.
            forca_evidencia=ForcaEvidencia.MODERADA,
            urgencia=Urgencia.ACOMPANHAR,
            origem=Origem.DETERMINISTICA,
            municipio_codigo_ibge=ctx.municipio_ibge,
            regime_aplicavel=ctx.regime,
            processo_id=p.get("id"),
            regra_codigo=self.codigo,
            metadados={
                "soma": soma,
                "limite": limite,
                "chave_norma": chave_norma,
                "processos_agrupados": [o.get("numero") for o in irmaos],
                "orgaos_envolvidos": sorted(orgaos),
                "limiar_semelhanca": LIMIAR_SEMELHANCA,
                "janela_dias": JANELA_DIAS,
            },
        )


# -- auxiliares -------------------------------------------------------------


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento, sem pontuação."""
    sem_acento = "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9\s]", " ", sem_acento)


def termos(texto: str) -> set[str]:
    """Termos significativos do objeto, sem as palavras de praxe."""
    return {
        t
        for t in normalizar(texto).split()
        if len(t) > 2 and t not in VAZIAS and not t.isdigit()
    }


def semelhanca(a: set[str], b: set[str]) -> float:
    """Sobreposição de termos, medida sobre o conjunto menor.

    Escolha deliberada sobre Jaccard: um objeto descrito em três palavras e
    outro descrito em trinta podem ser a mesma compra, e Jaccard os separaria
    só pela diferença de verbosidade — comum entre órgãos que redigem de
    formas diferentes.
    """
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def reais(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _num(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _data(v: Any) -> date | None:
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


REGRA = REGISTRO.registrar(R003Fracionamento())
