"""Backward-compatible entrypoint.

Mantem o comando atual (`jarvis.chat_once:main`) funcionando enquanto
o codigo principal foi movido para modulos dedicados.
"""

from .cli import main


if __name__ == "__main__":
    main()
