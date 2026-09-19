"""Testes da base normativa — a regra R4 de AGENTS.md em forma executável."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from radar.analise.normas import (
    BaseNormas,
    NormaInexistente,
    NormaNaoConferida,
    NormaNaoVigente,
)

RAIZ = Path(__file__).resolve().parents[2] / "normas"


@pytest.fixture(scope="module")
def base() -> BaseNormas:
    return BaseNormas(RAIZ)


def test_carrega_a_base_do_repositorio(base):
    assert len(base) > 0


def test_dispositivo_pendente_nao_vira_fundamento(base):
    """A trava central: não se cita o que ninguém abriu na fonte oficial."""
    with pytest.raises(NormaNaoConferida) as exc:
        base.fundamento(
            "lei_14133_art_164_impugnacao", date(2026, 3, 12), "explicação qualquer"
        )
    assert "pendente" in str(exc.value)
    assert "planalto" in str(exc.value).lower()


def test_parametro_de_prazo_vem_da_base_e_nao_do_codigo(base):
    """Regra de análise não guarda prazo; ela pergunta aqui."""
    dias = base.valor(
        "tce_pr_mural_prazo_modalidades_in208",
        date(2026, 7, 1),
        "prazo_dias_uteis_antes_encerramento_propostas",
    )
    assert dias == 7


def test_prazo_novo_nao_alcanca_certame_anterior(base):
    """O erro que a R4 existe para impedir, provado por teste.

    A IN 208/2026 não pode ser aplicada a certame de 2024. Aqui o sistema
    recusa, em vez de gerar apontamento falso de atraso.
    """
    with pytest.raises(NormaNaoVigente) as exc:
        base.obter("tce_pr_mural_prazo_modalidades_in208", date(2024, 5, 10))
    assert "regra de hoje a fato de ontem" in str(exc.value)


def test_redacao_anterior_sem_parametros_bloqueia_com_explicacao(base):
    """Lacuna conhecida tem que falar, não silenciar."""
    with pytest.raises(NormaNaoConferida) as exc:
        base.valor("tce_pr_mural_prazo_redacao_original_in156", date(2024, 5, 10))
    assert "NÃO PODE rodar" in str(exc.value) or "não pode rodar" in str(exc.value).lower()


def test_chave_inexistente_falha_claramente(base):
    with pytest.raises(NormaInexistente):
        base.obter("lei_que_nao_existe_art_1", date(2026, 1, 1))


def test_pendentes_listam_o_que_trava_pecas(base):
    pend = base.pendentes()
    assert pend, "a base começa toda pendente — é o esperado"
    assert all(not d.conferido for d in pend)


def test_fundamento_conferido_passa(tmp_path):
    """Conferido de verdade, com texto literal, vira fundamento citável."""
    (tmp_path / "x.yaml").write_text(
        """
diploma: "Lei Exemplo nº 1/2000"
url_oficial: https://exemplo.gov.br/lei
dispositivos:
  - chave: exemplo_art_1
    dispositivo: "Art. 1º"
    ementa: "teste"
    texto_literal: "Art. 1º Este é o texto literal conferido na fonte oficial."
    vigencia_inicio: "2000-01-01"
    vigencia_fim: null
    conferido: {status: conferido, por: "Fulano", em: "2026-09-19"}
""",
        encoding="utf-8",
    )
    b = BaseNormas(tmp_path)
    f = b.fundamento("exemplo_art_1", date(2026, 1, 1), "aplica-se porque X")
    assert f.texto_conferido.startswith("Art. 1º")
    assert f.vigente_em(date(2026, 1, 1))
