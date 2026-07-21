"""Testes unitários do núcleo do Site Extractor.

Focam na lógica pura (mapeamento de URL → caminho, reescrita de links,
compactação), sem tocar a rede.
"""

from __future__ import annotations

import os

import pytest

from site_extractor.crawler import SiteExtractor, create_zip


@pytest.fixture
def extractor(tmp_path):
    return SiteExtractor(
        "https://exemplo.com",
        str(tmp_path),
        respect_robots=False,
        delay=0,
    )


class TestUrlToLocalPath:
    def test_raiz_vira_index_html(self, extractor, tmp_path):
        path = extractor._url_to_local_path("https://exemplo.com/")
        assert path == os.path.join(str(tmp_path), "exemplo.com", "index.html")

    def test_arquivo_com_extensao(self, extractor, tmp_path):
        path = extractor._url_to_local_path("https://exemplo.com/css/main.css")
        assert path.endswith(os.path.join("exemplo.com", "css", "main.css"))

    def test_query_string_gera_sufixo_deterministico(self, extractor):
        a = extractor._url_to_local_path("https://exemplo.com/p.html?x=1")
        b = extractor._url_to_local_path("https://exemplo.com/p.html?x=1")
        c = extractor._url_to_local_path("https://exemplo.com/p.html?x=2")
        assert a == b  # determinístico
        assert a != c  # queries diferentes → caminhos diferentes

    def test_caracteres_invalidos_sao_sanitizados(self, extractor):
        path = extractor._url_to_local_path("https://exemplo.com/a<b>c.txt")
        assert "<" not in path and ">" not in path


class TestHelpers:
    def test_normalize_remove_fragmento(self, extractor):
        assert extractor._normalize("https://x.com/a#topo") == "https://x.com/a"

    def test_looks_like_html(self, extractor):
        assert extractor._looks_like_html("/pagina.html")
        assert extractor._looks_like_html("/pasta/")
        assert not extractor._looks_like_html("/style.css")

    def test_relative_path_entre_arquivos(self, extractor):
        rel = extractor._relative_path(
            "/out/exemplo.com/index.html",
            "/out/exemplo.com/css/main.css",
        )
        assert rel == "css/main.css"


class TestRewriteLinks:
    def test_links_sao_reescritos_para_caminho_local(self, extractor):
        from bs4 import BeautifulSoup

        from site_extractor.crawler import CrawlResult

        html = (
            "<html><body>"
            '<link href="https://exemplo.com/css/app.css">'
            '<a href="https://exemplo.com/sobre.html">sobre</a>'
            '<a href="https://outro.com/x">externo</a>'
            "</body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        # Não baixa de verdade: só exercita a reescrita in-place.
        extractor._download_file = lambda url, result: True  # type: ignore
        children = extractor._process_page(
            "https://exemplo.com/index.html", soup, CrawlResult()
        )

        assert soup.find("link")["href"] == "css/app.css"
        assert soup.find("a")["href"] == "sobre.html"
        # Link externo permanece intacto e não entra na fila de recursão.
        assert "https://exemplo.com/sobre.html" in children
        assert all("outro.com" not in c for c in children)


class TestAssetsCrossDomain:
    def test_asset_de_outro_dominio_e_baixado_por_padrao(self, tmp_path):
        from bs4 import BeautifulSoup

        from site_extractor.crawler import CrawlResult, SiteExtractor

        ext = SiteExtractor(
            "https://exemplo.com", str(tmp_path), respect_robots=False, delay=0
        )
        baixados = []
        ext._download_file = lambda url, result: baixados.append(url) or True  # type: ignore

        html = '<img src="https://cdn.outrodominio.com/foto.png">'
        soup = BeautifulSoup(html, "html.parser")
        ext._process_page("https://exemplo.com/index.html", soup, CrawlResult())

        # Asset em CDN de outro domínio deve ter sido baixado e reescrito.
        assert "https://cdn.outrodominio.com/foto.png" in baixados
        assert soup.find("img")["src"].endswith("cdn.outrodominio.com/foto.png")

    def test_asset_de_outro_dominio_ignorado_quando_desabilitado(self, tmp_path):
        from bs4 import BeautifulSoup

        from site_extractor.crawler import CrawlResult, SiteExtractor

        ext = SiteExtractor(
            "https://exemplo.com",
            str(tmp_path),
            respect_robots=False,
            delay=0,
            assets_all_domains=False,
        )
        baixados = []
        ext._download_file = lambda url, result: baixados.append(url) or True  # type: ignore

        html = '<img src="https://cdn.outrodominio.com/foto.png">'
        soup = BeautifulSoup(html, "html.parser")
        ext._process_page("https://exemplo.com/index.html", soup, CrawlResult())

        assert baixados == []  # nada baixado
        assert soup.find("img")["src"] == "https://cdn.outrodominio.com/foto.png"


class TestIgnoreQuery:
    def test_variacoes_de_query_colapsam(self, tmp_path):
        from bs4 import BeautifulSoup

        from site_extractor.crawler import CrawlResult, SiteExtractor

        ext = SiteExtractor(
            "https://exemplo.com",
            str(tmp_path),
            respect_robots=False,
            delay=0,
            ignore_query=True,
        )
        html = (
            '<a href="https://exemplo.com/loja.html?sort=preco">a</a>'
            '<a href="https://exemplo.com/loja.html?sort=nome">b</a>'
        )
        soup = BeautifulSoup(html, "html.parser")
        children = ext._process_page(
            "https://exemplo.com/index.html", soup, CrawlResult()
        )
        # Ambos os links colapsam para a mesma página sem query.
        assert children == [
            "https://exemplo.com/loja.html",
            "https://exemplo.com/loja.html",
        ]


class TestSrcset:
    def test_srcset_reescrito_por_url(self, tmp_path):
        from bs4 import BeautifulSoup

        from site_extractor.crawler import CrawlResult, SiteExtractor

        ext = SiteExtractor(
            "https://exemplo.com", str(tmp_path), respect_robots=False, delay=0
        )
        ext._download_file = lambda url, result: True  # type: ignore
        html = (
            '<img srcset="https://exemplo.com/a.png 1x, https://exemplo.com/b.png 2x">'
        )
        soup = BeautifulSoup(html, "html.parser")
        ext._process_page("https://exemplo.com/index.html", soup, CrawlResult())
        assert soup.find("img")["srcset"] == "a.png 1x, b.png 2x"

    def test_data_src_lazy_load_baixado(self, tmp_path):
        from bs4 import BeautifulSoup

        from site_extractor.crawler import CrawlResult, SiteExtractor

        ext = SiteExtractor(
            "https://exemplo.com", str(tmp_path), respect_robots=False, delay=0
        )
        baixados = []
        ext._download_file = lambda url, result: baixados.append(url) or True  # type: ignore
        html = '<img data-src="https://exemplo.com/lazy.png">'
        soup = BeautifulSoup(html, "html.parser")
        ext._process_page("https://exemplo.com/index.html", soup, CrawlResult())
        assert "https://exemplo.com/lazy.png" in baixados
        assert soup.find("img")["data-src"] == "lazy.png"


class TestMaxPages:
    def test_limite_de_paginas_para_o_crawl(self, tmp_path, monkeypatch):
        from site_extractor.crawler import SiteExtractor

        ext = SiteExtractor(
            "https://exemplo.com",
            str(tmp_path),
            respect_robots=False,
            delay=0,
            max_depth=5,
            max_pages=3,
        )
        # Cada página aponta para uma nova página interna, gerando recursão.
        counter = {"n": 0}

        def fake_fetch(url):
            counter["n"] += 1
            n = counter["n"]
            return f'<a href="https://exemplo.com/p{n}.html">x</a>'

        ext._fetch_page = fake_fetch  # type: ignore
        ext._save_html = lambda url, soup: None  # type: ignore
        result = ext.run()
        assert result.pages_visited == 3  # respeitou o teto


class TestCreateZip:
    def test_zip_nao_inclui_a_si_mesmo(self, tmp_path):
        src = tmp_path / "site"
        src.mkdir()
        (src / "a.txt").write_text("conteudo")
        zip_path = src / "saida.zip"  # dentro da própria pasta

        import zipfile

        create_zip(str(src), str(zip_path))
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert "a.txt" in names
        assert "saida.zip" not in names
