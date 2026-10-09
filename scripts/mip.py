"""Métodos baseados em programação inteira (HiGHS):

* BB  — baseline de controle: formulação compacta (MTZ) do artigo resolvida por
        branch-and-bound com limite de tempo fixo. Fornece solução primal e limitante dual.
* LBR — matheurística de Local Branching (Fischetti & Lodi, 2003) sobre a formulação (CUT), aplicada à melhor solução
        do multi-start com distâncias perturbadas (MSPD), como na heurística de inicialização
        de Álvarez-Miranda et al. (2018): k = 2, 4, 6; 20 s por vizinhança.

Uso:
  python scripts/mip.py bb  <nome_instancia> <tempo_s>
  python scripts/mip.py lbr <nome_instancia> <tempo_total_s> [<tempo_mspd_s>] [<seed>]
Saída: uma linha JSON (mesmo esquema do executável C++).
"""
import csv
import json
import os
import subprocess
import sys
import time

import highspy
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCOP = os.path.join(ROOT, "bin", "gcop.exe")
INF = highspy.kHighsInf


def load_manifest():
    with open(os.path.join(ROOT, "data", "instances.csv")) as f:
        return {r["name"]: r for r in csv.DictReader(f)}


def read_graph(path, profit):
    n = 0
    label, fileP, D = None, {}, None
    with open(os.path.join(ROOT, path)) as f:
        for line in f:
            t = line.split()
            if not t:
                continue
            if t[0] == "Nodes":
                n = int(t[1]); D = np.zeros((n, n)); label = [-1] * n
            elif t[0] == "V":
                label[int(t[1])] = int(t[2])
            elif t[0] == "E":
                i, j, w = int(t[1]), int(t[2]), float(t[3])
                D[i, j] = D[j, i] = w
            elif t[0] == "P":
                fileP[int(t[1])] = float(t[2])
    labs = sorted({l for l in label if l >= 0})
    clusters = [[i for i in range(n) if label[i] == l] for l in labs]
    if profit == "rand":
        p = [1 + (7213 * i) % 100 for i in range(n)]
    elif profit == "clus":
        p = [1 + (7213 * (label[i] + 1 if label[i] >= 0 else n + i)) % 100 for i in range(n)]
    elif profit == "file":
        p = [fileP[i] for i in range(n)]
    else:
        p = [1.0] * n
    return n, D, np.array(p, dtype=float), clusters


class MTZModel:
    """Formulação (MTZ) do artigo com (CLUSTER+), (GSEC-2) e (ASYM)."""

    def __init__(self, n, D, p, clusters, B):
        self.n, self.D, self.p, self.clusters, self.B = n, D, p, clusters, B
        C1 = min(clusters, key=len)  # cluster de partida: o menor (menos variáveis z)
        self.C1 = C1
        inC1 = set(C1)
        arcs = [(i, j) for i in range(n) for j in range(n) if i != j]
        self.arcs = arcs
        ny, na, nz = n, len(arcs), len(C1)
        self.oy, self.ot, self.oz, self.ou = 0, n, n + na, n + na + nz
        nv = ny + na + nz + n
        self.nv = nv
        aid = {a: k for k, a in enumerate(arcs)}
        cost = np.zeros(nv); cost[:n] = p
        lb = np.zeros(nv); ub = np.ones(nv); ub[self.ou:] = n - 1
        integ = np.zeros(nv, dtype=np.int32); integ[: self.ou] = 1

        rows_lo, rows_hi, starts, idx, val = [], [], [0], [], []

        def row(cols, coefs, lo, hi):
            idx.extend(cols); val.extend(coefs); starts.append(len(idx))
            rows_lo.append(lo); rows_hi.append(hi)

        out = [[] for _ in range(n)]; inn = [[] for _ in range(n)]
        for k, (i, j) in enumerate(arcs):
            out[i].append(k); inn[j].append(k)
        for i in range(n):  # (MTZ.1) e (MTZ.2)
            row([self.ot + k for k in out[i]] + [i], [1.0] * len(out[i]) + [-1.0], 0, 0)
            row([self.ot + k for k in inn[i]] + [i], [1.0] * len(inn[i]) + [-1.0], 0, 0)
        zid = {v: self.oz + q for q, v in enumerate(C1)}
        for v in C1:  # (MTZ.3), (MTZ.5)
            row([zid[v], v], [1, -1], -INF, 0)
            row([self.ou + v, zid[v]], [1, n - 1], -INF, n - 1)
        row(list(zid.values()), [1.0] * nz, 1, 1)  # (MTZ.4)
        for k, (i, j) in enumerate(arcs):  # (MTZ.7) / (MTZ.8)
            if j in inC1:
                row([self.ou + i, self.ou + j, self.ot + k, zid[j]], [1, -1, n, -n], -INF, n - 1)
            else:
                row([self.ou + i, self.ou + j, self.ot + k], [1, -1, n], -INF, n - 1)
        for C in clusters:  # (CLUSTER+)
            cols = list(C); coefs = [1.0] * len(C)
            for a in C:
                for b in C:
                    if a != b:
                        cols.append(self.ot + aid[a, b]); coefs.append(-1.0)
            row(cols, coefs, 1, INF)
        # (BUDGET)
        row([self.ot + k for k in range(na)], [D[i, j] for (i, j) in arcs], -INF, B)
        for k, (i, j) in enumerate(arcs):  # (GSEC-2)
            if i < j:
                row([self.ot + k, self.ot + aid[j, i], i], [1, 1, -1], -INF, 0)
                row([self.ot + k, self.ot + aid[j, i], j], [1, 1, -1], -INF, 0)
        sC1 = sorted(C1)
        for q, v in enumerate(sC1):  # (ASYM)
            later = [zid[w] for w in sC1[q + 1:]]
            if later:
                row([v] + later, [1.0] * (1 + len(later)), -INF, 1)

        lp = highspy.HighsLp()
        lp.num_col_ = nv
        lp.num_row_ = len(rows_lo)
        lp.col_cost_ = cost
        lp.col_lower_ = lb
        lp.col_upper_ = ub
        lp.row_lower_ = np.array(rows_lo, dtype=float)
        lp.row_upper_ = np.array(rows_hi, dtype=float)
        lp.sense_ = highspy.ObjSense.kMaximize
        lp.a_matrix_.format_ = highspy.MatrixFormat.kRowwise
        lp.a_matrix_.start_ = np.array(starts, dtype=np.int32)
        lp.a_matrix_.index_ = np.array(idx, dtype=np.int32)
        lp.a_matrix_.value_ = np.array(val, dtype=float)
        lp.integrality_ = [highspy.HighsVarType.kInteger if x else highspy.HighsVarType.kContinuous for x in integ]
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("threads", 1)
        h.setOptionValue("random_seed", 1)
        h.passModel(lp)
        self.h = h

    def tour_from(self, x):
        n = self.n
        succ = {}
        for k, (i, j) in enumerate(self.arcs):
            if x[self.ot + k] > 0.5:
                succ[i] = j
        if not succ:
            return []
        start = next(iter(succ))
        t, v = [start], succ[start]
        while v != start and len(t) <= n:
            t.append(v); v = succ[v]
        return t


def tour_len(D, t):
    return float(sum(D[t[i], t[(i + 1) % len(t)]] for i in range(len(t)))) if len(t) > 1 else 0.0


def check(n, D, p, clusters, B, t):
    ok = len(set(t)) == len(t) and len(t) > 0
    s = set(t)
    ok = ok and all(any(v in s for v in C) for C in clusters)
    L = tour_len(D, t)
    ok = ok and L <= B + 1e-6
    return ok, float(sum(p[v] for v in t)), L


def run_bb(name, tlim):
    r = load_manifest()[name]
    B = float(r["B"])
    n, D, p, clusters = read_graph(r["graph"], r["profit"])
    t0 = time.time()
    M = MTZModel(n, D, p, clusters, B)
    tbuild = time.time() - t0
    h = M.h
    h.setOptionValue("time_limit", max(1.0, tlim - tbuild))
    h.run()
    el = time.time() - t0
    info = h.getInfo()
    status = h.modelStatusToString(h.getModelStatus())
    tour = []
    if info.primal_solution_status == 2:  # kSolutionStatusFeasible
        tour = M.tour_from(h.getSolution().col_value)
    ok, prize, L = check(n, D, p, clusters, B, tour) if tour else (False, 0.0, 0.0)
    ub = info.mip_dual_bound
    res = dict(inst=name, algo="BB", seed=0, tlim=tlim, n=n, K=len(clusters), B=B, feasible=ok,
               prize=prize if ok else 0.0, len=L, m=len(tour), time=el, time_best=el,
               iters=int(info.mip_node_count), ub=float(ub) if np.isfinite(ub) else None,
               status=status, build_time=tbuild, trace=[], tour=tour)
    print(json.dumps(res))


# ---------------------------------------------------------------------------------------
# Formulação (CUT) do artigo: variáveis y (nós) e x (arestas), GSECs separados sob demanda
# em soluções inteiras (laço de geração de linhas). Os cortes são globalmente válidos e
# permanecem no modelo entre resoluções (pool de cortes).
# ---------------------------------------------------------------------------------------
def components(n, xs):
    adj = [[] for _ in range(n)]
    for (i, j) in xs:
        adj[i].append(j); adj[j].append(i)
    seen, comps = [False] * n, []
    for s in range(n):
        if seen[s] or not adj[s]:
            continue
        st, c = [s], []
        seen[s] = True
        while st:
            u = st.pop(); c.append(u)
            for w in adj[u]:
                if not seen[w]:
                    seen[w] = True; st.append(w)
        comps.append(c)
    return comps


def cycle_order(comp, xs):
    adj = {}
    for (i, j) in xs:
        adj.setdefault(i, []).append(j); adj.setdefault(j, []).append(i)
    start = comp[0]
    t, prev, v = [start], None, start
    while True:
        nx = [w for w in adj[v] if w != prev]
        if not nx:
            break
        prev, v = v, nx[0]
        if v == start or len(t) > len(comp):
            break
        t.append(v)
    return t


class CutModel:
    def __init__(self, n, D, p, clusters, B):
        self.n, self.D, self.p, self.clusters, self.B = n, D, p, clusters, B
        E = [(i, j) for i in range(n) for j in range(i + 1, n)]
        self.E, self.ne = E, len(E)
        self.eid = {e: k for k, e in enumerate(E)}
        ne, nv = len(E), n + len(E)
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("threads", 1)
        h.setOptionValue("random_seed", 1)
        h.addVars(nv, np.zeros(nv), np.ones(nv))
        h.changeColsIntegrality(nv, np.arange(nv, dtype=np.int32),
                                np.array([highspy.HighsVarType.kInteger] * nv))
        h.changeColsCost(n, np.arange(n, dtype=np.int32), p.astype(float))
        h.changeObjectiveSense(highspy.ObjSense.kMaximize)
        inc = [[] for _ in range(n)]
        for k, (i, j) in enumerate(E):
            inc[i].append(n + k); inc[j].append(n + k)
        for i in range(n):  # (DEGREE)
            h.addRow(0, 0, n, np.array(inc[i] + [i], dtype=np.int32), np.array([1.0] * (n - 1) + [-2.0]))
        for C in clusters:  # (CLUSTER+)
            cols = list(C) + [n + self.eid[a, b] for a in C for b in C if a < b]
            h.addRow(1, INF, len(cols), np.array(cols, dtype=np.int32),
                     np.array([1.0] * len(C) + [-1.0] * (len(cols) - len(C))))
        h.addRow(-INF, B, ne, np.arange(n, nv, dtype=np.int32), np.array([D[i, j] for (i, j) in E]))  # (BUDGET)
        for k, (i, j) in enumerate(E):  # GSEC de tamanho 2
            h.addRow(-INF, 0, 2, np.array([n + k, i], dtype=np.int32), np.array([1.0, -1.0]))
            h.addRow(-INF, 0, 2, np.array([n + k, j], dtype=np.int32), np.array([1.0, -1.0]))
        self.h = h
        self.cl_sets = [set(C) for C in clusters]
        self.ncuts = 0

    def add_cuts(self, comps):
        n, h = self.n, self.h
        for S in comps:
            Sset = set(S)
            out_cl = any(C.isdisjoint(Sset) for C in self.cl_sets)
            in_cl = any(C <= Sset for C in self.cl_sets)
            cut = [n + self.eid[min(a, b), max(a, b)] for a in S for b in range(n) if b not in Sset]
            if out_cl and in_cl:  # (GSEC.1)
                h.addRow(2, INF, len(cut), np.array(cut, dtype=np.int32), np.ones(len(cut))); self.ncuts += 1
            elif out_cl:  # (GSEC.2)
                for i in S:
                    h.addRow(0, INF, len(cut) + 1, np.array(cut + [i], dtype=np.int32),
                             np.array([1.0] * len(cut) + [-2.0])); self.ncuts += 1
            else:  # (GSEC)
                others = [v for T in comps if T is not S for v in T]
                for i in S:
                    for j in others:
                        h.addRow(-2, INF, len(cut) + 2, np.array(cut + [i, j], dtype=np.int32),
                                 np.array([1.0] * len(cut) + [-2.0, -2.0])); self.ncuts += 1

    def solve(self, tlim, stop_first=False):
        """Resolve até obter um tour único (ou esgotar o tempo).
        Retorna (status, tour, ub, rodadas); status em {optimal, feasible, infeasible, time_limit}."""
        t0 = time.time()
        h = self.h
        rounds, ub = 0, None
        h.setOptionValue("mip_max_improving_sols", 1 if stop_first else 2147483647)
        while True:
            rem = tlim - (time.time() - t0)
            if rem <= 0.5:
                return "time_limit", None, ub, rounds
            h.setOptionValue("time_limit", rem)
            h.run()
            rounds += 1
            ms = h.getModelStatus()
            info = h.getInfo()
            if ms == highspy.HighsModelStatus.kInfeasible:
                return "infeasible", None, ub, rounds
            ub = info.mip_dual_bound
            if info.primal_solution_status != 2:
                return "time_limit", None, ub, rounds
            x = h.getSolution().col_value
            xs = [self.E[k] for k in range(self.ne) if x[self.n + k] > 0.5]
            comps = components(self.n, xs)
            if len(comps) == 1:
                t = cycle_order(comps[0], xs)
                return ("optimal" if ms == highspy.HighsModelStatus.kOptimal else "feasible"), t, ub, rounds
            self.add_cuts(comps)
            h.clearSolver()


def run_cut(name, tlim, lb_hint=None):
    """Referência exata (formulação CUT). lb_hint opcional: exige prêmio >= dica."""
    r = load_manifest()[name]
    B = float(r["B"])
    n, D, p, clusters = read_graph(r["graph"], r["profit"])
    t0 = time.time()
    M = CutModel(n, D, p, clusters, B)
    if lb_hint is not None:
        M.h.addRow(lb_hint, INF, n, np.arange(n, dtype=np.int32), p.astype(float))
    status, t, ub, rounds = M.solve(tlim - (time.time() - t0))
    if status == "infeasible" and lb_hint is not None:
        status, ub = "hint_optimal", lb_hint
    res = dict(inst=name, algo="EXACT", seed=0, tlim=tlim, n=n, K=len(clusters), B=B, status=status,
               ub=float(ub) if ub is not None and np.isfinite(ub) else None, time=time.time() - t0,
               iters=rounds, cuts=M.ncuts, lb_hint=lb_hint)
    if t:
        ok, prize, L = check(n, D, p, clusters, B, t)
        res.update(feasible=ok, prize=prize, len=L, tour=t)
    else:
        res.update(feasible=False, prize=0.0, tour=[])
    print(json.dumps(res))


def run_lbr(name, tlim, tms=None, seed=1, kmax=6, tnb=20.0):
    """MSPD (C++) seguido de Local Branching sobre a formulação (CUT)."""
    r = load_manifest()[name]
    B = float(r["B"])
    n, D, p, clusters = read_graph(r["graph"], r["profit"])
    t0 = time.time()
    if tms is None:
        tms = max(1.0, n / 50)
    out = subprocess.run([GCOP, "solve", os.path.join(ROOT, r["graph"]), "--profit", r["profit"], "--budget", r["B"],
                          "--algo", "MSPD", "--seed", str(seed), "--time", str(tms), "--name", name],
                         capture_output=True, text=True, check=True)
    ms = json.loads(out.stdout)
    best_t = ms["tour"]
    ok, best_p, best_L = check(n, D, p, clusters, B, best_t)
    trace = [[x[0], x[1]] for x in ms["trace"]]
    M = CutModel(n, D, p, clusters, B)
    h = M.h
    k, improvements, solves, proven = 2, 0, 0, 0
    ycols = np.arange(n, dtype=np.int32)
    delta = 1.0 if np.allclose(p, np.round(p)) else 1e-4
    while time.time() - t0 < tlim and k <= kmax:
        inT = set(best_t)
        coefs = np.array([-1.0 if i in inT else 1.0 for i in range(n)])
        nr = h.getNumRow()
        h.addRow(-INF, k - len(inT), n, ycols, coefs)                    # (LB)
        h.addRow(best_p + delta - 1e-6, INF, n, ycols, p.astype(float))  # corte de melhoria
        rem = min(tnb, tlim - (time.time() - t0))
        status, t, ub, rounds = M.solve(rem, stop_first=True)
        solves += rounds
        found = False
        if t:
            ok2, p2, L2 = check(n, D, p, clusters, B, t)
            if ok2 and p2 > best_p + 1e-9:
                best_t, best_p, best_L, found = t, p2, L2, True
                improvements += 1
                trace.append([time.time() - t0, best_p])
        if status == "infeasible":
            proven += 1
        h.deleteRows(2, np.array([nr, nr + 1], dtype=np.int32))
        h.clearSolver()
        k = 2 if found else k + 2
    el = time.time() - t0
    res = dict(inst=name, algo="LBR", seed=seed, tlim=tlim, n=n, K=len(clusters), B=B, feasible=bool(ok),
               prize=best_p, len=best_L, m=len(best_t), time=el, time_best=trace[-1][0] if trace else el,
               iters=solves, lb_improvements=improvements, lb_proven_empty=proven, mspd_prize=ms["prize"],
               mspd_time=tms, trace=trace, tour=best_t)
    print(json.dumps(res))


if __name__ == "__main__":
    mode, name = sys.argv[1], sys.argv[2]
    if mode == "bb":
        run_bb(name, float(sys.argv[3]))
    elif mode == "cut":
        run_cut(name, float(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) > 4 else None)
    else:
        run_lbr(name, float(sys.argv[3]), float(sys.argv[4]) if len(sys.argv) > 4 else None,
                int(sys.argv[5]) if len(sys.argv) > 5 else 1)
