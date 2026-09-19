"""Testes do executor — o caminho completo, com banco de verdade.

O que estes testes protegem:

1. Que a execução seja REGISTRADA, inclusive quando não gera achado. É daqui que
   sai a resposta para "por que este processo nunca foi apontado?".
2. Que `cobertura` distinga o que foi examinado do que não pôde ser.
3. Que a ficha gravada carregue evidência — o trigger do banco depende disso.
4. Que rodar duas vezes não duplique achado.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from radar.analise.deterministico.base import RegistroRegras
from radar.analise.deterministico.r002_proposta_unica import R002PropostaUnica
from radar.analise.executor import Executor
from radar.analise.normas import BaseNormas

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture
def banco() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript((RAIZ / "src/radar/db/schema.sql").read_text(encoding="utf-8"))
    con.execute(
        "INSERT INTO municipio (codigo_ibge, nome, uf) VALUES ('4105607','Cidade Gaúcha','PR')"
    )
    con.execute(
        "INSERT INTO orgao (municipio_id, nome, tipo) VALUES (1,'Prefeitura','prefeitura')"
    )
    con.execute(
        "INSERT INTO processo (municipio_id, orgao_id, tipo, modalidade, numero,"
        " exercicio, objeto, regime_juridico, valor_contratado, data_publicacao)"
        " VALUES (1,1,'licitacao','pregao_eletronico','012',2026,"
        "'Aquisicao de medicamentos','lei_14133',120000.0,'2026-03-12')"
    )
    con.execute(
        "INSERT INTO entidade (tipo, documento_fiscal, razao_social)"
        " VALUES ('pj','12345678000199','Alfa Ltda')"
    )
    con.execute(
        "INSERT INTO participacao (processo_id, entidade_id, papel, valor_proposta)"
        " VALUES (1,1,'vencedor',120000.0)"
    )
    # Documento preservado: sem ele não há onde ancorar o achado, e a regra
    # devolve SEM_DADOS em vez de apontar (ver test_achado_exige_documento_preservado).
    con.execute(
        "INSERT INTO fonte (municipio_id, chave, nome, url_base, tipo, coletor)"
        " VALUES (1,'pncp','PNCP','https://pncp.gov.br','api','radar.coleta.pncp')"
    )
    con.execute(
        "INSERT INTO documento (municipio_id, orgao_id, fonte_id, tipo, titulo,"
        " numero, exercicio, url_origem, primeira_coleta)"
        " VALUES (1,1,1,'ata','Ata da sessao','012',2026,"
        "'https://pncp.gov.br/app/editais/x','2026-03-20')"
    )
    con.execute(
        "INSERT INTO documento_versao (documento_id, versao, sha256, tamanho_bytes,"
        " caminho_arquivo, coletado_em)"
        " VALUES (1,1,'" + "a" * 64 + "',2048,'dados/originais/x.pdf','2026-03-20')"
    )
    con.execute(
        "INSERT INTO processo_documento (processo_id, documento_id, papel, vinculo_origem)"
        " VALUES (1,1,'ata_sessao','identificador')"
    )
    return con


@pytest.fixture
def executor(banco: sqlite3.Connection) -> Executor:
    return Executor(banco, BaseNormas(RAIZ / "normas"))


def registro_r002() -> list:
    reg = RegistroRegras()
    return [reg.registrar(R002PropostaUnica())]


def test_um_unico_licitante_gera_e_grava_achado(executor, banco):
    b = executor.executar("4105607", regras=registro_r002())
    assert b.processos == 1
    assert b.achados == 1

    linha = banco.execute("SELECT codigo, titulo, gravidade, status FROM achado").fetchone()
    assert linha is not None
    assert "R002" in linha[0]

    evid = banco.execute("SELECT COUNT(*) FROM achado_evidencia").fetchone()[0]
    assert evid >= 1, "achado gravado sem evidência violaria a regra R1"


def test_execucao_e_registrada_mesmo_sem_achado(executor, banco):
    """Sem este registro, não há como distinguir 'examinado' de 'nunca olhado'."""
    banco.execute(
        "INSERT INTO entidade (tipo, documento_fiscal, razao_social)"
        " VALUES ('pj','98765432000188','Beta Ltda')"
    )
    banco.execute(
        "INSERT INTO participacao (processo_id, entidade_id, papel) VALUES (1,2,'licitante')"
    )
    b = executor.executar("4105607", regras=registro_r002())
    assert b.achados == 0
    assert b.limpos == 1

    exec_linha = banco.execute(
        "SELECT r.codigo, e.resultado FROM execucao_regra e JOIN regra r ON r.id=e.regra_id"
    ).fetchone()
    assert tuple(exec_linha) == ("R002", "limpo")


def test_achado_nao_duplica_entre_execucoes(executor, banco):
    executor.executar("4105607", regras=registro_r002())
    executor.executar("4105607", regras=registro_r002())
    assert banco.execute("SELECT COUNT(*) FROM achado").fetchone()[0] == 1
    # mas as duas execuções ficam registradas
    assert banco.execute("SELECT COUNT(*) FROM execucao_regra").fetchone()[0] == 2


def test_cobertura_separa_examinado_de_nao_examinado(executor, banco):
    """Processo sem participante não pode entrar na conta como 'limpo'."""
    banco.execute("DELETE FROM participacao")
    b = executor.executar("4105607", regras=registro_r002())
    assert b.sem_dados == 1
    assert b.limpos == 0
    assert b.cobertura == 0.0
    assert b.faltantes == {"participacao": 1}


def test_achado_exige_documento_preservado(executor, banco):
    """Sem documento arquivado, o fato existe mas o achado não pode existir.

    A alternativa — inventar um identificador de versão para passar pela
    validação — faria a regra R1 virar teatro: o achado passaria, sem ter
    documento nenhum atrás dele.
    """
    banco.execute("DELETE FROM processo_documento")
    b = executor.executar("4105607", regras=registro_r002())
    assert b.achados == 0
    assert b.sem_dados == 1
    assert b.faltantes == {"documento_versao": 1}


def test_banco_vazio_nao_e_municipio_sem_problemas(executor):
    b = executor.executar("9999999", regras=registro_r002())
    assert b.processos == 0
    assert b.achados == 0
    assert b.cobertura == 0.0  # nada examinado, não 'tudo certo'


def test_regra_e_cadastrada_automaticamente(executor, banco):
    executor.executar("4105607", regras=registro_r002())
    r = banco.execute(
        "SELECT codigo, categoria, fonte_metodologica FROM regra WHERE codigo='R002'"
    ).fetchone()
    assert r is not None
    assert r[1] == "competicao"
    assert "Cardinal" in r[2], "a fonte metodológica sustenta o achado; precisa ser gravada"


def test_trigger_barra_avanco_de_achado_sem_evidencia(banco):
    """A regra R1 aplicada pelo banco, e não pela boa vontade do programador."""
    banco.execute(
        "INSERT INTO achado (codigo, municipio_id, titulo, fatos_documentais,"
        " lacunas, gravidade, forca_evidencia, urgencia, origem, status)"
        " VALUES ('X-1',1,'t','f','l','baixa','fraca','sem_prazo','manual','novo')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="sem evidencia"):
        banco.execute("UPDATE achado SET status='aguardando_revisao_humana' WHERE codigo='X-1'")
