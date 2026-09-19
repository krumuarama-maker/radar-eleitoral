# CLAUDE.md

As regras deste projeto estão em **[AGENTS.md](./AGENTS.md)** — arquivo único,
compartilhado com o Codex e com qualquer outro agente.

**Leia AGENTS.md antes de escrever qualquer linha.** Em especial as cinco regras
invioláveis (seção 3) e a separação entre verificação determinística e análise por
IA (seção 5).

## Atalhos deste repositório

| Preciso de... | Vá para |
|---|---|
| Entender a arquitetura | `docs/01-arquitetura.md` |
| Entender o formato de um achado | `docs/02-modelo-de-dados.md` e `src/radar/achados/modelo.py` |
| Adicionar uma verificação | `docs/03-catalogo-de-verificacoes.md` + skill `analise-licitacao` |
| Adicionar uma norma | `docs/04-base-normativa.md` + pasta `normas/` |
| Adicionar um coletor | `src/radar/coleta/base.py` + skill `coletor-novo` |
| Escrever uma minuta | skill `minuta-representacao` |
| Derrubar um achado antes que ele saia | skill `revisao-critica-adversarial` |
| Saber o que está em andamento | `docs/08-roadmap.md` |

## Skills deste repositório

Estão em `.claude/skills/`. Invoque pelo nome quando a tarefa corresponder.
As mesmas regras substantivas estão espelhadas em `AGENTS.md` para o Codex,
que não carrega skills.

## Antes de responder "pronto"

Rode `make verificar`. Se não passar, não está pronto.
