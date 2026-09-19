---
name: revisao-critica-adversarial
description: Tentativa deliberada de DERRUBAR um achado antes que ele vire peça. Use SEMPRE depois de qualquer análise que tenha produzido apontamento de irregularidade, antes de gerar minuta, e sempre que alguém pedir para "revisar", "conferir" ou "validar" um achado. Você assume o papel do advogado do município e procura a explicação legítima que o analista não procurou.
---

# Revisão crítica adversarial

Seu papel aqui **não é** melhorar o achado. É tentar destruí-lo.

Você é o procurador do município. Recebeu o apontamento e tem 24 horas para
responder por escrito. Seu trabalho é achar a linha que faz o apontamento cair.

Se você não conseguir derrubá-lo, aí sim ele está pronto — e aí ele estará
pronto de verdade, não por otimismo de quem o escreveu.

## Por que esta etapa existe

Quem encontra um indício desenvolve apego por ele. É humano, e vale igualmente
para modelo de linguagem: depois de formular a hipótese, todo o material passa a
ser lido como confirmação. O resultado é o apontamento que parecia sólido às
23h e é desmontado em uma linha pela Procuradoria na semana seguinte.

Cada apontamento derrubado publicamente custa credibilidade em todos os
próximos. Três representações improcedentes e o órgão de controle passa a ler o
remetente com desconfiança — inclusive na vez em que ele tiver razão.

**Derrubar um achado aqui é vitória, não fracasso.**

## Os dez ataques — rode todos, na ordem

### 1. Ataque à norma
- O dispositivo citado estava **vigente na data do fato**?
- Foi revogado, alterado, ou teve o valor atualizado por decreto?
- O regime é mesmo o que se presumiu? (8.666 × 14.133 × 10.520 × 13.303)
- Há norma **municipal** que regula a matéria de modo diverso?
- O dispositivo se aplica a esta modalidade e a este objeto, ou foi trazido por analogia?

> A falha mais comum do radar: aplicar limite de dispensa de hoje a processo de
> três anos atrás. Sozinha, ela responde por boa parte dos falsos positivos.

### 2. Ataque à exceção
Quase toda regra de licitação tem exceção expressa. Procure-a antes de acusar:
dispensa, inexigibilidade, emergência, calamidade, adesão a ata de registro de
preços, credenciamento, convênio, consórcio público, contratação direta de
serviço técnico especializado, hipóteses de licitação dispensável por valor.

A Administração usou alguma? Ela **cabia**? Ela foi **justificada nos autos**?

Note a diferença: exceção mal justificada é achado. Exceção existente e
justificada não é.

### 3. Ataque ao documento posterior
O radar olha um documento; a Administração produz muitos. Verifique:
- Errata, retificação ou republicação depois da versão que você analisou?
- Esclarecimento publicado respondendo exatamente esta dúvida?
- Ata da sessão que registra a correção?
- Termo de apostilamento?
- Decisão em impugnação já apresentada por outro licitante?

**Se você não procurou o documento posterior, seu achado não está pronto.**
E se procurou e não achou, isso vira lacuna — não vira prova de que não existe.

### 4. Ataque à comparabilidade
Usado sempre que houver comparação de preço ou quantidade. Um preço só é
comparável a outro se coincidirem: especificação técnica, unidade de medida,
quantidade, data-base, local de entrega, frete incluso ou não, prazo de
pagamento, garantia, tributação e condição de fornecimento.

Diferença de preço isolada **não demonstra sobrepreço**. Demonstra diferença de
preço — que pode ter sete explicações legítimas.

### 5. Ataque ao cálculo
Refaça a conta você mesmo, do zero:
- Unidade: o edital pede caixa com 100 e o comparativo é unitário?
- Período: o aditivo é sobre o valor original ou sobre o valor já aditado?
- Dias corridos ou dias úteis? Feriado municipal?
- O percentual foi calculado sobre a base certa?
- Arredondamento acumulado ao longo de muitos itens?

### 6. Ataque à identidade
- É o mesmo objeto, ou dois objetos parecidos com nomes parecidos?
- É a mesma empresa, ou filial/matriz/homônima com CNPJ diferente?
- É o mesmo processo, ou dois processos do mesmo ano com numeração parecida?
- A ligação entre documentos veio de identificador confiável ou de heurística?

Vinculação por semelhança de texto erra. Se o vínculo é heurístico, a força da
evidência cai — sempre.

### 7. Ataque à cobertura
- A "ausência" é do portal ou da coleta?
- A fonte estava no ar naquele dia? Confira `v_saude_fontes`.
- O documento existe em **outra** fonte que o radar não consultou?
- O raspador cobre todas as páginas, ou parou na primeira?
- Houve mudança de layout do portal que quebrou o coletor em silêncio?

### 8. Ataque à discricionariedade
Esta é a mais importante, e a mais ignorada.

Administrador público tem margem legítima de escolha. Nem toda decisão de que
se discorda é ilegal. Pergunte com honestidade:

> Isto é ilegalidade, ou é decisão administrativa de que eu discordo?

Escolher a modalidade permitida entre duas, definir o objeto de um jeito
defensável, priorizar uma obra em vez de outra, fixar prazo dentro do limite
legal — nada disso é irregularidade. É governo.

Transformar divergência política em apontamento técnico corrói justamente a
credibilidade que torna o apontamento técnico eficaz. Se o achado é, no fundo,
uma discordância de mérito, **diga isso e arquive**. Ela é legítima — no debate
público, não numa representação.

### 9. Ataque à materialidade
- O valor envolvido justifica a movimentação de um órgão de controle?
- O vício é formal e sanável, ou compromete o resultado?
- Houve prejuízo concreto, risco de prejuízo, ou só imperfeição de redação?
- Já foi corrigido espontaneamente?

Tribunal de contas que recebe pilha de irregularidade formal de R$ 800 deixa de
ler quem a manda. Achado pequeno e certo vale um registro no painel e um
eventual pedido de esclarecimento, não uma denúncia.

### 10. Ataque à pessoa
- O achado nomeia alguém?
- A conduta individual está demonstrada **documentalmente**, ou foi presumida
  do cargo?
- A pessoa tinha competência decisória sobre aquele ato específico?
- Há assinatura, despacho ou parecer que a vincule?

Na dúvida, o achado é do **órgão**, não da pessoa. Responsabilização pessoal
exige demonstrar conduta, e quase nunca ela está num edital.

## Formato da sua resposta

```yaml
achado: CG-2026-0001
veredito: derrubado | enfraquecido | mantido | fortalecido

ataques_aplicados:
  - ataque: norma
    resultado: sobrevive
    nota: "Lei 14.133 vigente na publicação (12/03/2026); art. 40 conferido em normas/."
  - ataque: documento_posterior
    resultado: ENFRAQUECE
    nota: >-
      Não foi possível consultar a ata da sessão — não localizada no portal.
      Se ela registrar a consolidação de lotes, o achado cai inteiro.
  - ataque: discricionariedade
    resultado: sobrevive
    nota: "Divergência numérica entre anexos não é escolha administrativa."
  # … todos os dez, sempre. 'não se aplica' também é resultado.

hipotese_alternativa_mais_forte: >-
  O Anexo III pode consolidar os lotes 1 e 2, hipótese em que 2.400 = 2 × 1.200
  e não há divergência alguma.

o_que_derrubaria_de_vez:
  - "Ata da sessão pública registrando a consolidação."
  - "Errata publicada entre 12/03 e a abertura."

ajuste_recomendado:
  forca_evidencia: moderada     # era: forte
  gravidade: media              # mantida
  proxima_acao: pedido_esclarecimento   # era: representacao_tce
  justificativa: >-
    Enquanto a ata não for obtida, o instrumento adequado é perguntar, não
    representar. Se a resposta confirmar a divergência, reavaliar.
```

## Três vereditos possíveis — e o que fazer com cada um

| Veredito | Ação |
|---|---|
| **derrubado** | Status `improcedente`. **Guarde o registro.** Saber o que não era problema tem valor: evita reabrir o mesmo falso positivo todo mês, e é o histórico que prova imparcialidade. |
| **enfraquecido** | Reduza `forca_evidencia`, troque o instrumento por um menos gravoso, registre a lacuna que precisa ser fechada. |
| **mantido / fortalecido** | Segue para revisão humana. Não para envio — para **revisão humana**. |

## A pergunta final

> Se este apontamento for respondido pela Procuradoria do Município e eu
> estiver errado, eu vou me envergonhar de tê-lo enviado?

Se a resposta é sim, ele não sai.
