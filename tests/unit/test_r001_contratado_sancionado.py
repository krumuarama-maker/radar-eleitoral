"""Testes da R001.

O que estes testes protegem, na ordem de importância:

1. Que 'não olhei' nunca seja reportado como 'está limpo' (SEM_DADOS × LIMPO).
2. Que sanção fora de vigência na data do ato não gere achado.
3. Que sanção não impeditiva (advertência, multa) não gere achado.
4. Que coincidência de raiz de CNPJ gere achado mais fraco, não igual.

Os três primeiros são falsos positivos que destroem credibilidade. O quarto é
a diferença entre um apontamento calibrado e um exagerado.
"""

from __future__ import annotations

from datetime import date

import pytest

from radar.achados.modelo import ForcaEvidencia, Gravidade
from radar.analise.deterministico.base import Contexto, Desfecho
from radar.analise.deterministico.r001_contratado_sancionado import REGRA


class NormasFalsas:
    def obter(self, chave: str, em: date):
        return None

    def valor(self, chave: str, em: date):
        return None


def contexto(*, participantes, sancoes, data="2026-03-12"):
    return Contexto(
        processo={
            "id": 42,
            "numero": "012/2026",
            "regime_juridico": "lei_14133",
            "data_publicacao": data,
        },
        documentos=[],
        participantes=participantes,
        normas=NormasFalsas(),
        municipio_ibge="4105607",
        extras={"sancoes": sancoes},
    )


VENCEDOR = {
    "papel": "vencedor",
    "documento_fiscal": "12345678000199",
    "razao_social": "Empresa Exemplo Ltda",
}

SANCAO_VIGENTE = {
    "cadastro": "ceis",
    "tipo": "declaracao_de_inidoneidade",
    "documento_fiscal": "12345678000199",
    "orgao_sancionador": "Controladoria-Geral da União",
    "data_inicio": "2025-01-10",
    "data_fim": "2027-01-10",
    "fonte_url": "https://portaldatransparencia.gov.br/sancoes/ceis",
    "sha256": "b" * 64,
    "coletado_em": "2026-09-19",
}


def test_sancao_impeditiva_vigente_gera_achado_forte():
    r = REGRA.executar(contexto(participantes=[VENCEDOR], sancoes=[SANCAO_VIGENTE]))
    assert r.desfecho is Desfecho.ACHADO
    f = r.fichas[0]
    assert f.gravidade is Gravidade.ALTA
    assert f.forca_evidencia is ForcaEvidencia.FORTE
    assert f.hipotese_alternativa, "achado grave exige hipótese alternativa"
    assert f.evidencias[0].url_origem.startswith("https://")


def test_base_de_sancoes_ausente_nao_vira_empresa_limpa():
    """A distinção que impede o radar de mentir sobre a própria cobertura."""
    ctx = contexto(participantes=[VENCEDOR], sancoes=[])
    ctx.extras["sancoes"] = None
    r = REGRA.executar(ctx)
    assert r.desfecho is Desfecho.SEM_DADOS
    assert r.desfecho is not Desfecho.LIMPO
    assert "sanções" in r.motivo.lower() or "sancoes" in r.motivo.lower()


def test_sancao_posterior_ao_ato_nao_gera_achado():
    """Empresa sancionada DEPOIS de assinar não errou ao assinar."""
    posterior = {**SANCAO_VIGENTE, "data_inicio": "2026-06-01", "data_fim": "2028-06-01"}
    r = REGRA.executar(contexto(participantes=[VENCEDOR], sancoes=[posterior]))
    assert r.desfecho is Desfecho.LIMPO


def test_sancao_ja_encerrada_nao_gera_achado():
    encerrada = {**SANCAO_VIGENTE, "data_inicio": "2020-01-01", "data_fim": "2022-01-01"}
    r = REGRA.executar(contexto(participantes=[VENCEDOR], sancoes=[encerrada]))
    assert r.desfecho is Desfecho.LIMPO


@pytest.mark.parametrize("tipo", ["advertencia", "multa"])
def test_sancao_nao_impeditiva_nao_gera_achado(tipo):
    """Advertência e multa punem, mas não impedem contratar."""
    r = REGRA.executar(
        contexto(participantes=[VENCEDOR], sancoes=[{**SANCAO_VIGENTE, "tipo": tipo}])
    )
    assert r.desfecho is Desfecho.LIMPO


def test_sancao_sem_data_de_inicio_nao_gera_achado():
    """Dado incompleto não pode ser presumido a favor da acusação."""
    sem_data = {**SANCAO_VIGENTE, "data_inicio": None}
    r = REGRA.executar(contexto(participantes=[VENCEDOR], sancoes=[sem_data]))
    assert r.desfecho is Desfecho.LIMPO


def test_mesma_raiz_de_cnpj_gera_achado_mais_fraco():
    """Filial sancionada não é matriz sancionada — o achado existe, calibrado."""
    filial = {**SANCAO_VIGENTE, "documento_fiscal": "12345678000288"}
    r = REGRA.executar(contexto(participantes=[VENCEDOR], sancoes=[filial]))
    assert r.desfecho is Desfecho.ACHADO
    f = r.fichas[0]
    assert f.forca_evidencia is ForcaEvidencia.MODERADA
    assert f.gravidade is Gravidade.MEDIA
    assert "controvertida" in (f.hipotese_alternativa or "")


def test_processo_sem_vencedor_e_nao_aplicavel_com_motivo():
    r = REGRA.executar(contexto(participantes=[], sancoes=[SANCAO_VIGENTE]))
    assert r.desfecho is Desfecho.NAO_APLICAVEL
    assert r.motivo


def test_processo_sem_data_devolve_sem_dados():
    ctx = contexto(participantes=[VENCEDOR], sancoes=[SANCAO_VIGENTE])
    ctx.processo.pop("data_publicacao")
    r = REGRA.executar(ctx)
    assert r.desfecho is Desfecho.SEM_DADOS
    assert "data" in r.motivo.lower()
