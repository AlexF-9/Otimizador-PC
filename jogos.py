"""Estimativa aproximada de FPS a partir do hardware.

Não é uma medição: compara a placa gráfica e o processador com tabelas de desempenho relativo
(médias públicas de benchmarks) e aplica resolução, qualidade e VRAM. Serve para ter uma ideia
da ordem de grandeza e de qual peça limita cada jogo.
"""
import re

# Desempenho relativo em jogos (rasterização), RTX 3060 12 GB = 100. Valores aproximados.
GPUS = {
    # NVIDIA
    "rtx 5090": 350, "rtx 5080": 265, "rtx 5070 ti": 235, "rtx 5070": 190, "rtx 5060 ti": 145, "rtx 5060": 130,
    "rtx 4090": 300, "rtx 4080 super": 250, "rtx 4080": 245, "rtx 4070 ti super": 215, "rtx 4070 ti": 200,
    "rtx 4070 super": 185, "rtx 4070": 160, "rtx 4060 ti": 125, "rtx 4060": 112,
    "rtx 3090 ti": 180, "rtx 3090": 165, "rtx 3080 ti": 162, "rtx 3080": 150, "rtx 3070 ti": 130,
    "rtx 3070": 122, "rtx 3060 ti": 112, "rtx 3060": 100, "rtx 3050": 72,
    "rtx 2080 ti": 125, "rtx 2080 super": 110, "rtx 2080": 103, "rtx 2070 super": 97, "rtx 2070": 88,
    "rtx 2060 super": 85, "rtx 2060": 75,
    "gtx 1660 ti": 63, "gtx 1660 super": 62, "gtx 1660": 56, "gtx 1650 super": 48, "gtx 1650": 38,
    "gtx 1080 ti": 92, "gtx 1080": 75, "gtx 1070 ti": 68, "gtx 1070": 62, "gtx 1060 3gb": 42, "gtx 1060": 47,
    "gtx 1050 ti": 28, "gtx 1050": 22, "gtx 980 ti": 55, "gtx 980": 45, "gtx 970": 38, "gtx 960": 25,
    # AMD
    "rx 9070 xt": 220, "rx 9070": 195, "rx 9060 xt": 130,
    "rx 7900 xtx": 245, "rx 7900 xt": 215, "rx 7900 gre": 180, "rx 7800 xt": 165, "rx 7700 xt": 140,
    "rx 7600 xt": 108, "rx 7600": 103,
    "rx 6950 xt": 175, "rx 6900 xt": 165, "rx 6800 xt": 155, "rx 6800": 135, "rx 6750 xt": 115,
    "rx 6700 xt": 110, "rx 6700": 100, "rx 6650 xt": 92, "rx 6600 xt": 88, "rx 6600": 78,
    "rx 6500 xt": 40, "rx 6400": 32,
    "rx 5700 xt": 85, "rx 5700": 77, "rx 5600 xt": 70, "rx 5500 xt": 45,
    "rx 590": 45, "rx 580": 40, "rx 570": 35, "rx 480": 38, "rx 470": 33, "vega 64": 60, "vega 56": 55,
    # Intel
    "arc b580": 105, "arc b570": 92, "arc a770": 95, "arc a750": 85, "arc a580": 75, "arc a380": 32,
    # integradas
    "890m": 40, "880m": 35, "780m": 30, "760m": 24, "680m": 26, "660m": 18,
    "radeon graphics": 12, "radeon vega": 12, "iris xe": 14, "arc graphics": 22,
    "uhd graphics 770": 8, "uhd graphics 750": 7, "uhd graphics 730": 6, "uhd graphics 630": 6,
    "uhd graphics": 6, "hd graphics": 4,
}

# Desempenho em jogos com a gráfica sem limitar, Ryzen 5 5600 = 100. Valores aproximados.
CPUS = {
    "9800x3d": 165, "9950x3d": 160, "9900x3d": 150, "7800x3d": 150, "7950x3d": 148, "7900x3d": 140,
    "9950x": 140, "9900x": 138, "9700x": 135, "9600x": 130, "7950x": 132, "7900x": 130, "7900": 125,
    "7700x": 128, "7700": 125, "7600x": 122, "7600": 118, "8700g": 112, "8600g": 108, "8500g": 95,
    "5800x3d": 128, "5700x3d": 122, "5950x": 112, "5900x": 110, "5800x": 108, "5700x": 104, "5700": 98,
    "5600x3d": 120, "5600x": 102, "5600": 100, "5500": 88, "5700g": 92, "5600g": 88,
    "3950x": 88, "3900x": 86, "3800x": 84, "3700x": 82, "3600x": 81, "3600": 80, "3500x": 72, "3400g": 62,
    "3300x": 74, "3100": 66, "2700x": 70, "2700": 66, "2600x": 67, "2600": 65, "2400g": 55, "1700": 58, "1600": 58,
    "285k": 140, "265k": 135, "265kf": 135, "245k": 125, "245kf": 125,
    "14900k": 150, "14900": 140, "14700k": 145, "14700": 135, "14600k": 135, "14400f": 115, "14400": 115,
    "13900k": 148, "13700k": 140, "13600k": 132, "13500": 118, "13400f": 112, "13400": 112,
    "12900k": 132, "12700k": 125, "12700": 120, "12600k": 120, "12400f": 105, "12400": 105, "12100f": 95,
    "11900k": 105, "11700k": 100, "11600k": 98, "11400f": 92, "11400": 92,
    "10900k": 98, "10700k": 92, "10700": 88, "10600k": 88, "10400f": 82, "10400": 82, "10100": 70,
    "9900k": 88, "9700k": 84, "9600k": 76, "9400f": 72, "9400": 72, "8700k": 78, "8700": 75, "8600k": 72,
    "8400": 68, "7700k": 62, "6700k": 58, "4790k": 50, "4770": 45,
}

# (nome, género, FPS de referência limitado pela gráfica, FPS de referência limitado pelo processador,
#  VRAM pedida a 1080p alto em GB, limite de FPS do jogo ou None)
# Referência: RTX 3060 + Ryzen 5 5600, 1080p, qualidade alta, sem ray tracing nem upscaling.
JOGOS = [
    ("Fortnite", "Battle royale", 105, 220, 6, None),
    ("Valorant", "Shooter competitivo", 420, 480, 2, None),
    ("Counter-Strike 2", "Shooter competitivo", 230, 300, 3, None),
    ("League of Legends", "MOBA", 400, 360, 2, None),
    ("Minecraft (Java)", "Sandbox", 320, 260, 2, None),
    ("Rocket League", "Desporto", 300, 360, 3, None),
    ("Apex Legends", "Battle royale", 150, 230, 6, 300),
    ("Call of Duty: Warzone", "Battle royale", 95, 165, 8, None),
    ("Marvel Rivals", "Shooter de heróis", 72, 145, 6, None),
    ("GTA V", "Mundo aberto", 140, 165, 4, None),
    ("Forza Horizon 5", "Corridas", 95, 165, 6, None),
    ("EA Sports FC", "Desporto", 170, 220, 4, None),
    ("Red Dead Redemption 2", "Mundo aberto", 65, 125, 6, None),
    ("Cyberpunk 2077", "RPG de ação", 65, 120, 8, None),
    ("Elden Ring", "RPG de ação", 75, 140, 6, 60),
    ("Black Myth: Wukong", "Ação", 45, 110, 8, None),
]

RESOLUCOES = {"1080p": 1.0, "1440p": 0.72, "4k": 0.42}
QUALIDADES = {"baixa": 1.7, "media": 1.3, "alta": 1.0, "ultra": 0.82}
VRAM_RES = {"1080p": 1.0, "1440p": 1.15, "4k": 1.4}
VRAM_QUAL = {"baixa": 0.65, "media": 0.85, "alta": 1.0, "ultra": 1.2}


def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"\((tm|r)\)|™|®|nvidia|geforce|amd|radeon(?= rx)|intel|core|processor|with radeon graphics", " ", s)
    s = s.replace("-", " ")
    return re.sub(r"\s+", " ", s).strip()


def _procurar(nome, tabela):
    n = _norm(nome)
    for chave in sorted(tabela, key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(chave)}(?![a-z0-9])", n):
            return chave, tabela[chave]
    return None, None


def pontuar_gpu(nome):
    chave, v = _procurar(nome, GPUS)
    if v and ("laptop" in nome.lower() or "mobile" in nome.lower()):
        v = round(v * 0.75)
    return v


def pontuar_cpu(nome, nucleos=None, mhz=None):
    chave, v = _procurar(nome, CPUS)
    if v:
        return v, True
    # não está na tabela: estimativa pelos núcleos e frequência
    if nucleos and mhz:
        v = 100 * (mhz / 4400) * (min(nucleos, 8) / 6) ** 0.3
        return max(40, min(130, round(v))), False
    return 75, False


def nivel_gpu(p):
    if p is None:
        return "Desconhecida"
    return "Topo de gama" if p >= 200 else "Gama alta" if p >= 130 else "Gama média" if p >= 85 \
        else "Gama de entrada" if p >= 40 else "Básica"


def estimar(info, resolucao="1080p", qualidade="alta"):
    resolucao = resolucao if resolucao in RESOLUCOES else "1080p"
    qualidade = qualidade if qualidade in QUALIDADES else "alta"
    gpus = [(g, pontuar_gpu(g["nome"])) for g in info.get("gpus", [])]
    gpus = [x for x in gpus if x[1]] or gpus
    gpu, pg = max(gpus, key=lambda x: x[1] or 0) if gpus else ({"nome": "", "vram": None}, None)
    cpu = info.get("cpu", {})
    pc, cpu_exata = pontuar_cpu(cpu.get("nome"), cpu.get("nucleos"), cpu.get("mhz"))
    vram_gb = (gpu.get("vram") or 0) / 1024 ** 3
    hz = (info.get("ecra") or {}).get("hz")

    jogos = []
    if pg:
        for nome, genero, ref_gpu, ref_cpu, vram, limite in JOGOS:
            fg = ref_gpu * pg / 100 * RESOLUCOES[resolucao] * QUALIDADES[qualidade]
            fc = ref_cpu * pc / 100 * (1.08 if qualidade == "baixa" else 1.0)
            fps = (fg ** -4 + fc ** -4) ** -0.25  # o mais lento manda, com transição suave
            precisa = vram * VRAM_RES[resolucao] * VRAM_QUAL[qualidade]
            falta_vram = bool(vram_gb) and vram_gb + 0.3 < precisa
            if falta_vram:
                fps *= 0.75
            gargalo = "Gráfica" if fg < fc * 0.85 else "Processador" if fc < fg * 0.85 else "Equilibrado"
            baixo, alto = fps * 0.88, fps * 1.1
            if limite:
                baixo, alto = min(baixo, limite), min(alto, limite)
            jogos.append({"nome": nome, "genero": genero, "min": round(baixo), "max": round(alto),
                          "gargalo": gargalo, "falta_vram": falta_vram, "limite": limite})
    return {
        "gpu": {"nome": gpu.get("nome", ""), "pontos": pg, "nivel": nivel_gpu(pg), "vram": gpu.get("vram")},
        "cpu": {"nome": cpu.get("nome", ""), "pontos": pc, "exata": cpu_exata},
        "ram": info.get("ram"),
        "hz": hz, "resolucao": resolucao, "qualidade": qualidade, "jogos": jogos,
    }
