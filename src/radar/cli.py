"""Interface de linha de comando do radar.

O comando mais importante daqui não é `coletar` nem `analisar`. É `cobertura`,
que responde à pergunta que todo sistema de fiscalização precisa saber
responder e quase nenhum responde: **o que eu NÃO consegui ver?**

Um radar que só mostra o que encontrou induz o operador a confundir silêncio com
regularidade. Aqui o silêncio tem que se explicar.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

from radar.coleta.base import ResultadoColeta

app = typer.Typer(help="Radar de Fiscalização Municipal", no_args_is_help=True)
banco_app = typer.Typer(help="Gestão do banco local")
app.add_typer(banco_app, name="banco")

con = Console()
RAIZ = Path(__file__).resolve().parents[2]


def _db(caminho: str | None = None) -> sqlite3.Connection:
    p = Path(caminho or "dados/radar.db")
    p.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(p)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


# ---------------------------------------------------------------------------


@banco_app.command("criar")
def banco_criar(db: Annotated[str, typer.Option()] = "dados/radar.db") -> None:
    """Cria ou atualiza o banco a partir de schema.sql."""
    esquema = (RAIZ / "src/radar/db/schema.sql").read_text(encoding="utf-8")
    with _db(db) as c:
        c.executescript(esquema)
        n = c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    con.print(f"[green]banco pronto[/] em {db} — {n} tabelas")


@app.command()
def municipio(
    config: Annotated[str, typer.Option()] = "config/municipios/cidade-gaucha.yaml",
    db: Annotated[str, typer.Option()] = "dados/radar.db",
) -> None:
    """Carrega município, órgãos e fontes no banco a partir do YAML."""
    cfg = yaml.safe_load((RAIZ / config).read_text(encoding="utf-8"))
    m = cfg["municipio"]
    with _db(db) as c:
        c.execute(
            "INSERT OR IGNORE INTO municipio (codigo_ibge, nome, uf, populacao, populacao_ano)"
            " VALUES (?,?,?,?,?)",
            (m["codigo_ibge"], m["nome"], m["uf"], m.get("populacao"), m.get("populacao_ano")),
        )
        mid = c.execute(
            "SELECT id FROM municipio WHERE codigo_ibge=?", (m["codigo_ibge"],)
        ).fetchone()[0]

        for o in cfg.get("orgaos", []):
            c.execute(
                "INSERT OR IGNORE INTO orgao (municipio_id, nome, cnpj, tipo) VALUES (?,?,?,?)",
                (mid, o["nome"], o.get("cnpj"), o["tipo"]),
            )
        for f in cfg.get("fontes", []):
            c.execute(
                "INSERT OR IGNORE INTO fonte"
                " (municipio_id, chave, nome, url_base, tipo, coletor, periodicidade_min,"
                "  ativo, observacoes) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    mid,
                    f["chave"],
                    f["nome"],
                    f["url_base"],
                    f["tipo"],
                    f.get("coletor") or "",
                    f.get("periodicidade_min", 1440),
                    1 if f.get("coletor") else 0,
                    f"verificacao={f.get('verificacao')}",
                ),
            )
    con.print(
        f"[green]{m['nome']}/{m['uf']}[/] carregado: "
        f"{len(cfg.get('orgaos', []))} órgãos, {len(cfg.get('fontes', []))} fontes"
    )
    naoverif = [f for f in cfg.get("fontes", []) if f.get("verificacao") != "verificada"]
    if naoverif:
        con.print(
            f"[yellow]atenção:[/] {len(naoverif)} de {len(cfg.get('fontes', []))} fontes "
            "ainda não foram verificadas por acesso real.\n"
            "        rode [bold]python scripts/smoke_fontes.py[/] de uma máquina com rede livre."
        )


@app.command()
def catalogo(
    prioridade: Annotated[int, typer.Option(help="mostrar até esta prioridade")] = 9,
    tipo: Annotated[str, typer.Option(help="D, D+, H ou IA")] = "",
) -> None:
    """Lista as verificações catalogadas."""
    cfg = yaml.safe_load(
        (RAIZ / "config/catalogo-verificacoes.yaml").read_text(encoding="utf-8")
    )
    itens = [v for v in cfg["verificacoes"] if v["prio"] <= prioridade]
    if tipo:
        itens = [v for v in itens if v["tipo"] == tipo]

    t = Table(title=f"Catálogo de verificações ({len(itens)} de {len(cfg['verificacoes'])})")
    for col in ("id", "prio", "tipo", "status", "regra"):
        t.add_column(col.upper())
    for v in sorted(itens, key=lambda x: (x["prio"], x["id"])):
        cor = {"implementada": "green", "bloqueada": "red"}.get(v["status"], "yellow")
        t.add_row(
            v["id"], str(v["prio"]), v["tipo"], f"[{cor}]{v['status']}[/]", v["regra"][:70]
        )
    con.print(t)


@app.command()
def normas(
    pendentes: Annotated[bool, typer.Option(help="só o que trava peças")] = False,
) -> None:
    """Estado da base normativa."""
    from radar.analise.normas import BaseNormas

    base = BaseNormas(RAIZ / "normas")
    lista = base.pendentes() if pendentes else None

    if pendentes:
        assert lista is not None
        t = Table(title=f"Dispositivos pendentes de conferência ({len(lista)})")
        for col in ("chave", "diploma", "dispositivo", "url"):
            t.add_column(col.upper())
        for d in lista:
            t.add_row(d.chave, d.diploma[:34], d.dispositivo, d.url_oficial[:48])
        con.print(t)
        con.print(
            "\n[yellow]Enquanto pendentes, estes dispositivos NÃO entram em peça alguma.[/]\n"
            "Abra a fonte oficial, copie o texto literal e marque conferido em normas/."
        )
    else:
        pend = len(base.pendentes())
        con.print(
            f"base normativa: {len(base)} dispositivos, "
            f"[{'yellow' if pend else 'green'}]{pend} pendentes[/]"
        )


@app.command()
def cobertura(
    db: Annotated[str, typer.Option()] = "dados/radar.db",
) -> None:
    """O que o radar NÃO conseguiu ver.

    Fonte fora do ar não é município sem problemas. Este comando existe para
    impedir que o silêncio seja lido como regularidade.
    """
    con.print(f"\n[bold]RELATÓRIO DE COBERTURA[/]  ·  {datetime.now():%d/%m/%Y %H:%M}\n")

    with _db(db) as c:
        try:
            fontes = c.execute("SELECT * FROM v_saude_fontes").fetchall()
        except sqlite3.OperationalError:
            con.print("[red]banco não inicializado.[/] rode: make banco")
            raise typer.Exit(1) from None

        t = Table(title="Saúde das fontes")
        for col in ("fonte", "última coleta ok", "dias sem", "último status"):
            t.add_column(col.upper())
        for f in fontes:
            dias = f["dias_sem_coleta"]
            cor = "red" if dias is None or dias > 3 else "green"
            t.add_row(
                f["chave"],
                f["ultima_coleta_ok"] or "[red]nunca[/]",
                f"[{cor}]{dias if dias is not None else '—'}[/]",
                f["ultimo_status"] or "—",
            )
        con.print(t)

        nunca = [f for f in fontes if not f["ultima_coleta_ok"]]
        if nunca:
            con.print(
                f"\n[red bold]{len(nunca)} fontes nunca coletadas com sucesso.[/]\n"
                "Qualquer conclusão sobre ausência de documento é, no momento, "
                "inválida para os dados que elas cobrem."
            )

        incompletos = c.execute(
            "SELECT COUNT(*) FROM v_processos_incompletos WHERE tem_edital=0"
        ).fetchone()[0]
        if incompletos:
            con.print(
                f"\n[yellow]{incompletos} processos sem edital vinculado.[/] "
                "Pode ser lacuna de coleta, não de publicação."
            )

        semdados = c.execute(
            "SELECT r.codigo, r.nome, COUNT(*) n FROM execucao_regra e"
            " JOIN regra r ON r.id = e.regra_id WHERE e.resultado='sem_dados'"
            " GROUP BY r.codigo ORDER BY n DESC LIMIT 10"
        ).fetchall()
        if semdados:
            con.print("\n[bold]Regras que não puderam rodar por falta de dado:[/]")
            for r in semdados:
                con.print(f"  {r['codigo']} {r['nome'][:48]} — {r['n']} processos")

    # As pendências de conferência também são cobertura: sem norma conferida,
    # o achado existe mas não vira peça.
    from radar.analise.normas import BaseNormas

    pend = BaseNormas(RAIZ / "normas").pendentes()
    if pend:
        con.print(
            f"\n[yellow]{len(pend)} dispositivos pendentes de conferência[/] — "
            "nenhuma peça pode citá-los. Ver docs/09-pendencias-de-conferencia.md"
        )


@app.command()
def coletar(
    municipio_ibge: Annotated[str, typer.Option("--municipio")] = "4105607",
    fonte: Annotated[str, typer.Option(help="chave da fonte; vazio = todas ativas")] = "",
    desde: Annotated[str, typer.Option(help="AAAA-MM-DD")] = "",
    db: Annotated[str, typer.Option()] = "dados/radar.db",
) -> None:
    """Executa os coletores ativos."""
    from radar.coleta.pncp import ColetorPNCP

    coletores = {"pncp": ColetorPNCP}
    alvos = [fonte] if fonte else list(coletores)

    inicio = datetime.fromisoformat(desde) if desde else None
    dados_dir = Path("dados")

    for chave in alvos:
        if chave not in coletores:
            con.print(f"[yellow]coletor '{chave}' ainda não implementado — pulando[/]")
            continue
        con.print(f"\n[bold]{chave}[/] …")
        with coletores[chave](dados_dir, municipio_ibge) as col:
            r = col.executar(inicio)
        cor = {"sucesso": "green", "falha_parcial": "yellow"}.get(r.status, "red")
        con.print(
            f"  [{cor}]{r.status}[/] — {r.itens_vistos} vistos, "
            f"{len(r.itens)} preservados, {len(r.erros)} erros"
        )
        for e in r.erros[:5]:
            con.print(f"    [red]·[/] {e[:110]}")
        for b in r.bloqueios[:5]:
            con.print(f"    [yellow]⊘[/] {b[:110]}")
        _registrar_coleta(db, chave, r)


def _registrar_coleta(db: str, chave: str, r: ResultadoColeta) -> None:
    """Registra a execução — inclusive quando falha. É daqui que sai a cobertura."""
    with _db(db) as c:
        linha = c.execute("SELECT id FROM fonte WHERE chave=?", (chave,)).fetchone()
        if not linha:
            return
        c.execute(
            "INSERT INTO coleta (fonte_id, iniciada_em, encerrada_em, status,"
            " itens_vistos, itens_novos, erro) VALUES (?,?,?,?,?,?,?)",
            (
                linha[0],
                r.iniciada_em.isoformat(),
                r.encerrada_em.isoformat() if r.encerrada_em else None,
                r.status,
                r.itens_vistos,
                len(r.itens),
                "; ".join(r.erros)[:2000] or None,
            ),
        )
        if r.status == "sucesso":
            c.execute(
                "UPDATE fonte SET ultima_coleta_ok=?, ultima_coleta_erro=NULL WHERE id=?",
                (date.today().isoformat(), linha[0]),
            )
        else:
            c.execute(
                "UPDATE fonte SET ultima_coleta_erro=? WHERE id=?",
                ("; ".join(r.erros or r.bloqueios)[:500], linha[0]),
            )


@app.command()
def analisar(
    municipio_ibge: Annotated[str, typer.Option("--municipio")] = "4105607",  # noqa: ARG001
    db: Annotated[str, typer.Option()] = "dados/radar.db",  # noqa: ARG001
) -> None:
    """Roda as verificações determinísticas sobre o que foi coletado."""
    import radar.analise.deterministico.r001_contratado_sancionado  # noqa: F401
    from radar.analise.deterministico import base as motor

    con.print(f"regras registradas: {len(motor.REGISTRO)}")
    for r in motor.REGISTRO:
        con.print(f"  {r.codigo} {r.nome}")
    con.print(
        "\n[yellow]O executor sobre o banco ainda não foi escrito.[/]\n"
        "Falta a etapa de vinculação (processo ↔ documentos), sem a qual as "
        "regras não têm contexto para avaliar. Ver docs/08-roadmap.md."
    )


if __name__ == "__main__":
    app()
