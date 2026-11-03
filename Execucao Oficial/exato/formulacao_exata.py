"""Referência exata da H3: formulação de arestas do GCOP (Álvarez-Miranda et al., 2018) no HiGHS,
com uma thread, por geração iterativa de restrições: resolve-se o modelo sem as restrições de
subciclo e, enquanto a solução tiver mais de um ciclo, acrescentam-se cortes que os eliminam.
Como cada modelo é uma relaxação, o limitante dual é um limitante superior válido mesmo sem
provar a otimalidade. A melhor rota das heurísticas entra como solução inicial do solver.

Uso: python exato/formulacao_exata.py <instancia> <tempo_s> [arquivo_json_com_rota_inicial]
Saída: uma linha JSON.
"""
import csv
import json
import os
import sys
import time

import highspy
import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INF = highspy.kHighsInf


def le_grafo(caminho, premio):
    n, rot, pa, D = 0, None, {}, None
    with open(os.path.join(RAIZ, caminho)) as f:
        for linha in f:
            t = linha.split()
            if not t:
                continue
            if t[0] == "Nodes":
                n = int(t[1]); D = np.zeros((n, n)); rot = [-1] * n
            elif t[0] == "V":
                rot[int(t[1])] = int(t[2])
            elif t[0] == "E":
                i, j, w = int(t[1]), int(t[2]), float(t[3])
                D[i, j] = D[j, i] = w
            elif t[0] == "P":
                pa[int(t[1])] = float(t[2])
    labs = sorted({r for r in rot if r >= 0})
    clusters = [[i for i in range(n) if rot[i] == r] for r in labs]
    if premio == "rand":
        p = [1 + (7213 * i) % 100 for i in range(n)]
    elif premio == "arquivo":
        p = [pa[i] for i in range(n)]
    else:
        p = [1.0] * n
    return n, D, np.array(p, dtype=float), clusters


def confere(n, D, p, clusters, B, t):
    """Verificador independente de uma rota."""
    if len(t) < 3 or len(set(t)) != len(t):
        return False, 0.0, 0.0
    s = set(t)
    L = float(sum(D[t[i], t[(i + 1) % len(t)]] for i in range(len(t))))
    ok = all(any(v in s for v in C) for C in clusters) and L <= B + 1e-6
    return ok, float(sum(p[v] for v in t)), L


def componentes(n, arestas):
    adj = [[] for _ in range(n)]
    for i, j in arestas:
        adj[i].append(j); adj[j].append(i)
    visto, comps = [False] * n, []
    for s in range(n):
        if visto[s] or not adj[s]:
            continue
        pilha, c = [s], []
        visto[s] = True
        while pilha:
            u = pilha.pop(); c.append(u)
            for w in adj[u]:
                if not visto[w]:
                    visto[w] = True; pilha.append(w)
        comps.append(c)
    return comps


def ordem_ciclo(comp, arestas):
    adj = {}
    for i, j in arestas:
        adj.setdefault(i, []).append(j); adj.setdefault(j, []).append(i)
    ini = comp[0]
    t, ant, v = [ini], None, ini
    while True:
        prox = [w for w in adj[v] if w != ant]
        if not prox:
            break
        ant, v = v, prox[0]
        if v == ini or len(t) > len(comp):
            break
        t.append(v)
    return t


class Modelo:
    MAX_LINHAS_GSEC = 400

    def __init__(self, n, D, p, clusters, B, inteiro):
        self.n, self.clusters = n, clusters
        self.E = [(i, j) for i in range(n) for j in range(i + 1, n)]
        self.eid = {e: k for k, e in enumerate(self.E)}
        ne, nv = len(self.E), n + len(self.E)
        self.nv = nv
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("threads", 1)
        h.setOptionValue("random_seed", 1)
        h.setOptionValue("mip_rel_gap", 0.0)
        # com prêmios inteiros, um gap absoluto abaixo de 1 já prova a otimalidade
        h.setOptionValue("mip_abs_gap", 0.999 if inteiro else 1e-6)
        h.addVars(nv, np.zeros(nv), np.ones(nv))
        h.changeColsIntegrality(nv, np.arange(nv, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * nv))
        h.changeColsCost(n, np.arange(n, dtype=np.int32), p.astype(float))
        h.changeObjectiveSense(highspy.ObjSense.kMaximize)
        inc = [[] for _ in range(n)]
        for k, (i, j) in enumerate(self.E):
            inc[i].append(n + k); inc[j].append(n + k)
        for i in range(n):  # grau: x(delta(i)) = 2 y_i
            h.addRow(0, 0, n, np.array(inc[i] + [i], dtype=np.int32), np.array([1.0] * (n - 1) + [-2.0]))
        for C in clusters:  # cobertura fortalecida (CLUSTER+)
            col = list(C) + [n + self.eid[a, b] for a in C for b in C if a < b]
            h.addRow(1, INF, len(col), np.array(col, dtype=np.int32),
                     np.array([1.0] * len(C) + [-1.0] * (len(col) - len(C))))
        h.addRow(-INF, B, ne, np.arange(n, nv, dtype=np.int32), np.array([D[i, j] for (i, j) in self.E]))
        for k, (i, j) in enumerate(self.E):  # x_ij <= y_i e x_ij <= y_j
            h.addRow(-INF, 0, 2, np.array([n + k, i], dtype=np.int32), np.array([1.0, -1.0]))
            h.addRow(-INF, 0, 2, np.array([n + k, j], dtype=np.int32), np.array([1.0, -1.0]))
        self.h = h
        self.conj = [set(C) for C in clusters]
        self.ncortes = 0
        self.inicial = None

    def define_inicial(self, t):
        x = np.zeros(self.nv)
        for v in t:
            x[v] = 1.0
        for q in range(len(t)):
            a, b = t[q], t[(q + 1) % len(t)]
            x[self.n + self.eid[min(a, b), max(a, b)]] = 1.0
        self.inicial = x

    def aplica_inicial(self):
        if self.inicial is not None:
            s = highspy.HighsSolution()
            s.col_value = list(self.inicial)
            self.h.setSolution(s)

    def corta(self, comps):
        n, h = self.n, self.h
        for S in comps:
            cj = set(S)
            fora = any(C.isdisjoint(cj) for C in self.conj)   # algum cluster sem vértice em S
            dentro = any(C <= cj for C in self.conj)          # algum cluster inteiro em S
            cut = [n + self.eid[min(a, b), max(a, b)] for a in S for b in range(n) if b not in cj]
            if fora and dentro:  # a rota precisa entrar e sair de S
                h.addRow(2, INF, len(cut), np.array(cut, dtype=np.int32), np.ones(len(cut)))
                self.ncortes += 1
            elif fora:  # visitar i em S obriga a sair de S
                for i in S:
                    h.addRow(0, INF, len(cut) + 1, np.array(cut + [i], dtype=np.int32),
                             np.array([1.0] * len(cut) + [-2.0]))
                    self.ncortes += 1
            else:  # corte geral: x(delta(S)) >= 2 (y_i + y_j - 1), i em S, j fora de S
                outros = [v for T in comps if T is not S for v in T]
                pares = [(i, j) for i in S for j in outros][: self.MAX_LINHAS_GSEC]
                for i, j in pares:
                    h.addRow(-2, INF, len(cut) + 2, np.array(cut + [i, j], dtype=np.int32),
                             np.array([1.0] * len(cut) + [-2.0, -2.0]))
                    self.ncortes += 1

    def resolve(self, tlim):
        """Retorna (situação, rota, limitante superior, rodadas)."""
        t0 = time.time()
        h, sup, rodadas = self.h, None, 0
        def atualiza(ub):
            nonlocal sup
            if np.isfinite(ub):
                sup = ub if sup is None else min(sup, ub)
        while True:
            resto = tlim - (time.time() - t0)
            if resto <= 0.5:
                return "limite_tempo", None, sup, rodadas
            h.setOptionValue("time_limit", resto)
            self.aplica_inicial()
            h.run()
            rodadas += 1
            ms = h.getModelStatus()
            info = h.getInfo()
            if ms == highspy.HighsModelStatus.kInfeasible:
                return "inviavel", None, sup, rodadas
            atualiza(info.mip_dual_bound)
            if info.primal_solution_status != 2:
                return "limite_tempo", None, sup, rodadas
            x = h.getSolution().col_value
            ar = [self.E[k] for k in range(len(self.E)) if x[self.n + k] > 0.5]
            comps = componentes(self.n, ar)
            if len(comps) == 1:
                t = ordem_ciclo(comps[0], ar)
                return ("otimo" if ms == highspy.HighsModelStatus.kOptimal else "limite_tempo"), t, sup, rodadas
            self.corta(comps)
            h.clearSolver()


def main():
    nome, tlim = sys.argv[1], float(sys.argv[2])
    with open(os.path.join(RAIZ, "dados", "instancias.csv")) as f:
        r = {x["nome"]: x for x in csv.DictReader(f)}[nome]
    B = float(r["B"])
    n, D, p, clusters = le_grafo(r["grafo"], r["premio"])
    t0 = time.time()
    M = Modelo(n, D, p, clusters, B, bool(np.allclose(p, np.round(p))))
    inicial = None
    if len(sys.argv) > 3 and os.path.exists(sys.argv[3]):
        with open(sys.argv[3]) as f:
            inicial = json.load(f).get(nome)
        if inicial:
            ok, _, _ = confere(n, D, p, clusters, B, inicial)
            if ok:
                M.define_inicial(inicial)
            else:
                inicial = None
    sit, t, sup, rodadas = M.resolve(tlim - (time.time() - t0))
    saida = dict(inst=nome, algo="EXATO", tlim=tlim, n=n, K=len(clusters), B=B, situacao=sit,
                 sup=float(sup) if sup is not None else None, tempo=time.time() - t0,
                 rodadas=rodadas, cortes=M.ncortes, com_inicial=bool(inicial), viavel=False, P=0.0, L=0.0, rota=[])
    if t:
        ok, P, L = confere(n, D, p, clusters, B, t)
        if ok:
            saida.update(viavel=True, P=P, L=L, rota=[int(v) for v in t])
        elif sit == "otimo":
            saida["situacao"] = "erro_rota"
    print(json.dumps(saida))


if __name__ == "__main__":
    main()
