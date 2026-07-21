"""Site Extractor - baixa o conteúdo de um site para navegação offline.

Expõe a classe principal :class:`~site_extractor.crawler.SiteExtractor`,
que contém toda a lógica de download, reescrita de links, respeito ao
``robots.txt`` e controle de profundidade - sem qualquer dependência de
interface gráfica.
"""

from .crawler import CrawlResult, SiteExtractor

__all__ = ["SiteExtractor", "CrawlResult"]
__version__ = "1.0.0"
