"""Gera as tabelas LaTeX das Seções 4 e 5 do artigo a partir das tabelas CSV de analisa.py.

Os números são copiados das tabelas, sem redigitação. Saída: <pasta>/latex/tab_h1.tex, tab_h2.tex e
tab_h3_ref.tex, para \\input no artigo (pacotes: booktabs).

Uso: python analise/tabelas_latex.py [pasta_resultados]
"""
import json
import os
import sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "resultados")
TAB = os.path.join(RES, "tabelas")


def le(nome):
    return pd.read_csv(os.path.join(TAB, f"{nome}.csv"), dtype=str, keep_default_na=False)


def tx(v):
    v = str(v)
    if v.startswith("-") and v[1:2].isdigit():
        v = "$-$" + v[1:]
    return v.replace("<", "$<$").replace("%", "\\%").replace("n/d", "--")


def arred(v, c):
    """Arredonda um número já formatado com vírgula ("27,892" -> "27,9")."""
    return f"{float(v.replace(',', '.')):.{c}f}".replace(".", ",")


def grava(nome, linhas):
    os.makedirs(os.path.join(RES, "latex"), exist_ok=True)
    with open(os.path.join(RES, "latex", f"{nome}.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


def main():
    with open(os.path.join(RES, "resumo.json"), encoding="utf-8") as f:
        r = json.load(f)

    # H1
    t = le("h1_por_classe")
    L = [r"\begin{table}[t]", r"\centering",
         r"\caption{H1: MSPD e MSPD-LS por classe (gap médio ao BKS, iterações do laço principal, tempo médio de uma fase de melhoria, vitórias/empates/derrotas do MSPD-LS e $p$ do Wilcoxon unilateral).}",
         r"\label{tab:h1}", r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
         r"\begin{tabular}{lrrrrrrrcr}", r"\toprule",
         r" & & \multicolumn{2}{c}{Gap (\%)} & \multicolumn{2}{c}{Iterações} & \multicolumn{2}{c}{Melhoria (ms)} & & \\",
         r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(lr){7-8}",
         r"Classe & $n$ & MSPD & MSPD-LS & MSPD & MSPD-LS & MSPD & MSPD-LS & V/E/D & $p$ \\", r"\midrule"]
    for _, x in t.iterrows():
        if x.Classe == "Total":
            L.append(r"\midrule")
        L.append(" & ".join(tx(v) for v in x.values) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    grava("tab_h1", L)

    # H2: medidas + Wilcoxon + sensibilidade sem brg180
    m = le("h2_medidas").set_index("Método")
    w = le("h2_wilcoxon")
    s = le("h2_sensibilidade_brg180").set_index("Método")
    vs = {x["Comparação"].split(" <")[0]: x for _, x in w[w["Comparação"].str.endswith("< MSPD")].iterrows()}
    ma = {x["Comparação"].split("< ")[1]: x for _, x in w[w["Família"] == "MA vs. propostos"].iterrows()}
    s2 = r.get("H2_sem_brg180", {})
    fr, fr_s = r["H2"]["friedman_p"], s2.get("friedman_p", float("nan"))
    fp = lambda p: "$<$0,0001" if p < 1e-4 else f"{p:.4f}".replace(".", ",")
    L = [r"\begin{table}[t]", r"\centering",
         r"\caption{H2: medidas por método nas 408 instâncias (gap médio, máximo e da melhor semente, desvio entre sementes, "
         r"execuções que atingem o BKS, tempo até a melhor solução e rank médio), Wilcoxon contra o MSPD e do MA contra os "
         r"demais ($p$ corrigido por Holm em cada família) e, à direita, sem as 6 instâncias \texttt{brg180}. "
         f"Friedman: $p$ {fp(fr)} com e $p$ {fp(fr_s)} sem \\texttt{{brg180}}.}}".replace("$p$ $<$", "$p<$"),
         r"\label{tab:h2}", r"\scriptsize", r"\setlength{\tabcolsep}{2.6pt}",
         r"\begin{tabular}{lrrrrrrrcrr|rrr}", r"\toprule",
         r" & \multicolumn{3}{c}{Gap (\%)} & & & & & \multicolumn{2}{c}{vs. MSPD} & MA vs. & \multicolumn{3}{c}{Sem \texttt{brg180}} \\",
         r"\cmidrule(lr){2-4}\cmidrule(lr){9-10}\cmidrule(lr){12-14}",
         r"Método & Médio & Máx. & Melhor & Desv. & BKS (\%) & $t^*$ (s) & Rank & V/E/D & $p_{\mathrm{Holm}}$ & $p_{\mathrm{Holm}}$ & Gap (\%) & Rank & $p_{\mathrm{Holm}}$ \\",
         r"\midrule"]
    sem_vs = s2.get("vs_mspd", {})
    for metodo, x in m.iterrows():
        v = vs.get(metodo)
        a = ma.get(metodo)
        ps = sem_vs.get(f"{metodo} < MSPD")
        cel = [metodo, x["Gap médio (%)"], x["Gap máximo (%)"], x["Gap melhor semente (%)"], x["Desvio entre sementes (%)"],
               arred(x["Atinge BKS (%)"], 1), arred(x["Tempo até a melhor (s)"], 2), arred(x["Rank médio"], 2),
               v["V/E/D"] if v is not None else "--", v["p Holm"] if v is not None else "--",
               a["p Holm"] if a is not None else "--",
               s.loc[metodo, "Gap sem brg180 (%)"], s.loc[metodo, "Rank sem"], fp(ps) if ps is not None else "--"]
        L.append(" & ".join(tx(c) if not str(c).startswith("$") else c for c in cel) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    grava("tab_h2", L)

    # H3 e referência exata, lado a lado
    d = le("h3_degradacao")
    e = le("ref_exato")
    L = [r"\begin{table}[t]", r"\centering", r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
         r"\begin{minipage}[t]{0.42\textwidth}\centering",
         r"\caption{H3: gap médio ao BKS (\%) em T4 e PK e degradação (p.p.).}", r"\label{tab:h3}",
         r"\begin{tabular}{lrrr}", r"\toprule", r"Método & T4 & PK & Degr. \\", r"\midrule"]
    for _, x in d.iterrows():
        L.append(" & ".join(tx(v) for v in x.values) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{minipage}\hfill",
          r"\begin{minipage}[t]{0.55\textwidth}\centering",
          r"\caption{Formulação exata (limite de 600~s): ótimos provados, tempo médio das resolvidas e distância média do limitante ao BKS nas demais.}",
          r"\label{tab:exato}",
          r"\begin{tabular}{lrrrr}", r"\toprule", r"Classe & Inst. & Ótimos & Tempo (s) & Lim.$-$BKS (\%) \\", r"\midrule"]
    for _, x in e.iterrows():
        if x.Classe == "Total":
            L.append(r"\midrule")
        L.append(" & ".join(tx(v) for v in x.values) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{minipage}", r"\end{table}"]
    grava("tab_h3_ref", L)
    print("tabelas LaTeX geradas em", os.path.join(RES, "latex"))


if __name__ == "__main__":
    main()
