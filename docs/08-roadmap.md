# Roadmap e coordenação

> **Antes de começar qualquer frente, leia este arquivo. Ao terminar, atualize-o.**
> É o que evita que Codex e Claude Code trabalhem no mesmo arquivo ao mesmo tempo.
> Uma frente por branch.

## Estado em 19/09/2026

| Frente | Estado | Onde |
|---|---|---|
| Constituição e travas | pronto | `AGENTS.md` |
| Modelo da ficha de evidência | pronto, testado | `src/radar/achados/modelo.py` |
| Esquema do banco | pronto, com triggers | `src/radar/db/schema.sql` |
| Base coletora com preservação | pronto | `src/radar/coleta/base.py` |
| Coletor PNCP | escrito, **nunca executado contra a API real** | `src/radar/coleta/pncp.py` |
| Base normativa com vigência | pronto, testado | `src/radar/analise/normas.py` |
| Motor determinístico | pronto | `src/radar/analise/deterministico/base.py` |
| Regra R001 (sancionado) | pronto, 10 testes | `r001_contratado_sancionado.py` |
| Catálogo de verificações | 114 catalogadas, 1 implementada | `config/catalogo-verificacoes.yaml` |
| Skills e agentes | 3 skills, 4 agentes | `.claude/` |
| CLI | funcional | `src/radar/cli.py` |
| Extração de PDF | **não começou** | `src/radar/extracao/` |
| Vinculação processo↔documento | **não começou** | — |
| Painel | **não começou** | `src/radar/painel/` |

---

## Etapa 0 — Conferir a fundação (bloqueia tudo)

Nada abaixo faz sentido antes disto. Ver `docs/09-pendencias-de-conferencia.md`.

- [ ] Rodar `scripts/smoke_fontes.py` de máquina com rede livre
- [ ] Baixar os dois OpenAPI do PNCP e conferir nomes de parâmetro e teto de página
- [ ] Confirmar CNPJ da Prefeitura e código IBGE
- [ ] Conferir os dispositivos da seção B de `09-pendencias`, começando pelo
      art. 170 §4º da Lei 14.133 — é a base da legitimidade de quase toda peça

## Etapa 1 — Primeira coleta real

- [ ] Rodar o coletor do PNCP contra os últimos 12 meses, modalidades 6, 8 e 9
- [ ] Verificar quantos processos apareceram e se bate com o portal
- [ ] Coletor do Diário Oficial próprio (maior densidade de informação do município)
- [ ] Baixar os dados do SIM-AM no PIT do TCE-PR — resolve os CNPJs dos fundos

## Etapa 2 — Extração e vinculação

Sem isto as regras não têm contexto para avaliar. É o gargalo atual.

- [ ] Extração de PDF com página e posição (pdfplumber / PyMuPDF)
- [ ] OCR para documento escaneado
- [ ] Vinculação processo ↔ documentos, com `vinculo_origem` registrado
- [ ] Diff entre versões de edital (detecta retificação — regra PRO-08)

## Etapa 3 — As 30 regras do alicerce

Prioridade 1 do catálogo, todas determinísticas puras. Ordem sugerida, da mais
barata para a mais cara:

- [ ] PRO-02 proposta única em modalidade competitiva *(o indicador mais robusto da literatura)*
- [ ] PRO-01 prazo abaixo do mínimo
- [ ] PRO-07 contratação ausente do PNCP
- [ ] ADI-01 aditivos acima do limite · ADI-04 aditivo muito próximo do contrato
- [ ] FRAC-01 a 05 fracionamento *(rodar sobre TODOS os órgãos, não só a Prefeitura)*
- [ ] PAG-01, 02, 04, 06 pagamentos — **o espaço vazio, e o diferencial**
- [ ] PRO-03, PRO-04, PRO-06 julgamento
- [ ] PRO-15 Mural do TCE-PR *(bloqueada até B6 de `09-pendencias`)*
- [ ] DIR-29 cotação de quem venceu · DIR-30 cronologia invertida
- [ ] SOB-06 cotação datada depois do TR

## Etapa 4 — Base CNPJ + quadro societário

**Maior retorno marginal do projeto.** Uma integração destrava ~15 regras.

- [ ] Carregar dump da Receita (ou subir MinhaReceita) com `Socios.csv`
- [ ] CONL-01, 02, 03, 07 vínculos entre licitantes
- [ ] EMP-01 a 07 empresa de fachada
- [ ] Baixar CEIS/CNEP em CSV diário e ligar na R001 *(já implementada, falta o dado)*

## Etapa 5 — Revisão e painel

- [ ] Executor que roda o registro de regras sobre o banco
- [ ] Integração do revisor adversarial no pipeline
- [ ] Painel: achado, evidência, documento original, revisão, **e cobertura**
- [ ] Geração de minuta a partir da ficha aprovada

## Etapa 6 — Ampliação

- [ ] SOB-14 medicamento acima do PMVG *(teto legal — achado binário e forte)*
- [ ] Indicadores estatísticos com fences de Tukey
- [ ] CONL-13 metadados de PDF *(barato e quase ninguém faz)*
- [ ] Engenharia: SINAPI versionado por mês, jogo de planilha
- [ ] Legislativo, emendas, saúde e educação

---

## Divisão sugerida

| Frente | Quem costuma tocar |
|---|---|
| Coletores, extração, banco, painel, infra | Codex |
| Regras de análise, base normativa, minutas, revisão adversarial | Claude Code |
| Conferência de normas e de fontes | **pessoa** — não delegue |
| Testes | quem escreveu |

A terceira linha não é preciosismo. Conferir se um artigo existe e estava
vigente é exatamente o tipo de tarefa em que um modelo erra com confiança, e o
erro só aparece quando a peça já foi protocolada.
