# Regras do projeto SiteExtractor

## Escrita (docs, comentários, código, mensagens)
- NUNCA usar travessão (em dash, unicode U+2014). Use hífen "-" quando precisar de um separador.
- NUNCA usar emoji em nenhum lugar (código, docstrings, comentários, README, commits).

## Git
- NUNCA adicionar `Co-Authored-By` em commits.
- NUNCA fazer commit sem perguntar antes.

## Estrutura
- Lógica de negócio fica em `site_extractor/crawler.py` (sem dependência de UI).
- `site_extractor/cli.py` e `site_extractor/gui.py` são apenas camadas de apresentação.
- Testes em `tests/`, rodados com `pytest`.

## Qualidade
- Linters: Ruff (lint + format), Bandit (segurança), Semgrep (padrões).
- Rodar antes de commitar: `ruff check . && bandit -r site_extractor -c pyproject.toml && pytest -q`.
