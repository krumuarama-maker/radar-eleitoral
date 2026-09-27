# Pauta de verificação — Cidade Gaúcha/PR · 27/09/2026

> **Isto não é uma denúncia, nem um laudo, nem uma lista de irregularidades.**
> São perguntas fundamentadas e a indicação de quais documentos buscar para
> respondê-las. Nenhum item foi conferido contra documento original.

## Procedência do dado — leia antes de qualquer conclusão

| | |
|---|---|
| Origem | texto capturado do agregador `licinexus.com.br/licitacoes/pr/cidade-gaucha/` |
| Capturado em | 27/09/2026, colado do navegador pelo usuário |
| Natureza | **fonte secundária** — agregador de dados do PNCP, não o PNCP |
| Preservado em | `dados/originais/4105607/2026/09/fd31da7f73b75438….txt` |
| sha256 | `fd31da7f73b754388ca0fdfc6dc5e41078f6639b7e670efb15f79c7546d75cdf` |

**O que este dado NÃO contém**, e que por isso limita tudo abaixo:

- data de abertura/encerramento das propostas → **impossível verificar prazo**
- lista de participantes → **impossível verificar proposta única**
- número do processo e `numeroControlePNCP` → não dá para vincular ao PNCP
- valores sem centavos, aparentemente arredondados
- nenhum documento: sem edital, termo de referência, ata ou contrato

## Resultado da análise automática

O sistema rodou 3 regras sobre 20 processos — 60 execuções — e produziu:

```
ACHADOS: 0   |   limpos: 0   |   sem dados: 18   |   não aplicável: 42
COBERTURA EFETIVA: 0%
```

**Zero achados com zero por cento de cobertura não significa que está tudo
certo. Significa que este dado não permite verificar nada.** Os motivos que o
próprio sistema registrou:

| Regra | Resultado | Por quê |
|---|---|---|
| R001 sancionado | não aplicável (20x) | nenhum vencedor registrado no dado |
| R002 proposta única | sem dados (16x) | nenhum participante registrado |
| R003 fracionamento | sem dados (2x) | limite de dispensa não conferido na fonte oficial |

## Panorama da janela

Período capturado: **21/07/2026 a 21/09/2026** (62 dias), 20 contratações.
A página declara 27 nos últimos 90 dias — então há ~7 fora desta lista.

| | |
|---|---|
| Valor estimado total da janela | R$ 4.951.834 |
| Registro de preços | 8 de 20 · R$ 2.313.648 |
| Contratação direta (dispensa + inexigibilidade) | 4 de 20 · R$ 163.581 |
| **Anuladas** | **3 de 20 (15%) · R$ 687.733** |
| Órgãos compradores | 2 — Prefeitura e Câmara |
| Contexto declarado pela página | 243 processos, R$ 135,4 mi, desde jun/2022 |

**Observação estrutural:** apenas **dois** órgãos publicam no PNCP. Não há Fundo
Municipal de Saúde, de Educação ou de Assistência Social com CNPJ próprio na
lista. Ou compram pelo CNPJ da Prefeitura, ou não publicam. Isso precisa ser
esclarecido — e reduz, aqui, a superfície do fracionamento disperso entre entes.

---

# Perguntas, por prioridade

Cada item traz o **fato** (o que a lista diz), a **pergunta** e o **documento a
buscar**. Nenhum afirma irregularidade.

## 1. Inexigibilidade de R$ 72.000 para serviços de segurança da informação

**Fato.** 17/09/2026, Prefeitura, situação **Homologada**. Objeto: contratação da
empresa GG SEC CONSULTORIA EM TECNOLOGIA DA INFORMAÇÃO LTDA, CNPJ
50.977.439/0001-47, para prestação de serviços técnicos em segurança da
informação. Valor R$ 72.000.

**Pergunta.** Inexigibilidade pressupõe fornecedor exclusivo ou serviço técnico
especializado com notória especialização. Consultoria em segurança da informação
é mercado com muitos prestadores. **Qual foi a justificativa para afastar a
competição?**

**Segunda pergunta.** A numeração do CNPJ (faixa 50.9xx) sugere registro
recente. Notória especialização pressupõe reputação consolidada. **Qual a data
de abertura da empresa e em que se baseou o reconhecimento da especialização?**
*(Inferência de data por faixa de CNPJ é heurística — precisa ser confirmada na
Receita antes de virar argumento.)*

**Buscar:** processo completo da inexigibilidade no PNCP — justificativa, razão
da escolha do fornecedor, justificativa de preço, parecer jurídico. Cartão CNPJ
e quadro societário da empresa.

## 2. Dispensa de R$ 45.000 pela Câmara para revisar a Lei Orgânica

**Fato.** 18/09/2026, Câmara Municipal, **Dispensa**. Objeto: contratação de
pessoa jurídica especializada para serviços técnicos de consultoria em revisão e
atualização da Lei Orgânica Municipal e do Regimento Interno. Valor R$ 45.000.

**Pergunta.** Revisar a Lei Orgânica e o Regimento é atividade central da
assessoria jurídica e da procuradoria da própria Câmara. **O que justificou a
contratação externa, e por dispensa?**

**Segunda pergunta.** O valor está dentro do limite de dispensa vigente em
18/09/2026 para serviços? *Não posso responder: o limite não foi conferido na
fonte oficial — é a pendência B8 do projeto.*

**Buscar:** processo da dispensa — justificativa, enquadramento legal invocado,
pesquisa de preços, parecer. Estrutura de assessoria jurídica da Câmara.

## 3. Três anulações em 62 dias, somando R$ 687.733

**Fato.**

| Data | Órgão | Valor | Objeto |
|---|---|---|---|
| 20/08/2026 | Câmara | R$ 371.215 | obra de reforma da nova Câmara de Vereadores, 417,37 m² |
| 08/09/2026 | Prefeitura | R$ 271.024 | serviços de fisioterapia |
| 15/09/2026 | Prefeitura | R$ 45.494 | locação de enxoval hospitalar com lavanderia |

**Pergunta.** 15% de anulação em dois meses é taxa alta. Anulação é ato da
própria Administração, normalmente por vício identificado. **Quais foram os
fundamentos de cada anulação?**

A resposta pode ser boa notícia — controle interno funcionando e corrigindo antes
do dano. Ou pode indicar editais publicados com defeito de forma reiterada. Os
dois cenários pedem o mesmo documento, e a distinção importa.

**Nota lateral:** dois dos três casos são da área de saúde. Vale olhar se há
padrão na preparação das contratações de saúde.

**Buscar:** ato de anulação de cada um, com a motivação. Se houve republicação
posterior, comparar o edital novo com o anulado.

## 4. Dois valores que pedem olhar a memória de cálculo

**Fato.** 24/08/2026, R$ 760.552 — registro de preços para materiais de
construção. E 11/09/2026, R$ 517.092 — registro de preços para materiais de
expediente e papelaria.

**Pergunta.** **Como foram estimados os quantitativos?**

**Ressalva importante, que precisa acompanhar qualquer questionamento:** registro
de preços fixa um teto estimado, não um gasto comprometido. O valor de referência
pode não se realizar. A pergunta legítima é sobre a base de cálculo da
estimativa, não sobre o valor em si.

**Buscar:** termo de referência com os quantitativos e sua justificativa; a
pesquisa de preços; e, depois, quanto foi efetivamente empenhado sobre a ata.

## 5. Pneus divididos em dois pregões — provavelmente nada

**Fato.** 22/07/2026, R$ 248.485, pneus e câmaras para frota média e pesada.
08/09/2026, R$ 112.250, pneus e câmaras para frota leve. Soma R$ 360.735,
48 dias de intervalo, mesmo órgão.

**Por que fica aqui e não mais acima.** O cruzamento automático de objetos
apontou este par (semelhança 0,80). Mas **os dois foram licitados por pregão
eletrônico** — não houve fuga de licitação. E pneu de veículo leve e de veículo
pesado são especificações e mercados fornecedores distintos, o que justifica
separar.

Registrado por transparência do método, com a avaliação de que **provavelmente
não há nada aqui.** Só mereceria atenção se os dois certames tivessem o mesmo
vencedor e houvesse indício de que a divisão serviu a outro fim.

---

# O que fazer com isto

**A escada, na ordem** (`docs/05-fluxo-de-revisao.md`):

Para os itens 1, 2 e 3, o instrumento correto agora é **pedido de esclarecimento
ou pedido de informação via LAI** ao órgão — não representação. A resposta (ou a
ausência dela) é o que constrói o degrau seguinte.

Nenhum item aqui tem, hoje, base para representação a Tribunal de Contas, e muito
menos ao Ministério Público. Falta o documento. Todos são perguntas legítimas com
documento identificável — que é exatamente o que um pedido de esclarecimento
existe para resolver.

**Se apenas um documento puder ser buscado:** o processo da inexigibilidade de
segurança da informação (item 1). É o que tem a pergunta mais nítida e a
justificativa mais estreita a sustentar.
