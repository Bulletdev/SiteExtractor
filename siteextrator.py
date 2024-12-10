# Site extractor

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import zipfile
import tkinter as tk
from tkinter import filedialog, messagebox

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
}

def criar_estrutura_pasta(url, pasta_destino):
    parsed_url = urlparse(url)
    caminho_relativo = os.path.join(parsed_url.netloc, parsed_url.path.lstrip("/"))
    pasta_completa = os.path.dirname(os.path.join(pasta_destino, caminho_relativo))
    os.makedirs(pasta_completa, exist_ok=True)
    return pasta_completa

def baixar_arquivo(url, pasta_destino):
    try:
        response = requests.get(url, headers=HEADERS, stream=True, timeout=10)
        response.raise_for_status()
        
        caminho_arquivo = criar_estrutura_pasta(url, pasta_destino)
        nome_arquivo = os.path.basename(urlparse(url).path) or "index.html"
        caminho_completo = os.path.join(caminho_arquivo, nome_arquivo)

        # Verifica o tipo de conteúdo e baixa o arquivo
        with open(caminho_completo, 'wb') as f:
            f.write(response.content)
        print(f"Baixado: {url}")
        return caminho_completo
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar {url}: {e}")
    return None

def extrair_links(url, pasta_destino, visitados=set()):
    if url in visitados:
        return
    visitados.add(url)

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        for tag in soup.find_all(["a", "link", "script", "img"]):
            atributo = tag.get("href") or tag.get("src")
            if atributo:
                link = urljoin(url, atributo)
                # Limita ao mesmo domínio
                if urlparse(link).netloc == urlparse(url).netloc:
                    baixar_arquivo(link, pasta_destino)
                    # Recursão para páginas HTML internas
                    if link.endswith(".html") or link.endswith("/"):
                        extrair_links(link, pasta_destino, visitados)

    except requests.exceptions.RequestException as e:
        print(f"Erro ao extrair links de {url}: {e}")

def iniciar_download():
    url = entrada_url.get()
    pasta_destino = filedialog.askdirectory()
    if not pasta_destino:
        messagebox.showwarning("Aviso", "Por favor, selecione uma pasta de destino.")
        return

    extrair_links(url, pasta_destino)

    # Cria o arquivo zip
    zip_caminho = os.path.join(pasta_destino, "conteudo_site.zip")
    with zipfile.ZipFile(zip_caminho, 'w') as zipf:
        for root, _, files in os.walk(pasta_destino):
            for file in files:
                caminho_completo = os.path.join(root, file)
                arcname = os.path.relpath(caminho_completo, pasta_destino)
                zipf.write(caminho_completo, arcname)
    
    print(f"Arquivo zip criado: {zip_caminho}")
    messagebox.showinfo("Concluído", f"Download concluído e salvo em: {zip_caminho}")

# Configuração da interface gráfica
janela = tk.Tk()
janela.title("Download Completo de Sites")
janela.geometry("400x200")

label_url = tk.Label(janela, text="URL do site:")
label_url.pack(pady=5)

entrada_url = tk.Entry(janela, width=50)
entrada_url.pack(pady=5)

botao_download = tk.Button(janela, text="Baixar Conteúdo do Site e Compactar", command=iniciar_download)
botao_download.pack(pady=20)

janela.mainloop()
