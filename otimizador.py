import ctypes
import os
import sys
import tkinter as tk
from tkinter import font as tkfont

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import tema as t
from arranque import Arranque
from energia import Energia
from inicio import Inicio
from limpeza import Limpeza
from monitor import Monitor
from versao import VERSAO

ICONES = {"Início": chr(0xE80F), "Limpeza": chr(0xE74D), "Monitorização": chr(0xE9D9),
          "Arranque": chr(0xE768), "Energia": chr(0xE7E8)}
LOGO = chr(0xE945)


def recurso(nome):
    return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), nome)


def e_administrador():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Otimizador de PC {VERSAO}")
        self.configure(bg=t.BG)
        try:
            self.iconbitmap(default=recurso("icone.ico"))
        except tk.TclError:
            pass
        esc = self.winfo_fpixels("1i") / 96
        self.geometry(f"{int(1060 * esc)}x{int(800 * esc)}")
        self.minsize(int(940 * esc), int(760 * esc))
        t.estilos(self)
        self._barra_titulo_escura()

        familias = set(tkfont.families())
        self.fonte_icones = next((f for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets") if f in familias), None)

        lateral = tk.Frame(self, bg=t.LATERAL, width=int(220 * esc))
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        logo = tk.Frame(lateral, bg=t.LATERAL)
        logo.pack(fill="x", padx=20, pady=(24, 28))
        if self.fonte_icones:
            tk.Label(logo, text=LOGO, font=(self.fonte_icones, 18), bg=t.LATERAL, fg=t.ACENTO).pack(side="left")
        tk.Label(logo, text="Otimizador", font=t.fonte(15, "bold"), bg=t.LATERAL, fg=t.TEXTO).pack(side="left", padx=8)

        self.conteudo = tk.Frame(self, bg=t.BG)
        self.conteudo.pack(side="left", fill="both", expand=True)
        self.atual = None
        self.paginas = {
            "Início": Inicio(self.conteudo, self.mostrar),
            "Limpeza": Limpeza(self.conteudo),
            "Monitorização": Monitor(self.conteudo),
            "Arranque": Arranque(self.conteudo),
            "Energia": Energia(self.conteudo),
        }

        self.nav = {}
        for nome in self.paginas:
            self.nav[nome] = self._item_menu(lateral, nome)

        rod = tk.Frame(lateral, bg=t.LATERAL)
        rod.pack(side="bottom", fill="x", padx=20, pady=20)
        admin = e_administrador()
        tk.Label(rod, text="● " + ("Administrador" if admin else "Sem administrador"), font=t.fonte(9, "bold"),
                 bg=t.LATERAL, fg=t.VERDE if admin else t.AMARELO).pack(anchor="w")
        if not admin:
            tk.Label(rod, text="Algumas pastas e programas\ndo Windows não vão poder\nser alterados.",
                     font=t.fonte(8), bg=t.LATERAL, fg=t.SUAVE, justify="left").pack(anchor="w", pady=(2, 0))
        tk.Label(rod, text=f"Versão {VERSAO}", font=t.fonte(8), bg=t.LATERAL, fg="#5c6378").pack(anchor="w", pady=(10, 0))

        self.mostrar("Início")

    def _item_menu(self, master, nome):
        f = tk.Frame(master, bg=t.LATERAL, cursor="hand2")
        f.pack(fill="x", padx=12, pady=2)
        ind = tk.Frame(f, bg=t.LATERAL, width=3)
        ind.pack(side="left", fill="y")
        partes = [f, ind]
        if self.fonte_icones:
            ic = tk.Label(f, text=ICONES[nome], font=(self.fonte_icones, 12), bg=t.LATERAL, fg=t.SUAVE, width=2)
            ic.pack(side="left", padx=(10, 0), pady=10)
            partes.append(ic)
        tx = tk.Label(f, text=nome, font=t.fonte(10, "bold"), bg=t.LATERAL, fg=t.SUAVE)
        tx.pack(side="left", padx=10, pady=10)
        partes.append(tx)
        for w in partes:
            w.bind("<Button-1>", lambda e, n=nome: self.mostrar(n))
            w.bind("<Enter>", lambda e, n=nome: self._pintar(n, hover=True))
            w.bind("<Leave>", lambda e, n=nome: self._pintar(n))
        return partes

    def _pintar(self, nome, hover=False):
        ativo = nome == self.atual
        bg = t.CARTAO if ativo else (t.CARTAO2 if hover else t.LATERAL)
        f, ind, *labels = self.nav[nome]
        f.config(bg=bg)
        ind.config(bg=t.ACENTO if ativo else bg)
        for l in labels:
            l.config(bg=bg, fg=t.TEXTO if ativo or hover else t.SUAVE)
        if ativo and self.fonte_icones:
            labels[0].config(fg=t.ACENTO)

    def mostrar(self, nome):
        if nome == self.atual:
            return
        self.atual = nome
        for p in self.paginas.values():
            p.pack_forget()
        pagina = self.paginas[nome]
        if hasattr(pagina, "ao_mostrar"):
            pagina.ao_mostrar()
        pagina.pack(fill="both", expand=True)
        for n in self.nav:
            self._pintar(n)

    def _barra_titulo_escura(self):
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            val = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass


if __name__ == "__main__":
    App().mainloop()
