"""Figuras de exemplo para a apresentação: um grafo TSPLIB-GCOP (berlin52) e um POKE (cidadeA).

Para cada instância grava duas versões em resultados/figuras/:
  exemplo_<nome>_grafo.{png,pdf}  -> vértices coloridos por cluster
  exemplo_<nome>_rota.{png,pdf}   -> idem + melhor rota encontrada (melhores_rotas.json)

Uso: python analise/figura_exemplos.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(RAIZ, "resultados", "figuras")
ROTAS = json.load(open(os.path.join(RAIZ, "resultados", "brutos", "melhores_rotas.json")))

plt.rcParams.update({"font.size": 12, "font.family": "sans-serif"})

EXEMPLOS = [
    # (arquivo, instância cuja rota é desenhada, título, unidade)
    ("dados/tsplib/berlin52p00005.tsp", "berlin52_a050_unif", "TSPLIB-GCOP — berlin52", ""),
    ("dados/poke/cidadeA.tsp", "cidadeA_B15_unif", "POKE — cidade A", " (km)"),
]


def le(caminho):
    V = []
    for linha in open(os.path.join(RAIZ, caminho)):
        p = linha.split()
        if p and p[0] == "V":
            V.append((int(p[2]), float(p[3]), float(p[4])))
    return V


def desenha(V, rota, titulo, unidade, saida):
    rot = sorted({c for c, _, _ in V if c >= 0})
    cmap = plt.get_cmap("tab20")
    cor = {c: cmap(i % 20) for i, c in enumerate(rot)}
    fig, ax = plt.subplots(figsize=(7, 6.3))
    grande = len(V) > 200
    sv, sr, lw = (30, 45, 0.8) if grande else (55, 110, 1.3)

    if rota:
        xs = [V[v][1] for v in rota] + [V[rota[0]][1]]
        ys = [V[v][2] for v in rota] + [V[rota[0]][2]]
        ax.plot(xs, ys, "-", color="#222222", lw=1.2 if grande else 1.6, zorder=2)

    opc = [(x, y) for c, x, y in V if c < 0]
    if opc:
        ax.scatter(*zip(*opc), s=14, c="#c4c4c4", edgecolors="none", zorder=1)
    for c in rot:
        pts = [(x, y) for cc, x, y in V if cc == c]
        ax.scatter(*zip(*pts), s=sv, color=cor[c], edgecolors="white", linewidths=0.6, zorder=3)
    if rota:
        ax.scatter([V[v][1] for v in rota], [V[v][2] for v in rota], s=sr, facecolors="none",
                   edgecolors="black", linewidths=lw, zorder=4)

    leg = [Line2D([], [], marker="o", ls="", color="#888888", markersize=8,
                  label=f"vértice de cluster ({len(rot)} clusters, cores)")]
    if opc:
        leg.append(Line2D([], [], marker="o", ls="", color="#c4c4c4", markersize=5,
                          label="vértice opcional (sem cluster)"))
    if rota:
        leg.append(Line2D([], [], color="#222222", lw=1.6, marker="o", markerfacecolor="none",
                          markeredgecolor="black", markersize=9, label="melhor rota encontrada"))
    ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=1, frameon=False)

    ax.set_title(f"{titulo}   (n = {len(V)}, K = {len(rot)})")
    ax.set_xlabel("x" + unidade)
    ax.set_ylabel("y" + unidade)
    ax.set_aspect("equal")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{saida}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("gravado", saida)


def main():
    os.makedirs(FIG, exist_ok=True)
    for arq, inst, titulo, un in EXEMPLOS:
        V = le(arq)
        nome = inst.split("_")[0]
        desenha(V, None, titulo, un, os.path.join(FIG, f"exemplo_{nome}_grafo"))
        desenha(V, ROTAS[inst], titulo + f"\nrota da instância {inst}", un, os.path.join(FIG, f"exemplo_{nome}_rota"))


if __name__ == "__main__":
    main()
