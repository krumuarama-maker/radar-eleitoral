# Roteiro de verificação manual — Cidade Gaúcha/PR

> **Para quando o radar não pode rodar.** Este documento não traz achados: traz
> onde olhar e o que procurar. Serve a quem vai abrir os portais no navegador e
> examinar com os próprios olhos — um auditor, um contador, um vereador.
>
> Todas as URLs abaixo **vieram de índice de buscador, não de acesso real.**
> Nenhuma foi aberta e confirmada. Se alguma não responder, isso é informação
> (ver seção 6), não erro deste roteiro.

Município: Cidade Gaúcha – PR · IBGE 4105607
CNPJ da Prefeitura: 75.377.200/0001-67 *(indexado, a conferir)*
CNPJ da Câmara: 01.201.556/0001-09 *(indexado, a conferir)*

---

## 1. Comece pelo PNCP — é onde tudo está reunido

Sob a Lei 14.133, publicar no PNCP é condição de eficácia do ato. Quem procura
contratação municipal começa aqui, não no site da Prefeitura.

**Busca pela página:** `https://pncp.gov.br` → Consultas → filtrar por município.

**Pelo endereço direto de uma contratação:**
`https://pncp.gov.br/app/editais/{cnpj}/{ano}/{sequencial}`
Ex.: `https://pncp.gov.br/app/editais/75377200000167/2026/12`

> Atenção ao erro clássico: o `numeroControlePNCP` (formato
> `75377200000167-1-000012/2026`) é identificador, **não** caminho de URL. Colar
> ele no endereço não funciona.

### O que olhar em cada contratação

| # | Verificação | O que seria achado |
|---|---|---|
| 1 | **Quantos licitantes participaram?** | Um só, em pregão ou concorrência. É o indicador mais robusto da literatura de contratação pública — e o mais barato de checar. |
| 2 | **Prazo entre publicação e abertura** | Abaixo do mínimo da modalidade. Prazo curto favorece quem já sabia do certame. |
| 3 | **Quem cotou na pesquisa de preços venceu?** | Fornecedor que forneceu cotação ou estudo técnico e depois ganhou a disputa. Achado forte e objetivo. |
| 4 | **Datas dos documentos** | ETP datado depois do Termo de Referência; TR depois do edital; cotação datada depois do TR. Cronologia invertida indica documento feito para justificar decisão já tomada. |
| 5 | **Quem assinou o quê** | Mesma pessoa assinando ETP, TR, edital e ata. Ausência de segregação de funções. |
| 6 | **Exigências de habilitação** | Atestado acima de 50% do quantitativo; vínculo por CTPS do responsável técnico; vistoria obrigatória sob pena de inabilitação; capital social acima de 10% do valor estimado; sede ou filial no município. |
| 7 | **Marca ou modelo no objeto** | Menção a fabricante sem "ou similar"; combinação de atributos que só um produto atende. |
| 8 | **Desclassificações** | Menor proposta desclassificada num certame de menor preço; todas desclassificadas menos a vencedora. |

---

## 2. Dispensas e inexigibilidades — onde mora o risco

No PNCP, filtre pelas modalidades **Dispensa** e **Inexigibilidade**. Num
município pequeno é aqui que o volume de risco se concentra, porque é a porta
por onde se evita a disputa.

### A checagem que quase ninguém faz

**Some as dispensas de objeto parecido, de TODOS os órgãos do município.**

Não só da Prefeitura. Câmara, Fundo Municipal de Saúde, Fundo de Assistência
Social, FUNDEB — cada um tem CNPJ próprio e licita sozinho. O fracionamento
clássico não se esconde dentro de um órgão: ele se dispersa entre eles.

Três compras de medicamentos no mesmo trimestre, uma por ente, cada uma
confortavelmente abaixo do limite. Isoladas, todas regulares. Somadas, uma
licitação que deveria ter existido.

> **Antes de apontar:** confira qual era o limite de dispensa **na data da
> compra**. Ele foi atualizado por decreto mais de uma vez desde 2021, e aplicar
> o valor de hoje a uma compra de 2022 produz acusação que cai em uma linha.

### Outras checagens de contratação direta

- Atestado de exclusividade **emitido pelo próprio fornecedor** (inexigibilidade)
- Emergência que se repete: a mesma "urgência" todo ano indica falta de planejamento, não imprevisto
- Mesmo fornecedor vencendo várias dispensas análogas no mesmo órgão

---

## 3. Execução contratual — o terreno vazio

Os robôs dos órgãos de controle olham o edital. Quase ninguém acompanha o que
acontece **depois da assinatura** — e é lá que o dinheiro se perde.

| Verificação | O que seria achado |
|---|---|
| Soma dos aditivos sobre o valor **inicial** | Acima do limite legal. Cuidado: a base é o valor original, não o já aditado — errar isso inverte o resultado. |
| Data do primeiro aditivo | Muito próxima à assinatura do contrato. Indica planejamento deliberadamente incompleto. |
| Prorrogações sucessivas | "Serviço de natureza contínua" usado para nunca mais licitar. |
| Soma dos pagamentos × valor contratado + aditivos | Pago acima do contratado. |
| Nota fiscal × contrato × empenho | NF com data anterior ao contrato ou ao empenho. |
| Ordem cronológica de pagamentos | Fornecedor pago à frente de outros sem justificativa publicada. O marco é a data da **liquidação**, não a da nota fiscal. |

Fontes: Portal da Transparência do município e os dados do SIM-AM no TCE-PR
(seção 5).

---

## 4. Obras e engenharia

- **Projeto básico existe e é suficiente?** É a causa-raiz da maioria dos aditivos.
- **Critério de aceitabilidade de preços unitários E global** — é obrigação, não faculdade.
- **BDI explicitado** e dentro de faixa defensável.
- **Jogo de planilha:** preço unitário alto em itens que depois crescem por aditivo, e baixo nos que somem. Só aparece comparando planilha licitada × aditivos.
- **Medições:** compatíveis com o prazo decorrido? Há medição de item que depende de etapa anterior não medida?

> Preço acima do SINAPI **não é sobrepreço**. SINAPI é referência, não teto:
> região, acesso, porte e prazo justificam variação. O achado é a **divergência
> não justificada** — e sempre comparando com a tabela **da data-base do
> orçamento**, nunca com a de hoje.

---

## 5. Fontes de Cidade Gaúcha

Todas **indexadas, não verificadas**. Confirme antes de citar.

| Fonte | Endereço | Por que importa |
|---|---|---|
| **Diário Oficial próprio** | `diario.cidadegaucha.pr.gov.br` | Maior densidade de informação. Publica atos do Executivo **e** do Legislativo. Avisos, homologações, extratos de contrato e aditivos passam todos por aqui. PDFs em `/storage/diarios/{ano}/{mês}/diario{N}-signed.pdf` |
| **Contratos e aditivos** | `cidadegaucha.pr.gov.br/index.php?meio=172139` | ~860 contratos em ~108 páginas (`&pag=N`) |
| **Portal da Transparência** | `cidadegaucha.govbr.cloud/pronimtb/` | Produto PRONIM TB (GOVBR). Despesas, empenhos, liquidações, pagamentos |
| **Mural de Licitações TCE-PR** | `servicos.tce.pr.gov.br/tcepr/municipal/aml/ConsultarProcessoCompraWeb.aspx` | Municípios do PR são **obrigados** a publicar. Licitação que aparece no diário mas não no Mural, ou publicada fora do prazo, é achado objetivo |
| **Dados do SIM-AM** | `pit.tce.pr.gov.br/Dados/DadosConsulta/Consulta` | Dados estruturados de **todas as entidades** do município — resolve a lista de CNPJs dos fundos |
| **Câmara Municipal** | `cmcidadegaucha.pr.gov.br/?mod=busca&pagina=N&q=&tabela=` | Não há sistema de tramitação: proposições são PDF solto |
| **e-SIC / Ouvidoria** | `cidadegaucha.1doc.com.br` | Canal para pedir o que não está publicado |
| **Validação cruzada** | `alertalicitacao.com.br/!municipios/4105607` | Agregador independente: mostra licitação que se perdeu nas outras fontes |

---

## 6. Documento que não abre também é informação

Se uma fonte não responder, ou um PDF estiver ilegível, **anote**. Não é
obstáculo ao trabalho: é o trabalho.

A frase correta nunca é *"o município não publicou"*. É:

> *"não localizado nas fontes consultadas em [data], a saber: [lista]"*

E o encaminhamento não é denúncia — é **pedido de informação via LAI**, pelo
e-SIC. O prazo de resposta e o rito de recurso estão na Lei 12.527. Documento
negado ou ignorado vira, aí sim, achado de transparência com prova própria.

---

## 7. Antes de levar qualquer coisa adiante

**A escada, na ordem.** Pular degrau enfraquece o seguinte:

```
LAI → esclarecimento → impugnação → representação ao TCE-PR → Ministério Público
```

O pedido de esclarecimento produz resposta oficial. Se ela for evasiva, essa
omissão vira peça — e é ela que demonstra o `periculum in mora` numa futura
cautelar. A impugnação negada demonstra que a via administrativa foi tentada.
O conjunto — perguntou, foi respondido de forma evasiva, impugnou, foi negado,
e a irregularidade permaneceu — é o material de que o dolo é feito.

**Erro formal não é improbidade.** Sem indício de dolo, dano ao erário e fato
dentro do prazo prescricional, o caminho é o Tribunal de Contas. Mandar erro
formal ao Ministério Público produz arquivamento e queima credibilidade com a
promotoria local, que é quem vai receber os próximos casos.

### Três perguntas que derrubam a maioria dos apontamentos ruins

1. **Isto é ilegalidade, ou decisão administrativa de que eu discordo?**
   Escolher entre duas modalidades permitidas, priorizar uma obra, fixar prazo
   dentro do limite legal — é governo, não irregularidade.
2. **A Procuradoria do município derruba isto em um parágrafo?**
   Se sim, faltou procurar a errata, o esclarecimento publicado ou a exceção legal.
3. **Eu conferi o regime jurídico?**
   Contrato firmado sob a Lei 8.666/93 continua sob ela durante toda a sua
   duração, inclusive nos aditivos. Aplicar a Lei 14.133 a ele é o erro mais
   comum e o mais fácil de derrubar.

---

## 8. Escreva o fato, nunca o rótulo

| Não escreva | Escreva |
|---|---|
| "houve superfaturamento" | "o preço unitário contratado foi R$ X; a mediana de N contratações comparáveis no período foi R$ Y" |
| "o edital foi direcionado" | "o item 7.3 exige [citação literal]; das N empresas do ramo consultadas, M atendem" |
| "o prefeito agiu com dolo" | "em [data] o controle interno registrou alerta; a cláusula foi mantida na republicação de [data]" |

Rótulo é conclusão jurídica, e conclusão jurídica é do órgão — não de quem
aponta. A peça que descreve o fato com precisão é mais forte que a que grita, e
tem a vantagem de não ser respondida com pedido de retratação.
