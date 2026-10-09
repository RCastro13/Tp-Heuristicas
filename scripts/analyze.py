"""Consolida os resultados (results/*.jsonl) em tabelas Markdown (results/tables.md) e
figuras PNG (docs/figs/). Uso: python scripts/analyze.py"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
FIG = os.path.join(ROOT, "docs", "figs")
os.makedirs(FIG, exist_ok=True)

CONSTR = ["NI", "FI", "ST", "TSPD"]
META = ["MSPD", "MSPD-LS", "GRASP", "ILS", "VNS", "ALNS", "SA", "TS", "MA"]
META8 = ["MSPD", "GRASP", "ILS", "VNS", "ALNS", "SA", "TS", "MA"]
# paleta categórica de referência (skill dataviz), ordem fixa
PAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
COL = dict(zip(META8, PAL))
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
    "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150, "savefig.bbox": "tight",
    "lines.linewidth": 2,
})


def load(name):
    p = os.path.join(RES, f"{name}.jsonl")
    if not os.path.exists(p):
        return pd.DataFrame()
    rows = []
    with open(p) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return pd.DataFrame(rows)


def size_class(r):
    if r["set"] == "POKE":
        return "E: POKE (450)"
    n = r["n"]
    if n <= 52:
        return "A: n<=52"
    if n <= 101:
        return "B: 70-101"
    if n <= 200:
        return "C: 130-200"
    return "D: 262-442"


def md(df, floatfmt=".2f"):
    return df.to_markdown(floatfmt=floatfmt)


def main():
    inst = pd.read_csv(os.path.join(ROOT, "data", "instances.csv"))
    inst["cls"] = inst.apply(size_class, axis=1)
    inst = inst.set_index("name")
    H = load("heur"); EX = load("exact"); LB = load("lbr")
    BB = pd.concat([load("bb"), load("bb_asc")], ignore_index=True)  # 2 executores concorrentes
    if not BB.empty:
        BB = BB.drop_duplicates(subset="inst", keep="first").reset_index(drop=True)
    for df in (H, BB, EX, LB):
        if not df.empty and "error" in df.columns:
            df.drop(df[df["error"].notna()].index, inplace=True)
    H["prize"] = np.where(H["feasible"], H["prize"], np.nan)
    out = []

    # ------------------------------------------------ referências por instância
    allp = [H[["inst", "prize"]]]
    for df in (BB, EX, LB):
        if not df.empty:
            allp.append(df.loc[df["feasible"] == True, ["inst", "prize"]])
    bks = pd.concat(allp).groupby("inst")["prize"].max()
    inst["BKS"] = bks
    inst["OPT"] = np.nan
    inst["UB"] = np.nan
    if not EX.empty:
        e = EX.set_index("inst")
        opt_mask = e["status"].isin(["optimal", "hint_optimal"])
        inst.loc[e.index[opt_mask], "OPT"] = e.loc[opt_mask, "ub"].round(6)
        inst["UB_exact"] = e["ub"]
        inst["exact_time"] = e["time"]
        inst["exact_status"] = e["status"]
    ubs = []
    if not EX.empty:
        ubs.append(EX.set_index("inst")["ub"])
    if not BB.empty:
        ubs.append(BB.set_index("inst")["ub"])
    if ubs:
        inst["UB"] = pd.concat(ubs, axis=1).min(axis=1)
        inst["UB"] = np.minimum(inst["UB"], np.where(inst["OPT"].notna(), inst["OPT"], np.inf))
    H = H.join(inst[["BKS", "UB", "cls", "set", "alpha", "profit"]], on="inst")
    H["gap"] = 100 * (H["BKS"] - H["prize"].fillna(0)) / H["BKS"]
    H["gap_ub"] = 100 * (H["UB"] - H["prize"].fillna(0)) / H["UB"]

    # ------------------------------------------------ T0: referências
    nopt = int(inst["OPT"].notna().sum())
    out.append("## T0. Referências por instância\n")
    out.append(f"Instâncias: {len(inst)}; com ótimo provado pelo EXACT (CUT): {nopt}.\n")
    cols = ["set", "n", "K", "alpha", "profit", "B", "BKS", "OPT", "UB"]
    t0 = inst[cols].copy()
    if not BB.empty:
        b = BB.set_index("inst")
        t0["BB_prize"] = b["prize"]; t0["BB_ub"] = b["ub"]; t0["BB_status"] = b["status"]
    if not EX.empty:
        t0["EX_time"] = inst["exact_time"]; t0["EX_status"] = inst["exact_status"]
    out.append(md(t0))
    out.append("")

    # ------------------------------------------------ T1: construtivas (H1)
    C = H[H["algo"].isin([f"{c}{s}" for c in CONSTR for s in ["", "-SR", "-LS"]])].copy()
    C["constr"] = C["algo"].str.split("-").str[0]
    C["var"] = C["algo"].str.split("-").str[1].fillna("raw")
    t1 = C.pivot_table(index="constr", columns="var", values="gap", aggfunc="mean")[["raw", "SR", "LS"]]
    t1t = C.pivot_table(index="constr", columns="var", values="time", aggfunc="mean")[["raw", "SR", "LS"]] * 1000
    t1.columns = [f"gap% {c}" for c in t1.columns]
    t1t.columns = [f"tempo ms {c}" for c in t1t.columns]
    out.append("## T1. Construtivas: gap médio (%) ao BKS e tempo médio (ms) — sem BL (raw), refinamento sigma do artigo (SR) e BL exata proposta (LS)\n")
    out.append(md(pd.concat([t1, t1t], axis=1)))
    # vitórias LS x SR
    p = C.pivot_table(index=["inst", "constr"], columns="var", values="prize")
    w = (p["LS"] > p["SR"] + 1e-9).sum(); l = (p["LS"] < p["SR"] - 1e-9).sum(); t = len(p) - w - l
    st = stats.wilcoxon(p["LS"], p["SR"], zero_method="wilcox", alternative="greater") if w + l > 0 else None
    out.append(f"\nLS x SR (pares instância x construtiva): LS melhor em {w}, pior em {l}, empate em {t}; "
               f"Wilcoxon unilateral p = {st.pvalue:.3g}.\n" if st else "")
    t1c = C.pivot_table(index="cls", columns="algo", values="gap", aggfunc="mean")
    out.append("### T1b. Gap médio (%) das construtivas por classe de tamanho\n")
    out.append(md(t1c[[f"{c}{s}" for c in CONSTR for s in ["", "-SR", "-LS"]]].T))
    out.append("")

    # ------------------------------------------------ T2: metaheurísticas
    M = H[H["algo"].isin(META)].copy()
    agg = M.groupby(["algo", "inst"]).agg(gap=("gap", "mean"), gbest=("gap", "min"), gsd=("gap", "std"),
                                           hit=("gap", lambda g: (g < 1e-9).mean()),
                                           tb=("time_best", "mean"), it=("iters", "mean"),
                                           tl=("tlim", "mean")).reset_index()
    t2 = agg.groupby("algo").agg(**{
        "gap médio %": ("gap", "mean"), "gap melhor semente %": ("gbest", "mean"),
        "desvio entre sementes": ("gsd", "mean"), "% exec. = BKS": ("hit", lambda h: 100 * h.mean()),
        "% inst. BKS (alguma semente)": ("gbest", lambda g: 100 * (g < 1e-9).mean()),
        "gap máx %": ("gap", "max"), "t até melhor (s)": ("tb", "mean"),
        "t até melhor / t lim": ("tb", lambda x: np.nan), "iterações": ("it", "mean")}).reindex(META)
    t2["t até melhor / t lim"] = (agg.assign(r=agg["tb"] / agg["tl"]).groupby("algo")["r"].mean()).reindex(META)
    # rank médio (Friedman)
    piv = agg.pivot(index="inst", columns="algo", values="gap")[META].dropna()
    ranks = piv.rank(axis=1, method="average").mean()
    t2["rank médio"] = ranks
    out.append("## T2. Metaheurísticas (5 sementes, t(n) = max(1, n/50) s): desempenho global\n")
    out.append(md(t2))
    fr = stats.friedmanchisquare(*[piv[a] for a in META])
    out.append(f"\nFriedman (9 métodos, {len(piv)} instâncias): chi2 = {fr.statistic:.1f}, p = {fr.pvalue:.3g}.\n")
    # Wilcoxon vs controle MSPD com Holm
    rows = []
    for a in META:
        if a == "MSPD":
            continue
        d = piv["MSPD"] - piv[a]
        w = (d > 1e-9).sum(); l = (d < -1e-9).sum()
        pv = stats.wilcoxon(piv[a], piv["MSPD"], alternative="less").pvalue if (w + l) > 0 else 1.0
        rows.append(dict(metodo=a, melhor_que_MSPD=w, pior=l, empate=len(d) - w - l, p_bruto=pv))
    wt = pd.DataFrame(rows).sort_values("p_bruto")
    k = len(wt); adj = []; run = 0
    for i, pv in enumerate(wt["p_bruto"]):
        run = max(run, min(1, (k - i) * pv)); adj.append(run)
    wt["p_Holm"] = adj
    out.append("### T2b. Wilcoxon pareado (unilateral: método tem gap menor que MSPD), correção de Holm\n")
    out.append(md(wt.set_index("metodo"), floatfmt=".3g"))
    # melhor proposta vs. melhor par
    out.append("")
    t3 = agg.join(inst[["cls"]], on="inst").pivot_table(index="cls", columns="algo", values="gap", aggfunc="mean")[META]
    out.append("## T3. Gap médio (%) ao BKS por classe de tamanho\n")
    out.append(md(t3))
    out.append("")
    a2 = agg.join(inst[["set", "alpha", "profit"]], on="inst")
    a2["grupo"] = np.where(a2["set"] == "POKE", "POKE " + a2["profit"], "TSPLIB a=" + a2["alpha"].astype(str) + " " + a2["profit"])
    t4 = a2.pivot_table(index="grupo", columns="algo", values="gap", aggfunc="mean")[META]
    out.append("## T4. Gap médio (%) por folga de orçamento (alpha) e esquema de prêmio\n")
    out.append(md(t4))
    out.append("")
    if inst["OPT"].notna().any():
        g = M.join(inst[["OPT"]], on="inst")
        g = g[g["OPT"].notna()]
        g["gopt"] = 100 * (g["OPT"] - g["prize"].fillna(0)) / g["OPT"]
        t5 = g.groupby("algo").agg(**{"gap ao ótimo %": ("gopt", "mean"), "% exec. ótimas": ("gopt", lambda x: 100 * (x < 1e-9).mean())}).reindex(META)
        out.append(f"## T5. Gap ao ótimo provado ({g['inst'].nunique()} instâncias com ótimo conhecido)\n")
        out.append(md(t5))
        out.append("")

    # ------------------------------------------------ T6: B&B baseline x heurísticas
    if not BB.empty:
        b = BB.set_index("inst")
        cmp = inst[["cls", "BKS", "UB"]].copy()
        cmp["BB"] = b["prize"].where(b["feasible"] == True)
        cmp["BB_ub"] = b["ub"]
        best_meta = agg.groupby("inst")["gap"].min()
        alns = agg[agg["algo"] == "ALNS"].set_index("inst")["gap"]
        cmp["gap_BB"] = 100 * (cmp["BKS"] - cmp["BB"].fillna(0)) / cmp["BKS"]
        cmp["gap_BBub"] = 100 * (cmp["BB_ub"] - cmp["BB"]) / cmp["BB_ub"]
        cmp["gap_melhor_meta"] = best_meta
        cmp["gap_ALNS"] = alns
        t6 = cmp.groupby("cls").agg(**{
            "inst.": ("BKS", "size"), "BB viável %": ("BB", lambda x: 100 * x.notna().mean()),
            "gap BB→BKS %": ("gap_BB", "mean"), "gap BB (próprio UB) %": ("gap_BBub", "mean"),
            "gap ALNS (média sementes) %": ("gap_ALNS", "mean"),
            "gap melhor meta (média sementes) %": ("gap_melhor_meta", "mean")})
        out.append(f"## T6. Baseline B&B (MTZ, {BB['tlim'].iloc[0]:.0f} s) versus metaheurísticas (t(n) s)\n")
        out.append(md(t6))
        meanp = agg.join(inst[["BKS"]], on="inst")
        meanp["mp"] = meanp["BKS"] * (1 - meanp["gap"] / 100)
        rows = []
        for a in META:
            x = meanp[meanp["algo"] == a].set_index("inst")["mp"]
            y = cmp["BB"].fillna(0).reindex(x.index)
            rows.append(dict(metodo=a, melhor_que_BB=int((x > y + 1e-9).sum()), igual=int((abs(x - y) <= 1e-9).sum()),
                             pior=int((x < y - 1e-9).sum())))
        out.append("\nComparação instância a instância (prêmio médio das 5 sementes vs. BB):\n")
        out.append(md(pd.DataFrame(rows).set_index("metodo")))
        out.append("")

    # ------------------------------------------------ T7: Local Branching
    if not LB.empty:
        l = LB.copy()
        l["ganho"] = l["prize"] - l["mspd_prize"]
        l = l.join(inst[["BKS", "cls"]], on="inst")
        l["gap_ms"] = 100 * (l["BKS"] - l["mspd_prize"]) / l["BKS"]
        l["gap_lb"] = 100 * (l["BKS"] - l["prize"]) / l["BKS"]
        t7 = l.groupby("cls").agg(**{"inst.": ("inst", "size"), "% melhoradas pelo LB": ("ganho", lambda g: 100 * (g > 1e-9).mean()),
                                     "gap MSPD %": ("gap_ms", "mean"), "gap MSPD+LB %": ("gap_lb", "mean"),
                                     "vizinhanças provadas vazias": ("lb_proven_empty", "mean"),
                                     "tempo (s)": ("time", "mean")})
        out.append("## T7. Matheurística de Local Branching (MSPD + LB sobre CUT, 60 s)\n")
        out.append(md(t7))
        out.append("")

    # ------------------------------------------------ T8: pesos ALNS
    wc = [c for c in H.columns if c.startswith("w_")]
    if wc:
        aw = H[H["algo"] == "ALNS"].join(inst[["cls"]], on="inst", rsuffix="_")
        t8 = aw.groupby("cls")[wc].mean()
        out.append("## T8. Pesos finais médios dos operadores do ALNS\n")
        out.append(md(t8))
        out.append("")

    # ------------------------------------------------ T9: MSPD 10 iterações (como no artigo)
    if "ms10_prize" in H.columns:
        ms = H[H["algo"] == "MSPD"].copy()
        ms["gap10"] = 100 * (ms["BKS"] - ms["ms10_prize"]) / ms["BKS"]
        t9 = ms.groupby("cls").agg(**{"gap MSPD 10 iterações %": ("gap10", "mean"), "tempo 10 it. (s)": ("ms10_time", "mean"),
                                      "gap MSPD t(n) %": ("gap", "mean")})
        out.append("## T9. MSPD com 10 iterações (configuração do artigo) vs. MSPD com t(n)\n")
        out.append(md(t9))
        out.append("")

    # ------------------------------------------------ T10: tabela por instância (média sementes)
    full = agg.pivot(index="inst", columns="algo", values="gap")[META]
    full = inst[["n", "K", "BKS"]].join(full)
    out.append("## T10. Gap médio (%) ao BKS por instância e metaheurística\n")
    out.append(md(full.sort_values(["n"])))

    # ------------------------------------------------ T11: complexidade empírica
    TM = load("timing")
    if not TM.empty:
        TM["ms"] = TM["time"] * 1000
        tt = TM.pivot_table(index=["n"], columns="algo", values="ms", aggfunc="mean")
        tt = tt[[f"{c}{s}" for c in CONSTR for s in ["", "-SR", "-LS"]]]
        slopes = {}
        sub = TM[TM["inst"].str.contains("_a050_")]
        for a in tt.columns:
            d = sub[sub["algo"] == a]
            d = d[d["ms"] > 0]
            slopes[a] = np.polyfit(np.log(d["n"]), np.log(d["ms"]), 1)[0] if len(d) > 2 else np.nan
        tt.loc["expoente b (t ~ n^b, TSPLIB)"] = pd.Series(slopes)
        out.append("## T11. Tempo médio (ms) das construtivas por n (1 instância por grafo; POKE = n 450) e expoente empírico\n")
        out.append(md(tt, floatfmt=".3f"))
        out.append("")
        fig, ax = plt.subplots(figsize=(7, 3.4))
        for a, c in zip(["NI-LS", "FI-LS", "ST-LS", "TSPD-LS", "NI-SR", "ST"], PAL):
            d = sub[sub["algo"] == a].sort_values("n")
            ax.plot(d["n"], d["ms"], marker="o", markersize=3.5, color=c, label=f"{a} (b≈{slopes[a]:.2f})")
        ax.set_xscale("log"); ax.set_yscale("log")
        ax.set_xlabel("n (escala log)"); ax.set_ylabel("tempo médio (ms, escala log)")
        ax.legend(frameon=False, fontsize=7.5, ncol=2)
        ax.set_title("Complexidade empírica das construtivas (TSPLIB, α = 0,5)", loc="left", fontsize=10, color=INK)
        fig.savefig(os.path.join(FIG, "f7_complexidade.png")); plt.close(fig)

    with open(os.path.join(RES, "tables.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    # ================================================ FIGURAS
    # F1: boxplot gap por metaheurística
    fig, ax = plt.subplots(figsize=(7, 3.2))
    data = [agg[agg["algo"] == a]["gap"].values for a in META]
    bp = ax.boxplot(data, tick_labels=META, showfliers=True, patch_artist=True, widths=0.5,
                    medianprops=dict(color=INK, linewidth=1.5), flierprops=dict(markersize=3, markerfacecolor=INK2, markeredgecolor="none"))
    for patch in bp["boxes"]:
        patch.set_facecolor("#cfe0f6"); patch.set_edgecolor(PAL[0])
    ax.set_ylabel("gap ao BKS (%) — média de 5 sementes")
    ax.set_title("Distribuição do gap por metaheurística (126 instâncias)", loc="left", fontsize=10, color=INK)
    fig.savefig(os.path.join(FIG, "f1_boxplot_gap.png")); plt.close(fig)

    # F2: gap vs n (por grafo TSPLIB, média sobre alpha/prêmio)
    tsp = agg.join(inst[["n", "set"]], on="inst")
    tsp = tsp[tsp["set"] == "TSPLIB"].groupby(["algo", "n"])["gap"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(7, 3.4))
    for a in META8:
        d = tsp[tsp["algo"] == a]
        ax.plot(d["n"], d["gap"], marker="o", markersize=3.5, color=COL[a], label=a)
    ax.set_xlabel("n (nº de nós)"); ax.set_ylabel("gap médio ao BKS (%)")
    ax.legend(ncol=4, frameon=False, fontsize=8)
    ax.set_title("Gap médio por tamanho de instância (TSPLIB)", loc="left", fontsize=10, color=INK)
    fig.savefig(os.path.join(FIG, "f2_gap_vs_n.png")); plt.close(fig)

    # F3: curvas anytime (prêmio/BKS vs fração do tempo)
    grid = np.logspace(-3, 0, 60)
    fig, axs = plt.subplots(1, 2, figsize=(8, 3.2), sharey=True)
    for ax, big in zip(axs, [False, True]):
        sub = M[(M["n"] >= 262) == big]
        for a in META8:
            ss = sub[sub["algo"] == a]
            vals = np.zeros(len(grid)); cnt = 0
            for _, r in ss.iterrows():
                tr = r["trace"]
                if not tr:
                    continue
                ts = np.array([x[0] for x in tr]) / r["tlim"]; ps = np.array([x[1] for x in tr]) / r["BKS"]
                idx = np.searchsorted(ts, grid, side="right") - 1
                vals += np.where(idx >= 0, ps[np.clip(idx, 0, None)], 0); cnt += 1
            if cnt:
                ax.plot(grid, 100 * (1 - vals / cnt), color=COL[a], label=a)
        ax.set_xscale("log"); ax.set_yscale("symlog", linthresh=1)
        ax.set_xlabel("fração do tempo limite")
        ax.set_title("n ≥ 262 (inclui POKE)" if big else "n ≤ 200", loc="left", fontsize=10, color=INK)
    axs[0].set_ylabel("gap médio ao BKS (%)")
    axs[1].legend(ncol=2, frameon=False, fontsize=7.5)
    fig.savefig(os.path.join(FIG, "f3_anytime.png")); plt.close(fig)

    # F4: perfil de desempenho (fração de instâncias com gap <= tau)
    taus = np.linspace(0, 5, 201)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    for a in META8:
        g = agg[agg["algo"] == a]["gap"].values
        ax.plot(taus, [100 * (g <= t + 1e-9).mean() for t in taus], color=COL[a], label=a)
    ax.set_xlabel("tolerância τ de gap ao BKS (%)"); ax.set_ylabel("% instâncias com gap ≤ τ")
    ax.legend(ncol=4, frameon=False, fontsize=8, loc="lower right")
    ax.set_title("Perfil de desempenho (gap médio por instância)", loc="left", fontsize=10, color=INK)
    fig.savefig(os.path.join(FIG, "f4_perfil.png")); plt.close(fig)

    # F5: construtivas raw/SR/LS
    fig, ax = plt.subplots(figsize=(7, 3))
    xs = np.arange(len(CONSTR)); wd = 0.26
    for q, (v, c) in enumerate([("raw", PAL[1]), ("SR", PAL[0]), ("LS", PAL[2])]):
        vals = [C[(C["constr"] == k) & (C["var"] == v)]["gap"].mean() for k in CONSTR]
        bars = ax.bar(xs + (q - 1) * wd, vals, wd - 0.03, color=c, label={"raw": "sem BL", "SR": "refino σ (artigo)", "LS": "BL exata (proposta)"}[v])
        for b_, val in zip(bars, vals):
            ax.text(b_.get_x() + b_.get_width() / 2, val + 0.5, f"{val:.1f}", ha="center", fontsize=7, color=INK2)
    ax.set_xticks(xs, CONSTR); ax.set_ylabel("gap médio ao BKS (%)")
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Construtivas: efeito da busca local", loc="left", fontsize=10, color=INK)
    fig.savefig(os.path.join(FIG, "f5_construtivas.png")); plt.close(fig)

    # F6: BB vs melhor metaheurística por instância
    if not BB.empty:
        fig, ax = plt.subplots(figsize=(7, 3.2))
        cmp2 = cmp.join(inst[["n"]], rsuffix="_")
        ax.scatter(cmp2["n"], cmp2["gap_BB"], s=14, color=PAL[1], label="B&B MTZ", zorder=3, edgecolors="white", linewidths=0.5)
        ax.scatter(cmp2["n"], cmp2["gap_ALNS"], s=14, color=PAL[0], label="ALNS (média)", zorder=3, edgecolors="white", linewidths=0.5)
        ax.set_xlabel("n"); ax.set_ylabel("gap ao BKS (%)"); ax.set_yscale("symlog", linthresh=1)
        ax.legend(frameon=False, fontsize=8)
        ax.set_title("Baseline B&B (tempo fixo) vs. ALNS (t(n))", loc="left", fontsize=10, color=INK)
        fig.savefig(os.path.join(FIG, "f6_bb_vs_alns.png")); plt.close(fig)

    print(open(os.path.join(RES, "tables.md"), encoding="utf-8").read()[:3000])


if __name__ == "__main__":
    main()
