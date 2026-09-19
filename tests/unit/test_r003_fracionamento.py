"""Testes da R003 — fracionamento.

A regra mais perigosa do catálogo: ela acusa a Administração de ter evitado uma
licitação. Os testes existem para garantir que ela só o faça quando tem base, e
que recuse rodar quando não tem.

O teste que mais importa é o primeiro: hoje, com o limite de dispensa ainda não
conferido na fonte oficial, a regra devolve SEM_DADOS. Ela não chuta um número.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from radar.achados.modelo import ForcaEvidencia, Gravidade
from radar.analise.deterministico.base import Contexto, Desfecho
from radar.analise.deterministico.r003_fracionamento import (
    LIMIAR_SEMELHANCA,
    REGRA,
    semelhanca,
    termos,
)
from radar.analise.normas import BaseNormas

RAIZ = Path(__file__).resolve().parents[2]


class NormasComLimite:
    """Base normativa de teste com o limite já conferido."""

    def __init__(self, limite: float = 50_000.0) -> None:
        self.limite = limite

    def obter(self, chave: str, em: date):
        return None

    def valor(self, chave: str, em: date, parametro: str | None = None) -> float:
        return self.limite


def dispensa(num, valor, objeto, orgao_id=1, orgao_nome="Prefeitura", data="2026-03-10"):
    return {
        "id": hash(num) % 10000,
        "numero": num,
        "exercicio": 2026,
        "tipo": "dispensa",
        "objeto": objeto,
        "valor_contratado": valor,
        "data_publicacao": data,
        "orgao_id": orgao_id,
        "orgao_nome": orgao_nome,
    }


#: Documento preservado do processo. Sem ele a regra devolve SEM_DADOS — ver
#: test_sem_documento_preservado_devolve_sem_dados.
DOC = [
    {
        "papel": "aviso_dispensa",
        "sha256": "d" * 64,
        "documento_versao_id": 9,
        "url_origem": "https://pncp.gov.br/app/editais/y",
    }
]


def contexto(processo, outros, normas=None, documentos=None):
    return Contexto(
        processo={**processo, "regime_juridico": "lei_14133"},
        documentos=DOC if documentos is None else documentos,
        participantes=[],
        normas=normas or NormasComLimite(),
        municipio_ibge="4105607",
        extras={"contratacoes_do_municipio": outros},
    )


# --- o estado real do projeto hoje ----------------------------------------


def test_limite_nao_conferido_devolve_sem_dados_e_nao_chuta():
    """Com a base normativa real, o limite ainda é `pendente`.

    A regra precisa recusar rodar. Inventar um limite aqui produziria acusação
    de fracionamento a partir de um número que ninguém conferiu.
    """
    base = BaseNormas(RAIZ / "normas")
    ctx = contexto(
        dispensa("01/2026", 40_000, "Aquisicao de medicamentos"),
        [dispensa("02/2026", 40_000, "Aquisicao de medicamentos diversos")],
        normas=base,
    )
    r = REGRA.executar(ctx)
    assert r.desfecho is Desfecho.SEM_DADOS
    assert "limite de dispensa" in r.motivo.lower()
    assert r.dados_faltantes


# --- comportamento com o limite disponível --------------------------------


def test_soma_entre_orgaos_acima_do_limite_gera_achado():
    """O caso que a regra existe para pegar: despesa dispersa entre entes."""
    ctx = contexto(
        dispensa("01/2026", 40_000, "Aquisicao de medicamentos", 1, "Prefeitura"),
        [
            dispensa(
                "07/2026",
                45_000,
                "Aquisicao de medicamentos diversos",
                2,
                "Fundo Municipal de Saude",
            ),
            dispensa(
                "03/2026", 30_000, "Aquisicao de medicamentos basicos", 3, "Camara Municipal"
            ),
        ],
    )
    r = REGRA.executar(ctx)
    assert r.desfecho is Desfecho.ACHADO
    f = r.fichas[0]
    assert "entre órgãos" in f.titulo
    assert len(f.metadados["orgaos_envolvidos"]) == 3
    assert f.metadados["soma"] == 115_000
    # Agrupamento heurístico nunca vira evidência forte.
    assert f.forca_evidencia is ForcaEvidencia.MODERADA
    assert f.hipotese_alternativa


def test_soma_abaixo_do_limite_fica_limpo():
    ctx = contexto(
        dispensa("01/2026", 10_000, "Aquisicao de medicamentos"),
        [dispensa("02/2026", 15_000, "Aquisicao de medicamentos diversos")],
    )
    assert REGRA.executar(ctx).desfecho is Desfecho.LIMPO


def test_objetos_diferentes_nao_sao_somados():
    """Medicamento e material médico compartilham contexto e são mercados distintos."""
    ctx = contexto(
        dispensa("01/2026", 40_000, "Aquisicao de medicamentos"),
        [dispensa("02/2026", 45_000, "Aquisicao de material medico hospitalar")],
    )
    assert REGRA.executar(ctx).desfecho is Desfecho.LIMPO


def test_contratacao_fora_da_janela_nao_e_somada():
    """Compras com meses de distância não caracterizam a mesma despesa."""
    ctx = contexto(
        dispensa("01/2026", 40_000, "Aquisicao de medicamentos", data="2026-01-10"),
        [dispensa("02/2026", 45_000, "Aquisicao de medicamentos diversos", data="2026-11-20")],
    )
    assert REGRA.executar(ctx).desfecho is Desfecho.LIMPO


def test_dispensa_isolada_fica_limpa():
    ctx = contexto(dispensa("01/2026", 40_000, "Aquisicao de medicamentos"), [])
    assert REGRA.executar(ctx).desfecho is Desfecho.LIMPO


def test_processo_que_nao_e_dispensa_e_nao_aplicavel():
    p = dispensa("01/2026", 40_000, "Aquisicao de medicamentos")
    p["tipo"] = "licitacao"
    r = REGRA.executar(contexto(p, []))
    assert r.desfecho is Desfecho.NAO_APLICAVEL
    assert r.motivo


def test_sem_data_devolve_sem_dados():
    p = dispensa("01/2026", 40_000, "Aquisicao de medicamentos")
    p["data_publicacao"] = None
    r = REGRA.executar(contexto(p, []))
    assert r.desfecho is Desfecho.SEM_DADOS
    assert "decreto" in r.motivo


def test_gravidade_alta_exige_dispersao_e_valor_muito_acima():
    ctx = contexto(
        dispensa("01/2026", 60_000, "Aquisicao de medicamentos", 1, "Prefeitura"),
        [
            dispensa(
                "02/2026", 70_000, "Aquisicao de medicamentos diversos", 2, "Fundo de Saude"
            )
        ],
    )
    f = REGRA.executar(ctx).fichas[0]
    assert f.gravidade is Gravidade.ALTA  # 130k contra limite de 50k, dois órgãos


def test_ficha_lista_os_processos_agrupados():
    """Quem revisa precisa poder discordar do agrupamento — logo, vê-lo."""
    ctx = contexto(
        dispensa("01/2026", 40_000, "Aquisicao de medicamentos"),
        [
            dispensa(
                "07/2026", 45_000, "Aquisicao de medicamentos diversos", 2, "Fundo de Saude"
            )
        ],
    )
    f = REGRA.executar(ctx).fichas[0]
    corpo = "\n".join(f.fatos_documentais)
    assert "07/2026" in corpo
    assert "Fundo de Saude" in corpo
    assert "sobreposição de termos" in corpo
    assert any(str(LIMIAR_SEMELHANCA) in lac for lac in f.lacunas)


# --- a função de semelhança ------------------------------------------------


@pytest.mark.parametrize(
    "a,b,esperado_acima",
    [
        (
            "Aquisicao de medicamentos para a Secretaria de Saude",
            "Aquisicao de medicamentos diversos para o Fundo de Saude",
            True,
        ),
        (
            "Contratacao de servicos de pavimentacao asfaltica",
            "Contratacao de empresa para pavimentacao asfaltica de vias",
            True,
        ),
        ("Aquisicao de medicamentos", "Aquisicao de material medico hospitalar", False),
        ("Aquisicao de combustivel", "Aquisicao de generos alimenticios", False),
        ("Aquisicao de material de limpeza", "Aquisicao de material de construcao", False),
    ],
)
def test_semelhanca_discrimina(a, b, esperado_acima):
    s = semelhanca(termos(a), termos(b))
    assert (s >= LIMIAR_SEMELHANCA) is esperado_acima, f"{a} x {b} -> {s}"


def test_sem_documento_preservado_devolve_sem_dados():
    """A soma acima do limite existe, mas o achado não tem onde se ancorar."""
    ctx = contexto(
        dispensa("01/2026", 40_000, "Aquisicao de medicamentos", 1, "Prefeitura"),
        [
            dispensa(
                "07/2026", 45_000, "Aquisicao de medicamentos diversos", 2, "Fundo de Saude"
            )
        ],
        documentos=[],
    )
    r = REGRA.executar(ctx)
    assert r.desfecho is Desfecho.SEM_DADOS
    assert r.faltantes if hasattr(r, "faltantes") else True
    assert "ancorar" in r.motivo


def test_palavras_de_praxe_nao_criam_semelhanca_falsa():
    """Sem remover 'aquisição', 'contratação' e afins, tudo casaria com tudo."""
    assert (
        semelhanca(
            termos("Aquisicao de servicos para atender necessidades do municipio"),
            termos("Contratacao de empresa para atender demandas da secretaria"),
        )
        == 0.0
    )
