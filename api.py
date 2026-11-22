"""Funções que a interface (ui/app.js) chama através de window.pywebview.api."""
import ctypes
import json
import threading

import arranque
import energia
import limpeza
import monitor
from versao import VERSAO

SEGURAS = ["Temporários do utilizador", "Temporários do Windows", "Relatórios de erros",
           "Cache do Chrome", "Cache do Edge"]
BROWSERS = {"Cache do Chrome": ("chrome.exe", "o Chrome"), "Cache do Edge": ("msedge.exe", "o Edge")}


def e_administrador():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _id(p):
    return f"{p.raiz}|{p.sub}|{p.nome}"


class Api:
    def __init__(self):
        self._janela = None
        self._cpu = monitor.CpuMeter()
        self._progs = []
        self._trabalho = threading.Lock()  # só uma limpeza de cada vez

    def _emitir(self, evento, dados):
        if self._janela:
            self._janela.evaluate_js(f"window.receber({json.dumps(evento)}, {json.dumps(dados)})")

    # --- geral ------------------------------------------------------------

    def info(self):
        return {"versao": VERSAO, "admin": e_administrador()}

    def resumo(self):
        usado, total, pct = monitor.disco()
        progs = arranque.listar()
        return {"livre": total - usado, "total": total, "pct": pct,
                "arranque_ativos": sum(p.ativo for p in progs), "arranque_total": len(progs),
                "plano": energia.plano_ativo()}

    def otimizar_tudo(self):
        if not self._trabalho.acquire(blocking=False):
            return {"erro": "Já está uma limpeza a decorrer."}
        try:
            abertos = {p[0].lower() for p in monitor.processos()}
            res = []
            for i, nome in enumerate(SEGURAS):
                self._emitir("otimizar", {"i": i, "n": len(SEGURAS), "nome": nome})
                if nome in BROWSERS and BROWSERS[nome][0] in abertos:
                    res.append({"nome": nome, "ignorado": f"Ignorado: {BROWSERS[nome][1]} está aberto",
                                "bytes": 0, "falhas": 0})
                    continue
                lib, falhas = limpeza.limpar_categoria(nome)
                res.append({"nome": nome, "bytes": lib, "falhas": falhas})
            return {"resultados": res}
        except Exception as e:
            return {"erro": str(e)}
        finally:
            self._trabalho.release()

    # --- limpeza ----------------------------------------------------------

    def limpeza_categorias(self):
        return {"categorias": [{"nome": n, "desc": d, "ligado": n != limpeza.RECICLAGEM}
                               for n, d in limpeza.ITENS],
                "seguras": SEGURAS}

    def limpeza_analisar(self):
        tamanhos = {}
        try:
            for i, (nome, _) in enumerate(limpeza.ITENS):
                self._emitir("analise", {"i": i, "n": len(limpeza.ITENS), "nome": nome})
                tamanhos[nome] = limpeza.tamanho_categoria(nome)
                self._emitir("tamanho", {"nome": nome, "bytes": tamanhos[nome]})
            return {"tamanhos": tamanhos}
        except Exception as e:
            return {"erro": str(e), "tamanhos": tamanhos}

    def limpeza_limpar(self, nomes):
        validos = {n for n, _ in limpeza.ITENS}
        nomes = [n for n in nomes if n in validos]
        if not self._trabalho.acquire(blocking=False):
            return {"erro": "Já está uma limpeza a decorrer."}
        libertado = falhas = 0
        try:
            for i, nome in enumerate(nomes):
                self._emitir("limpeza", {"i": i, "n": len(nomes), "nome": nome})
                lib, fal = limpeza.limpar_categoria(nome)
                libertado += lib
                falhas += fal
            return {"libertado": libertado, "falhas": falhas}
        except Exception as e:
            return {"erro": str(e), "libertado": libertado, "falhas": falhas}
        finally:
            self._trabalho.release()

    # --- monitorização ----------------------------------------------------

    def estado(self):
        cpu = self._cpu.percent()
        ru, rt, rp = monitor.ram()
        du, dt, dp = monitor.disco()
        return {"cpu": cpu, "ram": [ru, rt, rp], "disco": [du, dt, dp]}

    def processos(self):
        return [{"nome": n, "pid": pid, "mem": mem} for n, pid, mem in monitor.processos()[:50]]

    def terminar(self, pid, forcar=False):
        ok, msg = monitor.terminar_processo(int(pid), bool(forcar))
        return {"ok": ok, "msg": msg}

    # --- arranque ---------------------------------------------------------

    def arranque_listar(self):
        self._progs = arranque.listar()
        return [{"id": _id(p), "nome": arranque.nome_bonito(p), "comando": p.comando,
                 "origem": p.origem, "ativo": p.ativo} for p in self._progs]

    def arranque_definir(self, ident, ativo):
        prog = next((p for p in self._progs if _id(p) == ident), None)
        if prog is None:
            return {"ok": False, "erro": "Programa não encontrado. Atualize a lista."}
        try:
            arranque.definir(prog, bool(ativo))
            return {"ok": True}
        except PermissionError:
            return {"ok": False, "admin": True,
                    "erro": f"'{arranque.nome_bonito(prog)}' está configurado para todos os utilizadores. "
                            "Abra o Otimizador como administrador para o alterar."}
        except OSError as e:
            return {"ok": False, "erro": str(e)}

    # --- energia ----------------------------------------------------------

    def energia_planos(self):
        lista = energia.planos()
        return {"planos": [{"guid": g, "nome": n, "ativo": a,
                            "desc": energia.DESCRICOES.get(g, "Plano criado pelo fabricante ou por si.")}
                           for g, n, a in lista],
                "tem_alto": any(g == energia.ALTO_DESEMPENHO for g, _, _ in lista)}

    def energia_ativar(self, guid):
        if guid not in {g for g, _, _ in energia.planos()}:
            return {"ok": False, "msg": "Plano desconhecido."}
        ok, msg = energia.ativar(guid)
        return {"ok": ok, "msg": msg}

    def energia_adicionar_alto(self):
        ok, msg = energia._powercfg("/duplicatescheme", energia.ALTO_DESEMPENHO)
        return {"ok": ok, "msg": msg}
