"""Analisador de espaço: mede quanto ocupa cada pasta. Só lê, nunca apaga nada.

Durante uma análise guarda-se, para cada pasta visitada, o tamanho dos ficheiros que tem diretamente
e as subpastas. Assim, entrar depois numa subpasta não obriga a ler o disco outra vez.
"""
import os
import time


class Cancelado(Exception):
    pass


class Indice:
    def __init__(self):
        self.diretos, self.contagem, self.filhos = {}, {}, {}

    def limpar(self):
        self.__init__()

    def conhece(self, pasta):
        return pasta in self.filhos

    def totais(self, pasta):
        """Tamanho e número de ficheiros de `pasta` e de tudo o que está dentro dela."""
        tam = n = 0
        pilha = [pasta]
        while pilha:
            p = pilha.pop()
            tam += self.diretos.get(p, 0)
            n += self.contagem.get(p, 0)
            pilha.extend(self.filhos.get(p, ()))
        return tam, n


def _ligacao(entrada):
    # nunca seguir symlinks nem junctions (ex.: "Documents and Settings")
    try:
        return entrada.is_symlink() or entrada.is_junction()
    except OSError:
        return True


def _ler(pasta, cancelar, indice, conta, tique):
    pilha = [pasta]
    while pilha:
        if cancelar.is_set():
            raise Cancelado
        atual = pilha.pop()
        tam = n = 0
        subs = []
        try:
            with os.scandir(atual) as it:
                for e in it:
                    try:
                        if _ligacao(e):
                            continue
                        if e.is_dir(follow_symlinks=False):
                            subs.append(e.path)
                        else:
                            tam += e.stat(follow_symlinks=False).st_size
                            n += 1
                    except OSError:
                        pass
        except OSError:
            pass  # sem permissão ou pasta desaparecida
        indice.diretos[atual], indice.contagem[atual], indice.filhos[atual] = tam, n, subs
        conta[0] += n
        pilha.extend(subs)
        tique()


def analisar(pasta, cancelar, progresso, indice):
    """Devolve as subpastas de `pasta` ordenadas por tamanho, mais uma entrada com os ficheiros soltos."""
    pasta = os.path.abspath(pasta)
    if not os.path.isdir(pasta):
        raise FileNotFoundError(f"A pasta {pasta} não existe.")

    if not indice.conhece(pasta):
        conta, ultimo = [0], [0.0]
        try:
            with os.scandir(pasta) as it:
                primeiro = [e.path for e in it if not _ligacao(e) and e.is_dir(follow_symlinks=False)]
        except OSError as erro:
            raise PermissionError(f"Não foi possível abrir {pasta}: {erro.strerror or erro}")
        for i, sub in enumerate(primeiro):
            def tique(i=i, sub=sub):
                agora = time.monotonic()
                if agora - ultimo[0] > 0.25:
                    ultimo[0] = agora
                    progresso(i, len(primeiro), os.path.basename(sub), conta[0])
            tique()
            _ler(sub, cancelar, indice, conta, tique)
        # a própria pasta (ficheiros soltos), registada no fim para só contar como conhecida se terminou
        tam = n = 0
        try:
            with os.scandir(pasta) as it:
                for e in it:
                    try:
                        if not _ligacao(e) and not e.is_dir(follow_symlinks=False):
                            tam += e.stat(follow_symlinks=False).st_size
                            n += 1
                    except OSError:
                        pass
        except OSError:
            pass
        indice.diretos[pasta], indice.contagem[pasta], indice.filhos[pasta] = tam, n, primeiro

    itens = []
    for sub in indice.filhos[pasta]:
        tam, n = indice.totais(sub)
        itens.append({"nome": os.path.basename(sub), "caminho": sub, "bytes": tam, "ficheiros": n, "pasta": True})
    if indice.contagem.get(pasta):
        itens.append({"nome": "Ficheiros nesta pasta", "caminho": pasta, "bytes": indice.diretos[pasta],
                      "ficheiros": indice.contagem[pasta], "pasta": False})
    itens.sort(key=lambda x: x["bytes"], reverse=True)
    total, n = indice.totais(pasta)
    return {"pasta": pasta, "total": total, "ficheiros": n, "itens": itens}
