# Site Extractor

Baixa o conteúdo de um site para navegação offline. Recria a estrutura de
pastas original, baixa HTML, CSS, JavaScript e imagens, reescreve os links para
caminhos locais (a cópia navega de verdade) e opcionalmente compacta tudo em um
ZIP. Funciona por interface gráfica (Tkinter) ou por linha de comando.

## Funcionalidades

- Download recursivo com limite de profundidade configurável.
- Reescrita de links: a cópia offline navega entre as páginas baixadas.
- Respeito ao `robots.txt` e rate limiting educado entre requisições.
- Restrição ao mesmo domínio (com opção de liberar).
- Interface gráfica com barra de progresso e botão de cancelar (sem travar).
- Modo linha de comando para automação.
- Compactação opcional em ZIP.

## Estrutura do projeto

```
SiteExtractor/
├── site_extractor/
│   ├── __init__.py
│   ├── crawler.py      # lógica de download e reescrita de links (sem UI)
│   ├── cli.py          # interface de linha de comando
│   └── gui.py          # interface gráfica (Tkinter, com threading)
├── tests/
│   └── test_crawler.py
├── siteextrator.py     # entrypoint compatível (abre a GUI)
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## Pré-requisitos

- Python 3.9 ou superior
- `requests` e `beautifulsoup4` (ver `requirements.txt`)
- `tkinter` (nativo do Python; em algumas distros Linux instala-se com o pacote
  `python3-tk`)

## Instalação

```bash
git clone https://github.com/bulletdev/site-extractor.git
cd site-extractor
pip install -r requirements.txt
```

Para desenvolvimento (testes e linters):

```bash
pip install -r requirements-dev.txt
```

## Uso

### Interface gráfica

```bash
python siteextrator.py
```

1. Informe a URL do site.
2. Ajuste a profundidade e as opções desejadas.
3. Clique em "Baixar Site" e escolha a pasta de destino.

### Linha de comando

```bash
# Baixa a página inicial e seus assets
python -m site_extractor.cli https://exemplo.com -o ./saida

# Recursão de até 3 níveis, gerando um ZIP
python -m site_extractor.cli https://exemplo.com --depth 3 --zip

# Ignora robots.txt e remove o delay entre requisições
python -m site_extractor.cli https://exemplo.com --no-robots --delay 0
```

Veja todas as opções com `python -m site_extractor.cli --help`.

## Desenvolvimento

Linters e testes (equivalentes Python do ecossistema Rails):

| Ferramenta | Papel                        | Equivalente Rails |
|------------|------------------------------|-------------------|
| Ruff       | lint e formatação            | RuboCop           |
| Bandit     | análise de segurança         | Brakeman          |
| Semgrep    | análise semântica de padrões | Semgrep           |
| pytest     | testes                       | RSpec             |

```bash
ruff check .
ruff format --check .
bandit -r site_extractor -c pyproject.toml
semgrep --config .semgrep.yml --config p/python .
pytest -q
```

O mesmo conjunto roda automaticamente no CI (ver `.github/workflows/ci.yml`).

## Observações

- Conteúdo dinâmico gerado por JavaScript ou protegido por autenticação pode não
  ser baixado.
- Use apenas em sites de domínio público ou para os quais você tem permissão.

## Licença

Distribuído sob a licença [MIT](LICENSE).
