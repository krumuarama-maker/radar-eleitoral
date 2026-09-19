-- ============================================================================
-- Radar de Fiscalização Municipal — esquema do banco
-- Alvo: SQLite 3.40+ (FTS5 e JSON1 habilitados). Caminho para Postgres: ver
-- docs/02-modelo-de-dados.md, seção "Migração".
--
-- Princípio que governa este esquema: NADA se apaga. Documento revisto vira nova
-- versão; achado derrubado vira achado com status 'improcedente'; correção da
-- Prefeitura é um evento registrado, não uma exclusão. O histórico é a prova.
-- ============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- 1. TERRITÓRIO E FONTES
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS municipio (
    id              INTEGER PRIMARY KEY,
    codigo_ibge     TEXT    NOT NULL UNIQUE,
    nome            TEXT    NOT NULL,
    uf              TEXT    NOT NULL,
    populacao       INTEGER,                 -- para cálculos per capita
    populacao_ano   INTEGER,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Um município tem vários "órgãos": Prefeitura, Câmara, Fundo de Saúde,
-- Fundo de Educação, SAAE, Instituto de Previdência. Cada um tem CNPJ próprio e
-- licita separadamente. Ignorar isso é o erro nº 1 de quem fiscaliza município:
-- o fracionamento de despesa costuma se esconder na divisão entre fundos.
CREATE TABLE IF NOT EXISTS orgao (
    id              INTEGER PRIMARY KEY,
    municipio_id    INTEGER NOT NULL REFERENCES municipio(id),
    nome            TEXT    NOT NULL,
    cnpj            TEXT,
    tipo            TEXT    NOT NULL,        -- prefeitura|camara|fundo|autarquia|consorcio
    UNIQUE (municipio_id, nome)
);

CREATE TABLE IF NOT EXISTS fonte (
    id                  INTEGER PRIMARY KEY,
    municipio_id        INTEGER REFERENCES municipio(id),
    chave               TEXT    NOT NULL UNIQUE,   -- ex.: 'pncp', 'mural_tce_pr'
    nome                TEXT    NOT NULL,
    url_base            TEXT    NOT NULL,
    tipo                TEXT    NOT NULL,   -- api|html|pdf|planilha
    coletor             TEXT    NOT NULL,   -- módulo Python responsável
    periodicidade_min   INTEGER NOT NULL DEFAULT 1440,  -- minutos entre coletas
    ativo               INTEGER NOT NULL DEFAULT 1,
    -- Honestidade sobre cobertura: se a fonte está fora do ar há uma semana,
    -- o painel PRECISA dizer isso, senão "nenhum achado" vira mentira.
    ultima_coleta_ok    TEXT,
    ultima_coleta_erro  TEXT,
    observacoes         TEXT
);

-- Cada execução de coleta é registrada, com sucesso OU falha. É daqui que sai o
-- indicador de cobertura. Ver docs/07-etica-e-limites.md.
CREATE TABLE IF NOT EXISTS coleta (
    id              INTEGER PRIMARY KEY,
    fonte_id        INTEGER NOT NULL REFERENCES fonte(id),
    iniciada_em     TEXT    NOT NULL,
    encerrada_em    TEXT,
    status          TEXT    NOT NULL,       -- sucesso|falha_parcial|falha|bloqueada
    itens_vistos    INTEGER NOT NULL DEFAULT 0,
    itens_novos     INTEGER NOT NULL DEFAULT 0,
    itens_alterados INTEGER NOT NULL DEFAULT 0,
    erro            TEXT,
    http_status     INTEGER,
    detalhes_json   TEXT
);
CREATE INDEX IF NOT EXISTS idx_coleta_fonte ON coleta(fonte_id, iniciada_em DESC);

-- ---------------------------------------------------------------------------
-- 2. DOCUMENTOS — preservação e proveniência
-- ---------------------------------------------------------------------------

-- Um 'documento' é a identidade estável (ex.: "Edital 12/2026 do Pregão X").
-- O arquivo em si é 'documento_versao'. Edital retificado NÃO sobrescreve: gera
-- versão 2. Detectar a retificação é, por si só, um sinal relevante.
CREATE TABLE IF NOT EXISTS documento (
    id              INTEGER PRIMARY KEY,
    municipio_id    INTEGER NOT NULL REFERENCES municipio(id),
    orgao_id        INTEGER REFERENCES orgao(id),
    fonte_id        INTEGER NOT NULL REFERENCES fonte(id),
    tipo            TEXT    NOT NULL,   -- edital|anexo|ata|contrato|aditivo|nota_empenho|
                                        -- liquidacao|pagamento|projeto_lei|parecer|
                                        -- medicao|planilha_orcamentaria|diario_oficial|outro
    titulo          TEXT,
    numero          TEXT,               -- ex.: '012/2026'
    exercicio       INTEGER,
    identificador_externo TEXT,         -- numeroControlePNCP, id do mural, etc.
    url_origem      TEXT    NOT NULL,
    primeira_coleta TEXT    NOT NULL,
    criado_em       TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (fonte_id, identificador_externo, tipo)
);
CREATE INDEX IF NOT EXISTS idx_documento_mun_tipo ON documento(municipio_id, tipo, exercicio);

CREATE TABLE IF NOT EXISTS documento_versao (
    id              INTEGER PRIMARY KEY,
    documento_id    INTEGER NOT NULL REFERENCES documento(id),
    versao          INTEGER NOT NULL,
    -- sha256 do arquivo como baixado. Prova que o que está guardado não mudou.
    -- NÃO prova autenticidade da origem — ver docs/07-etica-e-limites.md.
    sha256          TEXT    NOT NULL,
    tamanho_bytes   INTEGER NOT NULL,
    mime            TEXT,
    caminho_arquivo TEXT    NOT NULL,   -- dados/originais/<aaaa>/<mm>/<sha256>.<ext>
    coletado_em     TEXT    NOT NULL,
    coleta_id       INTEGER REFERENCES coleta(id),
    http_headers    TEXT,               -- JSON: Last-Modified, ETag, Content-Type
    -- Preenchido quando esta versão substitui outra; guarda o resumo do que mudou.
    substitui_versao INTEGER,
    diff_resumo     TEXT,
    UNIQUE (documento_id, versao),
    UNIQUE (sha256, documento_id)
);
CREATE INDEX IF NOT EXISTS idx_versao_sha ON documento_versao(sha256);

-- Texto extraído, ancorado em página. A âncora é o que torna o achado auditável:
-- sem ela não se cumpre a regra R1 do AGENTS.md.
CREATE TABLE IF NOT EXISTS extracao (
    id                  INTEGER PRIMARY KEY,
    documento_versao_id INTEGER NOT NULL REFERENCES documento_versao(id),
    pagina              INTEGER NOT NULL,
    texto               TEXT    NOT NULL,
    metodo              TEXT    NOT NULL,   -- pdftext|ocr|html|planilha
    confianca           REAL,               -- 0..1, relevante em OCR
    extraido_em         TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (documento_versao_id, pagina)
);

-- Busca em texto completo sobre as extrações.
CREATE VIRTUAL TABLE IF NOT EXISTS extracao_fts USING fts5(
    texto,
    content='extracao',
    content_rowid='id',
    tokenize="unicode61 remove_diacritics 2"
);

-- ---------------------------------------------------------------------------
-- 3. PROCESSO — a espinha dorsal
-- ---------------------------------------------------------------------------

-- O valor do radar não está no edital isolado; está em ligar
-- planejamento → edital → disputa → contrato → aditivo → medição → pagamento.
-- Divergência raramente aparece dentro de um documento. Aparece ENTRE eles.
CREATE TABLE IF NOT EXISTS processo (
    id                  INTEGER PRIMARY KEY,
    municipio_id        INTEGER NOT NULL REFERENCES municipio(id),
    orgao_id            INTEGER REFERENCES orgao(id),
    tipo                TEXT    NOT NULL,   -- licitacao|dispensa|inexigibilidade|
                                            -- adesao_ata|contrato_direto|projeto_lei|convenio
    modalidade          TEXT,               -- pregao_eletronico|concorrencia|dispensa|...
    numero              TEXT,
    exercicio           INTEGER,
    objeto              TEXT,
    regime_juridico     TEXT,               -- lei_8666|lei_14133|rdc|lei_13303 — define
                                            -- QUAIS regras se aplicam (regra R4)
    valor_estimado      REAL,
    valor_homologado    REAL,
    valor_contratado    REAL,
    valor_pago          REAL,
    data_publicacao     TEXT,
    data_abertura       TEXT,
    data_homologacao    TEXT,
    data_assinatura     TEXT,
    situacao            TEXT,
    criado_em           TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em       TEXT,
    UNIQUE (municipio_id, tipo, numero, exercicio, orgao_id)
);
CREATE INDEX IF NOT EXISTS idx_processo_mun ON processo(municipio_id, exercicio, tipo);

CREATE TABLE IF NOT EXISTS processo_documento (
    processo_id     INTEGER NOT NULL REFERENCES processo(id),
    documento_id    INTEGER NOT NULL REFERENCES documento(id),
    papel           TEXT    NOT NULL,   -- edital|anexo|ata_sessao|contrato|aditivo|...
    -- Como a ligação foi feita: importa para saber o quanto confiar nela.
    vinculo_origem  TEXT    NOT NULL,   -- identificador|numero_processo|heuristica|manual
    confianca       REAL    NOT NULL DEFAULT 1.0,
    PRIMARY KEY (processo_id, documento_id, papel)
);

-- ---------------------------------------------------------------------------
-- 4. PESSOAS E EMPRESAS
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS entidade (
    id                  INTEGER PRIMARY KEY,
    tipo                TEXT    NOT NULL,   -- pj|pf
    documento_fiscal    TEXT    NOT NULL UNIQUE,  -- CNPJ ou CPF (mascarado p/ PF)
    razao_social        TEXT,
    nome_fantasia       TEXT,
    data_abertura       TEXT,
    capital_social      REAL,
    cnae_principal      TEXT,
    situacao_cadastral  TEXT,
    endereco_cep        TEXT,
    endereco_completo   TEXT,
    telefone            TEXT,
    email               TEXT,
    fonte_cadastro      TEXT,
    atualizado_em       TEXT
);

-- Sócios: a tabela que permite detectar licitantes ligados entre si.
CREATE TABLE IF NOT EXISTS societario (
    id              INTEGER PRIMARY KEY,
    entidade_id     INTEGER NOT NULL REFERENCES entidade(id),
    socio_id        INTEGER NOT NULL REFERENCES entidade(id),
    qualificacao    TEXT,
    data_entrada    TEXT,
    fonte           TEXT,
    UNIQUE (entidade_id, socio_id, data_entrada)
);

CREATE TABLE IF NOT EXISTS participacao (
    id              INTEGER PRIMARY KEY,
    processo_id     INTEGER NOT NULL REFERENCES processo(id),
    entidade_id     INTEGER NOT NULL REFERENCES entidade(id),
    papel           TEXT    NOT NULL,   -- licitante|vencedor|contratado|desclassificado|
                                        -- inabilitado|desistente
    valor_proposta  REAL,
    classificacao   INTEGER,
    motivo          TEXT,
    UNIQUE (processo_id, entidade_id, papel)
);

-- Sanções (CEIS/CNEP/CEPIM/TCE). Contratar empresa sancionada é achado direto.
CREATE TABLE IF NOT EXISTS sancao (
    id              INTEGER PRIMARY KEY,
    entidade_id     INTEGER NOT NULL REFERENCES entidade(id),
    cadastro        TEXT    NOT NULL,   -- ceis|cnep|cepim|tce_pr|cnj_improbidade
    tipo            TEXT,
    orgao_sancionador TEXT,
    data_inicio     TEXT,
    data_fim        TEXT,
    fonte_url       TEXT,
    coletado_em     TEXT NOT NULL
);

-- ---------------------------------------------------------------------------
-- 5. BASE NORMATIVA VERSIONADA  (regra R4)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS norma (
    id                  INTEGER PRIMARY KEY,
    chave               TEXT    NOT NULL UNIQUE,  -- ex.: 'lei_14133_art_75_i'
    ambito              TEXT    NOT NULL,   -- federal|estadual_pr|municipal
    diploma             TEXT    NOT NULL,   -- 'Lei 14.133/2021'
    dispositivo         TEXT    NOT NULL,   -- 'Art. 75, I'
    ementa              TEXT,
    texto               TEXT    NOT NULL,   -- texto literal conferido
    url_oficial         TEXT    NOT NULL,
    vigencia_inicio     TEXT    NOT NULL,
    vigencia_fim        TEXT,
    -- Valores que mudam por decreto/atualização (ex.: limite de dispensa).
    valor_numerico      REAL,
    valor_unidade       TEXT,
    conferido_em        TEXT    NOT NULL,
    conferido_por       TEXT    NOT NULL,
    observacao          TEXT
);
CREATE INDEX IF NOT EXISTS idx_norma_vigencia ON norma(vigencia_inicio, vigencia_fim);

CREATE TABLE IF NOT EXISTS jurisprudencia (
    id              INTEGER PRIMARY KEY,
    tribunal        TEXT    NOT NULL,   -- tce_pr|tcu|stj|tj_pr
    identificador   TEXT    NOT NULL,   -- nº do acórdão/processo, conferível
    data            TEXT,
    ementa          TEXT,
    tese            TEXT,               -- o que se extrai dele, em uma frase
    url_oficial     TEXT    NOT NULL,
    conferido_em    TEXT    NOT NULL,
    UNIQUE (tribunal, identificador)
);

-- ---------------------------------------------------------------------------
-- 6. VERIFICAÇÕES E ACHADOS
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS regra (
    id                  INTEGER PRIMARY KEY,
    codigo              TEXT    NOT NULL UNIQUE,  -- 'R001'
    nome                TEXT    NOT NULL,
    categoria           TEXT    NOT NULL,   -- licitacao|contrato|pagamento|engenharia|
                                            -- saude|educacao|legislativo|transparencia|integridade
    natureza            TEXT    NOT NULL,   -- deterministica|ia|mista
    descricao           TEXT    NOT NULL,
    -- O que a regra precisa para rodar. Se falta dado, ela NÃO gera achado:
    -- ela gera 'nao_aplicavel'. Silenciosamente não rodar é proibido.
    requisitos_dados    TEXT    NOT NULL,   -- JSON
    normas_chave        TEXT,               -- JSON: chaves em norma()
    severidade_base     TEXT    NOT NULL,   -- baixa|media|alta|indeterminada
    ativa               INTEGER NOT NULL DEFAULT 1,
    versao              TEXT    NOT NULL DEFAULT '1.0.0',
    fonte_metodologica  TEXT                -- de onde veio a trilha (TCU, CGU, OCDE...)
);

-- Log de execução: reprodutibilidade. Permite responder "por que esse processo
-- nunca foi apontado?" — talvez a regra nem tenha rodado nele.
CREATE TABLE IF NOT EXISTS execucao_regra (
    id              INTEGER PRIMARY KEY,
    regra_id        INTEGER NOT NULL REFERENCES regra(id),
    processo_id     INTEGER REFERENCES processo(id),
    documento_id    INTEGER REFERENCES documento(id),
    executada_em    TEXT    NOT NULL DEFAULT (datetime('now')),
    resultado       TEXT    NOT NULL,   -- achado|limpo|nao_aplicavel|erro
    motivo          TEXT,               -- por que não aplicável / qual erro
    versao_regra    TEXT    NOT NULL,
    duracao_ms      INTEGER
);
CREATE INDEX IF NOT EXISTS idx_exec_proc ON execucao_regra(processo_id, regra_id);

-- ===== A FICHA DE EVIDÊNCIA =====
-- Coração do sistema. Um achado que não preenche estes campos não sai daqui.
CREATE TABLE IF NOT EXISTS achado (
    id                  INTEGER PRIMARY KEY,
    codigo              TEXT    NOT NULL UNIQUE,  -- 'CG-2026-0001'
    municipio_id        INTEGER NOT NULL REFERENCES municipio(id),
    processo_id         INTEGER REFERENCES processo(id),
    regra_id            INTEGER REFERENCES regra(id),

    titulo              TEXT    NOT NULL,
    -- Os três campos que a regra R2 do AGENTS.md obriga a separar:
    fatos_documentais   TEXT    NOT NULL,   -- só o que o documento diz
    hipoteses           TEXT,               -- a leitura proposta, marcada como leitura
    lacunas             TEXT    NOT NULL,   -- o que falta verificar

    consequencia_possivel TEXT,             -- efeito prático SE a hipótese proceder
    hipotese_alternativa  TEXT,             -- a explicação legítima que pode existir
                                            -- (preenchida pela revisão adversarial)

    -- Eixos separados de propósito: gravidade ≠ certeza. Um achado gravíssimo com
    -- evidência fraca não pode virar denúncia; um achado leve e certeiro pode
    -- virar um bom pedido de esclarecimento.
    gravidade           TEXT    NOT NULL,   -- baixa|media|alta|indeterminada
    forca_evidencia     TEXT    NOT NULL,   -- fraca|moderada|forte
    urgencia            TEXT    NOT NULL,   -- pode haver prazo: edital em curso
    prazo_limite        TEXT,               -- ex.: data da abertura das propostas

    regime_aplicavel    TEXT,               -- qual regime jurídico regia o fato
    origem              TEXT    NOT NULL,   -- deterministica|ia|mista|manual

    status              TEXT    NOT NULL DEFAULT 'novo',
        -- novo → em_revisao_adversarial → aguardando_revisao_humana →
        -- aprovado | improcedente | arquivado | corrigido_pelo_municipio | encaminhado
    criado_em           TEXT    NOT NULL DEFAULT (datetime('now')),
    atualizado_em       TEXT
);
CREATE INDEX IF NOT EXISTS idx_achado_status ON achado(status, gravidade, criado_em DESC);

-- Âncora obrigatória. Sem linha aqui, o achado é inválido (ver trigger abaixo).
CREATE TABLE IF NOT EXISTS achado_evidencia (
    id                  INTEGER PRIMARY KEY,
    achado_id           INTEGER NOT NULL REFERENCES achado(id) ON DELETE CASCADE,
    documento_versao_id INTEGER NOT NULL REFERENCES documento_versao(id),
    pagina              INTEGER,
    trecho              TEXT,               -- citação literal
    observacao          TEXT,
    ordem               INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS achado_norma (
    achado_id       INTEGER NOT NULL REFERENCES achado(id) ON DELETE CASCADE,
    norma_id        INTEGER NOT NULL REFERENCES norma(id),
    -- Não basta citar: é preciso explicar por que aquele dispositivo se aplica
    -- àquele fato, naquela data.
    explicacao      TEXT    NOT NULL,
    PRIMARY KEY (achado_id, norma_id)
);

CREATE TABLE IF NOT EXISTS achado_jurisprudencia (
    achado_id           INTEGER NOT NULL REFERENCES achado(id) ON DELETE CASCADE,
    jurisprudencia_id   INTEGER NOT NULL REFERENCES jurisprudencia(id),
    explicacao          TEXT,
    PRIMARY KEY (achado_id, jurisprudencia_id)
);

-- ---------------------------------------------------------------------------
-- 7. REVISÃO E ENCAMINHAMENTO — a porta para o mundo externo
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS revisao (
    id              INTEGER PRIMARY KEY,
    achado_id       INTEGER NOT NULL REFERENCES achado(id),
    etapa           TEXT    NOT NULL,   -- adversarial|juridica|contabil|engenharia|final
    revisor         TEXT    NOT NULL,   -- nome/identificação; 'agente:<nome>' se automática
    humano          INTEGER NOT NULL,   -- 1 = pessoa. Só revisão humana libera envio.
    decisao         TEXT    NOT NULL,   -- mantem|reduz_gravidade|improcedente|
                                        -- precisa_mais_dados|encaminhar
    parecer         TEXT    NOT NULL,
    revisado_em     TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_revisao_achado ON revisao(achado_id, revisado_em);

CREATE TABLE IF NOT EXISTS peca (
    id                  INTEGER PRIMARY KEY,
    achado_id           INTEGER NOT NULL REFERENCES achado(id),
    tipo                TEXT    NOT NULL,   -- pedido_esclarecimento|impugnacao|
                                            -- pedido_lai|representacao_tce|denuncia_tce|
                                            -- representacao_mp|requerimento_camara
    orgao_destino       TEXT    NOT NULL,
    conteudo_markdown   TEXT    NOT NULL,
    -- Nada sai sem estes dois. O gerador só cria rascunho.
    aprovada_por_humano INTEGER NOT NULL DEFAULT 0,
    aprovada_em         TEXT,
    aprovada_por        TEXT,
    criada_em           TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS encaminhamento (
    id              INTEGER PRIMARY KEY,
    peca_id         INTEGER NOT NULL REFERENCES peca(id),
    canal           TEXT    NOT NULL,   -- e-protocolo|ouvidoria|email|presencial
    protocolo       TEXT,
    enviado_em      TEXT    NOT NULL,
    enviado_por     TEXT    NOT NULL,   -- sempre uma PESSOA
    comprovante_path TEXT
);

CREATE TABLE IF NOT EXISTS resposta (
    id                  INTEGER PRIMARY KEY,
    encaminhamento_id   INTEGER NOT NULL REFERENCES encaminhamento(id),
    recebida_em         TEXT    NOT NULL,
    teor                TEXT    NOT NULL,   -- acolhida|parcial|rejeitada|em_analise|sem_resposta
    resumo              TEXT,
    documento_id        INTEGER REFERENCES documento(id),
    -- Fechamento do ciclo: o município corrigiu? Esse é o resultado que interessa.
    houve_correcao      INTEGER NOT NULL DEFAULT 0,
    descricao_correcao  TEXT
);

-- ---------------------------------------------------------------------------
-- 8. INTEGRIDADE — o banco recusa achado sem evidência
-- ---------------------------------------------------------------------------

-- Regra R1 do AGENTS.md, aplicada pelo banco e não pela boa vontade do programador.
CREATE TRIGGER IF NOT EXISTS trg_achado_exige_evidencia
BEFORE UPDATE OF status ON achado
WHEN NEW.status IN ('aguardando_revisao_humana','aprovado','encaminhado')
 AND (SELECT COUNT(*) FROM achado_evidencia WHERE achado_id = NEW.id) = 0
BEGIN
    SELECT RAISE(ABORT, 'achado sem evidencia ancorada nao pode avancar de status');
END;

-- Nenhuma peça é aprovada sem revisão humana registrada.
CREATE TRIGGER IF NOT EXISTS trg_peca_exige_revisao_humana
BEFORE UPDATE OF aprovada_por_humano ON peca
WHEN NEW.aprovada_por_humano = 1
 AND (SELECT COUNT(*) FROM revisao r
       WHERE r.achado_id = NEW.achado_id AND r.humano = 1 AND r.etapa = 'final') = 0
BEGIN
    SELECT RAISE(ABORT, 'peca exige revisao humana final registrada antes da aprovacao');
END;

-- ---------------------------------------------------------------------------
-- 9. VISÕES DE COBERTURA — honestidade sobre o que o radar NÃO viu
-- ---------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_saude_fontes AS
SELECT  f.chave,
        f.nome,
        f.ativo,
        f.ultima_coleta_ok,
        CAST(julianday('now') - julianday(f.ultima_coleta_ok) AS INTEGER) AS dias_sem_coleta,
        (SELECT status FROM coleta c WHERE c.fonte_id = f.id
          ORDER BY iniciada_em DESC LIMIT 1) AS ultimo_status,
        f.ultima_coleta_erro
FROM fonte f
WHERE f.ativo = 1;

CREATE VIEW IF NOT EXISTS v_processos_incompletos AS
SELECT  p.id,
        p.numero,
        p.exercicio,
        p.objeto,
        EXISTS(SELECT 1 FROM processo_documento pd WHERE pd.processo_id = p.id
                AND pd.papel = 'edital')   AS tem_edital,
        EXISTS(SELECT 1 FROM processo_documento pd WHERE pd.processo_id = p.id
                AND pd.papel = 'contrato') AS tem_contrato,
        EXISTS(SELECT 1 FROM processo_documento pd WHERE pd.processo_id = p.id
                AND pd.papel = 'ata_sessao') AS tem_ata
FROM processo p;
