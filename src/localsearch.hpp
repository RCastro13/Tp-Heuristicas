// Operadores de busca local: 2-opt, Or-opt, cobertura de clusters, inserção por razão,
// troca (swap), reparo de viabilidade e o refinamento baseado em sigma do artigo.
#pragma once
#include "solution.hpp"

// ---------------------------------------------------------------- roteamento
inline bool twoOpt(const Inst& I, Sol& s) {
    int m = s.m();
    if (m < 4) return false;
    bool any = false, improved = true;
    while (improved) {
        improved = false;
        for (int i = 0; i < m - 2; i++) {
            int a = s.tour[i], b = s.tour[i + 1];
            double dab = I.d(a, b);
            for (int j = i + 2; j < m; j++) {
                if (i == 0 && j == m - 1) continue;
                int c = s.tour[j], e = s.tour[j + 1 == m ? 0 : j + 1];
                double delta = I.d(a, c) + I.d(b, e) - dab - I.d(c, e);
                if (delta < -EPS) {
                    reverse(s.tour.begin() + i + 1, s.tour.begin() + j + 1);
                    s.len += delta;
                    improved = any = true;
                    b = s.tour[i + 1]; dab = I.d(a, b);
                }
            }
        }
    }
    return any;
}

// Or-opt: realoca segmentos de 1 a 3 nós consecutivos (com ou sem inversão).
// É o caso restrito do 3-opt mais usado na prática ("3-opt sem inversões arbitrárias").
inline bool orOpt(const Inst& I, Sol& s) {
    int m = s.m();
    if (m < 5) return false;
    bool any = false;
    for (int L = 1; L <= 3; L++) {
        for (int st = 0; st + L <= m; st++) {
            int a = s.tour[st], b = s.tour[st + L - 1];
            int pr = s.tour[(st - 1 + m) % m], nx = s.tour[(st + L) % m];
            double gain = I.d(pr, a) + I.d(b, nx) - I.d(pr, nx);
            if (gain <= EPS) continue;
            double bestC = gain - EPS; int bestK = -1; bool rev = false;
            for (int k = 0; k < m; k++) {
                // aresta (t[k], t[k+1]) não pode tocar o segmento
                if (k >= st - 1 && k <= st + L - 1) continue;
                if (st == 0 && k == m - 1) continue;
                int c = s.tour[k], e = s.tour[k + 1 == m ? 0 : k + 1];
                double dce = I.d(c, e);
                double c1 = I.d(c, a) + I.d(b, e) - dce;
                double c2 = I.d(c, b) + I.d(a, e) - dce;
                if (c1 < bestC) { bestC = c1; bestK = k; rev = false; }
                if (c2 < bestC) { bestC = c2; bestK = k; rev = true; }
            }
            if (bestK < 0) continue;
            int cNode = s.tour[bestK];
            vector<int> seg(s.tour.begin() + st, s.tour.begin() + st + L);
            if (rev) reverse(seg.begin(), seg.end());
            s.tour.erase(s.tour.begin() + st, s.tour.begin() + st + L);
            int ci = indexOf(s, cNode);
            s.tour.insert(s.tour.begin() + ci + 1, seg.begin(), seg.end());
            s.len += bestC - gain;
            any = true;
        }
    }
    return any;
}

inline void routeOpt(const Inst& I, Sol& s) {
    for (int it = 0; it < 100; it++) {
        bool a = twoOpt(I, s);
        bool b = orOpt(I, s);
        if (!a && !b) break;
    }
    s.len = tourLength(I, s.tour);  // elimina erro numérico acumulado
}

// ---------------------------------------------------------------- clusters
// mode 0: inserção mais barata global; mode 1: regret-2 entre clusters.
inline void coverClusters(const Inst& I, Sol& s, int mode = 0, mt19937* rng = nullptr, double noise = 0) {
    uniform_real_distribution<double> U(1 - noise, 1 + noise);
    while (s.uncovered > 0) {
        if (s.m() == 0) {
            for (int k = 0; k < I.K; k++) if (s.ccount[k] == 0) {
                int v = I.clusters[k][rng ? (*rng)() % I.clusters[k].size() : 0];
                insertAt(I, s, v, 0); break;
            }
            continue;
        }
        double bestScore = 1e300; int bestV = -1, bestPos = 0;
        for (int k = 0; k < I.K; k++) {
            if (s.ccount[k] > 0) continue;
            double c1 = 1e300, c2 = 1e300; int v1 = -1, p1 = 0;
            for (int v : I.clusters[k]) {
                auto [c, pos] = bestInsertion(I, s, v);
                if (rng && noise > 0) c *= U(*rng);
                if (c < c1) { c2 = c1; c1 = c; v1 = v; p1 = pos; }
                else if (c < c2) c2 = c;
            }
            double score = mode == 1 ? -(c2 >= 1e299 ? 1e12 : c2 - c1) : c1;
            if (score < bestScore) { bestScore = score; bestV = v1; bestPos = p1; }
        }
        insertAt(I, s, bestV, bestPos);
    }
}

// ---------------------------------------------------------------- inserção por razão
// Insere repetidamente o nó de maior razão prêmio / aumento de comprimento que caiba no
// orçamento. Mantém cache da melhor aresta de inserção de cada nó fora do tour.
inline bool insertPhase(const Inst& I, Sol& s, double noise = 0, mt19937* rng = nullptr) {
    if (s.m() == 0) return false;
    int n = I.n;
    vector<double> cst(n, 1e300);
    vector<int> pa(n, -1), pb(n, -1);
    auto full = [&](int v) {
        int m = s.m();
        if (m == 1) { cst[v] = 2 * I.d(s.tour[0], v); pa[v] = s.tour[0]; pb[v] = s.tour[0]; return; }
        double best = 1e300; int ba = -1, bb = -1;
        for (int i = 0; i < m; i++) {
            int a = s.tour[i], b = s.tour[i + 1 == m ? 0 : i + 1];
            double c = I.d(a, v) + I.d(v, b) - I.d(a, b);
            if (c < best) { best = c; ba = a; bb = b; }
        }
        cst[v] = best; pa[v] = ba; pb[v] = bb;
    };
    for (int v = 0; v < n; v++) if (!s.in[v]) full(v);
    vector<double> mult(n, 1.0);
    if (rng && noise > 0) {
        uniform_real_distribution<double> U(1 - noise, 1 + noise);
        for (int v = 0; v < n; v++) mult[v] = U(*rng);
    }
    double tiny = 1e-9 * I.avgD;
    bool any = false;
    while (true) {
        double slack = I.B - s.len + 1e-9;
        double bestScore = -1; int bv = -1;
        for (int v = 0; v < n; v++) {
            if (s.in[v] || cst[v] > slack) continue;
            double sc = I.p[v] / max(cst[v], tiny) * mult[v];
            if (cst[v] <= 0) sc = 1e18 * I.p[v] - cst[v];
            if (sc > bestScore) { bestScore = sc; bv = v; }
        }
        if (bv < 0) break;
        int a = pa[bv], b = pb[bv];
        int pos;
        if (s.m() == 1) pos = 1;
        else pos = indexOf(s, a) + 1;
        insertAt(I, s, bv, pos);
        any = true;
        int m = s.m();
        for (int v = 0; v < n; v++) {
            if (s.in[v]) continue;
            if (m <= 3 || (pa[v] == a && pb[v] == b) || (pa[v] == b && pb[v] == a)) { full(v); continue; }
            double c1 = I.d(a, v) + I.d(v, bv) - I.d(a, bv);
            if (c1 < cst[v]) { cst[v] = c1; pa[v] = a; pb[v] = bv; }
            double c2 = I.d(bv, v) + I.d(v, b) - I.d(bv, b);
            if (c2 < cst[v]) { cst[v] = c2; pa[v] = bv; pb[v] = b; }
        }
    }
    return any;
}

// ---------------------------------------------------------------- troca 1-1
// Custo exato de inserir j no tour após remover a posição idx, usando as três melhores
// arestas de inserção de j (precomputadas em top) mais a nova aresta (prev, next).
struct InsTop { double c[3]; int k[3]; };
inline InsTop insTop(const Inst& I, const Sol& s, int j) {
    InsTop t; for (int q = 0; q < 3; q++) { t.c[q] = 1e300; t.k[q] = -1; }
    int m = s.m();
    for (int k = 0; k < m; k++) {
        int a = s.tour[k], b = s.tour[k + 1 == m ? 0 : k + 1];
        double c = I.d(a, j) + I.d(j, b) - I.d(a, b);
        if (c < t.c[2]) {
            t.c[2] = c; t.k[2] = k;
            if (t.c[2] < t.c[1]) { swap(t.c[2], t.c[1]); swap(t.k[2], t.k[1]); }
            if (t.c[1] < t.c[0]) { swap(t.c[1], t.c[0]); swap(t.k[1], t.k[0]); }
        }
    }
    return t;
}
inline double swapNewLen(const Inst& I, const Sol& s, const InsTop& t, int j, int idx) {
    int m = s.m();
    int pi = prv(s, idx), ni = nxt(s, idx);
    int pr = s.tour[pi], nx = s.tour[ni];
    double rem = removalGain(I, s, idx);
    double best = (m >= 3) ? I.d(pr, j) + I.d(j, nx) - I.d(pr, nx) : 2 * I.d(pr, j);
    for (int q = 0; q < 3; q++) {
        if (t.k[q] < 0) break;
        if (t.k[q] == pi || t.k[q] == idx) continue;
        best = min(best, t.c[q]); break;
    }
    return s.len - rem + best;
}

inline bool swapPhase(const Inst& I, Sol& s) {
    if (s.m() < 3) return false;
    vector<int> outs;
    for (int v = 0; v < I.n; v++) if (!s.in[v]) outs.push_back(v);
    sort(outs.begin(), outs.end(), [&](int a, int b) { return I.p[a] > I.p[b]; });
    bool any = false;
    for (int j : outs) {
        if (s.in[j]) continue;
        InsTop t = insTop(I, s, j);
        int bestIdx = -1; double bestGain = 0, bestLen = s.len;
        for (int idx = 0; idx < s.m(); idx++) {
            int v = s.tour[idx];
            double g = I.p[j] - I.p[v];
            if (g < -EPS) continue;
            if (!removable(I, s, v, j)) continue;
            double nl = swapNewLen(I, s, t, j, idx);
            if (nl > I.B + 1e-9) continue;
            if (g <= EPS && nl >= s.len - 1e-6) continue;  // sem ganho de prêmio exige encurtar
            if (bestIdx < 0 || g > bestGain + EPS || (fabs(g - bestGain) <= EPS && nl < bestLen)) {
                bestIdx = idx; bestGain = g; bestLen = nl;
            }
        }
        if (bestIdx >= 0) {
            removeAt(I, s, bestIdx);
            insertBest(I, s, j);
            any = true;
        }
    }
    return any;
}

// Busca local exata (proposta): 2-opt/Or-opt + inserção por razão + troca, até ótimo local.
inline void improve(const Inst& I, Sol& s) {
    for (int it = 0; it < 50; it++) {
        routeOpt(I, s);
        bool a = insertPhase(I, s);
        bool b = swapPhase(I, s);
        if (!a && !b) break;
    }
    s.len = tourLength(I, s.tour);
}

// ---------------------------------------------------------------- reparo
// Remove nós de pior razão (ganho de comprimento / prêmio) até caber no orçamento e
// reinsere clusters descobertos pela inserção mais barata.
inline bool repair(const Inst& I, Sol& s) {
    for (int round = 0; round < 20; round++) {
        routeOpt(I, s);
        while (s.len > I.B + 1e-9 && s.m() > 1) {
            double best = -1e300; int bi = -1; bool bRem = false;
            for (int idx = 0; idx < s.m(); idx++) {
                int v = s.tour[idx];
                bool r = removable(I, s, v);
                double sc = removalGain(I, s, idx) / I.p[v];
                if ((r && !bRem) || (r == bRem && sc > best)) { best = sc; bi = idx; bRem = r; }
            }
            removeAt(I, s, bi);
            if (s.m() % 25 == 0) routeOpt(I, s);
        }
        coverClusters(I, s, 0);
        routeOpt(I, s);
        if (s.feasible(I)) return true;
    }
    return s.feasible(I);
}

// ---------------------------------------------------------------- refinamento do artigo
// Passos (a)-(e) de Álvarez-Miranda et al. (2018), com sigma_i = min_{j in V_T\{i}} d_ij / p_i.
inline vector<double> sigmaScores(const Inst& I, const Sol& s) {
    vector<double> sg(I.n, 1e300);
    for (int v = 0; v < I.n; v++) {
        double md = 1e300;
        for (int u : s.tour) if (u != v) md = min(md, I.d(u, v));
        if (md >= 1e299) md = 0;
        sg[v] = md / I.p[v];
    }
    return sg;
}

inline void sigmaRefine(const Inst& I, Sol& s) {
    for (int round = 0; round < 10; round++) {
        double P0 = s.prize, L0 = s.len;
        // (a) remoção de argmax sigma enquanto D(V_T) > B
        while (s.len > I.B + 1e-9 && s.m() > 1) {
            auto sg = sigmaScores(I, s);
            int bi = 0;
            for (int idx = 1; idx < s.m(); idx++) if (sg[s.tour[idx]] > sg[s.tour[bi]]) bi = idx;
            removeAt(I, s, bi);
        }
        // (b) inserção obrigatória: argmin sigma em cada cluster descoberto
        for (int k = 0; k < I.K; k++) {
            if (s.ccount[k] > 0) continue;
            auto sg = sigmaScores(I, s);
            int bv = I.clusters[k][0];
            for (int v : I.clusters[k]) if (sg[v] < sg[bv]) bv = v;
            insertBest(I, s, bv);
        }
        // (c) inserção opcional por menor sigma enquanto couber
        while (true) {
            auto sg = sigmaScores(I, s);
            vector<int> outs;
            for (int v = 0; v < I.n; v++) if (!s.in[v]) outs.push_back(v);
            sort(outs.begin(), outs.end(), [&](int a, int b) { return sg[a] < sg[b]; });
            bool ins = false;
            for (int v : outs) {
                auto [c, pos] = bestInsertion(I, s, v);
                if (s.len + c <= I.B + 1e-9) { insertAt(I, s, v, pos); ins = true; break; }
            }
            if (!ins) break;
        }
        // (d) troca i in V_T por j fora quando sigma_j < sigma_i, mantendo viabilidade
        {
            auto sg = sigmaScores(I, s);
            vector<int> ins(s.tour);
            sort(ins.begin(), ins.end(), [&](int a, int b) { return sg[a] > sg[b]; });
            vector<int> outs;
            for (int v = 0; v < I.n; v++) if (!s.in[v]) outs.push_back(v);
            sort(outs.begin(), outs.end(), [&](int a, int b) { return sg[a] < sg[b]; });
            for (int i : ins) {
                int idx = indexOf(s, i);
                if (idx < 0) continue;
                for (int j : outs) {
                    if (s.in[j] || sg[j] >= sg[i]) break;
                    if (!removable(I, s, i, j)) continue;
                    InsTop t = insTop(I, s, j);
                    double nl = swapNewLen(I, s, t, j, idx);
                    if (nl > I.B + 1e-9) continue;
                    removeAt(I, s, idx);
                    insertBest(I, s, j);
                    break;
                }
            }
        }
        // (e) 2-opt e 3-opt (Or-opt)
        routeOpt(I, s);
        if (!(s.prize > P0 + EPS || s.len < L0 - 1e-6)) break;
    }
    if (!s.feasible(I)) repair(I, s);
}
