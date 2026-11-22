import ctypes
import os
import sys

import webview

from api import Api
from versao import VERSAO


def recurso(*partes):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), *partes)


def barra_titulo_escura(janela):
    try:
        hwnd = janela.native.Handle.ToInt32()
        val = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


def main():
    api = Api()
    janela = webview.create_window(
        f"Otimizador de PC {VERSAO}", recurso("ui", "index.html"), js_api=api,
        width=1180, height=800, min_size=(820, 640), background_color="#0f1117",
    )
    api._janela = janela
    janela.events.shown += lambda: barra_titulo_escura(janela)
    webview.start(debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
