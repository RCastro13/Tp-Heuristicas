"""Painel compacto (2 x 2) para o artigo: H1 dispersão, H2 boxplot, H2 acumulada e H3 barras.

Lê resultados/tabelas/gap_por_instancia.csv (gerado por analisa.py) e grava
resultados/figuras/artigo_painel.pdf e .png, dimensionados para a largura do texto (~16 cm).

Uso: python analise/figuras_artigo.py [pasta_resultados]
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analisa import CLASSES, COR_CLASSE, COR_METODO, MARCA_CLASSE, METODOS, SUPERFICIE, TINTA, TINTA2, fn  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "resultados")

plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5,
                     "ytick.labelsize": 6.5, "legend.fontsize": 6.2, "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"]})


def main():
    M = pd.read_csv(os.path.join(RES, "tabelas", "gap_por_instancia.csv"), index_col=0)
    classe = M.pop("classe")
    M6 = M[METODOS].dropna()
    cl = classe.reindex(M6.index)
    fig, ax = plt.subplots(2, 2, figsize=(6.3, 4.3))

    # (a) H1
    a = ax[0, 0]
    lim = max(M6.MSPD.max(), M6["MSPD-LS"].max(), 1) * 1.5
    a.plot([0, lim], [0, lim], color=TINTA2, lw=0.8, zorder=1)
    for c in CLASSES:
        idx = M6.index[cl == c]
        a.scatter(M6.loc[idx, "MSPD"], M6.loc[idx, "MSPD-LS"], s=9, marker=MARCA_CLASSE[c], color=COR_CLASSE[c],
                  edgecolor=SUPERFICIE, linewidth=0.3, label=c, zorder=2)
    a.set_xscale("symlog", linthresh=0.1); a.set_yscale("symlog", linthresh=0.1)
    a.set_xlim(-0.01, lim); a.set_ylim(-0.01, lim)
    a.set_xlabel("Gap do MSPD (%)"); a.set_ylabel("Gap do MSPD-LS (%)")
    a.set_title("(a) H1: abaixo da diagonal, a BL vence", loc="left")
    a.legend(ncol=5, loc="upper left", handletextpad=0.1, columnspacing=0.6, borderaxespad=0.2)

    # (b) H2 boxplot
    b = ax[0, 1]
    bp = b.boxplot([M6[m] for m in METODOS], widths=0.5, patch_artist=True, showmeans=True,
                   medianprops=dict(color=TINTA, lw=0.9), whiskerprops=dict(color=TINTA2, lw=0.7),
                   capprops=dict(color=TINTA2, lw=0.7),
                   meanprops=dict(marker="D", markerfacecolor=SUPERFICIE, markeredgecolor=TINTA, markersize=3),
                   flierprops=dict(marker="o", markersize=1.6, markerfacecolor=TINTA2, markeredgecolor="none", alpha=.5))
    for caixa, m in zip(bp["boxes"], METODOS):
        caixa.set(facecolor=COR_METODO[m], edgecolor=TINTA2, linewidth=0.6)
    b.set_xticks(range(1, len(METODOS) + 1), METODOS)
    b.set_yscale("symlog", linthresh=1); b.set_ylim(bottom=-0.05)
    b.grid(axis="x", visible=False)
    b.set_ylabel("Gap por instância (%)")
    b.set_title(f"(b) H2: gap nas {len(M6)} instâncias (losango = média)", loc="left")

    # (c) H2 acumulada
    c_ = ax[1, 0]
    tau = np.linspace(0, 5, 501)
    for m in METODOS:
        c_.plot(tau, [100 * (M6[m] <= t + 1e-9).mean() for t in tau], color=COR_METODO[m], lw=1.3, label=m)
    c_.set_xlim(0, 5); c_.set_ylim(0, 102)
    c_.set_xlabel("Tolerância τ (%)"); c_.set_ylabel("Instâncias com gap ≤ τ (%)")
    c_.set_title("(c) H2: distribuição acumulada do gap", loc="left")
    c_.legend(ncol=2, loc="lower right", handlelength=1.4)

    # (d) H3 barras
    d = ax[1, 1]
    mh = ["ILS", "ILS-C", "VNS", "ALNS", "MA"]
    T4, PK = M.index[classe == "T4"], M.index[classe == "PK"]
    g4 = [M.loc[T4, m].mean() for m in mh]
    gp = [M.loc[PK, m].mean() for m in mh]
    x = np.arange(len(mh)); w = 0.36
    d.bar(x - w / 2 - 0.01, g4, w, color=COR_CLASSE["T1"], label="T4", edgecolor=SUPERFICIE, linewidth=0.8)
    d.bar(x + w / 2 + 0.01, gp, w, color=COR_CLASSE["T2"], label="PK", edgecolor=SUPERFICIE, linewidth=0.8)
    for i in range(len(mh)):
        d.annotate(fn(g4[i], 2), (i - w / 2, g4[i]), xytext=(0, 1.5), textcoords="offset points", ha="center", fontsize=5.5, color=TINTA2)
        d.annotate(fn(gp[i], 2), (i + w / 2, gp[i]), xytext=(0, 1.5), textcoords="offset points", ha="center", fontsize=5.5, color=TINTA2)
    d.set_xticks(x, mh); d.grid(axis="x", visible=False)
    d.set_ylim(0, max(g4 + gp) * 1.18)
    d.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
    d.set_ylabel("Gap médio (%)")
    d.set_title("(d) H3: gap médio em T4 e PK", loc="left")
    d.legend(loc="upper left")

    fig.tight_layout(pad=0.3, h_pad=0.6, w_pad=0.8)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(RES, "figuras", f"artigo_painel.{ext}"), dpi=300)
    plt.close(fig)
    print("artigo_painel gerado")


if __name__ == "__main__":
    main()
