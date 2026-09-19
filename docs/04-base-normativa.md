# Base normativa

A documentação operacional vive junto dos dados, em
**[`normas/README.md`](../normas/README.md)** — como conferir uma norma, como
declarar vigência, e por que dispositivo pendente não pode ser citado.

Resumo do que importa:

- Nenhum prazo, limite ou percentual pode estar escrito no código.
- `BaseNormas.obter(chave, em=data)` devolve a redação que valia **naquela data**.
- `BaseNormas.fundamento()` **recusa** montar citação de dispositivo cujo texto
  ninguém abriu na fonte oficial.

```bash
python -m radar.cli normas --pendentes   # o que ainda trava peças
```
