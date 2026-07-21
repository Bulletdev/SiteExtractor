"""Interface de linha de comando do Site Extractor.

Exemplos::

    python -m site_extractor.cli https://exemplo.com -o ./saida
    python -m site_extractor.cli https://exemplo.com --depth 3 --zip
    python -m site_extractor.cli https://exemplo.com --no-robots --delay 0
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from .crawler import SiteExtractor, create_zip


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="site-extractor",
        description="Baixa o conteúdo de um site para navegação offline.",
    )
    parser.add_argument("url", help="URL inicial do site a ser baixado.")
    parser.add_argument(
        "-o",
        "--output",
        default="./site_download",
        help="Pasta de destino (padrão: ./site_download).",
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=1,
        help="Profundidade máxima de recursão em links (padrão: 1).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Pausa entre requisições, em segundos (padrão: 0.5).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout de cada requisição HTTP, em segundos (padrão: 10).",
    )
    parser.add_argument(
        "--all-domains",
        action="store_true",
        help="Segue links para fora do domínio inicial (use com cautela).",
    )
    parser.add_argument(
        "--no-robots",
        action="store_true",
        help="Ignora o robots.txt do site.",
    )
    parser.add_argument(
        "--no-rewrite",
        action="store_true",
        help="Não reescreve os links do HTML para caminhos locais.",
    )
    parser.add_argument(
        "--zip",
        dest="zip_output",
        action="store_true",
        help="Cria um arquivo ZIP com todo o conteúdo baixado.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Exibe logs detalhados do processo.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )

    def progress(done: int, total: int, message: str) -> None:
        print(f"[{done}/{total}] {message}")

    extractor = SiteExtractor(
        args.url,
        args.output,
        max_depth=args.depth,
        same_domain=not args.all_domains,
        respect_robots=not args.no_robots,
        delay=args.delay,
        timeout=args.timeout,
        rewrite_links=not args.no_rewrite,
        progress_callback=progress,
    )

    result = extractor.run()

    print()
    print(f"Páginas visitadas : {result.pages_visited}")
    print(f"Arquivos baixados : {result.files_downloaded}")
    print(f"Erros             : {len(result.errors)}")
    print(f"Pasta de saída    : {os.path.abspath(args.output)}")

    if args.zip_output:
        zip_path = os.path.abspath(args.output.rstrip("/\\")) + ".zip"
        create_zip(args.output, zip_path)
        print(f"ZIP criado        : {zip_path}")

    return 1 if result.errors and result.pages_visited == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
