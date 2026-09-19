"""Coletor do PNCP — Portal Nacional de Contratações Públicas.

O PNCP é a única fonte que entrega o universo completo de contratações
municipais sob a Lei 14.133, com órgão, objeto, valor, modalidade, itens,
vencedor e o edital em PDF. Tudo mais neste projeto se pendura nele.

Sob a Lei 14.133 a publicação no PNCP é condição de eficácia do ato. Isso tem
uma consequência que vale mais que a coleta em si: **a ausência de publicação é,
ela própria, um achado** — e dos mais objetivos que existem.

## Duas APIs, e você precisa das duas

    /api/consulta   varre por período, modalidade e órgão. NÃO expõe anexos.
    /api/pncp       detalhe de um processo: itens, arquivos, resultados.

Quem tenta baixar edital pela API de consulta perde tempo: ela não serve isso.

## Armadilhas já pagas por outros

Cada uma destas custou horas a alguém. Estão codificadas abaixo:

- O WAF recusa requisição sem User-Agent de navegador.
- `/api/consulta` exige `Accept: application/json`.
- `codigoModalidadeContratacao` é obrigatório e **não existe "todas"** —
  tem que iterar código por código.
- Janela de datas maior que 365 dias devolve 422.
- `tamanhoPagina` omitido → pagina de 10 em 10 e **trunca em silêncio**.
- Limite de taxa às vezes chega como **HTML com status 200**, não como 429.
- Alguns endpoints devolvem JSON com caracteres de controle não escapados.
- `/contratos` usa `cnpjOrgao` e `usuarioId`; os outros usam `cnpj` e
  `idUsuario`. Não é erro de digitação — a API é assim mesmo.

As constantes de paginação e a lista de modalidades ficam aqui, e não em
`normas/`, porque são fatos técnicos da API, não regras jurídicas. O que nunca
pode vir para cá é limite legal (valor de dispensa, prazo de publicação).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterator

import httpx

from radar.coleta.base import ColetorBase, ItemColetado

log = logging.getLogger(__name__)

BASE_CONSULTA = "https://pncp.gov.br/api/consulta"
BASE_PNCP = "https://pncp.gov.br/api/pncp"

#: O WAF do PNCP recusa User-Agent que não pareça navegador. Não é tentativa de
#: disfarce — é o mínimo para a requisição passar. A identificação real do
#: projeto vai no cabeçalho From, que nenhum WAF filtra.
UA_NAVEGADOR = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)


class Modalidade:
    """Códigos de modalidade. Obrigatório iterar: não há filtro 'todas'."""

    LEILAO_ELETRONICO = 1
    DIALOGO_COMPETITIVO = 2
    CONCURSO = 3
    CONCORRENCIA_ELETRONICA = 4
    CONCORRENCIA_PRESENCIAL = 5
    PREGAO_ELETRONICO = 6
    PREGAO_PRESENCIAL = 7
    DISPENSA = 8
    INEXIGIBILIDADE = 9
    MANIFESTACAO_INTERESSE = 10
    PRE_QUALIFICACAO = 11
    CREDENCIAMENTO = 12

    #: Onde está o volume e onde está o risco, num município pequeno.
    #: Pregão eletrônico é o grosso; dispensa e inexigibilidade são as portas
    #: por onde se evita a disputa. Comece por estas três.
    PRIORITARIAS = (PREGAO_ELETRONICO, DISPENSA, INEXIGIBILIDADE)

    TODAS = tuple(range(1, 13))

    NOMES = {
        1: "Leilão Eletrônico", 2: "Diálogo Competitivo", 3: "Concurso",
        4: "Concorrência Eletrônica", 5: "Concorrência Presencial",
        6: "Pregão Eletrônico", 7: "Pregão Presencial", 8: "Dispensa",
        9: "Inexigibilidade", 10: "Manifestação de Interesse",
        11: "Pré-qualificação", 12: "Credenciamento",
    }


# Tetos de paginação. Divergem entre a documentação v1.0 (500) e o comportamento
# observado em 2026 (50 para contratações). Começamos pelo menor: subir é
# barato, descobrir truncamento silencioso em produção é caro.
PAGINA_CONTRATACOES = 50
PAGINA_ATAS_CONTRATOS = 500
JANELA_MAX_DIAS = 365


class RespostaInvalida(RuntimeError):
    """A API respondeu, mas não com o que prometeu.

    Existe porque o PNCP devolve página HTML de bloqueio com status 200. Sem
    esta checagem, o coletor registraria "0 contratações" — e o painel diria
    que o município não licitou nada naquele mês.
    """


@dataclass(slots=True)
class Contratacao:
    """Uma contratação como o PNCP a devolve, com o mínimo normalizado."""

    numero_controle: str
    cnpj_orgao: str
    ano: int
    sequencial: int
    modalidade: int
    objeto: str
    valor_estimado: float | None
    data_publicacao: date | None
    data_abertura_proposta: date | None
    data_encerramento_proposta: date | None
    situacao: str | None
    bruto: dict[str, Any]

    @classmethod
    def de_json(cls, d: dict[str, Any]) -> Contratacao:
        def dt(chave: str) -> date | None:
            if v := d.get(chave):
                try:
                    return date.fromisoformat(str(v)[:10])
                except ValueError:
                    return None
            return None

        return cls(
            numero_controle=d.get("numeroControlePNCP", ""),
            cnpj_orgao=(d.get("orgaoEntidade") or {}).get("cnpj", "") or d.get("cnpj", ""),
            ano=int(d.get("anoCompra") or 0),
            sequencial=int(d.get("sequencialCompra") or 0),
            modalidade=int(d.get("modalidadeId") or 0),
            objeto=d.get("objetoCompra") or "",
            valor_estimado=d.get("valorTotalEstimado"),
            data_publicacao=dt("dataPublicacaoPncp"),
            data_abertura_proposta=dt("dataAberturaProposta"),
            data_encerramento_proposta=dt("dataEncerramentoProposta"),
            situacao=d.get("situacaoCompraNome"),
            bruto=d,
        )

    @property
    def url_publica(self) -> str:
        """Página no portal — para citar em peça, um humano precisa poder abrir.

        Atenção: é montada com cnpj/ano/sequencial. Usar o numeroControlePNCP
        aqui NÃO funciona; ele é identificador, não caminho.
        """
        return f"https://pncp.gov.br/app/editais/{self.cnpj_orgao}/{self.ano}/{self.sequencial}"


class ColetorPNCP(ColetorBase):
    chave = "pncp"
    nome = "Portal Nacional de Contratações Públicas"
    url_base = BASE_CONSULTA
    versao = "0.1"
    intervalo_requisicao = 1.0
    #: O PNCP não publica robots.txt aplicável à API, e a API é feita para ser
    #: consumida por máquina. Checar robots a cada chamada só gasta requisição.
    respeitar_robots = False

    def __init__(
        self,
        diretorio_dados: Any,
        municipio_codigo_ibge: str,
        cnpjs_orgaos: list[str] | None = None,
        modalidades: tuple[int, ...] = Modalidade.PRIORITARIAS,
        baixar_anexos: bool = True,
    ) -> None:
        super().__init__(diretorio_dados, municipio_codigo_ibge)
        self.cnpjs = [so_digitos(c) for c in (cnpjs_orgaos or [])]
        self.modalidades = modalidades
        self.baixar_anexos = baixar_anexos
        self._cliente.headers.update({
            "User-Agent": UA_NAVEGADOR,
            "Accept": "application/json",
            "From": "radar-fiscalizacao-municipal (projeto de controle social)",
        })

    # -- leitura ----------------------------------------------------------

    def _json(self, url: str, params: dict[str, Any]) -> Any:
        resp = self.get(url, params=params)
        tipo = resp.headers.get("content-type", "")
        if "json" not in tipo:
            # Bloqueio do WAF costuma chegar assim: HTML, status 200.
            raise RespostaInvalida(
                f"{url} devolveu {tipo!r} em vez de JSON (status {resp.status_code}). "
                "Provável bloqueio por taxa. NÃO interprete como 'nada encontrado'."
            )
        try:
            return resp.json()
        except json.JSONDecodeError:
            # Caracteres de controle não escapados aparecem em objetos que vieram
            # de copiar-e-colar de Word. strict=False os tolera.
            return json.loads(resp.text, strict=False)

    def _paginar(
        self, caminho: str, params: dict[str, Any], tamanho: int
    ) -> Iterator[dict[str, Any]]:
        """Percorre todas as páginas. Nunca confia no default do servidor."""
        pagina = 1
        while True:
            p = {**params, "pagina": pagina, "tamanhoPagina": tamanho}
            try:
                dados = self._json(f"{BASE_CONSULTA}{caminho}", p)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 204:
                    return                      # sem conteúdo: fim normal
                if exc.response.status_code == 422:
                    log.error("422 em %s — janela de datas provavelmente > 365 dias", caminho)
                raise

            registros = dados.get("data") if isinstance(dados, dict) else dados
            if not registros:
                return
            yield from registros

            total_paginas = (dados.get("totalPaginas") if isinstance(dados, dict) else None)
            if total_paginas and pagina >= int(total_paginas):
                return
            if len(registros) < tamanho:
                return                          # última página parcial
            pagina += 1

    # -- contrato do ColetorBase ------------------------------------------

    def buscar(self, desde: datetime | None = None) -> Iterator[ItemColetado]:
        inicio = (desde.date() if desde else date.today() - timedelta(days=90))
        fim = date.today()

        for janela_ini, janela_fim in fatiar_janelas(inicio, fim):
            for modalidade in self.modalidades:
                yield from self._buscar_modalidade(modalidade, janela_ini, janela_fim)

    def _buscar_modalidade(
        self, modalidade: int, inicio: date, fim: date
    ) -> Iterator[ItemColetado]:
        params: dict[str, Any] = {
            "dataInicial": inicio.strftime("%Y%m%d"),   # sem hífen — a API exige
            "dataFinal": fim.strftime("%Y%m%d"),
            "codigoModalidadeContratacao": modalidade,
        }
        # Filtrar por município cobre todos os órgãos de uma vez (Prefeitura,
        # Câmara e fundos) — inclusive os cujo CNPJ ainda não descobrimos.
        # É justamente o que permite enxergar fracionamento entre entes.
        params["codigoMunicipioIbge"] = self.municipio

        log.info("PNCP %s %s→%s modalidade %s (%s)",
                 self.municipio, inicio, fim, modalidade, Modalidade.NOMES.get(modalidade))

        for bruto in self._paginar("/v1/contratacoes/publicacao", params, PAGINA_CONTRATACOES):
            c = Contratacao.de_json(bruto)
            if self.cnpjs and so_digitos(c.cnpj_orgao) not in self.cnpjs:
                continue

            yield ItemColetado(
                url_origem=c.url_publica,
                conteudo=json.dumps(bruto, ensure_ascii=False, sort_keys=True).encode(),
                tipo_documento="contratacao_pncp",
                titulo=c.objeto[:300],
                numero=c.numero_controle,
                exercicio=c.ano,
                identificador_externo=c.numero_controle,
                http_headers={"content-type": "application/json"},
                metadados={
                    "modalidade": modalidade,
                    "modalidade_nome": Modalidade.NOMES.get(modalidade, "?"),
                    "cnpj_orgao": c.cnpj_orgao,
                    "sequencial": c.sequencial,
                    "valor_estimado": c.valor_estimado,
                    "data_publicacao": c.data_publicacao.isoformat() if c.data_publicacao else None,
                    "data_encerramento_proposta": (
                        c.data_encerramento_proposta.isoformat()
                        if c.data_encerramento_proposta else None
                    ),
                    "situacao": c.situacao,
                },
            )

            if self.baixar_anexos:
                yield from self._baixar_anexos(c)

    def _baixar_anexos(self, c: Contratacao) -> Iterator[ItemColetado]:
        """Baixa edital, termo de referência, projeto básico e demais anexos.

        A URL de download vem no campo `url` de cada entrada da listagem — não
        se monta na mão.
        """
        listagem_url = (
            f"{BASE_PNCP}/v1/orgaos/{so_digitos(c.cnpj_orgao)}"
            f"/compras/{c.ano}/{c.sequencial}/arquivos"
        )
        try:
            arquivos = self._json(listagem_url, {})
        except (httpx.HTTPError, RespostaInvalida) as exc:
            log.warning("sem listagem de arquivos para %s: %s", c.numero_controle, exc)
            return

        if not isinstance(arquivos, list):
            return

        for arq in arquivos:
            url = arq.get("url") or arq.get("uri")
            if not url:
                continue
            try:
                resp = self.get(url)
            except httpx.HTTPError as exc:
                log.warning("falha baixando anexo %s: %s", url, exc)
                continue

            yield ItemColetado(
                url_origem=url,
                conteudo=resp.content,
                tipo_documento=classificar_anexo(arq.get("tipoDocumentoNome", "")),
                titulo=arq.get("titulo") or arq.get("tipoDocumentoNome"),
                numero=c.numero_controle,
                exercicio=c.ano,
                identificador_externo=(
                    f"{c.numero_controle}#{arq.get('sequencialDocumento', '')}"
                ),
                http_headers=dict(resp.headers),
                metadados={
                    "contratacao": c.numero_controle,
                    "tipo_documento_pncp": arq.get("tipoDocumentoNome"),
                    "sequencial_documento": arq.get("sequencialDocumento"),
                },
            )

    # -- consultas úteis fora da varredura --------------------------------

    def contratacoes_com_proposta_aberta(self) -> list[Contratacao]:
        """Licitações ainda recebendo proposta.

        É a consulta que dá utilidade prática ao radar: enquanto a proposta está
        aberta, um vício de edital ainda cabe em impugnação. Depois da abertura,
        sobra representação — que é mais lenta e mais grave. Achado encontrado a
        tempo vale muito mais que achado encontrado depois.
        """
        achadas: list[Contratacao] = []
        for modalidade in self.modalidades:
            params = {
                "dataFinal": (date.today() + timedelta(days=90)).strftime("%Y%m%d"),
                "codigoModalidadeContratacao": modalidade,
                "codigoMunicipioIbge": self.municipio,
            }
            for bruto in self._paginar("/v1/contratacoes/proposta", params, PAGINA_CONTRATACOES):
                achadas.append(Contratacao.de_json(bruto))
        return achadas

    def itens(self, c: Contratacao) -> list[dict[str, Any]]:
        """Itens de uma contratação — base para comparação de preço unitário."""
        url = (f"{BASE_PNCP}/v1/orgaos/{so_digitos(c.cnpj_orgao)}"
               f"/compras/{c.ano}/{c.sequencial}/itens")
        dados = self._json(url, {})
        return dados if isinstance(dados, list) else []


# -- auxiliares -------------------------------------------------------------


def so_digitos(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())


def fatiar_janelas(inicio: date, fim: date, dias: int = JANELA_MAX_DIAS) -> list[tuple[date, date]]:
    """Quebra o período em janelas aceitas pela API (>365 dias devolve 422)."""
    janelas: list[tuple[date, date]] = []
    atual = inicio
    while atual <= fim:
        prox = min(atual + timedelta(days=dias - 1), fim)
        janelas.append((atual, prox))
        atual = prox + timedelta(days=1)
    return janelas


def classificar_anexo(tipo_pncp: str) -> str:
    """Traduz o tipo do PNCP para o vocabulário interno de `documento.tipo`."""
    t = (tipo_pncp or "").lower()
    if "edital" in t:
        return "edital"
    if "termo de referência" in t or "termo de referencia" in t:
        return "termo_referencia"
    if "projeto básico" in t or "projeto basico" in t:
        return "projeto_basico"
    if "estudo técnico" in t or "estudo tecnico" in t:
        return "etp"
    if "ata" in t:
        return "ata"
    if "contrato" in t:
        return "contrato"
    if "planilha" in t or "orçament" in t:
        return "planilha_orcamentaria"
    return "anexo"
