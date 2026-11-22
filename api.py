"""Funções que a interface (ui/app.js) chama através de window.pywebview.api."""
import ctypes
import json
import os
import threading

import arranque
import energia
import espaco
import jogos
import limpeza
import monitor
import sistema
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
        self._sistema = None
        self._sistema_pronto = threading.Event()
        self._indice = espaco.Indice()
        self._cancelar_espaco = threading.Event()
        self._espaco = threading.Lock()
        # a leitura do hardware demora alguns segundos, por isso começa logo em segundo plano
        threading.Thread(target=self._ler_sistema, daemon=True).start()

    def _ler_sistema(self):
        try:
            self._sistema = sistema.informacao()
        finally:
            self._sistema_pronto.set()

    def _emitir(self, evento, dados):
        if self._janela:
            self._janela.evaluate_js(f"window.receber({json.dumps(evento)}, {json.dumps(dados)})")

    # --- geral ------------------------------------------------------------

    def info(self):
        return {"versao": VERSAO, "admin": e_administrador()}

    def resumo(self):
        usado, total, pct = monitor.disco()
        progs = arranque.listar()
        return {"livre": total - usado, "total": total, "pct": pct, "discos": monitor.discos(),
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
        return {"cpu": cpu, "ram": [ru, rt, rp], "discos": monitor.discos()}

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

    # --- sistema e jogos (só leitura) -------------------------------------

    def sistema_info(self, atualizar=False):
        if atualizar and self._sistema_pronto.is_set():
            self._sistema_pronto.clear()
            threading.Thread(target=self._ler_sistema, daemon=True).start()
        self._sistema_pronto.wait(90)
        if not self._sistema:
            return {"erro": "Não foi possível ler a informação do sistema."}
        info = dict(self._sistema)
        info["ligado_segundos"] = sistema.tempo_ligado()
        return info

    def jogos_estimar(self, resolucao="1080p", qualidade="alta"):
        info = self.sistema_info()
        if info.get("erro"):
            return info
        return jogos.estimar(info, resolucao, qualidade)

    # --- analisador de espaço (só leitura) --------------------------------

    def espaco_discos(self):
        return monitor.discos()

    def espaco_analisar(self, pasta, de_novo=False):
        if not self._espaco.acquire(blocking=False):
            return {"erro": "Já está uma análise a decorrer."}
        try:
            if de_novo:
                self._indice.limpar()
            self._cancelar_espaco.clear()
            return espaco.analisar(pasta, self._cancelar_espaco,
                                   lambda i, n, nome, f: self._emitir("espaco", {"i": i, "n": n, "nome": nome, "ficheiros": f}),
                                   self._indice)
        except espaco.Cancelado:
            return {"cancelado": True}
        except OSError as e:
            return {"erro": str(e)}
        finally:
            self._espaco.release()

    def espaco_cancelar(self):
        self._cancelar_espaco.set()
        return True

    def abrir_pasta(self, pasta):
        # só abre o Explorador numa pasta que existe; não altera nada
        if not os.path.isdir(pasta):
            return {"ok": False, "erro": "A pasta já não existe."}
        os.startfile(pasta)
        return {"ok": True}
