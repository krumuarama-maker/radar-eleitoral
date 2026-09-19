# Modelo de dados

Duas fontes, que precisam andar juntas:

- **[`src/radar/db/schema.sql`](../src/radar/db/schema.sql)** — as 30 tabelas,
  as duas visões de cobertura e os dois triggers de integridade. Cada bloco está
  comentado com o motivo de existir.
- **[`src/radar/achados/modelo.py`](../src/radar/achados/modelo.py)** — a ficha
  de evidência, que valida a si mesma.

## A ficha, em uma tela

```python
Ficha(
    codigo="CG-2026-0001",
    titulo="Divergência de quantitativo entre Anexo I e Anexo III",

    fatos_documentais=[...],   # literal, com página. Sem adjetivo.
    hipoteses=[...],           # leitura, marcada como leitura
    lacunas=[...],             # o que falta verificar
    hipotese_alternativa=...,  # o que derrubaria o achado

    evidencias=[Evidencia(...)],   # obrigatório, com sha256 e url
    fundamentos=[FundamentoNormativo(...)],  # só se conferido em normas/

    gravidade=Gravidade.MEDIA,            # quão sério SE proceder
    forca_evidencia=ForcaEvidencia.FORTE, # quão bem o documento sustenta
    urgencia=Urgencia.PRAZO_CORRENDO,
    regime_aplicavel=RegimeJuridico.LEI_14133,
)
```

## O que a ficha recusa

Estas validações levantam exceção, não aviso:

| Situação | Por quê |
|---|---|
| `evidencias` vazio | Sem âncora documental não há achado — há suspeita, e suspeita se registra em `lacunas` |
| `fatos_documentais` vazio | Achado feito só de interpretação não é apresentável |
| `lacunas` vazio | Quase sempre indica análise apressada. Se nada falta, escreva isso explicitamente |
| "provavelmente", "sugere que", "é evidente que" dentro de `fatos_documentais` | Interpretação disfarçada de fato |
| Gravidade alta + evidência fraca, sem `hipotese_alternativa` | É a combinação que mais produz acusação injusta |
| `FundamentoNormativo` com `texto_conferido` vazio | Trava contra citação inventada |

## Dois eixos, nunca um

`gravidade` e `forca_evidencia` são campos separados de propósito. Confundi-los é
o que transforma fiscalização em acusação: "é gravíssimo" não quer dizer "está
provado". Achado grave com evidência fraca não vira denúncia — vira pedido de
esclarecimento.

## Migração para Postgres

O esquema evita recursos exclusivos do SQLite, com duas exceções a tratar:
`extracao_fts` (FTS5 → `tsvector`) e os dois triggers (sintaxe própria de cada
banco, mas mesma semântica). O resto é SQL padrão.
