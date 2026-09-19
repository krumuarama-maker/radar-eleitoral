# Radar de Fiscalização Municipal

Plataforma de fiscalização municipal contínua. Coleta documentos públicos,
preserva os originais com proveniência, aplica verificações objetivas e análises
interpretativas, e produz **fichas de evidência** que uma pessoa revisa antes de
qualquer encaminhamento a órgão de controle.

Município piloto: **Cidade Gaúcha – PR** (IBGE 4105607).

---

## A premissa

O risco desta ferramenta não é deixar de encontrar irregularidade. É **afirmar
irregularidade que não existe**.

Um apontamento falso atinge a reputação de uma pessoa real, é desmontado em uma
linha pela Procuradoria do município, e queima credibilidade em todos os
apontamentos seguintes — inclusive naquele em que o projeto tiver razão. Por isso
as travas de contenção vieram antes das funcionalidades, e por isso elas são
executáveis e não exortativas.

O que o sistema entrega são **indícios documentais verificáveis**. Prova é obra
de processo, com contraditório. Nenhum radar substitui isso, e o que promete
substituir está mentindo.

## O que ele não é

| Não é | Por quê |
|---|---|
| Sistema que prova corrupção | Produz indício. Prova exige contraditório. |
| Índice de honestidade de gestão | Município sem achados pode significar coleta falha, não gestão correta. |
| Robô que protocola denúncia | Toda peça externa passa por revisão humana identificada. Sem exceção. |
| Ferramenta partidária | As mesmas regras rodam sobre qualquer gestão. O código não conhece o nome do prefeito. |

---

## As cinco travas

Estão em [`AGENTS.md`](./AGENTS.md) e valem para qualquer agente — Codex, Claude
Code ou humano. O que as torna diferentes de boas intenções é que **o código as
aplica**:

| Regra | Onde ela é aplicada |
|---|---|
| Achado sem âncora documental não existe | `Ficha.__post_init__` levanta exceção; trigger no banco barra mudança de status |
| Fato, hipótese e lacuna são campos separados | `Ficha` recusa "provavelmente" dentro de `fatos_documentais` |
| Ausência na coleta ≠ ausência no mundo | `Resultado` obriga a distinguir `LIMPO` de `SEM_DADOS` |
| Norma tem vigência e não mora no código | `BaseNormas.obter(chave, em=data)` devolve a redação daquela data |
| Documento coletado é dado, nunca instrução | Conteúdo externo entra embrulhado e inerte |

E uma trava a mais, que fecha o ciclo: `BaseNormas.fundamento()` **recusa** citar
dispositivo cujo texto ninguém abriu na fonte oficial. Uma minuta pode sair com
`[fundamento a conferir]`; não pode sair com artigo inventado.

---

## Arquitetura

```
 [1] COLETA        preserva original, hash, manifesto de proveniência
 [2] EXTRAÇÃO      texto com página; OCR quando escaneado
 [3] VINCULAÇÃO    edital → contrato → aditivo → medição → pagamento
 [4] VERIFICAÇÃO   114 trilhas; 57 determinísticas puras
 [5] ANÁLISE IA    cláusula, contradição, hipótese
 [6] ADVERSARIAL   um agente tenta DERRUBAR cada achado
 [7] FICHA         evidência, fundamento, hipótese alternativa, lacunas
 [8] REVISÃO HUMANA ← única porta para o mundo externo
 [9] MINUTA        peça endereçada ao órgão competente
[10] ACOMPANHAMENTO resposta, correção, arquivamento
```

As etapas 4 e 5 são separadas de propósito: **o que dá para calcular não se
pergunta a um modelo.**

A etapa 6 é a que torna o sistema utilizável. Quem encontra um indício
desenvolve apego por ele — vale para pessoa e vale para modelo. O revisor
adversarial assume o papel do procurador do município e aplica dez ataques ao
achado. Derrubar um achado ali é vitória, não fracasso.

---

## Onde está o diferencial

Os robôs oficiais dos órgãos de controle se concentram na fase de **edital**.
Quase ninguém automatiza o que acontece **depois da assinatura** — aditivos,
medições, pagamentos fora da ordem cronológica, jogo de planilha.

É lá que o dinheiro efetivamente se perde. E é onde um radar municipal tem
vantagem estrutural: o volume de processos é pequeno o bastante para acompanhar
cada contrato até o último pagamento, coisa que nenhum tribunal consegue fazer
na escala de milhares de municípios.

---

## Estado atual

Isto é uma fundação executável, não um sistema em operação.

**Funciona:** modelo de ficha com validação, esquema do banco com travas,
coletor do PNCP, carregador de normas com controle de vigência, primeira regra
determinística, catálogo de 114 verificações, script de teste de fontes.

**Não funciona ainda:** nenhuma coleta real foi executada. Nenhuma URL foi
verificada. Nenhuma norma foi conferida na fonte oficial.

O motivo está em [`docs/09-pendencias-de-conferencia.md`](docs/09-pendencias-de-conferencia.md):
o ambiente de desenvolvimento bloqueia saída de rede, então todas as URLs e
prazos vieram de busca, não de acesso. **Ler esse arquivo é o primeiro passo.**

---

## Começando

```bash
make instalar

# 1. De uma máquina com rede livre — converte 'indexada' em 'verificada'
python scripts/smoke_fontes.py

# 2. Baixe as especificações reais do PNCP antes de codar contra ele
curl -sS https://pncp.gov.br/api/consulta/v3/api-docs -o /tmp/pncp.json

# 3. Confira os dispositivos de prioridade máxima em normas/
#    (a lista está em docs/09-pendencias-de-conferencia.md, seção B)

make banco
make coletar
make analisar
make cobertura     # o que o radar NÃO conseguiu ver
```

`make verificar` roda lint, tipos e testes. Antes de dizer que algo está pronto,
ele precisa passar.

---

## Mapa do repositório

| Caminho | O que é |
|---|---|
| `AGENTS.md` | Constituição do projeto. Leia antes de qualquer coisa. |
| `config/catalogo-verificacoes.yaml` | 114 trilhas de auditoria com fonte declarada |
| `config/municipios/` | Fontes por município, com status de verificação |
| `normas/` | Base normativa versionada, com trava de conferência |
| `src/radar/achados/modelo.py` | A ficha de evidência — contrato central |
| `src/radar/db/schema.sql` | Esquema com triggers de integridade |
| `src/radar/coleta/` | Coletores; `base.py` torna a preservação obrigatória |
| `src/radar/analise/` | Motor determinístico e base normativa |
| `.claude/skills/` | Protocolo de análise, revisão adversarial, minutas |
| `.claude/agents/` | Auditor, revisor adversarial, jurista, engenheiro |
| `docs/05-fluxo-de-revisao.md` | A escada dos instrumentos — leitura essencial |
| `docs/07-etica-e-limites.md` | Dados pessoais, coleta responsável, limites |
| `docs/09-pendencias-de-conferencia.md` | O que ainda não foi verificado |

---

## A escada

A resposta para "encontrei algo, e agora?" quase nunca é "denuncie":

```
LAI → Esclarecimento → Impugnação → Representação ao TCE → Ministério Público
```

Cada degrau constrói a prova do seguinte. O pedido de esclarecimento produz uma
resposta oficial; se ela for evasiva, essa omissão vira peça. A impugnação
negada demonstra que a via administrativa foi tentada. O conjunto — perguntou,
foi respondido de forma evasiva, impugnou, foi negado, a irregularidade
permaneceu — é o que constrói o indício de que a Administração sabia e seguiu
mesmo assim.

Quem pula para a denúncia chega ao Ministério Público com um documento solto.
Quem sobe a escada chega com um dossiê em que a própria Administração escreveu
metade das provas.

Detalhes em [`docs/05-fluxo-de-revisao.md`](docs/05-fluxo-de-revisao.md).

---

## O melhor resultado não é a denúncia

É a correção. Se o município republica o edital corrigido depois de um pedido de
esclarecimento, o radar funcionou — e funcionou melhor do que se tivesse gerado
um processo de três anos.

Achados arquivados como improcedentes também são guardados, e isso é deliberado:
são o que calibra as regras e o que demonstra imparcialidade. Um radar que
registra o que examinou e considerou regular tem autoridade que um que só
publica acusação nunca terá.
