"""Lógica central de extração de sites - sem dependência de interface.

O módulo é totalmente utilizável de forma programática, pela CLI ou pela GUI.
Toda comunicação de progresso acontece através de um *callback* opcional, o que
mantém o núcleo desacoplado de qualquer camada de apresentação.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
)

# Tags cujo atributo aponta para um recurso que deve ser baixado.
TAG_ATTRS = {
    "a": "href",
    "link": "href",
    "script": "src",
    "img": "src",
    "source": "src",
    "iframe": "src",
}

# Extensões tratadas como páginas HTML (elegíveis para recursão).
HTML_EXTENSIONS = {"", ".html", ".htm", ".xhtml", ".php", ".asp", ".aspx"}


@dataclass
class CrawlResult:
    """Resumo do que foi baixado ao final de uma extração."""

    pages_visited: int = 0
    files_downloaded: int = 0
    errors: list[str] = field(default_factory=list)
    output_dir: str | None = None
    zip_path: str | None = None


# Assinatura do callback de progresso:
#   (feitos, total_conhecido, mensagem) -> None
# ``total_conhecido`` cresce conforme novos links são descobertos, então a
# fração feitos/total é uma estimativa que se refina ao longo do tempo.
ProgressCallback = Callable[[int, int, str], None]


class SiteExtractor:
    """Baixa um site inteiro (mesmo domínio) para navegação offline.

    Args:
        base_url: URL inicial da extração.
        output_dir: Pasta de destino onde a estrutura do site será recriada.
        max_depth: Profundidade máxima de recursão em links HTML. ``0`` baixa
            apenas a página inicial e seus assets diretos.
        same_domain: Se ``True``, restringe o download ao domínio da URL inicial.
        respect_robots: Se ``True``, consulta o ``robots.txt`` e ignora URLs
            proibidas.
        delay: Pausa (em segundos) entre requisições, para não sobrecarregar o
            servidor.
        timeout: Timeout de cada requisição HTTP, em segundos.
        rewrite_links: Se ``True``, reescreve os links do HTML baixado para
            caminhos locais relativos, tornando a cópia realmente navegável.
        user_agent: User-Agent enviado nas requisições.
        progress_callback: Função chamada a cada passo com o progresso.
    """

    def __init__(
        self,
        base_url: str,
        output_dir: str,
        *,
        max_depth: int = 1,
        same_domain: bool = True,
        respect_robots: bool = True,
        delay: float = 0.5,
        timeout: float = 10.0,
        rewrite_links: bool = True,
        user_agent: str = DEFAULT_USER_AGENT,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.base_url = self._normalize(base_url)
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.same_domain = same_domain
        self.respect_robots = respect_robots
        self.delay = delay
        self.timeout = timeout
        self.rewrite_links = rewrite_links
        self.progress_callback = progress_callback

        self.base_netloc = urlparse(self.base_url).netloc

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        self._visited: set[str] = set()
        self._downloaded: set[str] = set()
        self._robots: RobotFileParser | None = None
        self._user_agent = user_agent
        self._cancelled = False

    # API

    def cancel(self) -> None:
        """Sinaliza que a extração deve parar assim que possível.

        Seguro para chamar de outra thread (ex.: botão *Cancelar* na GUI).
        """
        self._cancelled = True

    def run(self) -> CrawlResult:
        """Executa a extração completa e retorna um :class:`CrawlResult`."""
        result = CrawlResult(output_dir=self.output_dir)

        if self.respect_robots:
            self._load_robots()

        # BFS por profundidade: fila de (url, profundidade).
        queue: deque[tuple[str, int]] = deque([(self.base_url, 0)])
        discovered = 1

        while queue and not self._cancelled:
            url, depth = queue.popleft()
            if url in self._visited:
                continue
            self._visited.add(url)

            if not self._allowed(url):
                logger.info("Ignorado por robots.txt: %s", url)
                continue

            html = self._fetch_page(url)
            if html is None:
                result.errors.append(url)
                self._emit(len(self._visited), discovered, f"Falha: {url}")
                continue

            result.pages_visited += 1
            soup = BeautifulSoup(html, "html.parser")

            # Baixa os assets e (opcionalmente) reescreve os links da página.
            child_pages = self._process_page(url, soup, result)

            # Salva a página (já com links reescritos, se habilitado).
            self._save_html(url, soup)
            self._emit(len(self._visited), discovered, f"Baixado: {url}")

            if depth < self.max_depth:
                for child in child_pages:
                    if child not in self._visited:
                        queue.append((child, depth + 1))
                        discovered += 1

            self._sleep()

        result.files_downloaded = len(self._downloaded)
        if self._cancelled:
            logger.info("Extração cancelada pelo usuário.")
        return result

    # helpers

    def _process_page(
        self, page_url: str, soup: BeautifulSoup, result: CrawlResult
    ) -> list[str]:
        """Baixa assets referenciados e devolve as páginas HTML internas.

        Quando ``rewrite_links`` está ativo, os atributos das tags são
        reescritos in-place para caminhos locais relativos.
        """
        child_pages: list[str] = []
        page_local = self._url_to_local_path(page_url)

        for tag in soup.find_all(list(TAG_ATTRS)):
            attr = TAG_ATTRS[tag.name]
            value = tag.get(attr)
            if not value:
                continue

            absolute = urljoin(page_url, value)
            absolute = self._normalize(absolute)
            parsed = urlparse(absolute)

            if parsed.scheme not in ("http", "https"):
                continue
            if self.same_domain and parsed.netloc != self.base_netloc:
                continue

            is_html = self._looks_like_html(parsed.path)

            if is_html:
                # Páginas internas: agendadas para recursão; assets ainda não
                # são baixados aqui (serão quando a página for visitada).
                child_pages.append(absolute)
            else:
                # Asset (css/js/img/...): baixa agora.
                if self._download_file(absolute, result):
                    self._sleep()

            if self.rewrite_links and self._allowed(absolute):
                local_target = self._url_to_local_path(absolute)
                tag[attr] = self._relative_path(page_local, local_target)

        return child_pages

    def _fetch_page(self, url: str) -> str | None:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.RequestException as exc:
            logger.warning("Erro ao acessar %s: %s", url, exc)
            return None

    def _download_file(self, url: str, result: CrawlResult) -> bool:
        if url in self._downloaded:
            return False
        if not self._allowed(url):
            logger.info("Ignorado por robots.txt: %s", url)
            return False

        self._downloaded.add(url)
        try:
            resp = self.session.get(url, timeout=self.timeout, stream=True)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            logger.warning("Erro ao baixar %s: %s", url, exc)
            result.errors.append(url)
            return False

        local_path = self._url_to_local_path(url)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            with open(local_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)
        except OSError as exc:
            logger.warning("Erro ao salvar %s: %s", local_path, exc)
            result.errors.append(url)
            return False

        logger.info("Baixado: %s", url)
        return True

    def _save_html(self, url: str, soup: BeautifulSoup) -> None:
        local_path = self._url_to_local_path(url)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as fh:
            fh.write(str(soup))
        self._downloaded.add(url)

    # path handling

    def _url_to_local_path(self, url: str) -> str:
        """Mapeia uma URL para um caminho local determinístico.

        O mapeamento é estável (mesma URL → mesmo caminho), o que permite que a
        reescrita de links aponte corretamente para os arquivos baixados.
        """
        parsed = urlparse(url)
        path = parsed.path
        if not path or path.endswith("/"):
            path = path + "index.html"

        # Query strings viram sufixo determinístico para evitar colisões.
        if parsed.query:
            root, ext = os.path.splitext(path)
            digest = hashlib.md5(
                parsed.query.encode(), usedforsecurity=False
            ).hexdigest()[:8]
            path = f"{root}__{digest}{ext or '.html'}"

        # Páginas sem extensão recebem .html para abrir no navegador.
        elif self._looks_like_html(path) and not os.path.splitext(path)[1]:
            path = path.rstrip("/") + "/index.html"

        segments = [self._safe_segment(s) for s in path.split("/") if s]
        return os.path.join(self.output_dir, parsed.netloc, *segments)

    @staticmethod
    def _relative_path(from_file: str, to_file: str) -> str:
        """Caminho relativo (estilo URL) de um arquivo para outro."""
        rel = os.path.relpath(to_file, os.path.dirname(from_file))
        return rel.replace(os.sep, "/")

    @staticmethod
    def _safe_segment(segment: str) -> str:
        """Remove caracteres inválidos para nomes de arquivo/pasta."""
        for ch in '<>:"|?*\\':
            segment = segment.replace(ch, "_")
        return segment or "_"

    @staticmethod
    def _looks_like_html(path: str) -> bool:
        ext = os.path.splitext(path.rstrip("/"))[1].lower()
        return ext in HTML_EXTENSIONS

    @staticmethod
    def _normalize(url: str) -> str:
        """Normaliza a URL removendo o fragmento (#âncora)."""
        parsed = urlparse(url.strip())
        return urlunparse(parsed._replace(fragment=""))

    # robots

    def _load_robots(self) -> None:
        robots_url = urljoin(self.base_url, "/robots.txt")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
            self._robots = parser
            logger.info("robots.txt carregado de %s", robots_url)
        except Exception as exc:  # rede indisponível, 404, etc.
            logger.info("robots.txt indisponível (%s); assumindo permitido.", exc)
            self._robots = None

    def _allowed(self, url: str) -> bool:
        if not self.respect_robots or self._robots is None:
            return True
        return self._robots.can_fetch(self._user_agent, url)

    # misc

    def _sleep(self) -> None:
        if self.delay > 0 and not self._cancelled:
            time.sleep(self.delay)

    def _emit(self, done: int, total: int, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(done, total, message)


def create_zip(source_dir: str, zip_path: str) -> str:
    """Compacta ``source_dir`` em ``zip_path``.

    O arquivo de saída é excluído da compactação caso esteja dentro de
    ``source_dir`` - assim o ZIP nunca tenta se incluir a si mesmo.
    """
    import zipfile

    zip_abs = os.path.abspath(zip_path)
    os.makedirs(os.path.dirname(zip_abs) or ".", exist_ok=True)

    with zipfile.ZipFile(zip_abs, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for name in files:
                full = os.path.join(root, name)
                if os.path.abspath(full) == zip_abs:
                    continue
                arcname = os.path.relpath(full, source_dir)
                zf.write(full, arcname)
    return zip_abs
