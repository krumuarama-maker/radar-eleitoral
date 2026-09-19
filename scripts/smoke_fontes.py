#!/usr/bin/env python3
"""Teste de fumaça das fontes — o PRIMEIRO comando a rodar no projeto.

Todas as URLs em config/ nasceram de índice de buscador, não de acesso real.
Este script abre cada uma, mede o que voltou e diz o que confiar. Rode-o de
uma máquina com saída de rede livre; o ambiente de desenvolvimento remoto do
Claude Code bloqueia egresso por política, e lá tudo falha por igual.

    python scripts/smoke_fontes.py                    # todas
    python scripts/smoke_fontes.py --prioridade 1     # só as críticas
    python scripts/smoke_fontes.py --atualizar-config # grava o status no YAML

Ele não coleta nada. Só pergunta: "isto responde, e responde o quê?"
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    import httpx
    import yaml
except ImportError:
    sys.exit("faltam dependências: uv pip install httpx pyyaml")

RAIZ = Path(__file__).resolve().parent.parent
UA = "RadarFiscalizacaoMunicipal/0.1 (verificacao de disponibilidade; contato no repositorio)"


@dataclass
class Sonda:
    chave: str
    url: str
    prioridade: int
    status_http: int | None = None
    content_type: str = ""
    tamanho: int = 0
    redirecionou_para: str = ""
    tempo_ms: int = 0
    erro: str = ""
    #: Heurística grosseira: a página parece depender de JavaScript para
    #: mostrar conteúdo? Se sim, o coletor vai precisar de navegador.
    parece_exigir_js: bool = False
    robots_permite: bool | None = None

    @property
    def veredito(self) -> str:
        if self.erro:
            return "FALHA"
        if self.status_http is None:
            return "FALHA"
        if 200 <= self.status_http < 300:
            if self.tamanho < 500:
                return "SUSPEITA"  # 200 com corpo vazio costuma ser erro mascarado
            return "OK"
        if self.status_http in (401, 403):
            return "BLOQUEADA"
        if self.status_http == 404:
            return "INEXISTENTE"
        return "ANOMALA"


MARCAS_JS = (
    "window.__NUXT__",
    "window.__NEXT_DATA__",
    "ng-app",
    "data-reactroot",
    '<div id="root"></div>',
    '<div id="app"></div>',
    "powerbi",
)


def sondar(cliente: httpx.Client, chave: str, url: str, prioridade: int) -> Sonda:
    s = Sonda(chave=chave, url=url, prioridade=prioridade)
    inicio = datetime.now(UTC)
    try:
        # GET, não HEAD: portais governamentais respondem HEAD de forma errática,
        # e alguns devolvem 405 num endpoint que funciona perfeitamente no GET.
        r = cliente.get(url)
        s.status_http = r.status_code
        s.content_type = r.headers.get("content-type", "").split(";")[0]
        corpo = r.content[:200_000]
        s.tamanho = len(r.content)
        if r.history:
            s.redirecionou_para = str(r.url)
        if "html" in s.content_type:
            texto = corpo.decode("utf-8", "ignore")
            s.parece_exigir_js = any(m.lower() in texto.lower() for m in MARCAS_JS)
    except httpx.HTTPError as exc:
        s.erro = f"{type(exc).__name__}: {exc}"
    s.tempo_ms = int((datetime.now(UTC) - inicio).total_seconds() * 1000)
    return s


def checar_robots(cliente: httpx.Client, url: str) -> bool | None:
    """Busca o robots.txt do host. None = não existe ou não respondeu."""
    p = urlparse(url)
    try:
        r = cliente.get(f"{p.scheme}://{p.netloc}/robots.txt")
        if r.status_code != 200:
            return None
        return "Disallow: /" not in r.text.replace("Disallow: /*", "")
    except httpx.HTTPError:
        return None


def coletar_urls(cfg: dict, prioridade_max: int) -> list[tuple[str, str, int]]:
    alvos: list[tuple[str, str, int]] = []
    for f in cfg.get("fontes", []):
        if f.get("prioridade", 9) > prioridade_max:
            continue
        for campo in ("url_base", "url_fallback", "url_camara", "openapi", "melhor_entrada"):
            if url := f.get(campo):
                if "{" in url:  # template, não URL — pular
                    continue
                alvos.append((f"{f['chave']}:{campo}", url, f.get("prioridade", 9)))
    for v in cfg.get("validacao_cruzada", []):
        alvos.append((f"cruzada:{v['nome']}", v["url"], 3))
    return alvos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default="config/municipios/cidade-gaucha.yaml")
    ap.add_argument("--prioridade", type=int, default=9, help="testar até esta prioridade")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    args = ap.parse_args()

    cfg = yaml.safe_load((RAIZ / args.config).read_text(encoding="utf-8"))
    alvos = coletar_urls(cfg, args.prioridade)

    print(f"Sondando {len(alvos)} URLs de {cfg['municipio']['nome']}…\n", file=sys.stderr)

    sondas: list[Sonda] = []
    hosts_vistos: set[str] = set()
    with httpx.Client(
        headers={"User-Agent": UA}, timeout=args.timeout, follow_redirects=True, verify=True
    ) as cli:
        for chave, url, prio in alvos:
            s = sondar(cli, chave, url, prio)
            host = urlparse(url).netloc
            if host not in hosts_vistos:
                s.robots_permite = checar_robots(cli, url)
                hosts_vistos.add(host)
            sondas.append(s)
            if not args.json:
                marca = {
                    "OK": "✓",
                    "SUSPEITA": "?",
                    "BLOQUEADA": "⊘",
                    "INEXISTENTE": "✗",
                    "FALHA": "✗",
                    "ANOMALA": "!",
                }[s.veredito]
                js = " [JS]" if s.parece_exigir_js else ""
                det = s.erro or f"{s.status_http} {s.content_type} {s.tamanho}B {s.tempo_ms}ms"
                print(f" {marca} P{s.prioridade} {s.chave:42s} {det}{js}")

    if args.json:
        print(json.dumps([asdict(s) for s in sondas], ensure_ascii=False, indent=2))
        return 0

    # ---- resumo -----------------------------------------------------------
    por_veredito: dict[str, int] = {}
    for s in sondas:
        por_veredito[s.veredito] = por_veredito.get(s.veredito, 0) + 1

    print("\n" + "=" * 70)
    print("RESUMO:", "  ".join(f"{k}={v}" for k, v in sorted(por_veredito.items())))

    criticas_ruins = [s for s in sondas if s.prioridade <= 2 and s.veredito != "OK"]
    if criticas_ruins:
        print("\nFONTES DE PRIORIDADE 1-2 QUE NÃO RESPONDERAM:")
        for s in criticas_ruins:
            print(f"  · {s.chave}: {s.veredito} — {s.erro or s.status_http}")
        print("\n  Enquanto estas não responderem, a cobertura do radar é parcial e")
        print("  o painel deve dizer isso. Fonte fora do ar NÃO é município sem problema.")

    js = [s for s in sondas if s.parece_exigir_js]
    if js:
        print(f"\nEXIGEM NAVEGADOR (JS) — {len(js)}: " + ", ".join(s.chave for s in js))
        print("  Estes coletores precisam de Playwright, não de httpx.")

    robots = [s for s in sondas if s.robots_permite is False]
    if robots:
        print(f"\nROBOTS.TXT RESTRITIVO — {len(robots)}: " + ", ".join(s.chave for s in robots))
        print("  Registre como limitação de transparência. Não contorne.")

    print("\nPróximo passo: atualize o campo `verificacao` em", args.config)
    print("de `indexada` para `verificada` nas fontes marcadas OK, com a data de hoje.")
    return 0 if not criticas_ruins else 1


if __name__ == "__main__":
    raise SystemExit(main())
