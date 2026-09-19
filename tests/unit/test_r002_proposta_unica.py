"""Testes da R002 — proposta única."""

from __future__ import annotations

from datetime import date

from radar.achados.modelo import ForcaEvidencia, Gravidade
from radar.analise.deterministico.base import Contexto, Desfecho
from radar.analise.deterministico.r002_proposta_unica import REGRA


class Normas:
    def obter(self, chave: str, em: date):
        return None

    def valor(self, chave: str, em: date):
        return None


def ctx(modalidade, participantes, **extra):
    processo = {
        "id": 1,
        "numero": "012",
        "exercicio": 2026,
        "modalidade": modalidade,
        "regime_juridico": "lei_14133",
        "data_publicacao": "2026-03-12",
        "orgao_id": 1,
    }
    processo.update(extra)
    return Contexto(
        processo=processo,
        documentos=[
            {
                "papel": "ata_sessao",
                "sha256": "a" * 64,
                "url_origem": "https://pncp.gov.br/x",
                "documento_versao_id": 5,
            }
        ],
        participantes=participantes,
        normas=Normas(),
        municipio_ibge="4105607",
        extras={},
    )


UM = [{"papel": "vencedor", "documento_fiscal": "12345678000199", "razao_social": "Alfa"}]
DOIS = [
    *UM,
    {"papel": "licitante", "documento_fiscal": "98765432000188", "razao_social": "Beta"},
]


def test_participante_unico_em_pregao_gera_achado():
    r = REGRA.executar(ctx("pregao_eletronico", UM))
    assert r.desfecho is Desfecho.ACHADO
    f = r.fichas[0]
    assert f.forca_evidencia is ForcaEvidencia.FORTE  # contar licitantes é exato
    assert f.gravidade is Gravidade.BAIXA  # caso isolado, valor baixo
    assert f.hipotese_alternativa


def test_dois_participantes_fica_limpo():
    assert REGRA.executar(ctx("pregao_eletronico", DOIS)).desfecho is Desfecho.LIMPO


def test_dispensa_nao_e_aplicavel():
    """Em dispensa a ausência de disputa é o pressuposto legal, não o desvio."""
    r = REGRA.executar(ctx("dispensa", UM))
    assert r.desfecho is Desfecho.NAO_APLICAVEL
    assert "pressuposto" in r.motivo


def test_sem_participante_registrado_nao_vira_achado():
    """Ata não coletada e licitação deserta são indistinguíveis aqui."""
    r = REGRA.executar(ctx("pregao_eletronico", []))
    assert r.desfecho is Desfecho.SEM_DADOS
    assert r.desfecho is not Desfecho.LIMPO
    assert "deserta" in r.motivo


def test_valor_alto_eleva_a_gravidade():
    f = REGRA.executar(ctx("pregao_eletronico", UM, valor_contratado=1_200_000.0)).fichas[0]
    assert f.gravidade is Gravidade.MEDIA


def test_valor_aparece_formatado_em_reais():
    f = REGRA.executar(ctx("pregao_eletronico", UM, valor_contratado=1_200_000.0)).fichas[0]
    assert "R$ 1.200.000,00." in "\n".join(f.fatos_documentais)


def test_evidencia_ancora_na_ata_da_sessao():
    f = REGRA.executar(ctx("pregao_eletronico", UM)).fichas[0]
    assert f.evidencias[0].sha256_versao == "a" * 64
    assert f.evidencias[0].documento_versao_id == 5
    assert "ata_sessao" in (f.evidencias[0].observacao or "")


def test_sem_documento_preservado_devolve_sem_dados():
    """Fato conhecido, achado impossível: não há onde ancorá-lo."""
    c = ctx("pregao_eletronico", UM)
    c.documentos.clear()
    r = REGRA.executar(c)
    assert r.desfecho is Desfecho.SEM_DADOS
    assert "âncora" in r.motivo
