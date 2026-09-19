# Pendências de conferência

> **Tudo neste repositório que afirma um fato sobre o mundo externo — uma URL,
> um prazo legal, um CNPJ, um parâmetro de API — veio de pesquisa secundária.
> Nada foi verificado na fonte primária.**

Isso não é uma ressalva de rodapé. É a informação mais importante do projeto
neste momento, e ela está aqui porque seria incoerente construir um sistema cuja
regra central é "não afirme o que não conferiu" e começar afirmando coisas não
conferidas.

## Por que nada foi verificado

O ambiente em que este projeto foi montado bloqueia saída de rede por política:
toda tentativa de alcançar `pncp.gov.br`, `tce.pr.gov.br`, `planalto.gov.br`,
`cidadegaucha.pr.gov.br` e similares recebe `403` no CONNECT do proxy. Somente
busca na web funcionou — e busca devolve o que o índice do buscador guardou, não
o que o servidor responde hoje.

Então toda URL aqui é **indexada**, não **verificada**. A distinção está
registrada em `config/municipios/cidade-gaucha.yaml`, campo `verificacao`.

## Como fechar estas pendências

De qualquer máquina com rede livre:

```bash
python scripts/smoke_fontes.py            # converte 'indexada' em 'verificada'
curl -sS https://pncp.gov.br/api/consulta/v3/api-docs -o /tmp/pncp_consulta.json
curl -sS https://pncp.gov.br/api/pncp/v3/api-docs     -o /tmp/pncp_core.json
```

---

## A. Bloqueiam a primeira coleta

| # | O que conferir | Onde | Efeito se estiver errado |
|---|---|---|---|
| A1 | Todas as URLs de `config/municipios/cidade-gaucha.yaml` respondem? | `scripts/smoke_fontes.py` | Coletor quebra em silêncio |
| A2 | Nomes exatos dos parâmetros da API do PNCP | `pncp.gov.br/api/consulta/v3/api-docs` | Consulta devolve vazio e o radar reporta "município sem licitações" |
| A3 | Teto real de `tamanhoPagina` (50? 500?) | mesmo `api-docs` | Paginação trunca em silêncio; metade dos processos some |
| A4 | Caminhos dos endpoints de `/atualizacao` | mesmo `api-docs` | Sem sincronização incremental; só varredura completa |
| A5 | CNPJ da Prefeitura (75.377.200/0001-67) | Receita / PNCP | Coleta do município errado |
| A6 | CNPJs dos fundos municipais | SIM-AM / TCE-PR | Fracionamento entre entes fica invisível — a irregularidade mais comum |
| A7 | Código IBGE 4105607 é mesmo Cidade Gaúcha? | API do IBGE | 4105508 é Cianorte. Confundir = fiscalizar o município errado |
| A8 | `robots.txt` de cada domínio | direto | Coleta pode violar limite declarado |
| A9 | Faixa atual de edições do Diário Oficial | índice do diário | Varredura começa no ponto errado |
| A10 | Os `meio=` de licitações, obras, convênios e emendas no site da Prefeitura | menu da home | Coleta parcial do portal |

## B. Bloqueiam a geração de peça

Enquanto pendentes, `BaseNormas.fundamento()` **recusa** montar a citação.
Este bloqueio é proposital: peça com artigo não conferido é risco para quem
assina.

| # | O que conferir | Fonte oficial |
|---|---|---|
| B1 | Texto literal da Lei 14.133, art. 164 (impugnação e esclarecimento) | Planalto |
| B2 | Texto literal do art. 170, §4º (legitimidade para representar) — **prioridade máxima**, é a base da legitimidade de quase toda peça | Planalto |
| B3 | Texto literal dos arts. 190 e 191 (transição 8.666 → 14.133) | Planalto |
| B4 | Texto literal do art. 165 (recursos e prazos) | Planalto |
| B5 | Artigos da Lei Orgânica do TCE-PR sobre denúncia e representação: requisitos, legitimidade, admissibilidade | PDF consolidado LO+RI no site do TCE-PR |
| B6 | Prazos do Mural na redação **original** da IN 156/2020 | site do TCE-PR |
| B7 | Data exata de início de vigência da IN 208/2026 | a própria IN |
| B8 | Limites de dispensa vigentes em cada ano de 2021 a hoje | Lei 14.133 + decretos de atualização |
| B9 | Limite percentual de aditivos e a base de cálculo, por regime | Lei 14.133 e Lei 8.666 |
| B10 | Prazos da LAI e do recurso | Lei 12.527 |
| B11 | Requisitos formais da representação ao TCE-PR (exige título de eleitor?) | Regimento Interno do TCE-PR |

## C. Afetam a calibragem das regras

| # | O que conferir | Por quê |
|---|---|---|
| C1 | Guia dos 73 indicadores da Open Contracting Partnership | Fórmulas exatas dos indicadores estatísticos |
| C2 | Licença do repositório `skills-licitacoes` | **Sem licença declarada não há permissão de reuso.** Abrir issue pedindo MIT/CC-BY antes de incorporar texto |
| C3 | Manuais de auditoria de obras da CGU e do IBRAOP | Trilhas de engenharia vieram de resumo |
| C4 | Acórdãos e súmulas citados no catálogo | Todos marcados `[conferir]` — nenhum foi recuperado na fonte |
| C5 | Janela temporal que a CGU adota para apurar fracionamento | Sem ela, FRAC-01 pode acusar indevidamente |
| C6 | Comunicado Transferegov nº 23/2026 sobre acesso às APIs | Pode ter passado a exigir credencial |
| C7 | Cobertura do Querido Diário para Cidade Gaúcha | Define se dá para reusar a API ou se é preciso raspador próprio |
| C8 | Domínio atual da API do Querido Diário | O host mudou em 2026; toda documentação na web ainda aponta para o antigo |

## D. Sobre o município

| # | O que conferir |
|---|---|
| D1 | Comarca e promotoria com atribuição — endereçamento correto de qualquer representação ao MP |
| D2 | Se a Câmara publica no PNCP com CNPJ próprio |
| D3 | Se a Câmara tem portal de transparência separado |
| D4 | Se o município publica no Diário Oficial dos Municípios do PR além do próprio |
| D5 | População atual, para cálculos per capita |
| D6 | Se o portal de transparência expõe JSON ou exige raspagem de HTML |

---

## Regra de ouro

> **Nenhum achado gerado com dado desta lista deve virar peça antes que a linha
> correspondente esteja conferida.**

O sistema aplica parte disso sozinho: a base normativa recusa citação não
conferida, e a `Ficha` recusa achado sem evidência ancorada. O resto depende de
quem opera.

Quando uma linha for conferida, remova-a daqui e registre no arquivo de origem
quem conferiu e quando. Este documento deve encolher — se não estiver
encolhendo, o projeto está andando sobre fundação que ninguém checou.
