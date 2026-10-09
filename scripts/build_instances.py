"""Monta o conjunto de instâncias do experimento e grava data/instances.csv.

1) TSPLIB (Álvarez-Miranda et al., 2018): grafos publicados pelos autores; o orçamento é
   B = alpha*TSP + (1-alpha)*GTSP_FEAS, alpha in {0.25, 0.5, 0.75}, e os prêmios seguem os
   esquemas uniforme (unif) e pseudo-aleatório (rand).
2) POKE (sintéticas no estilo Pokémon GO): avistamentos concentrados em pontos de interesse
   de uma área urbana de 4 km x 4 km, ~100 espécies com frequências de cauda longa,
   distâncias = euclidiana x fator de desvio de rua (não satisfaz desigualdade triangular),
   apenas um subconjunto de espécies é obrigatório e B in {10, 15, 20} km.
"""
import csv
import json
import math
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCOP = os.path.join(ROOT, "bin", "gcop.exe")
RAW = os.path.join(ROOT, "data", "raw_download", "gcop-tsplib", "gpctsp_tsplib")
POKE = os.path.join(ROOT, "data", "poke")

TSPLIB_SUBSET = [
    "ulysses22", "bayg29", "att48", "eil51", "berlin52", "st70", "eil76", "pr76",
    "kroA100", "rd100", "eil101", "ch130", "kroA150", "kroA200", "gil262", "a280",
    "lin318", "pcb442",
]
ALPHAS = [0.25, 0.5, 0.75]


def budget_info(graph):
    out = subprocess.run([GCOP, "budget", graph], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def gen_poke(city_seed, path, n=450, species=100, side=4.0):
    rng = random.Random(city_seed)
    hotspots = [(rng.uniform(0.5, side - 0.5), rng.uniform(0.5, side - 0.5), rng.uniform(0.15, 0.45))
                for _ in range(rng.randint(4, 7))]
    pts = []
    for _ in range(n):
        if rng.random() < 0.7:
            hx, hy, sd = rng.choice(hotspots)
            x = min(side, max(0.0, rng.gauss(hx, sd)))
            y = min(side, max(0.0, rng.gauss(hy, sd)))
        else:
            x, y = rng.uniform(0, side), rng.uniform(0, side)
        pts.append((x, y))
    # frequências de cauda longa (Zipf, s = 0.9) => poucas espécies comuns, muitas raras
    w = [1.0 / (r + 1) ** 0.9 for r in range(species)]
    sp = rng.choices(range(species), weights=w, k=n)
    for s in range(species):  # garante ao menos um avistamento por espécie
        if s not in sp:
            sp[rng.randrange(n)] = s
    detour = {}
    for i in range(n):
        for j in range(i + 1, n):
            e = math.dist(pts[i], pts[j])
            detour[i, j] = e * (1.15 + 0.25 * rng.random())
    return pts, sp, detour


def write_poke(path, pts, sp, detour, required):
    n = len(pts)
    req = set(required)
    with open(path, "w") as f:
        f.write(f"Nodes {n}\nClusters {len(req)}\n")
        for i, (x, y) in enumerate(pts):
            lab = sp[i] if sp[i] in req else -1
            f.write(f"V {i} {lab} {x:.5f} {y:.5f}\n")
        for i in range(n):  # prêmio por espécie (mesmo valor para todos os nós da espécie)
            f.write(f"P {i} {1 + (7213 * (sp[i] + 1)) % 100}\n")
        for (i, j), d in detour.items():
            f.write(f"E {i} {j} {d:.6f}\n")


def ni_feasible(graph, budget):
    out = subprocess.run([GCOP, "solve", graph, "--profit", "unif", "--budget", str(budget),
                          "--algo", "NI-LS"], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)["feasible"]


def main():
    rows = []
    for name in TSPLIB_SUBSET:
        g = os.path.join(RAW, f"{name}p00005.tsp")
        info = budget_info(g)
        for prof in ["unif", "rand"]:
            for a in ALPHAS:
                B = a * info["tsp"] + (1 - a) * info["gtsp_feas"]
                rows.append(dict(name=f"{name}_a{int(a*100):03d}_{prof}", set="TSPLIB", graph=rel(g),
                                 profit=prof, alpha=a, B=round(B, 6), n=info["n"], K=info["K"],
                                 tsp=info["tsp"], gtsp_feas=info["gtsp_feas"]))
        print(name, info, file=sys.stderr)

    os.makedirs(POKE, exist_ok=True)
    for city, seed in [("cityA", 101), ("cityB", 202), ("cityC", 303)]:
        pts, sp, detour = gen_poke(seed, None)
        rng = random.Random(seed + 1)
        cand = sorted({s for s in sp if sp.count(s) >= 2})
        kreq = 15
        path = os.path.join(POKE, f"{city}.tsp")
        while True:  # reduz o nº de espécies obrigatórias até B = 10 km ser viável
            required = rng.sample(cand, kreq)
            write_poke(path, pts, sp, detour, required)
            if ni_feasible(path, 10.0) or kreq <= 3:
                break
            kreq -= 1
        info = budget_info(path)
        for prof in ["unif", "file"]:
            for B in [10, 15, 20]:
                rows.append(dict(name=f"{city}_B{B}_{'unif' if prof == 'unif' else 'spec'}", set="POKE",
                                 graph=rel(path), profit=prof, alpha="", B=B, n=info["n"], K=info["K"],
                                 tsp=info["tsp"], gtsp_feas=info["gtsp_feas"]))
        print(city, info, "kreq", kreq, file=sys.stderr)

    with open(os.path.join(ROOT, "data", "instances.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "instancias", file=sys.stderr)


if __name__ == "__main__":
    main()
