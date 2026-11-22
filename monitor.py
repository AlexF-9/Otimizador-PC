import csv
import ctypes
import io
import os
import shutil
import subprocess
from ctypes import wintypes

CREATE_NO_WINDOW = 0x08000000


class _MEM(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]


def ram():
    m = _MEM()
    m.dwLength = ctypes.sizeof(_MEM)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullTotalPhys - m.ullAvailPhys, m.ullTotalPhys, m.dwMemoryLoad


def _tempos():
    i, k, u = (wintypes.FILETIME() for _ in range(3))
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u))
    v = lambda ft: (ft.dwHighDateTime << 32) | ft.dwLowDateTime
    return v(i), v(k) + v(u)  # inativo, total (o tempo de kernel já inclui o inativo)


class CpuMeter:
    def __init__(self):
        self.ultimo = _tempos()

    def percent(self):
        inativo, total = _tempos()
        di, dt = inativo - self.ultimo[0], total - self.ultimo[1]
        self.ultimo = (inativo, total)
        return max(0.0, min(100.0, 100.0 * (1 - di / dt))) if dt else 0.0


def disco():
    u = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
    return u.used, u.total, 100 * u.used / u.total


FIXO, AMOVIVEL = 3, 2

# leitores de cartões vazios não devem abrir a janela "Insira um disco"
try:
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x8000)
except Exception:
    pass


def discos():
    """Discos fixos e amovíveis com letra, ordenados com o disco do sistema primeiro."""
    k32 = ctypes.windll.kernel32
    buf = ctypes.create_unicode_buffer(512)
    n = k32.GetLogicalDriveStringsW(len(buf), buf)
    sistema = os.environ.get("SystemDrive", "C:").upper()
    res = []
    for raiz in (p for p in buf[:n].split("\0") if p):
        tipo = k32.GetDriveTypeW(raiz)
        if tipo not in (FIXO, AMOVIVEL):
            continue
        try:
            u = shutil.disk_usage(raiz)
        except OSError:
            continue
        if not u.total:
            continue
        nome, fs = ctypes.create_unicode_buffer(261), ctypes.create_unicode_buffer(261)
        k32.GetVolumeInformationW(raiz, nome, 261, None, None, None, fs, 261)
        letra = raiz[:2].upper()
        res.append({
            "letra": letra, "raiz": raiz,
            "nome": nome.value or ("Disco local" if tipo == FIXO else "Unidade amovível"),
            "amovivel": tipo == AMOVIVEL, "sistema": letra == sistema, "fs": fs.value,
            "total": u.total, "usado": u.used, "livre": u.free, "pct": 100 * u.used / u.total,
        })
    return sorted(res, key=lambda d: (not d["sistema"], d["amovivel"], d["letra"]))


def processos():
    out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                         encoding="oem", errors="replace", creationflags=CREATE_NO_WINDOW).stdout
    res = []
    for row in csv.reader(io.StringIO(out)):
        if len(row) >= 5 and row[1].isdigit():
            mem = "".join(c for c in row[4] if c.isdigit())
            res.append((row[0], int(row[1]), int(mem or 0) * 1024))
    return sorted(res, key=lambda r: r[2], reverse=True)


def terminar_processo(pid, forcar=False):
    cmd = ["taskkill", "/PID", str(pid)] + (["/F"] if forcar else [])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="oem", errors="replace",
                       creationflags=CREATE_NO_WINDOW)
    return r.returncode == 0, (r.stderr or r.stdout).strip()
