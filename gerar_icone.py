import struct

TAMANHOS = (16, 24, 32, 48, 64, 256)
TOPO, FUNDO = (0x7a, 0x98, 0xff), (0x4a, 0x63, 0xe0)
RAIO = [(0.57, 0.12), (0.27, 0.56), (0.48, 0.56), (0.42, 0.88), (0.74, 0.43), (0.53, 0.43), (0.61, 0.12)]
AMOSTRAS = 4


def dentro_poligono(x, y, pol):
    d = False
    j = len(pol) - 1
    for i in range(len(pol)):
        xi, yi = pol[i]
        xj, yj = pol[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            d = not d
        j = i
    return d


def dentro_quadrado(x, y, r=0.22, m=0.04):
    if not (m <= x <= 1 - m and m <= y <= 1 - m):
        return False
    cx = min(max(x, m + r), 1 - m - r)
    cy = min(max(y, m + r), 1 - m - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def imagem(n):
    linhas = []
    for py in range(n):
        linha = bytearray()
        for px in range(n):
            fundo = raio = 0
            for sy in range(AMOSTRAS):
                for sx in range(AMOSTRAS):
                    x = (px + (sx + 0.5) / AMOSTRAS) / n
                    y = (py + (sy + 0.5) / AMOSTRAS) / n
                    if dentro_quadrado(x, y):
                        fundo += 1
                        raio += dentro_poligono(x, y, RAIO)
            tot = AMOSTRAS * AMOSTRAS
            if not fundo:
                linha += b"\0\0\0\0"
                continue
            k = py / max(n - 1, 1)
            base = [TOPO[c] + (FUNDO[c] - TOPO[c]) * k for c in range(3)]
            f = raio / fundo
            r, g, b = (int(base[c] + (255 - base[c]) * f) for c in range(3))
            linha += bytes((b, g, r, int(255 * fundo / tot)))
        linhas.append(bytes(linha))
    return b"".join(reversed(linhas))


def gerar(destino="icone.ico"):
    blocos = []
    for n in TAMANHOS:
        pix = imagem(n)
        mascara = b"\0" * (((n + 31) // 32) * 4 * n)
        cab = struct.pack("<IiiHHIIiiII", 40, n, n * 2, 1, 32, 0, len(pix) + len(mascara), 0, 0, 0, 0)
        blocos.append((n, cab + pix + mascara))
    saida = struct.pack("<HHH", 0, 1, len(blocos))
    pos = 6 + 16 * len(blocos)
    for n, dados in blocos:
        saida += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(dados), pos)
        pos += len(dados)
    with open(destino, "wb") as f:
        f.write(saida + b"".join(d for _, d in blocos))
    print("Criado", destino)


if __name__ == "__main__":
    gerar()
