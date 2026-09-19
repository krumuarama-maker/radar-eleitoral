# Base normativa versionada

Nenhum limite legal, prazo ou percentual pode estar escrito no código do radar.
Todos moram aqui, com vigência declarada. Esta é a regra R4 de `AGENTS.md`, e
ela existe por um motivo concreto: um contrato de 2021 é julgado pela Lei
8.666/93 durante toda a sua duração, ainda que hoje estejamos sob a Lei 14.133.
Aplicar a regra de hoje a documento de ontem é a causa mais comum de
apontamento falso — e a mais fácil de o município derrubar.

## A trava contra citação inventada

Toda norma tem o campo `conferido`:

```yaml
conferido:
  status: pendente | conferido
  por: "<quem abriu a fonte oficial e leu>"
  em: "<data>"
```

**Norma com `status: pendente` não pode ser citada em peça.** O carregador se
recusa a montar `FundamentoNormativo` a partir dela, e a `Ficha` levanta exceção
se o texto vier vazio. Isso é intencional: é melhor a minuta sair com
`[fundamento a conferir]` do que sair com um artigo que ninguém leu.

O campo `texto_literal` só se preenche copiando da fonte oficial. Nunca de
memória, nunca de resumo de busca, nunca de blog jurídico.

## Como conferir uma norma

1. Abra a `url_oficial` (Planalto para lei federal, site do TCE-PR para
   instrução normativa, Diário Oficial para norma municipal).
2. Copie o texto **literal** do dispositivo para `texto_literal`.
3. Confira a vigência: houve alteração posterior? Revogação? Qual redação valia
   na janela que nos interessa?
4. Se o dispositivo já teve redações diferentes, crie **uma entrada por redação**,
   cada uma com sua vigência. É assim que a regra sabe o que valia em 2022.
5. Marque `conferido.status: conferido`, com seu nome e a data.

## Organização

```
normas/
  federal/        Lei 14.133, Lei 8.666, LAI, Lei 8.429, Código Penal (crimes licitatórios)
  estadual-pr/    LC 113/2005 (Lei Orgânica do TCE-PR), Regimento Interno, INs do TCE-PR
  municipal/      Lei Orgânica de Cidade Gaúcha, Regimento da Câmara, decretos
  jurisprudencia/ Acórdãos do TCE-PR e do TCU, com identificador conferível
```

## Prioridade de conferência

O que trava mais peças primeiro:

1. `federal/lei_14133.yaml` — art. 164 (impugnação), art. 170 §4º (legitimidade
   para representar), arts. 190/191 (transição). Sem eles, nenhuma peça sai.
2. `estadual-pr/tce_pr_in_mural.yaml` — prazos do Mural de Licitações. É a
   verificação automática de maior retorno para município do Paraná.
3. `federal/lei_12527_lai.yaml` — prazos de pedido de informação.
4. `estadual-pr/lc_113_2005.yaml` — requisitos de denúncia ao TCE-PR.
