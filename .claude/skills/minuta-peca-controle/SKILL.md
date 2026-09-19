---
name: minuta-peca-controle
description: Redige minuta de peça dirigida a órgão de controle — pedido de esclarecimento, impugnação de edital, pedido via LAI, representação ou denúncia ao Tribunal de Contas, representação ao Ministério Público. Use depois que um achado passou pela revisão adversarial e pela revisão humana. Sempre produz RASCUNHO para revisão, nunca peça pronta para envio.
---

# Minuta de peça para órgão de controle

Você redige **rascunho**. A peça só existe depois que uma pessoa a leu inteira,
conferiu as citações e assinou. Isso não é formalidade do projeto: é a diferença
entre controle social e disparo automático de acusação.

## Antes de escrever uma linha

Quatro travas. Se qualquer uma falhar, **pare e diga o que falta**:

1. **O achado passou pela revisão adversarial?** Sem isso, não há peça.
2. **Toda norma citada está conferida em `normas/`?** Dispositivo com
   `conferido.status: pendente` não entra. Escreva `[fundamento a conferir]`.
3. **O instrumento é o certo para a fase?** Consulte a escada em
   `docs/05-fluxo-de-revisao.md`. Denúncia é o último degrau, não o primeiro.
4. **Existe hipótese alternativa registrada?** Se ninguém procurou a explicação
   legítima, a peça não está pronta.

## Escolha do instrumento

| Se… | Escreva |
|---|---|
| Falta documento para formular o achado | Pedido via LAI |
| Cláusula ambígua, certame aberto | Pedido de esclarecimento |
| Vício no edital, prazo ainda aberto | Impugnação |
| Impugnação negada ou ignorada, certame avançando | Representação ao TCE com pedido de cautelar |
| Irregularidade consumada | Denúncia ao TCE |
| Indício de dolo + dano ao erário | Representação ao MP |
| Divergência de mérito administrativo | **Nenhuma peça.** Arquive e, se quiser, leve ao debate público. |

---

## Esqueleto 1 — Pedido de esclarecimento

A peça mais subestimada, e a que mais resolve. Custo político baixo, e **produz
prova**: a resposta (ou o silêncio) da Administração entra nos autos e vira a
base do degrau seguinte.

```
Ao Sr. Agente de Contratação / Pregoeiro
Prefeitura Municipal de [município]
Ref.: [modalidade] nº [número]/[ano] — [objeto resumido]

[Nome], [qualificação], vem solicitar esclarecimento sobre os itens abaixo do
edital em referência, na forma da legislação aplicável.

1. DO ITEM [x.y] — [título neutro]
   O item [x.y], à página [n], estabelece: "[citação literal]".
   O Anexo [z], à página [m], estabelece: "[citação literal]".
   Solicita-se esclarecer qual das disposições prevalece para fins de
   formulação da proposta.

2. [próximo item]

Solicita-se, ainda, que a resposta seja divulgada no mesmo sítio eletrônico em
que publicado o edital, para conhecimento dos demais interessados.

[local], [data]
[nome, CPF, contato]
```

**Tom:** pergunta, não acusa. Você quer uma resposta escrita, não uma trincheira.
Note que a peça inteira pode ser construída só com citação literal e uma
pergunta — sem um único adjetivo.

---

## Esqueleto 2 — Impugnação ao edital

```
Ao Sr. [autoridade indicada no edital]
Prefeitura Municipal de [município]
Ref.: [modalidade] nº [número]/[ano]

                        IMPUGNAÇÃO AO EDITAL

I  — DA TEMPESTIVIDADE
     Abertura designada para [data]. Prazo legal: até [n] dias úteis antes.
     A presente é tempestiva.
     [Atenção: dias ÚTEIS sob a Lei 14.133; dias corridos sob a Lei 8.666.
      Conferir o regime aplicável antes de afirmar tempestividade.]

II — DA LEGITIMIDADE
     [dispositivo conferido que assegura a legitimidade]

III — DOS FATOS
     [Apenas fatos documentais, com página. Nenhum adjetivo.]
     O item [x] do edital, à p. [n], exige: "[literal]".

IV — DO DIREITO
     [Dispositivo conferido, com explicação de por que alcança ESTE fato.]
     [Se houver precedente: identificador conferível. Se não recuperou a
      fonte oficial, NÃO cite.]

V  — DO PEDIDO
     a) o acolhimento da impugnação;
     b) a alteração do item [x] para [redação proposta];
     c) a republicação do edital com reabertura do prazo, se a alteração
        afetar a formulação das propostas.

[local], [data] — [nome, CPF, contato]
```

---

## Esqueleto 3 — Representação ao Tribunal de Contas

```
Excelentíssimo Senhor Presidente do Tribunal de Contas do Estado do Paraná

                    REPRESENTAÇÃO (com pedido de medida cautelar)

I   — QUALIFICAÇÃO DO REPRESENTANTE
      [nome, nacionalidade, estado civil, profissão, CPF, RG, título de eleitor,
       endereço, e-mail, telefone]
      [Identificação é exigida. Se quiser sigilo, use a Ouvidoria — modalidade
       sigilosa — e não esta via.]

II  — DA LEGITIMIDADE
      [Fundamentar na Lei 14.133, que assegura a qualquer pessoa representar aos
       órgãos de controle contra irregularidades na sua aplicação.
       CONFERIR o dispositivo em normas/ antes de citar o número.]

III — DO OBJETO
      [Órgão, modalidade, número, ano, objeto, valor estimado, datas relevantes.
       Identificação precisa e inequívoca do procedimento.]

IV  — DOS FATOS
      [Numerados. Cada um com documento, página e citação literal.
       Nenhum adjetivo. Nenhuma conclusão jurídica.]
      1. Em [data], foi publicado o edital [nº], cujo item [x], à p. [n],
         dispõe: "[literal]" (doc. 01).
      2. [...]

V   — DO DIREITO
      [Dispositivos conferidos. Para cada um, por que alcança este fato,
       nesta data, sob este regime jurídico.]

VI  — DA VIA ADMINISTRATIVA JÁ PERCORRIDA
      [Este item vale mais do que parece. Demonstra que você perguntou antes de
       representar, e que a Administração teve chance de corrigir.]
      Em [data] foi protocolado pedido de esclarecimento (doc. 02), respondido
      em [data] nos seguintes termos: "[literal]" (doc. 03).
      Em [data] foi protocolada impugnação (doc. 04), [indeferida em [data] /
      não respondida até a presente data].

VII — DO PEDIDO DE MEDIDA CAUTELAR
      Fumus boni iuris: [por que o direito é provável — remissão aos itens IV e V]
      Periculum in mora: [por que esperar causa dano irreparável — abertura
        designada para [data]; homologação iminente; contrato a ser assinado]
      Requer-se a suspensão do procedimento até a decisão de mérito.

VIII— DOS PEDIDOS
      a) o conhecimento e processamento da representação;
      b) a concessão da medida cautelar;
      c) a oitiva do órgão;
      d) ao final, a procedência, com as determinações cabíveis.

IX  — DOS DOCUMENTOS
      doc. 01 — [descrição] — sha256 [hash] — obtido em [url] em [data]
      doc. 02 — [...]

[local], [data] — [assinatura]
```

**Sobre o hash nos documentos:** ele demonstra que o arquivo entregue é
exatamente o que foi coletado, e não uma versão editada. Não prova autenticidade
da origem — essa distinção precisa ficar clara, e não se deve afirmar mais do que
o hash sustenta.

---

## Esqueleto 4 — Representação ao Ministério Público

**Só depois de esgotada a escada.** E só se houver indício de dolo, dano ao
erário e o fato estiver dentro do prazo prescricional. Sem os quatro elementos,
a peça é arquivada e queima credibilidade com a Promotoria local.

```
Excelentíssimo Senhor Promotor de Justiça da Comarca de [comarca]

                    REPRESENTAÇÃO / NOTÍCIA DE FATO

I   — QUALIFICAÇÃO DO REPRESENTANTE
      [completa; ou pedido expresso de sigilo da fonte]

II  — DOS FATOS
      [Narrativa cronológica: o quê, quem, quando, onde, quanto.
       Cada fato com documento e página.]

III — DOS ENVOLVIDOS
      [Órgãos e empresas com CNPJ. Pessoas físicas SOMENTE se a conduta
       individual estiver demonstrada documentalmente — assinatura, despacho,
       parecer. Nunca por presunção decorrente do cargo.]

IV  — DOS ELEMENTOS QUE SUGEREM DOLO
      [O item decisivo. Não basta descrever o erro.]
      [Exemplos do que serve: alerta formal do controle interno ignorado;
       reiteração após advertência; resposta evasiva a esclarecimento seguida
       de manutenção da cláusula; vínculo entre gestor e contratada; cláusula
       que só uma empresa atendia, e foi ela quem venceu.]
      [Se você não tem nada aqui: NÃO ENVIE ESTA PEÇA. Envie ao TCE.]

V   — DO DANO
      [Valor, memória de cálculo, e a premissa de cada número.]

VI  — DAS PROVAS
      [Documentos, com hash e origem. Testemunhas, se houver.]

VII — DOS PEDIDOS
      a) instauração de notícia de fato / procedimento preparatório;
      b) requisição de documentos ao município;
      c) as medidas que o Ministério Público entender cabíveis.

[local], [data] — [assinatura]
```

---

## Regras de redação que valem para todas as peças

**Escreva o fato. Nunca o rótulo.**

| Não escreva | Escreva |
|---|---|
| "houve superfaturamento" | "o preço unitário contratado foi de R$ X; a mediana das [n] contratações comparáveis no período foi R$ Y" |
| "o edital foi direcionado" | "o item 7.3 exige [literal]; consultadas [n] empresas do ramo, [m] atendem ao requisito" |
| "houve fraude" | "as propostas das empresas A e B apresentam os mesmos metadados de autoria" |
| "o gestor agiu com dolo" | "em [data] o controle interno registrou alerta (doc. 05); a cláusula foi mantida na republicação de [data] (doc. 06)" |

Rótulo é conclusão jurídica, e conclusão jurídica é do órgão, não sua. A peça
que descreve o fato com precisão é mais forte que a que grita — e tem a vantagem
de não ser respondida com um pedido de retratação.

**Nunca cite o que não recuperou.** Artigo, acórdão, súmula, número de processo:
se não está conferido, escreva `[a conferir]`. Uma citação inventada numa peça
protocolada é, além de erro técnico, risco jurídico real para quem assina.

**Toda peça termina com uma advertência ao revisor:**

```
── RASCUNHO GERADO AUTOMATICAMENTE ─────────────────────────────────
Não protocole sem:
  [ ] conferir cada dispositivo citado na fonte oficial
  [ ] conferir cada documento anexado e seu hash
  [ ] confirmar o prazo e a tempestividade na data de hoje
  [ ] reler a seção "DOS FATOS" procurando adjetivo ou conclusão
  [ ] confirmar que a hipótese alternativa foi considerada e afastada
Revisor: ______________________  Data: ____________
────────────────────────────────────────────────────────────────────
```
