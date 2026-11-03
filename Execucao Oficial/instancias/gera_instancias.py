"""Monta as 408 instâncias do artigo e grava dados/instancias.csv.

TSPLIB-GCOP: os 65 grafos do artigo base; B = alpha*TSP + (1-alpha)*GTSP, alpha em {0,25; 0,5; 0,75};
prêmios uniformes ou pseudoaleatórios (390 instâncias). TSP e GTSP são os melhores comprimentos
obtidos por ILS sobre as distâncias dos arquivos (gcop orcamento), guardados em dados/orcamento.csv.

POKE: 3 cidades com 450 locais em 4 km x 4 km, concentrados em pontos de interesse, cada local com
uma de 100 espécies, das quais 15 são obrigatórias (K = 15); distância = euclidiana x fator de
desvio sorteado em [1,15; 1,40] para cada par. Cidades em que NI + OTIMIZAROTA não encontre rota de
até 10 km cobrindo os clusters são refeitas. B em {10, 15, 20} km; prêmios uniformes ou
inversamente proporcionais à frequência da espécie (18 instâncias).

Uso: python instancias/gera_instancias.py [workers]
"""
import csv
import json
import math
import os
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCOP = os.path.join(RAIZ, "bin", "gcop.exe")
TSPLIB = os.path.join(RAIZ, "dados", "tsplib")
POKE = os.path.join(RAIZ, "dados", "poke")
ORC = os.path.join(RAIZ, "dados", "orcamento.csv")
ALFAS = [0.25, 0.5, 0.75]
SEMENTES_CIDADE = {"cidadeA": 101, "cidadeB": 202, "cidadeC": 303}
N_LOCAIS, N_ESPECIES, K, LADO, B_MIN = 450, 100, 15, 4.0, 10.0


def classe(n):
    return "T1" if n <= 52 else "T2" if n <= 101 else "T3" if n <= 200 else "T4"


def rel(p):
    return os.path.relpath(p, RAIZ).replace("\\", "/")


def orcamento_grafo(arq):
    with open(os.path.join(TSPLIB, arq)) as f:
        n = int(f.readline().split()[1])
    seg = min(60.0, max(10.0, n / 5.0))
    out = subprocess.run([GCOP, "orcamento", os.path.join(TSPLIB, arq), "--tempo", str(seg)],
                         capture_output=True, text=True, check=True)
    d = json.loads(out.stdout)
    d["arq"] = arq
    print(arq, d, flush=True)
    return d


def calcula_orcamentos(workers):
    if os.path.exists(ORC):
        with open(ORC) as f:
            return list(csv.DictReader(f))
    arqs = sorted(os.listdir(TSPLIB))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        linhas = list(ex.map(orcamento_grafo, arqs))
    with open(ORC, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["arq", "n", "K", "tsp", "gtsp"])
        w.writeheader()
        w.writerows(linhas)
    with open(ORC) as f:
        return list(csv.DictReader(f))


def gera_cidade(sem):
    """Sorteia uma cidade completa; devolve locais, espécies, distâncias e espécies obrigatórias."""
    r = random.Random(sem)
    focos = [(r.uniform(0.5, LADO - 0.5), r.uniform(0.5, LADO - 0.5), r.uniform(0.15, 0.45))
             for _ in range(r.randint(4, 7))]
    pts = []
    for _ in range(N_LOCAIS):
        if r.random() < 0.7:  # pontos de interesse
            hx, hy, dp = r.choice(focos)
            pts.append((min(LADO, max(0.0, r.gauss(hx, dp))), min(LADO, max(0.0, r.gauss(hy, dp)))))
        else:
            pts.append((r.uniform(0, LADO), r.uniform(0, LADO)))
    # frequências de cauda longa: poucas espécies comuns, muitas raras
    pesos = [1.0 / (e + 1) ** 0.9 for e in range(N_ESPECIES)]
    esp = r.choices(range(N_ESPECIES), weights=pesos, k=N_LOCAIS)
    for e in range(N_ESPECIES):
        if e not in esp:
            while True:  # garante ao menos uma ocorrência sem eliminar outra espécie
                i = r.randrange(N_LOCAIS)
                if esp.count(esp[i]) > 1:
                    esp[i] = e
                    break
    cand = sorted({e for e in esp if esp.count(e) >= 2})
    obrig = set(r.sample(cand, K))
    return pts, esp, obrig, [[(i, j, math.dist(pts[i], pts[j]) * r.uniform(1.15, 1.40))
                              for j in range(i + 1, N_LOCAIS)] for i in range(N_LOCAIS)]


def grava_cidade(caminho, pts, esp, obrig, arestas):
    freq = {e: esp.count(e) for e in set(esp)}
    fmax = max(freq.values())
    with open(caminho, "w") as f:
        f.write(f"Nodes {N_LOCAIS}\nClusters {K}\n")
        for i, (x, y) in enumerate(pts):
            f.write(f"V {i} {esp[i] if esp[i] in obrig else -1} {x:.5f} {y:.5f}\n")
        for i in range(N_LOCAIS):  # prêmio inversamente proporcional à frequência
            f.write(f"P {i} {fmax / freq[esp[i]]:.6f}\n")
        for linha in arestas:
            for i, j, d in linha:
                f.write(f"E {i} {j} {d:.6f}\n")


def gera_poke():
    os.makedirs(POKE, exist_ok=True)
    info = {}
    for nome, sem0 in SEMENTES_CIDADE.items():
        caminho = os.path.join(POKE, f"{nome}.tsp")
        for tent in range(100000):
            sem = sem0 + 1000 * tent
            pts, esp, obrig, arestas = gera_cidade(sem)
            grava_cidade(caminho, pts, esp, obrig, arestas)
            out = subprocess.run([GCOP, "checaNI", caminho], capture_output=True, text=True, check=True)
            L = json.loads(out.stdout)["L"]
            if L <= B_MIN:
                break
        tam = sorted(esp.count(e) for e in obrig)
        info[nome] = dict(semente=sem, tentativas=tent + 1, L_NI=L, tamanhos_clusters=tam)
        print(nome, info[nome], flush=True)
    with open(os.path.join(RAIZ, "dados", "poke_geracao.json"), "w") as f:
        json.dump(info, f, indent=1)


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    orc = calcula_orcamentos(workers)
    linhas = []
    for o in orc:
        n, tsp, gtsp = int(o["n"]), float(o["tsp"]), float(o["gtsp"])
        base = o["arq"].replace("p00005.tsp", "")
        for prem in ["unif", "rand"]:
            for a in ALFAS:
                linhas.append(dict(nome=f"{base}_a{int(a * 100):03d}_{prem}", conjunto="TSPLIB", classe=classe(n),
                                   grafo=rel(os.path.join(TSPLIB, o["arq"])), premio=prem, alfa=a,
                                   B=round(a * tsp + (1 - a) * gtsp, 6), n=n, K=int(o["K"]), tsp=tsp, gtsp=gtsp))
    if not all(os.path.exists(os.path.join(POKE, f"{c}.tsp")) for c in SEMENTES_CIDADE):
        gera_poke()
    for c in SEMENTES_CIDADE:
        for prem, rot in [("unif", "unif"), ("arquivo", "freq")]:
            for B in [10, 15, 20]:
                linhas.append(dict(nome=f"{c}_B{B}_{rot}", conjunto="POKE", classe="PK",
                                   grafo=rel(os.path.join(POKE, f"{c}.tsp")), premio=prem, alfa="", B=B,
                                   n=N_LOCAIS, K=K, tsp="", gtsp=""))
    with open(os.path.join(RAIZ, "dados", "instancias.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print(len(linhas), "instancias")


if __name__ == "__main__":
    main()
