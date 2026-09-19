# Catálogo de verificações

O catálogo em si vive em **[`config/catalogo-verificacoes.yaml`](../config/catalogo-verificacoes.yaml)** —
legível por máquina, porque é ele que dirige a implementação.

```bash
python -m radar.cli catalogo --prioridade 1          # o alicerce
python -m radar.cli catalogo --tipo D+               # o que depende de base externa
```

## Como ler

| Tipo | Significa |
|---|---|
| **D** | determinístico puro — só dado estruturado. Calculável, testável, reprodutível. |
| **D+** | determinístico, mas depende de base externa (CNPJ/QSA, CEIS, SINAPI, CMED) |
| **H** | híbrido — gatilho determinístico, confirmação por leitura de documento |
| **IA** | exige interpretação de texto |

Prioridade 1 são as que rodam sem base externa e sem IA: 30 regras que formam o
alicerce e entregam achado na primeira semana.

## Por que cada regra declara a fonte

Um apontamento lastreado em trilha publicada por órgão de controle é muito mais
difícil de descartar. "O TCU orienta que o detalhamento excessivo da
especificação pode resultar em direcionamento" pesa diferente de "achei
estranho". O campo `fonte` existe para que essa diferença apareça na peça.

Onde a fonte está marcada `[resumo]`, ela veio de sumário de busca e **não** do
documento primário. Antes de codificar a regra, abra a fonte. Regra construída
sobre citação de segunda mão produz achado que cai na primeira resposta.

## Escrevendo uma regra nova

1. Entrada no catálogo com id, tipo, prioridade e **fonte**.
2. Arquivo `src/radar/analise/deterministico/rNNN_nome.py`, expondo `REGRA`.
3. Nenhum limite legal no código — tudo vem de `normas/`, com a data do fato.
4. Devolver `SEM_DADOS` quando faltar insumo. Nunca falhar em silêncio.
5. Teste em `tests/unit/test_rNNN_*.py` cobrindo, no mínimo:
   - o caso que gera achado;
   - o caso limpo;
   - o caso sem dados (**e que ele não seja confundido com limpo**);
   - o caso fora de vigência;
   - o caso não aplicável.
6. Atualizar `status: implementada` e apontar o arquivo.

O modelo pronto é `r001_contratado_sancionado.py`, com seus 10 testes.
