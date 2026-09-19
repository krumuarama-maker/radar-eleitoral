# Arquitetura

## Decisões e por quê

### SQLite, não Postgres
Projeto de uma pessoa, volume de um município pequeno. Arquivo único, backup
trivial, zero infraestrutura, FTS5 embutido. O esquema evita recursos exclusivos
do SQLite justamente para deixar a migração aberta: quando o painel precisar
servir várias pessoas, ou quando entrarem mais municípios, troca-se o conector.

### Documento tem identidade e versões
`documento` é a identidade estável ("Edital 12/2026"); `documento_versao` é o
arquivo. Edital retificado **não sobrescreve**: vira versão 2. Detectar a
retificação é, por si, um sinal relevante — e a versão anterior é a prova de que
a cláusula existiu.

### Nada se apaga
Achado derrubado vira `improcedente`, não sumiço. Correção do município é evento
registrado. O histórico é o que calibra as regras e o que demonstra
imparcialidade quando alguém acusar o projeto de perseguição.

### Processo é a espinha dorsal
Divergência raramente aparece dentro de um documento. Aparece **entre**
documentos de fases diferentes: o que se planejou, o que se publicou, o que se
contratou, o que se aditou, o que se mediu, o que se pagou. Por isso
`processo_documento` guarda `vinculo_origem` e `confianca` — vínculo feito por
heurística vale menos que vínculo por identificador, e o achado que depende dele
tem que nascer mais fraco.

### Órgão, não município
Prefeitura, Câmara e cada fundo licitam com CNPJ próprio. Consolidar só o CNPJ
da Prefeitura torna invisível o fracionamento mais comum: três compras do mesmo
objeto, feitas por três entes, no mesmo mês, cada uma abaixo do limite.

### Determinístico separado de IA
Pastas diferentes, testes diferentes, e tipos de retorno diferentes. O que dá
para calcular não se pergunta a um modelo — é mais lento, mais caro e menos
confiável. E regra determinística pode gerar achado sozinha; análise de IA, não:
ela passa obrigatoriamente pela revisão adversarial.

### Quatro desfechos, nunca `None`
`ACHADO`, `LIMPO`, `NAO_APLICAVEL`, `SEM_DADOS`. A distinção entre `LIMPO` e
`SEM_DADOS` é a diferença entre "está correto" e "não fui capaz de olhar".
Colapsar os dois é como um sistema de fiscalização começa a mentir sem que
ninguém perceba.

## Fluxo

```
fonte ──▶ coletor ──▶ preservação ──▶ extração ──▶ vinculação
                         │                              │
                     hash + manifesto              processo formado
                         │                              │
                         └──────────▶ banco ◀───────────┘
                                        │
                              ┌─────────┴─────────┐
                         determinístico         IA
                              └─────────┬─────────┘
                                        ▼
                            revisão adversarial
                                        ▼
                            verificação de citações
                                        ▼
                               REVISÃO HUMANA
                                        ▼
                                     minuta
```

## Onde cada coisa mora

| Camada | Pasta | Regra que a governa |
|---|---|---|
| Coleta | `src/radar/coleta/` | preservação é obrigatória (`ColetorBase.preservar`) |
| Extração | `src/radar/extracao/` | texto sempre ancorado em página |
| Análise determinística | `src/radar/analise/deterministico/` | um arquivo, uma regra, um teste |
| Base normativa | `src/radar/analise/normas.py` + `normas/` | vigência e conferência |
| Achados | `src/radar/achados/` | a ficha valida a si mesma |
| Peças | `src/radar/pecas/` | só rascunho |
| Painel | `src/radar/painel/` | mostra cobertura junto com achados |
