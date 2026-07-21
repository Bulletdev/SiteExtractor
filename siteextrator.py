"""Entrypoint compatível - mantém o nome histórico do projeto.

A lógica agora vive no pacote ``site_extractor``. Executar este arquivo
diretamente abre a interface gráfica, como antes::

    python siteextrator.py
"""

from site_extractor.gui import main

if __name__ == "__main__":
    main()
