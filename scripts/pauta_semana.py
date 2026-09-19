#!/usr/bin/env python3
"""Pauta da semana — coleta, analisa e produz o relatório para revisão humana.

Um comando, do zero ao documento que vai para a mesa de quem revisa:

    python scripts/pauta_semana.py --dias 7

O relatório é endereçado a um auditor, e por isso tem uma seção que quase
nenhum painel de fiscalização tem: **o que não foi possível examinar**. Um
auditor que recebe vinte achados e não sabe quantos processos o sistema deixou
de olhar não consegue calibrar o quanto confiar no conjunto.

Nada aqui vira peça. O que sai é insumo de revisão, e o documento diz isso na
primeira linha.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

# Importar registra as regras no catálogo.
import radar.analise.deterministico.r001_contratado_sancionado  # noqa: E402
import radar.analise.deterministico.r002_proposta_unica  # noqa: E402
import radar.analise.deterministico.r003_fracionamento  # noqa: E402,F401
from radar.analise.deterministico import base as motor  # noqa: E402
from radar.analise.executor import Executor  # noqa: E402
from radar.analise.normas import BaseNormas  # noqa: E402
from radar.coleta.ingestao import Ingestor  # noqa: E402
from radar.coleta.pncp import ColetorPNCP, Modalidade  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--municipio", default="4105607")
    ap.add_argument("--dias", type=int, default=7, help="janela de coleta")
    ap.add_argument("--db", default="dados/radar.db")
    ap.add_argument("--saida", default=None)
    ap.add_argument(
        "--sem-anexos",
        action="store_true",
        help="não baixar PDFs; muito mais rápido, mas sem texto para ler",
    )
    args = ap.parse_args()

    hoje = date.today()
    desde = hoje - timedelta(days=args.dias)
    saida = Path(args.saida or f"verificacao/pauta-{hoje.isoformat()}.md")
    saida.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")

    print(f"[1/4] Coletando PNCP — {desde} a {hoje}", file=sys.stderr)
    with ColetorPNCP(
        RAIZ / "dados",
        args.municipio,
        modalidades=Modalidade.PRIORITARIAS,
        baixar_anexos=not args.sem_anexos,
    ) as col:
        resultado = col.executar(datetime.combine(desde, datetime.min.time(), tzinfo=UTC))

    print(
        f"      {resultado.status}: {resultado.itens_vistos} vistos, "
        f"{len(resultado.itens)} preservados, {len(resultado.erros)} erros",
        file=sys.stderr,
    )

    # Coleta que não chegou a lugar nenhum não vira relatório. Publicar um
    # documento dizendo "nada encontrado" quando na verdade nada foi consultado
    # é o defeito que este projeto inteiro existe para não cometer.
    if resultado.status in ("falha", "bloqueada") and not resultado.itens:
        print("\nA coleta não alcançou o PNCP. Nenhum relatório será gerado.", file=sys.stderr)
        for e in (resultado.erros or resultado.bloqueios)[:3]:
            print(f"  · {e[:160]}", file=sys.stderr)
        print(
            "\nIsto NÃO significa que o município não publicou nada esta semana.\n"
            "Significa que esta máquina não alcançou a API. Ver docs/10-rede-do-ambiente.md",
            file=sys.stderr,
        )
        return 2

    print("[2/4] Ingerindo", file=sys.stderr)
    ing = Ingestor(con, args.municipio)
    bi = ing.ingerir(resultado)
    con.commit()
    print(
        f"      {bi.processos_novos} processos novos, {bi.versoes_novas} versões, "
        f"{len(bi.orgaos_descobertos)} órgãos descobertos",
        file=sys.stderr,
    )

    print("[3/4] Analisando", file=sys.stderr)
    normas = BaseNormas(RAIZ / "normas")
    balanco = Executor(con, normas).executar(args.municipio)
    con.commit()
    print(
        f"      {balanco.achados} achados, {balanco.limpos} limpos, "
        f"{balanco.sem_dados} sem dados",
        file=sys.stderr,
    )

    print("[4/4] Escrevendo relatório", file=sys.stderr)
    saida.write_text(
        montar_relatorio(con, normas, balanco, bi, resultado, desde, hoje, args),
        encoding="utf-8",
    )
    print(f"\n{saida}", file=sys.stderr)
    return 0


def montar_relatorio(con, normas, balanco, bi, resultado, desde, hoje, args) -> str:
    linhas: list[str] = []
    a = linhas.append

    a(f"# Pauta de verificação — Cidade Gaúcha/PR · {desde} a {hoje}")
    a("")
    a("> **Isto não é uma denúncia nem um laudo.** É material de trabalho: uma lista")
    a("> do que foi publicado na semana, o que as verificações automáticas apontaram,")
    a("> e — igualmente importante — **o que não foi possível examinar**.")
    a(">")
    a("> Nenhum item aqui foi conferido por uma pessoa. Nenhum deve ser encaminhado")
    a("> a órgão de controle sem revisão. Ver `docs/05-fluxo-de-revisao.md`.")
    a("")
    a(f"Gerado em {datetime.now():%d/%m/%Y %H:%M}.")
    a("")

    # --- cobertura vem ANTES dos achados, de propósito --------------------
    a("## 1. O que o radar conseguiu ver")
    a("")
    a(f"- Contratações examinadas na janela: **{balanco.processos}**")
    a(f"- Documentos preservados nesta coleta: **{bi.versoes_novas}**")
    a(f"- Execuções de regra: {balanco.executadas}")
    a(
        f"- Cobertura efetiva: **{balanco.cobertura:.0%}** "
        "(fração das verificações em que a regra conseguiu de fato olhar)"
    )
    a("")
    if resultado.erros:
        a(f"⚠️ **{len(resultado.erros)} erros durante a coleta.** O que falhou não foi")
        a("examinado, e não pode ser lido como regular:")
        for e in resultado.erros[:8]:
            a(f"- `{e[:150]}`")
        a("")
    if balanco.sem_dados:
        a(f"⚠️ **{balanco.sem_dados} verificações não puderam rodar por falta de dado.**")
        a("")
        a("| Dado ausente | Verificações bloqueadas |")
        a("|---|---|")
        for campo, n in sorted(balanco.faltantes.items(), key=lambda x: -x[1]):
            a(f"| `{campo}` | {n} |")
        a("")

    pendentes = normas.pendentes()
    if pendentes:
        a(
            f"⚠️ **{len(pendentes)} dispositivos legais ainda não conferidos na fonte "
            "oficial.** Enquanto isso durar, nenhum achado pode ser fundamentado em peça, "
            "e as regras que dependem de limite legal devolvem `sem dados`."
        )
        a("")

    # --- órgãos -----------------------------------------------------------
    if bi.orgaos_descobertos:
        a("## 2. Órgãos descobertos nesta coleta")
        a("")
        a("Cada CNPJ abaixo licita por conta própria. Isso importa: a despesa")
        a("fracionada costuma se dispersar entre Prefeitura, Câmara e fundos, e fica")
        a("invisível para quem consolida um CNPJ de cada vez.")
        a("")
        for o in bi.orgaos_descobertos:
            a(f"- {o}")
        a("")

    # --- achados ----------------------------------------------------------
    a(f"## 3. Apontamentos automáticos ({balanco.achados})")
    a("")
    if not balanco.achados:
        a("Nenhuma verificação disparou nesta janela.")
        a("")
        a("**Leia isso junto com a seção 1.** Ausência de apontamento com cobertura")
        a("baixa significa que o radar não olhou, não que está tudo certo.")
        a("")
    else:
        a("Ordenados por gravidade. Cada ficha separa **fato documental** de")
        a("**hipótese** e lista o que falta verificar — as três coisas são diferentes.")
        a("")
        ordem = {"alta": 0, "media": 1, "baixa": 2, "indeterminada": 3}
        for f in sorted(
            balanco.fichas,
            key=lambda x: (ordem.get(x.gravidade.value, 9), x.forca_evidencia.value),
        ):
            a("---")
            a("")
            a(f.resumo_humano())
            a("")

    # --- o que fazer ------------------------------------------------------
    a("## 4. Para quem vai revisar")
    a("")
    a("A ordem dos instrumentos importa, e pular degrau enfraquece o degrau seguinte")
    a("(`docs/05-fluxo-de-revisao.md`):")
    a("")
    a("1. **Falta documento** → pedido via LAI ao município")
    a("2. **Cláusula dúbia, certame aberto** → pedido de esclarecimento")
    a("3. **Vício no edital, prazo aberto** → impugnação")
    a("4. **Impugnação negada, certame avançando** → representação ao TCE-PR")
    a("5. **Indício de dolo + dano ao erário** → representação ao MP")
    a("")
    a("Erro formal **não** é improbidade. Sem elementos de dolo, o caminho é o")
    a("Tribunal de Contas — não o Ministério Público.")
    a("")
    a("Três perguntas antes de levar qualquer item adiante:")
    a("")
    a("- Isto é ilegalidade, ou decisão administrativa de que se discorda?")
    a("- A Procuradoria do município derruba isto em um parágrafo?")
    a("- A explicação alternativa da ficha foi realmente afastada?")
    a("")

    # --- processos examinados --------------------------------------------
    a("## 5. Anexo — contratações examinadas")
    a("")
    a("| Processo | Órgão | Modalidade | Valor estimado | Publicação | Objeto |")
    a("|---|---|---|---|---|---|")
    for p in con.execute(
        "SELECT p.numero, p.exercicio, p.modalidade, p.valor_estimado,"
        "       p.data_publicacao, p.objeto, o.nome AS orgao"
        "  FROM processo p LEFT JOIN orgao o ON o.id = p.orgao_id"
        "  JOIN municipio m ON m.id = p.municipio_id"
        " WHERE m.codigo_ibge = ? AND p.data_publicacao >= ?"
        " ORDER BY p.data_publicacao DESC",
        (args.municipio, desde.isoformat()),
    ):
        valor = (
            f"R$ {p['valor_estimado']:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
            if p["valor_estimado"]
            else "—"
        )
        a(
            f"| {p['numero']}/{p['exercicio']} | {(p['orgao'] or '—')[:28]} "
            f"| {p['modalidade'] or '—'} | {valor} | {p['data_publicacao'] or '—'} "
            f"| {(p['objeto'] or '')[:70]} |"
        )
    a("")

    a("---")
    a("")
    a(
        f"Regras aplicadas: {len(motor.REGISTRO)} "
        f"({', '.join(r.codigo for r in motor.REGISTRO)}). "
        f"Catálogo completo em `config/catalogo-verificacoes.yaml`."
    )
    return "\n".join(linhas)


if __name__ == "__main__":
    raise SystemExit(main())
