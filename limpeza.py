import ctypes
import os

LOCAL = os.environ.get("LOCALAPPDATA", "")
WINDIR = os.environ.get("WINDIR", r"C:\Windows")
TEMP = os.environ.get("TEMP", "")
RECICLAGEM = "Reciclagem"
MINIATURAS = "Cache de miniaturas"

CATEGORIAS = {
    "Temporários do utilizador": ([TEMP], "Ficheiros temporários deixados pelas aplicações"),
    "Temporários do Windows": ([os.path.join(WINDIR, "Temp")], "Requer administrador"),
    "Cache do Chrome": ([
        os.path.join(LOCAL, r"Google\Chrome\User Data\Default\Cache"),
        os.path.join(LOCAL, r"Google\Chrome\User Data\Default\Code Cache"),
    ], "Feche o Chrome antes de limpar"),
    "Cache do Edge": ([
        os.path.join(LOCAL, r"Microsoft\Edge\User Data\Default\Cache"),
        os.path.join(LOCAL, r"Microsoft\Edge\User Data\Default\Code Cache"),
    ], "Feche o Edge antes de limpar"),
    MINIATURAS: ([os.path.join(LOCAL, r"Microsoft\Windows\Explorer")], "Pré-visualizações de imagens no Explorador"),
    "Relatórios de erros": ([os.path.join(LOCAL, r"Microsoft\Windows\WER")], "Relatórios de falhas antigos"),
    "Cache do Windows Update": ([os.path.join(WINDIR, r"SoftwareDistribution\Download")], "Requer administrador"),
}
ITENS = [(n, d) for n, (_, d) in CATEGORIAS.items()] + [(RECICLAGEM, "Esvazia a Reciclagem (desligado por defeito)")]


def _e_ligacao(p):
    # nunca seguir symlinks/junctions
    try:
        return os.path.islink(p) or os.path.isjunction(p)
    except OSError:
        return True


def ficheiros(pasta, so_miniaturas=False):
    if not pasta or not os.path.isdir(pasta):
        return
    for raiz, dirs, nomes in os.walk(pasta):
        dirs[:] = [d for d in dirs if not _e_ligacao(os.path.join(raiz, d))]
        for nome in nomes:
            if so_miniaturas and not nome.lower().startswith(("thumbcache_", "iconcache_")):
                continue
            p = os.path.join(raiz, nome)
            try:
                if not os.path.islink(p):
                    yield p, os.path.getsize(p)
            except OSError:
                pass


def tamanho_categoria(nome):
    if nome == RECICLAGEM:
        return tamanho_reciclagem()
    return sum(s for p in CATEGORIAS[nome][0] for _, s in ficheiros(p, nome == MINIATURAS))


def tamanho_reciclagem():
    class QUERY(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_ulong), ("i64Size", ctypes.c_longlong),
                    ("i64NumItems", ctypes.c_longlong)]
    q = QUERY(ctypes.sizeof(QUERY), 0, 0)
    try:
        ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(q))
        return q.i64Size
    except Exception:
        return 0


def limpar_categoria(nome):
    if nome == RECICLAGEM:
        antes = tamanho_reciclagem()
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7)
        return antes - tamanho_reciclagem(), 0
    libertado = falhas = 0
    for pasta in CATEGORIAS[nome][0]:
        for p, s in list(ficheiros(pasta, nome == MINIATURAS)):
            try:
                os.remove(p)
                libertado += s
            except OSError:
                falhas += 1
        if os.path.isdir(pasta):
            for raiz, dirs, _ in os.walk(pasta, topdown=False):
                for d in dirs:
                    sub = os.path.join(raiz, d)
                    if not _e_ligacao(sub):
                        try:
                            os.rmdir(sub)
                        except OSError:
                            pass
    return libertado, falhas
