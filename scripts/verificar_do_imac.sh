#!/usr/bin/env bash
#
# Etapa 0 — conferir a fundação, de uma máquina com rede livre.
#
# Existe porque o ambiente onde este projeto foi escrito bloqueia saída de rede:
# toda URL e todo parâmetro de API vieram de busca, nenhum de acesso real.
# Este script é o que converte `indexada` em `verificada`.
#
# Rode de qualquer Mac ou Linux com internet:
#
#   git clone -b claude/radar-fiscalizacao-municipal-egi5ub \
#     https://github.com/krumuarama-maker/radar-eleitoral.git
#   cd radar-eleitoral && bash scripts/verificar_do_imac.sh
#
# O que ele faz, nesta ordem:
#   1. monta um ambiente Python isolado (não mexe no Python do sistema)
#   2. sonda todas as fontes de Cidade Gaúcha e mede o que voltou
#   3. baixa as especificações reais da API do PNCP
#   4. faz uma consulta real ao PNCP pelo município e conta o que veio
#   5. confere o código IBGE e a cobertura do Querido Diário
#   6. escreve um relatório em verificacao/ e tenta devolvê-lo pelo git
#
# Ele NÃO coleta documentos, NÃO envia nada a órgão nenhum e NÃO altera
# nenhuma regra de análise. Só pergunta "isto responde, e responde o quê?".

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"
SAIDA="verificacao"
mkdir -p "$SAIDA"
HOJE="$(date +%Y-%m-%d)"
REL="$SAIDA/relatorio-$HOJE.md"

azul()  { printf "\033[1;34m%s\033[0m\n" "$*"; }
verde() { printf "\033[1;32m%s\033[0m\n" "$*"; }
amar()  { printf "\033[1;33m%s\033[0m\n" "$*"; }
verm()  { printf "\033[1;31m%s\033[0m\n" "$*"; }

echo
azul "═══ Radar de Fiscalização Municipal — verificação da fundação ═══"
echo "   máquina: $(uname -s) $(uname -m)   ·   data: $HOJE"
echo

# ---------------------------------------------------------------------------
azul "[1/6] Ambiente Python"
if ! command -v python3 >/dev/null 2>&1; then
  verm "python3 não encontrado."
  echo "  No macOS, instale com:  xcode-select --install"
  exit 1
fi
echo "   $(python3 --version)"

if [ ! -d .venv ]; then
  python3 -m venv .venv >/dev/null 2>&1 || { verm "falha ao criar .venv"; exit 1; }
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip >/dev/null 2>&1
pip install --quiet httpx pyyaml >/dev/null 2>&1 || { verm "falha ao instalar dependências"; exit 1; }
verde "   ambiente pronto"

# ---------------------------------------------------------------------------
echo
azul "[2/6] Sondando as fontes de Cidade Gaúcha"
python3 scripts/smoke_fontes.py 2>&1 | tee "$SAIDA/fontes-$HOJE.txt"
python3 scripts/smoke_fontes.py --json > "$SAIDA/fontes-$HOJE.json" 2>/dev/null

# ---------------------------------------------------------------------------
echo
azul "[3/6] Especificações reais da API do PNCP"
for par in "consulta:https://pncp.gov.br/api/consulta/v3/api-docs" \
           "core:https://pncp.gov.br/api/pncp/v3/api-docs"; do
  nome="${par%%:*}"; url="${par#*:}"
  if curl -fsS --max-time 60 -H "Accept: application/json" "$url" -o "$SAIDA/pncp-$nome.json" 2>/dev/null; then
    tam=$(wc -c < "$SAIDA/pncp-$nome.json" | tr -d ' ')
    verde "   pncp-$nome.json baixado ($tam bytes)"
  else
    verm "   falhou: $url"
  fi
done

# Os parâmetros e o teto de paginação são as duas maiores incógnitas do coletor.
if [ -f "$SAIDA/pncp-consulta.json" ]; then
  python3 - "$SAIDA/pncp-consulta.json" <<'PY' | tee "$SAIDA/pncp-parametros-$HOJE.txt"
import json, sys
try:
    spec = json.load(open(sys.argv[1]))
except Exception as e:
    print("não foi possível ler o spec:", e); raise SystemExit
print("=== endpoints e parâmetros reais da API de consulta do PNCP ===\n")
for caminho, metodos in sorted(spec.get("paths", {}).items()):
    for metodo, op in metodos.items():
        if metodo.lower() != "get":
            continue
        print(f"{metodo.upper()} {caminho}")
        for p in op.get("parameters", []):
            obrig = "OBRIGATORIO" if p.get("required") else "opcional  "
            esq = p.get("schema", {}) or {}
            lim = ""
            if esq.get("maximum") is not None:
                lim = f"  (max {esq['maximum']})"
            print(f"   {obrig}  {p.get('name'):34s} {esq.get('type','?'):8s}{lim}")
        print()
PY
fi

# ---------------------------------------------------------------------------
echo
azul "[4/6] Consulta real ao PNCP — Cidade Gaúcha (IBGE 4105607)"
python3 - <<'PY' 2>&1 | tee "$SAIDA/pncp-consulta-real-$(date +%Y-%m-%d).txt"
import json
import pathlib
from datetime import date, timedelta

import httpx

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
BASE = "https://pncp.gov.br/api/consulta"
IBGE = "4105607"
CNPJ_PREF = "75377200000167"
MODALIDADES = {6: "Pregão Eletrônico", 8: "Dispensa", 9: "Inexigibilidade"}

fim = date.today()
ini = fim - timedelta(days=365)
print(f"janela: {ini} a {fim}\n")

total_geral = 0
orgaos = {}
# Contabiliza separadamente o que NAO pode ser medido. Sem isso, tres erros de
# rede viram "0 contratacoes" — que e exatamente a mentira que a regra R3 de
# AGENTS.md existe para impedir.
falhas = []
with httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"},
                  timeout=60.0, follow_redirects=True) as c:
    for cod, nome in MODALIDADES.items():
        params = {
            "dataInicial": ini.strftime("%Y%m%d"),
            "dataFinal": fim.strftime("%Y%m%d"),
            "codigoModalidadeContratacao": cod,
            "codigoMunicipioIbge": IBGE,
            "pagina": 1,
            "tamanhoPagina": 50,
        }
        try:
            r = c.get(f"{BASE}/v1/contratacoes/publicacao", params=params)
        except httpx.HTTPError as e:
            print(f"  {nome:22s} ERRO DE REDE: {e}")
            falhas.append((nome, f"erro de rede: {e}"))
            continue

        tipo = r.headers.get("content-type", "")
        if r.status_code == 204:
            print(f"  {nome:22s} 204 — nenhuma contratação na janela")
            continue
        if "json" not in tipo:
            print(f"  {nome:22s} !! devolveu {tipo} com status {r.status_code}")
            print("     (provável bloqueio por taxa — NÃO é 'município sem licitações')")
            falhas.append((nome, f"resposta {tipo} em vez de JSON"))
            continue
        if r.status_code != 200:
            print(f"  {nome:22s} HTTP {r.status_code}: {r.text[:180]}")
            falhas.append((nome, f"HTTP {r.status_code}"))
            continue

        d = r.json()
        registros = d.get("data", d if isinstance(d, list) else [])
        tot = d.get("totalRegistros", len(registros)) if isinstance(d, dict) else len(registros)
        pag = d.get("totalPaginas", "?") if isinstance(d, dict) else "?"
        total_geral += int(tot or 0)
        print(f"  {nome:22s} {tot} contratações, {pag} páginas "
              f"(vieram {len(registros)} nesta)")
        for reg in registros:
            oe = reg.get("orgaoEntidade") or {}
            chave = (oe.get("cnpj", "?"), oe.get("razaoSocial", "?"))
            orgaos[chave] = orgaos.get(chave, 0) + 1
        if registros:
            ex = registros[0]
            print(f"     exemplo: {ex.get('numeroControlePNCP')} — "
                  f"{(ex.get('objetoCompra') or '')[:64]}")

if falhas:
    print(f"\n!! {len(falhas)} de {len(MODALIDADES)} modalidades NÃO PUDERAM SER MEDIDAS:")
    for nome, motivo in falhas:
        print(f"     {nome}: {motivo}")
    if len(falhas) == len(MODALIDADES):
        print("\nRESULTADO: INDETERMINADO — nenhuma consulta chegou ao PNCP.")
        print("Isto NÃO significa que o município não licitou. Significa que esta")
        print("máquina não alcançou a API. Rode de onde haja rede livre.")
        VEREDITO.write_text("indeterminado")
    else:
        print(f"\nPARCIAL: {total_geral} contratações nas modalidades que responderam.")
        print("O total real é maior — as modalidades acima não foram medidas.")
        VEREDITO.write_text("parcial")
else:
    print(f"\nTOTAL nos últimos 12 meses: {total_geral} contratações")
    VEREDITO.write_text("medido")

if orgaos:
    print("\n=== ÓRGÃOS ENCONTRADOS (resolve a lacuna A6 das pendências) ===")
    for (cnpj, razao), n in sorted(orgaos.items(), key=lambda x: -x[1]):
        marca = "  <- Prefeitura" if cnpj == CNPJ_PREF else ""
        print(f"  {cnpj}  {n:4d}x  {razao[:56]}{marca}")
    print("\nCada CNPJ acima é um ente que licita sozinho. Os que não são a")
    print("Prefeitura são Câmara e fundos — é entre eles que o fracionamento")
    print("de despesa costuma se esconder.")
elif not falhas:
    print("\nNenhum órgão identificado, e todas as consultas responderam.")
    print("Ou a janela está mesmo vazia, ou `codigoMunicipioIbge` não é o")
    print("parâmetro certo — confira pncp-parametros.txt antes de concluir.")
else:
    print("\nNenhum órgão identificado, mas houve falha de consulta acima.")
    print("Não conclua nada a partir disto.")
PY

# ---------------------------------------------------------------------------
echo
azul "[5/6] Identificadores e cobertura"
python3 - <<'PY' 2>&1 | tee "$SAIDA/identificadores-$(date +%Y-%m-%d).txt"
import httpx

UA = "RadarFiscalizacaoMunicipal/0.1 (verificacao)"
with httpx.Client(headers={"User-Agent": UA}, timeout=45.0, follow_redirects=True) as c:
    # A7 — 4105607 é mesmo Cidade Gaúcha? (4105508 é Cianorte)
    try:
        r = c.get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios/4105607")
        if r.status_code == 200:
            d = r.json()
            nome = d.get("nome")
            uf = (((d.get("microrregiao") or {}).get("mesorregiao") or {})
                  .get("UF") or {}).get("sigla")
            ok = "CONFERE" if nome and "Gaúcha" in nome else "NÃO CONFERE"
            print(f"IBGE 4105607 -> {nome}/{uf}   [{ok}]")
        else:
            print(f"IBGE: HTTP {r.status_code}")
    except httpx.HTTPError as e:
        print(f"IBGE: erro {e}")

    # C7 — o Querido Diário cobre o município? Decide se dá para reusar a API
    # deles ou se é preciso escrever raspador do diário próprio.
    for host in ("https://api.queridodiario.org.br", "https://api.queridodiario.ok.org.br"):
        try:
            r = c.get(f"{host}/cities", params={"city_name": "Cidade Gaúcha"})
            if r.status_code == 200:
                cidades = r.json().get("cities", [])
                print(f"\nQuerido Diário ({host}): {len(cidades)} resultado(s)")
                for cid in cidades[:5]:
                    print(f"   {cid.get('territory_id')} {cid.get('territory_name')}/"
                          f"{cid.get('state_code')}  desde {cid.get('availability_date')}")
                if not cidades:
                    print("   não cobre — será preciso raspador do diário próprio")
                break
            print(f"\nQuerido Diário ({host}): HTTP {r.status_code}")
        except httpx.HTTPError as e:
            print(f"\nQuerido Diário ({host}): erro {e}")

    # A9 — até que edição o diário próprio chegou? Define onde a varredura começa.
    print("\nDiário Oficial próprio de Cidade Gaúcha:")
    try:
        r = c.get("https://diario.cidadegaucha.pr.gov.br/diariooficial")
        print(f"   índice: HTTP {r.status_code}, {len(r.content)} bytes, "
              f"{r.headers.get('content-type','?')}")
    except httpx.HTTPError as e:
        print(f"   índice: erro {e}")
PY

# ---------------------------------------------------------------------------
echo
azul "[6/6] Consolidando"
{
  echo "# Verificação da fundação — $HOJE"
  echo
  echo "Executado em \`$(uname -s) $(uname -m)\`, de máquina com rede livre."
  echo "Este relatório substitui suposição por medição. O que estiver marcado"
  echo "como falha aqui é lacuna real de cobertura, e o painel precisa dizer isso."
  echo
  echo "## Fontes sondadas"
  echo '```'
  sed -e 's/\x1b\[[0-9;]*m//g' "$SAIDA/fontes-$HOJE.txt" 2>/dev/null | tail -40
  echo '```'
  echo
  echo "## Consulta real ao PNCP"
  echo '```'
  sed -e 's/\x1b\[[0-9;]*m//g' "$SAIDA/pncp-consulta-real-$HOJE.txt" 2>/dev/null | head -60
  echo '```'
  echo
  echo "## Identificadores e cobertura"
  echo '```'
  sed -e 's/\x1b\[[0-9;]*m//g' "$SAIDA/identificadores-$HOJE.txt" 2>/dev/null
  echo '```'
  echo
  echo "## Arquivos gerados"
  for f in "$SAIDA"/*"$HOJE"* "$SAIDA"/pncp-consulta.json "$SAIDA"/pncp-core.json; do
    [ -f "$f" ] && echo "- \`$f\` ($(wc -c < "$f" | tr -d ' ') bytes)"
  done
  echo
  echo "## Próximo passo"
  echo
  echo "Atualizar \`config/municipios/cidade-gaucha.yaml\`, campo \`verificacao\`,"
  echo "de \`indexada\` para \`verificada\` nas fontes marcadas OK — e registrar"
  echo "como \`nao_confirmada\` as que falharam, em vez de deixá-las prometendo"
  echo "o que não entregam."
} > "$REL"

verde "   relatório: $REL"

# ---------------------------------------------------------------------------
echo
azul "Devolvendo o resultado pelo git"

# Registrar no repositório um relatório em que NADA foi medido seria pior que
# não registrar nada: alguém leria os 403 como se fossem achados. Um relatório
# só vira commit quando ele de fato mediu alguma coisa.
VEREDITO="$(cat "$SAIDA/.veredito" 2>/dev/null || echo indeterminado)"
rm -f "$SAIDA/.veredito"

if [ "$VEREDITO" = "indeterminado" ]; then
  amar "   NADA foi medido nesta máquina — nenhuma consulta chegou aos servidores."
  echo "      O relatório fica salvo localmente em $REL, mas NÃO vai para o"
  echo "      repositório: um registro de 403 se pareceria com um resultado."
  echo
  verm "   Esta máquina não tem acesso à internet aberta, ou há proxy no caminho."
  echo "      Teste direto:  curl -sS -o /dev/null -w '%{http_code}\n' https://pncp.gov.br"
  exit 2
fi

git add -A "$SAIDA" >/dev/null 2>&1
if git diff --cached --quiet 2>/dev/null; then
  amar "   nada novo para enviar"
else
  if [ "$VEREDITO" = "parcial" ]; then
    RESUMO="Verificacao PARCIAL da fundacao em $HOJE

Parte das consultas nao chegou aos servidores. O que esta no relatorio foi
medido; o que falhou esta nomeado como falha, nao como ausencia."
  else
    RESUMO="Verificacao da fundacao em $HOJE

Primeira medicao real das fontes e da API do PNCP. Substitui as suposicoes
que vieram de busca por respostas de servidor."
  fi
  git -c user.name="${GIT_AUTHOR_NAME:-verificacao-local}" \
      -c user.email="${GIT_AUTHOR_EMAIL:-verificacao@local}" \
      commit -q -m "$RESUMO" 2>&1 | tail -2
  if git push -q origin HEAD 2>/dev/null; then
    verde "   enviado. O relatório já está no GitHub."
  else
    amar "   push falhou (provavelmente falta credencial do GitHub nesta máquina)."
    echo "      O relatório está salvo em: $REL"
    echo "      Para enviar depois:  git push origin HEAD"
  fi
fi

echo
azul "═══ Fim ═══"
echo "   Leia: $REL"
echo
