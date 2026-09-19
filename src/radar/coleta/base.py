"""Coleta com preservação de prova.

Um documento baixado sem proveniência registrada é inútil para fiscalização:
seis meses depois ninguém consegue dizer de onde veio, quando, nem se mudou.
Esta classe existe para tornar impossível coletar sem preservar.

Também é aqui que mora a honestidade sobre cobertura. Toda execução é registrada,
inclusive as que falham — porque uma fonte fora do ar não pode aparecer no painel
como "município sem irregularidades".
"""

from __future__ import annotations

import abc
import hashlib
import json
import logging
import mimetypes
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger(__name__)

UA = (
    "RadarFiscalizacaoMunicipal/0.1 (projeto de fiscalização cívica; "
    "contato via repositório; respeita robots.txt)"
)


@dataclass(slots=True)
class ItemColetado:
    """Um documento baixado, antes de entrar no banco."""

    url_origem: str
    conteudo: bytes
    tipo_documento: str
    titulo: str | None = None
    numero: str | None = None
    exercicio: int | None = None
    identificador_externo: str | None = None
    http_headers: dict[str, str] = field(default_factory=dict)
    metadados: dict[str, Any] = field(default_factory=dict)
    coletado_em: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.conteudo).hexdigest()

    @property
    def extensao(self) -> str:
        ct = self.http_headers.get("content-type", "").split(";")[0].strip()
        if ext := mimetypes.guess_extension(ct):
            return ext
        sufixo = Path(urlparse(self.url_origem).path).suffix
        return sufixo if sufixo else ".bin"


@dataclass(slots=True)
class ResultadoColeta:
    """O que uma execução produziu — inclusive quando produziu nada.

    `bloqueios` é deliberadamente separado de `erros`: uma fonte que recusa
    acesso (403, captcha, robots) é informação relevante de transparência, não
    um defeito do coletor. Vira item de pedido de LAI, não de bug.
    """

    fonte_chave: str
    iniciada_em: datetime
    encerrada_em: datetime | None = None
    itens: list[ItemColetado] = field(default_factory=list)
    itens_vistos: int = 0
    erros: list[str] = field(default_factory=list)
    bloqueios: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.bloqueios and not self.itens:
            return "bloqueada"
        if self.erros and self.itens:
            return "falha_parcial"
        if self.erros:
            return "falha"
        return "sucesso"


class ColetorBase(abc.ABC):
    """Base de todo coletor.

    Subclasse implementa `buscar()`. O resto — limite de taxa, robots, repetição,
    preservação em disco — vem de graça e não é opcional.
    """

    chave: str
    nome: str
    url_base: str

    #: Segundos entre requisições. Fiscalizar não autoriza derrubar o site de
    #: uma prefeitura pequena, que costuma rodar em hospedagem modesta.
    intervalo_requisicao: float = 1.5
    timeout: float = 60.0
    tentativas: int = 3
    respeitar_robots: bool = True

    def __init__(self, diretorio_dados: Path, municipio_codigo_ibge: str) -> None:
        self.diretorio_dados = Path(diretorio_dados)
        self.municipio = municipio_codigo_ibge
        self._ultima_req = 0.0
        self._robots: dict[str, RobotFileParser] = {}
        self._cliente = httpx.Client(
            headers={"User-Agent": UA},
            timeout=self.timeout,
            follow_redirects=True,
        )

    # -- contrato ----------------------------------------------------------

    @abc.abstractmethod
    def buscar(self, desde: datetime | None = None) -> Iterator[ItemColetado]:
        """Produz os documentos da fonte. Pode levantar exceção; o executor trata."""

    # -- execução ----------------------------------------------------------

    def executar(self, desde: datetime | None = None) -> ResultadoColeta:
        r = ResultadoColeta(fonte_chave=self.chave, iniciada_em=datetime.now(UTC))
        try:
            for item in self.buscar(desde):
                r.itens_vistos += 1
                try:
                    self.preservar(item)
                    r.itens.append(item)
                except Exception as exc:
                    r.erros.append(f"preservar {item.url_origem}: {exc}")
                    log.exception("falha ao preservar %s", item.url_origem)
        except PermissionError as exc:
            r.bloqueios.append(str(exc))
        except Exception as exc:
            r.erros.append(f"{type(exc).__name__}: {exc}")
            log.exception("coletor %s falhou", self.chave)
        finally:
            r.encerrada_em = datetime.now(UTC)
        return r

    # -- preservação -------------------------------------------------------

    def preservar(self, item: ItemColetado) -> Path:
        """Grava o original imutável + manifesto de proveniência ao lado.

        O arquivo é nomeado pelo hash: mesmo conteúdo nunca é gravado duas vezes,
        e o nome já é a prova de integridade. O manifesto `.json` é o que
        responde "de onde veio e quando" sem depender do banco estar vivo.
        """
        sha = item.sha256
        destino = (
            self.diretorio_dados
            / "originais"
            / self.municipio
            / item.coletado_em.strftime("%Y/%m")
            / f"{sha}{item.extensao}"
        )
        destino.parent.mkdir(parents=True, exist_ok=True)

        if not destino.exists():
            destino.write_bytes(item.conteudo)

        manifesto = destino.with_suffix(destino.suffix + ".json")
        if manifesto.exists():
            # Já visto antes: registra que foi reencontrado, sem sobrescrever a
            # primeira observação. Saber que um documento continua no ar importa.
            dados = json.loads(manifesto.read_text(encoding="utf-8"))
            dados.setdefault("reobservado_em", []).append(item.coletado_em.isoformat())
        else:
            dados = {
                "sha256": sha,
                "url_origem": item.url_origem,
                "fonte": self.chave,
                "municipio_ibge": self.municipio,
                "tipo_documento": item.tipo_documento,
                "titulo": item.titulo,
                "numero": item.numero,
                "exercicio": item.exercicio,
                "identificador_externo": item.identificador_externo,
                "coletado_em": item.coletado_em.isoformat(),
                "tamanho_bytes": len(item.conteudo),
                "http_headers": item.http_headers,
                "metadados": item.metadados,
                "coletor_versao": getattr(self, "versao", "0.1"),
                "reobservado_em": [],
            }
        manifesto.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        return destino

    # -- rede --------------------------------------------------------------

    def get(self, url: str, **kw: Any) -> httpx.Response:
        """GET com limite de taxa, checagem de robots e repetição com recuo."""
        if self.respeitar_robots and not self._permitido(url):
            raise PermissionError(
                f"robots.txt do host proíbe {url}. "
                "Registre como limitação de transparência — não contorne."
            )
        self._aguardar()
        ultimo: Exception | None = None
        for tentativa in range(self.tentativas):
            try:
                resp = self._cliente.get(url, **kw)
                if resp.status_code in (429, 503):
                    espera = float(resp.headers.get("retry-after", 2**tentativa * 5))
                    log.warning("%s pediu espera de %.0fs", url, espera)
                    time.sleep(min(espera, 120))
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPError as exc:
                ultimo = exc
                if tentativa < self.tentativas - 1:
                    time.sleep(2**tentativa)
        raise RuntimeError(f"GET falhou após {self.tentativas} tentativas: {url}") from ultimo

    def _aguardar(self) -> None:
        decorrido = time.monotonic() - self._ultima_req
        if decorrido < self.intervalo_requisicao:
            time.sleep(self.intervalo_requisicao - decorrido)
        self._ultima_req = time.monotonic()

    def _permitido(self, url: str) -> bool:
        p = urlparse(url)
        raiz = f"{p.scheme}://{p.netloc}"
        if raiz not in self._robots:
            rp = RobotFileParser()
            rp.set_url(f"{raiz}/robots.txt")
            try:
                rp.read()
            except Exception:
                # Sem robots.txt acessível, o padrão da web é permitir. Alimentar
                # o parser com um arquivo vazio expressa isso sem depender de
                # atributo interno da stdlib.
                rp.parse([])
            self._robots[raiz] = rp
        return self._robots[raiz].can_fetch(UA, url)

    def __enter__(self) -> ColetorBase:
        return self

    def __exit__(self, *exc: object) -> None:
        self._cliente.close()
