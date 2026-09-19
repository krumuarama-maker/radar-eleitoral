"""Testes da base de coleta.

O primeiro teste existe por causa de um defeito real: o User-Agent do projeto
tinha acento ("fiscalização cívica"), e cabeçalho HTTP não aceita caracteres
fora de ASCII. O httpx levantava UnicodeEncodeError e a requisição não saía.

O defeito não aparecia em nenhum teste unitário nem no lint — só em execução,
na primeira coleta real. Este teste é a trava para que não volte.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from radar.coleta.base import UA, ColetorBase, ItemColetado, ResultadoColeta
from radar.coleta.pncp import UA_NAVEGADOR


@pytest.mark.parametrize("cabecalho", [UA, UA_NAVEGADOR])
def test_user_agent_e_ascii(cabecalho: str) -> None:
    """Acento em cabeçalho HTTP impede a requisição de sair."""
    assert cabecalho.isascii(), f"cabeçalho com caractere não-ASCII: {cabecalho!r}"
    cabecalho.encode("ascii")  # o que o httpx faz internamente


def test_cliente_httpx_aceita_os_cabecalhos_do_projeto() -> None:
    """Constrói o cliente como o coletor faz. Falhava com UnicodeEncodeError."""
    cli = httpx.Client(
        headers={
            "User-Agent": UA_NAVEGADOR,
            "Accept": "application/json",
            "From": "radar-fiscalizacao-municipal (controle social)",
        }
    )
    cli.close()


class ColetorFalso(ColetorBase):
    chave = "falso"
    nome = "Coletor de teste"
    url_base = "https://exemplo.gov.br"
    respeitar_robots = False

    def __init__(self, diretorio, municipio, itens=(), explode=None):
        super().__init__(diretorio, municipio)
        self._itens = list(itens)
        self._explode = explode

    def buscar(self, desde=None):
        if self._explode:
            raise self._explode
        yield from self._itens


def item(conteudo: bytes = b"conteudo") -> ItemColetado:
    return ItemColetado(
        url_origem="https://exemplo.gov.br/doc.pdf",
        conteudo=conteudo,
        tipo_documento="edital",
        titulo="Edital de teste",
        http_headers={"content-type": "application/pdf"},
        coletado_em=datetime(2026, 9, 18, tzinfo=UTC),
    )


def test_preservar_grava_original_e_manifesto(tmp_path: Path) -> None:
    with ColetorFalso(tmp_path, "4105607", [item()]) as c:
        r = c.executar()

    assert r.status == "sucesso"
    esperado = hashlib.sha256(b"conteudo").hexdigest()
    arquivos = list((tmp_path / "originais" / "4105607").rglob("*"))
    nomes = {f.name for f in arquivos if f.is_file()}
    assert f"{esperado}.pdf" in nomes
    assert f"{esperado}.pdf.json" in nomes, "manifesto de proveniência é obrigatório"


def test_conteudo_identico_nao_grava_duas_vezes(tmp_path: Path) -> None:
    """O arquivo é nomeado pelo hash: o nome já é a prova de integridade."""
    with ColetorFalso(tmp_path, "4105607", [item(), item()]) as c:
        c.executar()
    pdfs = list((tmp_path / "originais").rglob("*.pdf"))
    assert len(pdfs) == 1


def test_falha_da_fonte_nao_vira_coleta_vazia_silenciosa(tmp_path: Path) -> None:
    """Fonte fora do ar tem que aparecer como falha, não como 'nada encontrado'."""
    with ColetorFalso(tmp_path, "4105607", explode=RuntimeError("502 no portal")) as c:
        r = c.executar()
    assert r.status == "falha"
    assert r.erros
    assert not r.itens


def test_bloqueio_de_acesso_e_distinto_de_erro(tmp_path: Path) -> None:
    """Portal que recusa acesso é limitação de transparência, não bug do coletor."""
    with ColetorFalso(tmp_path, "4105607", explode=PermissionError("robots.txt proíbe")) as c:
        r = c.executar()
    assert r.status == "bloqueada"
    assert r.bloqueios
    assert not r.erros


def test_resultado_parcial_e_sinalizado() -> None:
    r = ResultadoColeta(fonte_chave="x", iniciada_em=datetime.now(UTC))
    r.itens = [item()]
    r.erros = ["um documento falhou"]
    assert r.status == "falha_parcial"
