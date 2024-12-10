# Site Extractor

Um projeto Python com interface gráfica para download completo do conteúdo de um site. O aplicativo permite baixar arquivos HTML, CSS, JavaScript, imagens, e outros ativos de um site, mantendo a estrutura de pastas original, e cria um arquivo ZIP com todo o conteúdo baixado.

## Funcionalidades

- **Download Completo**: Baixa arquivos HTML, CSS, JavaScript, imagens e outros ativos relacionados ao site.
- **Estrutura de Pastas**: Mantém a estrutura de pastas do site conforme exibida na aba de fontes do navegador.
- **Compactação**: Cria um arquivo ZIP com o conteúdo baixado.

## Pré-requisitos

- **Python 3.x** instalado
- Bibliotecas necessárias:
  - `requests`
  - `bs4` (BeautifulSoup4)
  - `tkinter` (nativo do Python para interface gráfica)

## Instalação

1. Clone o repositório:
    ```bash
    git clone https://github.com/bulletdev/SiteExtractor.git
    cd site-extractor
    ```

2. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

3. Execute o aplicativo:
    ```bash
    python siteextrator.py
    ```

## Como Usar

1. Insira a URL do site que deseja baixar.
2. Escolha uma pasta de destino para salvar o conteúdo.
3. Clique no botão **"Baixar Conteúdo do Site e Compactar"**.
4. O conteúdo do site será baixado e compactado em um arquivo ZIP na pasta de destino escolhida.

## Estrutura de Código

- `siteextrator.py` - Arquivo principal que contém o código para baixar o site.
- `extrair_links` - Função responsável por encontrar e baixar todos os arquivos relacionados ao site.
- `baixar_arquivo` - Função que baixa um único arquivo e o salva na estrutura de pastas correspondente.
- `iniciar_download` - Função principal para iniciar o processo de download e compactação.

## Observações

- O programa pode não baixar certos arquivos protegidos por restrições de acesso (como conteúdo dinâmico gerado por JavaScript ou protegido por autenticação).
- Recomendado para uso em sites de domínio público ou para os quais você tem permissão de download.

## Licença

Este projeto é de código aberto e está disponível sob a licença [MIT](LICENSE).
