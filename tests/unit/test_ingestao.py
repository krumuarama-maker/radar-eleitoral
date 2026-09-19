"""Ingestão — do coletor ao banco, e do banco às regras.

Este é o teste que prova que a corrente inteira fecha. Ele usa uma carga com a
forma que o PNCP devolve e verifica que, ao final, uma regra consegue rodar e
gerar achado ancorado num documento preservado.

O caso central é o último: três dispensas do mesmo objeto, feitas por três
órgãos diferentes do mesmo município. É o fracionamento clássico, e é invisível
para quem consolida um CNPJ de cada vez.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from radar.analise.deterministico.base import RegistroRegras
from radar.analise.deterministico.r002_proposta_unica import R002PropostaUnica
from radar.analise.executor import Executor
from radar.analise.normas import BaseNormas
from radar.coleta.base import ItemColetado, ResultadoColeta
from radar.coleta.ingestao import Ingestor

RAIZ = Path(__file__).resolve().parents[2]


def contratacao_pncp(
    *,
    cnpj_orgao: str,
    razao_orgao: str,
    sequencial: int,
    objeto: str,
    modalidade: int = 6,
    valor: float = 120000.0,
    data: str = "2026-09-15",
    vencedores: list[tuple[str, str, float]] | None = None,
) -> ItemColetado:
    """Monta um item com a forma que o coletor do PNCP produz."""
    bruto = {
        "numeroControlePNCP": f"{cnpj_orgao}-1-{sequencial:06d}/2026",
        "numeroCompra": f"{sequencial:03d}",
        "anoCompra": 2026,
        "sequencialCompra": sequencial,
        "modalidadeId": modalidade,
        "objetoCompra": objeto,
        "valorTotalEstimado": valor,
        "dataPublicacaoPncp": f"{data}T10:00:00",
        "situacaoCompraNome": "Divulgada no PNCP",
        "orgaoEntidade": {"cnpj": cnpj_orgao, "razaoSocial": razao_orgao},
        "amparoLegal": {"nome": "Lei 14.133/2021, Art. 75, II"},
        "resultados": [
            {"niFornecedor": c, "nomeRazaoSocialFornecedor": r, "valorTotalHomologado": v}
            for c, r, v in (vencedores or [])
        ],
    }
    return ItemColetado(
        url_origem=f"https://pncp.gov.br/app/editais/{cnpj_orgao}/2026/{sequencial}",
        conteudo=json.dumps(bruto, ensure_ascii=False, sort_keys=True).encode(),
        tipo_documento="contratacao_pncp",
        titulo=objeto[:120],
        numero=bruto["numeroControlePNCP"],
        exercicio=2026,
        identificador_externo=bruto["numeroControlePNCP"],
        http_headers={"content-type": "application/json"},
        metadados={
            "modalidade": modalidade,
            "cnpj_orgao": cnpj_orgao,
            "sequencial": sequencial,
            "data_publicacao": data,
        },
        coletado_em=datetime(2026, 9, 18, 23, 0, tzinfo=UTC),
    )


@pytest.fixture
def banco() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript((RAIZ / "src/radar/db/schema.sql").read_text(encoding="utf-8"))
    con.execute(
        "INSERT INTO municipio (codigo_ibge, nome, uf) VALUES ('4105607','Cidade Gaúcha','PR')"
    )
    return con


@pytest.fixture
def ingestor(banco: sqlite3.Connection) -> Ingestor:
    return Ingestor(banco, "4105607")


def coleta(*itens: ItemColetado) -> ResultadoColeta:
    r = ResultadoColeta(fonte_chave="pncp", iniciada_em=datetime.now(UTC))
    r.itens = list(itens)
    r.itens_vistos = len(itens)
    return r


# --- o básico --------------------------------------------------------------


def test_contratacao_vira_processo_documento_e_versao(ingestor, banco):
    b = ingestor.ingerir(
        coleta(
            contratacao_pncp(
                cnpj_orgao="75377200000167",
                razao_orgao="Prefeitura Municipal de Cidade Gaúcha",
                sequencial=12,
                objeto="Aquisicao de medicamentos",
            )
        )
    )
    assert b.processos_novos == 1
    assert b.documentos_novos == 1
    assert b.versoes_novas == 1

    p = banco.execute(
        "SELECT numero, tipo, modalidade, regime_juridico FROM processo"
    ).fetchone()
    assert tuple(p) == ("012", "licitacao", "pregao_eletronico", "lei_14133")

    # o registro estruturado fica preservado e vinculado — é a âncora do achado
    v = banco.execute("SELECT sha256, tamanho_bytes FROM documento_versao").fetchone()
    assert len(v[0]) == 64
    assert v[1] > 0
    vinc = banco.execute(
        "SELECT papel, vinculo_origem, confianca FROM processo_documento"
    ).fetchone()
    assert tuple(vinc) == ("registro_contratacao", "identificador", 1.0)


def test_reingerir_o_mesmo_nao_duplica(ingestor, banco):
    item = contratacao_pncp(
        cnpj_orgao="75377200000167",
        razao_orgao="Prefeitura",
        sequencial=12,
        objeto="Aquisicao de medicamentos",
    )
    ingestor.ingerir(coleta(item))
    b2 = ingestor.ingerir(coleta(item))
    assert b2.processos_novos == 0
    assert b2.versoes_novas == 0
    assert b2.ja_conhecidos == 1
    assert banco.execute("SELECT COUNT(*) FROM processo").fetchone()[0] == 1


def test_conteudo_alterado_vira_nova_versao_sem_apagar_a_anterior(ingestor, banco):
    """Edital retificado não sobrescreve. A retificação é, ela própria, um sinal."""
    v1 = contratacao_pncp(
        cnpj_orgao="75377200000167",
        razao_orgao="Prefeitura",
        sequencial=12,
        objeto="Aquisicao de medicamentos",
        valor=120000.0,
    )
    v2 = contratacao_pncp(
        cnpj_orgao="75377200000167",
        razao_orgao="Prefeitura",
        sequencial=12,
        objeto="Aquisicao de medicamentos",
        valor=180000.0,
    )
    ingestor.ingerir(coleta(v1))
    b = ingestor.ingerir(coleta(v2))
    assert b.versoes_novas == 1

    versoes = banco.execute(
        "SELECT versao, substitui_versao, diff_resumo FROM documento_versao ORDER BY versao"
    ).fetchall()
    assert len(versoes) == 2
    assert versoes[1]["substitui_versao"] == 1
    assert "permanece arquivada" in versoes[1]["diff_resumo"]


def test_regime_indeterminado_quando_o_amparo_nao_diz(ingestor, banco):
    """Presumir a lei nova é o erro que a regra R4 existe para impedir."""
    item = contratacao_pncp(
        cnpj_orgao="75377200000167",
        razao_orgao="Prefeitura",
        sequencial=12,
        objeto="Aquisicao de medicamentos",
    )
    bruto = json.loads(item.conteudo)
    del bruto["amparoLegal"]
    item.conteudo = json.dumps(bruto, ensure_ascii=False, sort_keys=True).encode()

    ingestor.ingerir(coleta(item))
    assert (
        banco.execute("SELECT regime_juridico FROM processo").fetchone()[0] == "indeterminado"
    )


# --- o que justifica o projeto --------------------------------------------


def test_orgaos_novos_sao_descobertos_pelo_cnpj(ingestor, banco):
    """Descobrir um fundo é informação, não efeito colateral.

    O mapeamento inicial do município não sabia o CNPJ de nenhum fundo. Eles
    aparecem sozinhos na primeira coleta — e é entre eles que a despesa se
    dispersa.
    """
    b = ingestor.ingerir(
        coleta(
            contratacao_pncp(
                cnpj_orgao="75377200000167",
                razao_orgao="Prefeitura Municipal de Cidade Gaúcha",
                sequencial=12,
                objeto="Aquisicao de medicamentos",
            ),
            contratacao_pncp(
                cnpj_orgao="11222333000144",
                razao_orgao="Fundo Municipal de Saude de Cidade Gaucha",
                sequencial=3,
                objeto="Aquisicao de medicamentos diversos",
                modalidade=8,
            ),
            contratacao_pncp(
                cnpj_orgao="01201556000109",
                razao_orgao="Camara Municipal de Cidade Gaucha",
                sequencial=5,
                objeto="Aquisicao de material de expediente",
                modalidade=8,
            ),
        )
    )
    assert len(b.orgaos_descobertos) == 3
    tipos = dict(banco.execute("SELECT tipo, COUNT(*) FROM orgao GROUP BY tipo").fetchall())
    assert tipos == {"prefeitura": 1, "fundo": 1, "camara": 1}


def test_dispensas_de_tres_orgaos_ficam_no_mesmo_municipio(ingestor, banco):
    """A montagem que torna o fracionamento entre entes visível à R003."""
    ingestor.ingerir(
        coleta(
            contratacao_pncp(
                cnpj_orgao="75377200000167",
                razao_orgao="Prefeitura",
                sequencial=12,
                objeto="Aquisicao de medicamentos",
                modalidade=8,
                valor=40000.0,
                data="2026-09-10",
            ),
            contratacao_pncp(
                cnpj_orgao="11222333000144",
                razao_orgao="Fundo Municipal de Saude",
                sequencial=3,
                objeto="Aquisicao de medicamentos diversos",
                modalidade=8,
                valor=45000.0,
                data="2026-09-12",
            ),
            contratacao_pncp(
                cnpj_orgao="01201556000109",
                razao_orgao="Camara Municipal",
                sequencial=5,
                objeto="Aquisicao de medicamentos basicos",
                modalidade=8,
                valor=30000.0,
                data="2026-09-15",
            ),
        )
    )
    dispensas = banco.execute(
        "SELECT COUNT(*), COUNT(DISTINCT orgao_id) FROM processo WHERE tipo='dispensa'"
    ).fetchone()
    assert tuple(dispensas) == (3, 3)


# --- a corrente inteira ----------------------------------------------------


def test_da_coleta_ao_achado_ancorado(ingestor, banco):
    """Coleta -> ingestão -> regra -> achado com evidência preservada.

    Se este teste passa, a execução de amanhã é só questão de ter rede.
    """
    ingestor.ingerir(
        coleta(
            contratacao_pncp(
                cnpj_orgao="75377200000167",
                razao_orgao="Prefeitura Municipal de Cidade Gaúcha",
                sequencial=12,
                objeto="Aquisicao de medicamentos",
                modalidade=6,
                vencedores=[("12345678000199", "Alfa Distribuidora Ltda", 118000.0)],
            )
        )
    )

    reg = RegistroRegras()
    regras = [reg.registrar(R002PropostaUnica())]
    balanco = Executor(banco, BaseNormas(RAIZ / "normas")).executar("4105607", regras=regras)

    assert balanco.achados == 1
    ficha = balanco.fichas[0]
    assert ficha.evidencias
    assert len(ficha.evidencias[0].sha256_versao) == 64
    assert ficha.evidencias[0].url_origem.startswith("https://pncp.gov.br/")

    gravado = banco.execute(
        "SELECT a.titulo, COUNT(e.id) FROM achado a"
        "  JOIN achado_evidencia e ON e.achado_id = a.id GROUP BY a.id"
    ).fetchone()
    assert gravado is not None
    assert gravado[1] >= 1, "achado gravado sem evidência violaria a regra R1"


def test_sem_participante_a_regra_recusa_apontar(ingestor, banco):
    """PNCP sem resultados não é licitação com proposta única.

    Pode ser certame em andamento, ou consulta que não trouxe o resultado. A
    diferença entre SEM_DADOS e ACHADO aqui é a diferença entre um radar
    confiável e um que acusa a partir de lacuna de coleta.
    """
    ingestor.ingerir(
        coleta(
            contratacao_pncp(
                cnpj_orgao="75377200000167",
                razao_orgao="Prefeitura",
                sequencial=12,
                objeto="Aquisicao de medicamentos",
                modalidade=6,
                vencedores=[],
            )
        )
    )
    reg = RegistroRegras()
    b = Executor(banco, BaseNormas(RAIZ / "normas")).executar(
        "4105607", regras=[reg.registrar(R002PropostaUnica())]
    )
    assert b.achados == 0
    assert b.sem_dados == 1
