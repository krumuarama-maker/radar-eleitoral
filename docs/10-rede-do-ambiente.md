# Liberar a rede do ambiente

O ambiente de nuvem em que este projeto roda tem **nível de acesso de rede**
configurável. No nível padrão (**Trusted**), só passam registradores de pacote,
GitHub e alguns domínios de nuvem — nenhum portal público brasileiro. Foi por
isso que todo o levantamento inicial veio de busca em vez de acesso real, e é
por isso que `docs/09-pendencias-de-conferencia.md` existe.

Trocar para **Custom** com a lista abaixo resolve isso de uma vez, e o próprio
agente passa a conferir as fontes, baixar as especificações do PNCP e coletar.

## Onde mudar

Não existe página de configuração nem URL direta: a troca é feita pelo seletor
de ambiente.

1. Abra **claude.ai/code** (no navegador ou na aba **Code** do app).
2. Na linha acima da caixa de mensagem, toque no **ícone de nuvem** com o nome
   do ambiente atual.
3. Passe sobre o ambiente e toque no **ícone de engrenagem** à direita.
4. Em **Network access**, escolha **Custom**.
5. Cole a lista abaixo em **Allowed domains**, um domínio por linha.
6. **Marque** a caixa *"Also include default list of common package managers"* —
   sem ela, `pip` e `npm` param de funcionar e o projeto não instala.
7. Salve.

A política é lida quando o contêiner da sessão sobe. **A sessão atual continua
com a política antiga** — depois de salvar, abra uma sessão nova apontando para
este repositório e a branch `claude/radar-fiscalizacao-municipal-egi5ub`.

## Lista de domínios

```text
*.gov.br
gov.br
*.jus.br
*.leg.br
*.govbr.cloud
*.cidade360.cloud
*.1doc.com.br
*.org.br
alertalicitacao.com.br
minhareceita.org
brasilapi.com.br
```

### Por que cada linha

| Linha | Cobre |
|---|---|
| `*.gov.br`, `gov.br` | PNCP, TCE-PR, Prefeitura e Câmara de Cidade Gaúcha, diário oficial próprio, IBGE, Tesouro/SICONFI, Transferegov, Portal da Transparência federal, Compras.gov.br, ANVISA/CMED, FNDE, Receita Federal — e o **Planalto**, sem o qual não há como conferir nenhuma lei e nenhuma peça pode sair |
| `*.jus.br` | Tribunal de Justiça e CNJ, para confirmar comarca e consultar processo |
| `*.leg.br` | Câmaras municipais que usam Interlegis (a de Cidade Gaúcha não usa, mas outros municípios usarão) |
| `*.govbr.cloud`, `*.cidade360.cloud` | Portal da Transparência do município (produto PRONIM TB, da GOVBR) e seu host legado |
| `*.1doc.com.br` | e-SIC e Ouvidoria — é por onde se protocola pedido de informação |
| `*.org.br` | Querido Diário (Open Knowledge Brasil), BLL, associações municipais |
| `alertalicitacao.com.br` | Agregador independente, usado para **validação cruzada**: detecta licitação que o radar perdeu |
| `minhareceita.org`, `brasilapi.com.br` | Consulta de CNPJ e quadro societário — destrava ~15 regras de conluio e empresa de fachada |

## Por que não usar "Full"

**Full** libera qualquer domínio e funcionaria. Mas um sistema de fiscalização
que só alcança portais públicos é mais fácil de auditar e de defender: se alguém
perguntar o que esta ferramenta acessa, a resposta cabe em onze linhas.

É a mesma lógica da minimização de dados em `docs/07-etica-e-limites.md` —
pedir o mínimo necessário, e conseguir mostrar qual é esse mínimo.

## Depois de liberar

O primeiro comando deixa de precisar de máquina externa:

```bash
python scripts/smoke_fontes.py        # indexada -> verificada
python -m radar.cli coletar           # primeira coleta real
python -m radar.cli cobertura         # o que ainda não se viu
```

E `scripts/verificar_do_imac.sh` continua valendo para quem quiser rodar de
fora — ele não depende de nada deste ambiente.
