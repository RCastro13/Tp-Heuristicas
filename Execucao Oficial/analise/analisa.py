"""Tabelas, gráficos, testes estatísticos e vereditos de H1 a H4 (Seção 3.3 do artigo).

Antes de qualquer cálculo, todas as rotas são reavaliadas aqui, de forma independente do C++: vértices
distintos, cobertura dos clusters, orçamento e prêmio.

Uso: python analise/analisa.py [heur.jsonl] [exato.jsonl] [pasta_saida]
Saída: <pasta>/tabelas/*.md e *.csv, <pasta>/figuras/*.png e <pasta>/resumo.json
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "exato"))
from formulacao_exata import confere, le_grafo  # noqa: E402

METODOS = ["MSPD", "MSPD-LS", "VNS", "ILS", "ALNS", "MA"]
CLASSES = ["T1", "T2", "T3", "T4", "PK"]
ALFA = 0.05

# Paleta categórica validada (skill dataviz), em ordem fixa; a cor segue a entidade.
COR_METODO = {"MSPD": "#2a78d6", "MSPD-LS": "#eb6834", "VNS": "#1baf7a", "ILS": "#eda100", "ALNS": "#e87ba4",
              "MA": "#008300", "ILS-C": "#6250d6"}
COR_CLASSE = {"T1": "#2a78d6", "T2": "#eb6834", "T3": "#1baf7a", "T4": "#eda100", "PK": "#e87ba4"}
MARCA_CLASSE = {"T1": "o", "T2": "s", "T3": "^", "T4": "D", "PK": "X"}
SUPERFICIE, TINTA, TINTA2, GRADE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE, "savefig.facecolor": SUPERFICIE,
    "axes.edgecolor": TINTA2, "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "text.color": TINTA, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRADE, "grid.linewidth": 0.8, "axes.axisbelow": True, "font.size": 10, "legend.frameon": False,
})


def le_jsonl(caminho):
    linhas = []
    if os.path.exists(caminho):
        with open(caminho) as f:
            for l in f:
                try:
                    linhas.append(json.loads(l))
                except json.JSONDecodeError:
                    pass
    return linhas


def verifica_rotas(heur, ex, inst):
    """Reavalia cada rota; devolve o número de divergências."""
    graf, erros = {}, 0
    for d in heur + ex:
        if not d.get("viavel"):
            continue
        r = inst.loc[d["inst"]]
        chave = (r.grafo, r.premio)
        if chave not in graf:
            graf[chave] = le_grafo(r.grafo, r.premio)
        n, D, p, cl = graf[chave]
        ok, P, L = confere(n, D, p, cl, float(r.B), d["rota"])
        if not ok or abs(P - d["P"]) > 1e-4 or abs(L - d["L"]) > 1e-4:
            erros += 1
    return erros


def wilcoxon(x, y):
    """Wilcoxon unilateral pareado (x < y), empates pelo método de Pratt."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    dif = np.round(x - y, 9)
    if len(dif) == 0 or np.all(dif == 0):
        return 1.0
    return float(stats.wilcoxon(dif, zero_method="pratt", alternative="less", correction=False, method="approx").pvalue)


def holm(ps):
    ps = np.asarray(ps, float)
    ordem = np.argsort(ps)
    aj = np.empty(len(ps))
    atual = 0.0
    for i, k in enumerate(ordem):
        atual = max(atual, min(1.0, (len(ps) - i) * ps[k]))
        aj[k] = atual
    return aj.tolist()


def vde(x, y):
    """Vitórias, empates e derrotas de x (menor gap vence)."""
    dif = np.round(np.asarray(x, float) - np.asarray(y, float), 9)
    return int((dif < 0).sum()), int((dif == 0).sum()), int((dif > 0).sum())


def fp(p):
    return "n/d" if p is None or (isinstance(p, float) and np.isnan(p)) else ("<0,0001" if p < 1e-4 else f"{p:.4f}".replace(".", ","))


def fn(x, c=3):
    return "n/d" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{c}f}".replace(".", ",")


def salva(df, pasta, nome, titulo):
    df.to_csv(os.path.join(pasta, f"{nome}.csv"), index=False, encoding="utf-8")
    with open(os.path.join(pasta, f"{nome}.md"), "w", encoding="utf-8") as f:
        f.write(f"**{titulo}**\n\n{df.to_markdown(index=False)}\n")


def main():
    arq_h = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "resultados", "brutos", "heur.jsonl")
    arq_e = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "resultados", "brutos", "exato.jsonl")
    saida = sys.argv[3] if len(sys.argv) > 3 else os.path.join(RAIZ, "resultados")
    ptab, pfig = os.path.join(saida, "tabelas"), os.path.join(saida, "figuras")
    os.makedirs(ptab, exist_ok=True)
    os.makedirs(pfig, exist_ok=True)

    inst = pd.read_csv(os.path.join(RAIZ, "dados", "instancias.csv"), keep_default_na=False).set_index("nome")
    heur_cru, ex_cru = le_jsonl(arq_h), le_jsonl(arq_e)
    erros_exec = [d for d in heur_cru if "erro" in d]
    heur_ok = [d for d in heur_cru if "erro" not in d]
    # numa retomada, vale a primeira execução gravada de cada (instância, método, semente)
    vistos, unicos = set(), []
    for d in heur_ok:
        k = (d["inst"], d["algo"], d["semente"])
        if k not in vistos:
            vistos.add(k); unicos.append(d)
    heur_ok = unicos
    ex_ok = [d for d in ex_cru if "erro" not in d]
    div = verifica_rotas(heur_ok, ex_ok, inst)
    R = pd.DataFrame([{k: v for k, v in d.items() if k != "rota"} for d in heur_ok])
    E = pd.DataFrame([{k: v for k, v in d.items() if k != "rota"} for d in ex_ok])
    R["classe"] = R.inst.map(inst.classe)

    # ------------------------------------------------------------- BKS e gaps
    bks = R.groupby("inst").P.max()
    otimo = {}
    if len(E):
        for _, e in E.iterrows():
            if e.viavel:
                bks[e.inst] = max(bks.get(e.inst, 0.0), e.P)
            if e.situacao == "otimo":
                otimo[e.inst] = e.P
    acima_otimo = [d["inst"] for d in heur_ok if d["inst"] in otimo and d["P"] > otimo[d["inst"]] + 1e-6]
    R["bks"] = R.inst.map(bks)
    R["gap"] = np.where(R.viavel, 100 * (R.bks - R.P) / R.bks, 100.0)
    R["atinge"] = R.viavel & (R.bks - R.P <= 1e-6)
    M = R.groupby(["inst", "algo"]).gap.mean().unstack()  # unidade de análise: média das sementes
    classe = inst.classe.reindex(M.index)
    presentes = [m for m in METODOS if m in M.columns]
    M6 = M[presentes].dropna()
    resumo = dict(execucoes=len(heur_ok), erros_execucao=len(erros_exec), rotas_divergentes=div,
                  inviaveis=int((~R.viavel).sum()), instancias=int(M6.shape[0]),
                  heuristica_acima_do_otimo=len(set(acima_otimo)),
                  excesso_tempo_max_s=float((R.tempo - R.tlim).max()),
                  excesso_tempo_p99_s=float((R.tempo - R.tlim).quantile(.99)))

    # ------------------------------------------------------------- H1
    linhas = []
    por = R.groupby(["inst", "algo"]).agg(iter=("iter", "mean"), nm=("n_melhoria", "sum"), tm=("t_melhoria", "sum")).reset_index()
    por["ms"] = 1000 * por.tm / por.nm.replace(0, np.nan)
    for c in CLASSES + ["Total"]:
        idx = M6.index if c == "Total" else M6.index[classe.reindex(M6.index) == c]
        if len(idx) == 0:
            continue
        a, b = M6.loc[idx, "MSPD"], M6.loc[idx, "MSPD-LS"]
        v, e_, d = vde(b, a)
        pa = por[por.inst.isin(idx) & (por.algo == "MSPD")]
        pb = por[por.inst.isin(idx) & (por.algo == "MSPD-LS")]
        linhas.append({"Classe": c, "n": len(idx), "Gap MSPD (%)": a.mean(), "Gap MSPD-LS (%)": b.mean(),
                       "Iter. MSPD": pa.iter.mean(), "Iter. MSPD-LS": pb.iter.mean(),
                       "Melhoria MSPD (ms)": pa.ms.mean(), "Melhoria MSPD-LS (ms)": pb.ms.mean(),
                       "V/E/D MSPD-LS": f"{v}/{e_}/{d}", "p": wilcoxon(b, a)})
    t1 = pd.DataFrame(linhas)
    ptot = float(t1[t1.Classe == "Total"].p.iloc[0])
    pior = t1[(t1.Classe != "Total") & (t1["Gap MSPD-LS (%)"] > t1["Gap MSPD (%)"] + 1e-9)].Classe.tolist()
    resumo["H1"] = dict(p=ptot, classes_pior=pior,
                        veredito="refutada" if ptot >= ALFA else ("parcialmente confirmada" if pior else "confirmada"))
    t1f = t1.copy()
    for c in ["Gap MSPD (%)", "Gap MSPD-LS (%)"]:
        t1f[c] = t1f[c].map(lambda x: fn(x, 3))
    for c in ["Iter. MSPD", "Iter. MSPD-LS"]:
        t1f[c] = t1f[c].map(lambda x: fn(x, 1))
    for c in ["Melhoria MSPD (ms)", "Melhoria MSPD-LS (ms)"]:
        t1f[c] = t1f[c].map(lambda x: fn(x, 2))
    t1f["p"] = t1f["p"].map(fp)
    salva(t1f, ptab, "h1_por_classe", "H1: MSPD versus MSPD-LS por classe (p: Wilcoxon unilateral a favor do MSPD-LS)")

    fig, ax = plt.subplots(figsize=(6, 5.6))
    lim = max(M6.MSPD.max(), M6["MSPD-LS"].max(), 1) * 1.5
    ax.plot([0, lim], [0, lim], color=TINTA2, lw=1, zorder=1, label="y = x")
    for c in CLASSES:
        idx = M6.index[classe.reindex(M6.index) == c]
        if len(idx):
            ax.scatter(M6.loc[idx, "MSPD"], M6.loc[idx, "MSPD-LS"], s=30, marker=MARCA_CLASSE[c], color=COR_CLASSE[c],
                       edgecolor=SUPERFICIE, linewidth=0.6, label=c, zorder=2)
    ax.set_xscale("symlog", linthresh=0.1); ax.set_yscale("symlog", linthresh=0.1)
    ax.set_xlim(-0.01, lim); ax.set_ylim(-0.01, lim)
    ax.set_xlabel("Gap médio do MSPD ao BKS (%)"); ax.set_ylabel("Gap médio do MSPD-LS ao BKS (%)")
    ax.set_title("H1: pontos abaixo da diagonal favorecem o MSPD-LS", loc="left", fontsize=11)
    ax.legend(title="Classe", loc="upper left")
    fig.tight_layout(); fig.savefig(os.path.join(pfig, "h1_dispersao.png"), dpi=200); plt.close(fig)

    # ------------------------------------------------------------- H2
    ranks = M6.rank(axis=1, method="average")
    linhas = []
    Rm = R[R.algo.isin(presentes) & R.inst.isin(M6.index)]
    for m in presentes:
        x = Rm[Rm.algo == m]
        g = x.groupby("inst").gap
        linhas.append({"Método": m, "Gap médio (%)": M6[m].mean(), "Gap máximo (%)": x.gap.max(),
                       "Gap melhor semente (%)": g.min().mean(), "Desvio entre sementes (%)": g.std().mean(),
                       "Atinge BKS (%)": 100 * x.atinge.mean(), "Tempo até a melhor (s)": x.t_melhor.mean(),
                       "Rank médio": ranks[m].mean()})
    t2 = pd.DataFrame(linhas)
    fried = float(stats.friedmanchisquare(*[M6[m] for m in presentes]).pvalue) if len(M6) > 1 and len(presentes) > 2 else float("nan")
    melhor_rank = t2.sort_values("Rank médio").iloc[0]["Método"]
    t2f = t2.copy()
    for c in t2f.columns[1:]:
        t2f[c] = t2f[c].map(lambda x: fn(x, 3))
    salva(t2f, ptab, "h2_medidas", f"H2: medidas por método (Friedman p = {fp(fried)})")

    def familia(pares):
        ps = [wilcoxon(M6[a], M6[b]) for a, b in pares]
        aj = holm(ps)
        return [{"Comparação": f"{a} < {b}", "V/E/D": "/".join(map(str, vde(M6[a], M6[b]))), "Dif. média (p.p.)": (M6[a] - M6[b]).mean(),
                 "p bruto": p, "p Holm": q} for (a, b), p, q in zip(pares, ps, aj)]
    f1 = familia([(m, "MSPD") for m in ["VNS", "ILS", "ALNS", "MA"]])
    f2 = familia([("MA", m) for m in ["MSPD-LS", "VNS", "ILS", "ALNS"]])
    t3 = pd.DataFrame([{"Família": "Metaheurística vs. MSPD", **x} for x in f1] + [{"Família": "MA vs. propostos", **x} for x in f2])
    t3f = t3.copy()
    t3f["Dif. média (p.p.)"] = t3f["Dif. média (p.p.)"].map(lambda x: fn(x, 3))
    t3f["p bruto"] = t3f["p bruto"].map(fp); t3f["p Holm"] = t3f["p Holm"].map(fp)
    salva(t3f, ptab, "h2_wilcoxon", "H2: Wilcoxon unilateral pareado por instância, com correção de Holm em cada família")
    venc = [x["Comparação"].split(" <")[0] for x in f1 if x["p Holm"] < ALFA]
    ver = "refutada" if fried >= ALFA or not venc else ("confirmada" if len(venc) == 4 else "parcialmente confirmada")
    ma_melhor = melhor_rank == "MA" and all(x["p Holm"] < ALFA for x in f2)
    resumo["H2"] = dict(friedman_p=fried, vencem_mspd=venc, veredito=ver, melhor_rank=melhor_rank,
                        ranks={m: float(ranks[m].mean()) for m in presentes}, ma_e_o_melhor=bool(ma_melhor),
                        ma_vs={x["Comparação"]: x["p Holm"] for x in f2})

    # Detalhe por classe, para sustentar a discussão
    linhas = []
    for c in CLASSES:
        idx = M6.index[classe.reindex(M6.index) == c]
        if len(idx):
            linhas.append({"Classe": c, **{m: fn(M6.loc[idx, m].mean(), 3) for m in presentes},
                           "Menor rank": ranks.loc[idx].mean().idxmin()})
    salva(pd.DataFrame(linhas), ptab, "h2_gap_por_classe", "Complemento de H2: gap médio ao BKS (%) por classe")

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    bp = ax.boxplot([M6[m] for m in presentes], widths=0.5, patch_artist=True, showmeans=True,
                    medianprops=dict(color=TINTA, lw=1.2), whiskerprops=dict(color=TINTA2), capprops=dict(color=TINTA2),
                    meanprops=dict(marker="D", markerfacecolor=SUPERFICIE, markeredgecolor=TINTA, markersize=5),
                    flierprops=dict(marker="o", markersize=3, markerfacecolor=TINTA2, markeredgecolor="none", alpha=.5))
    for caixa, m in zip(bp["boxes"], presentes):
        caixa.set(facecolor=COR_METODO[m], edgecolor=TINTA2, linewidth=0.8)
    ax.set_xticks(range(1, len(presentes) + 1), presentes)
    ax.set_yscale("symlog", linthresh=1); ax.set_ylim(bottom=-0.05)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Gap médio por instância ao BKS (%)")
    ax.set_title(f"H2: distribuição do gap nas {len(M6)} instâncias (losango = média)", loc="left", fontsize=11)
    fig.tight_layout(); fig.savefig(os.path.join(pfig, "h2_boxplot.png"), dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    tau = np.linspace(0, 5, 501)
    for m in presentes:
        y = [100 * (M6[m] <= t + 1e-9).mean() for t in tau]
        ax.plot(tau, y, color=COR_METODO[m], lw=2, label=m)
    ax.set_xlim(0, 5); ax.set_ylim(0, 102)
    ax.set_xlabel("Tolerância τ (%)"); ax.set_ylabel("Instâncias com gap ≤ τ (%)")
    ax.set_title("H2: distribuição acumulada do gap médio por instância", loc="left", fontsize=11)
    ax.legend(ncol=3, loc="lower right")
    fig.tight_layout(); fig.savefig(os.path.join(pfig, "h2_acumulada.png"), dpi=200); plt.close(fig)

    # ------------------------------------------------------------- H3
    cl3 = ["T1", "T2", "T3"]
    Ro = R[R.inst.isin(otimo.keys()) & R.algo.isin(presentes)].copy()
    resumo["H3"] = dict(provadas=len(otimo), melhor=melhor_rank)
    if len(Ro):
        Ro["opt"] = Ro.inst.map(otimo)
        Ro["gap_opt"] = np.where(Ro.viavel, 100 * (Ro.opt - Ro.P) / Ro.opt, 100.0)
        Ro["e_otima"] = Ro.viavel & (Ro.opt - Ro.P <= 1e-6)
        linhas = []
        for m in presentes:
            x = Ro[Ro.algo == m]
            lin = {"Método": m}
            for c in cl3 + ["Total"]:
                y = x if c == "Total" else x[x.classe == c]
                lin[f"{c} gap méd."] = fn(y.gap_opt.mean(), 3) if len(y) else "n/d"
                lin[f"{c} gap máx."] = fn(y.gap_opt.max(), 3) if len(y) else "n/d"
                lin[f"{c} % ótimas"] = fn(100 * y.e_otima.mean(), 1) if len(y) else "n/d"
            linhas.append(lin)
        salva(pd.DataFrame(linhas), ptab, "h3_gap_otimo", f"H3: distância ao ótimo nas {len(otimo)} instâncias com ótimo provado")
        xb = Ro[Ro.algo == melhor_rank]
        g_b, t_b = float(xb.groupby("inst").gap_opt.mean().mean()), float(100 * xb.e_otima.mean())
        desc = len(otimo) < 30
        ver3 = ("refutada" if g_b > 0.5 else "confirmada" if t_b >= 90 else "parcialmente confirmada")
        resumo["H3"].update(gap_medio=g_b, pct_otimas=t_b, apenas_descritiva=desc, veredito="descritiva" if desc else ver3)
    if len(E):
        E["classe"] = E.inst.map(inst.classe)
        E["bks"] = E.inst.map(bks)
        linhas = []
        for c in cl3 + ["Total"]:
            x = E if c == "Total" else E[E.classe == c]
            if not len(x):
                continue
            ot = x[x.situacao == "otimo"]
            ab = x[x.situacao != "otimo"]
            d = 100 * (ab["sup"] - ab.bks) / ab.bks
            linhas.append({"Classe": c, "Instâncias": len(x), "Ótimo provado": len(ot),
                           "Tempo médio resolvidas (s)": fn(ot.tempo.mean(), 1) if len(ot) else "n/d",
                           "Limitante - BKS nas não resolvidas (%)": fn(d.mean(), 2) if d.notna().any() else "n/d"})
        salva(pd.DataFrame(linhas), ptab, "h3_exato", "H3: resolução da formulação exata por classe")

    # ------------------------------------------------------------- H4
    mh4 = [m for m in ["ILS", "ILS-C", "VNS", "ALNS", "MA"] if m in M.columns]
    T4 = M.index[classe == "T4"]
    PK = M.index[classe == "PK"]
    if len(T4) and len(PK):
        linhas = [{"Método": m, "Gap T4 (%)": M.loc[T4, m].mean(), "Gap PK (%)": M.loc[PK, m].mean(),
                   "Degradação (p.p.)": M.loc[PK, m].mean() - M.loc[T4, m].mean()} for m in mh4]
        t4 = pd.DataFrame(linhas)
        deg = dict(zip(t4["Método"], t4["Degradação (p.p.)"]))
        c1 = deg["ILS"] > deg["VNS"] and deg["ILS"] > deg["ALNS"]
        pc = wilcoxon(M.loc[PK, "ILS-C"], M.loc[PK, "ILS"])
        c2 = pc < ALFA and M.loc[PK, "ILS-C"].mean() < M.loc[PK, "ILS"].mean()
        resumo["H4"] = dict(degradacao={k: float(v) for k, v in deg.items()}, cond_i=bool(c1), p_ilsc=pc, cond_ii=bool(c2),
                            vde_ilsc_ils=list(vde(M.loc[PK, "ILS-C"], M.loc[PK, "ILS"])),
                            veredito="refutada" if not c1 else ("confirmada" if c2 else "parcialmente confirmada"))
        t4f = t4.copy()
        for c in t4f.columns[1:]:
            t4f[c] = t4f[c].map(lambda x: fn(x, 3))
        salva(t4f, ptab, "h4_degradacao", f"H4: gap por classe e degradação (ILS-C < ILS em PK: Wilcoxon unilateral p = {fp(pc)})")

        fig, ax = plt.subplots(figsize=(7, 4))
        x = np.arange(len(mh4)); w = 0.36
        ax.bar(x - w / 2 - 0.01, t4["Gap T4 (%)"], w, color="#2a78d6", label="T4", edgecolor=SUPERFICIE, linewidth=1)
        ax.bar(x + w / 2 + 0.01, t4["Gap PK (%)"], w, color="#eb6834", label="PK", edgecolor=SUPERFICIE, linewidth=1)
        for i, m in enumerate(mh4):
            ax.annotate(fn(t4["Gap T4 (%)"][i], 2), (i - w / 2, t4["Gap T4 (%)"][i]), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, color=TINTA2)
            ax.annotate(fn(t4["Gap PK (%)"][i], 2), (i + w / 2, t4["Gap PK (%)"][i]), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, color=TINTA2)
        ax.set_xticks(x, mh4); ax.grid(axis="x", visible=False)
        ax.set_ylabel("Gap médio ao BKS (%)")
        ax.set_title("H4: gap médio por método nas classes T4 e PK", loc="left", fontsize=11)
        ax.legend()
        fig.tight_layout(); fig.savefig(os.path.join(pfig, "h4_barras.png"), dpi=200); plt.close(fig)

    with open(os.path.join(saida, "resumo.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, indent=1, ensure_ascii=False)
    print(json.dumps(resumo, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
