// Heurísticas construtivas.
#pragma once
#include "localsearch.hpp"

// Nó inicial determinístico: menor índice do menor cluster.
inline int defaultStart(const Inst& I) {
    int bk = 0;
    for (int k = 1; k < I.K; k++) if (I.clusters[k].size() < I.clusters[bk].size()) bk = k;
    return *min_element(I.clusters[bk].begin(), I.clusters[bk].end());
}

// Inserção do mais próximo / mais distante adaptada ao GTSP (Fischetti et al., 1997):
// escolhe o cluster descoberto mais próximo (ou mais distante) do tour e insere o seu nó
// de menor custo de inserção.
inline Sol gtspInsertion(const Inst& I, bool nearest, int start) {
    Sol s; s.init(I);
    insertAt(I, s, start, 0);
    vector<double> mind(I.n);
    for (int v = 0; v < I.n; v++) mind[v] = I.d(start, v);
    while (s.uncovered > 0) {
        int bk = -1; double bd = nearest ? 1e300 : -1;
        for (int k = 0; k < I.K; k++) {
            if (s.ccount[k] > 0) continue;
            double dk = 1e300;
            for (int v : I.clusters[k]) dk = min(dk, mind[v]);
            if ((nearest && dk < bd) || (!nearest && dk > bd)) { bd = dk; bk = k; }
        }
        double bc = 1e300; int bv = -1, bp = 0;
        for (int v : I.clusters[bk]) {
            auto [c, pos] = bestInsertion(I, s, v);
            if (c < bc) { bc = c; bv = v; bp = pos; }
        }
        insertAt(I, s, bv, bp);
        for (int v = 0; v < I.n; v++) mind[v] = min(mind[v], I.d(bv, v));
    }
    return s;
}

// Construção por árvore de Steiner (heurística de caminhos mais curtos de Takahashi &
// Matsuyama, 1980) no grafo com um terminal artificial por cluster; o tour é obtido por
// percurso em pré-ordem a partir da raiz (generalização da heurística MST para o TSP).
inline Sol steinerConstruct(const Inst& I, int root) {
    int n = I.n;
    vector<char> inTree(n, 0), covered(I.K, 0);
    vector<vector<int>> adj(n);
    int unc = I.K;
    auto addNode = [&](int v) {
        inTree[v] = 1;
        for (int c : I.nodeCl[v]) if (!covered[c]) { covered[c] = 1; unc--; }
    };
    addNode(root);
    vector<double> dist(n);
    vector<int> par(n);
    vector<char> done(n);
    while (unc > 0) {
        // Dijkstra multi-fonte (denso) a partir de todos os nós da árvore
        for (int v = 0; v < n; v++) { dist[v] = inTree[v] ? 0 : 1e300; par[v] = -1; done[v] = 0; }
        int target = -1;
        for (int it = 0; it < n; it++) {
            int u = -1; double bd = 1e300;
            for (int v = 0; v < n; v++) if (!done[v] && dist[v] < bd) { bd = dist[v]; u = v; }
            if (u < 0) break;
            done[u] = 1;
            if (!inTree[u]) {
                bool hit = false;
                for (int c : I.nodeCl[u]) if (!covered[c]) { hit = true; break; }
                if (hit) { target = u; break; }
            }
            for (int v = 0; v < n; v++) if (!done[v]) {
                double nd = dist[u] + I.d(u, v);
                if (nd < dist[v]) { dist[v] = nd; par[v] = u; }
            }
        }
        // adiciona o caminho até a árvore
        int v = target;
        while (!inTree[v]) {
            int u = par[v];
            adj[u].push_back(v); adj[v].push_back(u);
            addNode(v);
            v = u;
        }
    }
    // pré-ordem: filhos visitados do mais próximo ao mais distante
    Sol s; s.init(I);
    vector<int> order;
    vector<char> vis(n, 0);
    vector<int> st = {root};
    while (!st.empty()) {
        int u = st.back(); st.pop_back();
        if (vis[u]) continue;
        vis[u] = 1; order.push_back(u);
        vector<int> ch;
        for (int w : adj[u]) if (!vis[w]) ch.push_back(w);
        sort(ch.begin(), ch.end(), [&](int a, int b) { return I.d(u, a) > I.d(u, b); });
        for (int w : ch) st.push_back(w);
    }
    for (int v : order) { s.tour.push_back(v); }
    recompute(I, s);
    routeOpt(I, s);
    return s;
}

// Tour do caixeiro viajante sobre um conjunto de nós: vizinho mais próximo + 2-opt/Or-opt.
inline vector<int> tspTour(const Inst& I, const vector<int>& nodes, int starts, mt19937& rng) {
    vector<int> best; double bestL = 1e300;
    int m = nodes.size();
    if (m <= 3) return nodes;
    for (int r = 0; r < starts; r++) {
        vector<char> used(m, 0);
        int cur = r == 0 ? 0 : rng() % m;
        vector<int> t = {nodes[cur]}; used[cur] = 1;
        for (int it = 1; it < m; it++) {
            int bj = -1; double bd = 1e300;
            for (int j = 0; j < m; j++) if (!used[j] && I.d(nodes[cur], nodes[j]) < bd) { bd = I.d(nodes[cur], nodes[j]); bj = j; }
            used[bj] = 1; t.push_back(nodes[bj]); cur = bj;
        }
        Sol s; s.init(I); s.tour = t; s.len = tourLength(I, t);
        routeOpt(I, s);
        if (s.len < bestL) { bestL = s.len; best = s.tour; }
    }
    return best;
}

// Construção baseada no TSP ("route-first"): tour do TSP sobre todos os nós seguido de
// remoções (drop) pela pior razão ganho/prêmio até o tour caber no orçamento.
inline Sol tspDrop(const Inst& I, mt19937& rng, int starts = 1) {
    vector<int> all(I.n);
    iota(all.begin(), all.end(), 0);
    Sol s; s.init(I);
    s.tour = tspTour(I, all, starts, rng);
    recompute(I, s);
    int lastOpt = s.m();
    while (s.len > I.B + 1e-9 && s.m() > 1) {
        double best = -1e300; int bi = -1; bool bRem = false;
        for (int idx = 0; idx < s.m(); idx++) {
            int v = s.tour[idx];
            bool r = removable(I, s, v);
            double sc = removalGain(I, s, idx) / I.p[v];
            if ((r && !bRem) || (r == bRem && sc > best)) { best = sc; bi = idx; bRem = r; }
        }
        removeAt(I, s, bi);
        if (s.m() < 0.9 * lastOpt) { routeOpt(I, s); lastOpt = s.m(); }
    }
    return s;
}

// Construção aleatorizada do GRASP: cobertura de clusters e depois inserção por razão,
// ambas escolhendo ao acaso dentro de uma lista restrita de candidatos (LRC).
inline Sol graspConstruct(const Inst& I, double alpha, mt19937& rng) {
    Sol s; s.init(I);
    int k0 = rng() % I.K;
    insertAt(I, s, I.clusters[k0][rng() % I.clusters[k0].size()], 0);
    vector<int> cand; vector<double> cc; vector<int> cp;
    while (s.uncovered > 0) {
        cand.clear(); cc.clear(); cp.clear();
        double cmin = 1e300, cmax = -1e300;
        for (int k = 0; k < I.K; k++) {
            if (s.ccount[k] > 0) continue;
            for (int v : I.clusters[k]) {
                if (s.in[v]) continue;
                auto [c, pos] = bestInsertion(I, s, v);
                cand.push_back(v); cc.push_back(c); cp.push_back(pos);
                cmin = min(cmin, c); cmax = max(cmax, c);
            }
        }
        double thr = cmin + alpha * (cmax - cmin);
        vector<int> rcl;
        for (size_t q = 0; q < cand.size(); q++) if (cc[q] <= thr + 1e-12) rcl.push_back(q);
        int q = rcl[rng() % rcl.size()];
        insertAt(I, s, cand[q], cp[q]);
    }
    double tiny = 1e-9 * I.avgD;
    while (true) {
        cand.clear(); cc.clear(); cp.clear();
        double rmin = 1e300, rmax = -1e300, slack = I.B - s.len + 1e-9;
        for (int v = 0; v < I.n; v++) {
            if (s.in[v]) continue;
            auto [c, pos] = bestInsertion(I, s, v);
            if (c > slack) continue;
            double r = I.p[v] / max(c, tiny);
            cand.push_back(v); cc.push_back(r); cp.push_back(pos);
            rmin = min(rmin, r); rmax = max(rmax, r);
        }
        if (cand.empty()) break;
        double thr = rmax - alpha * (rmax - rmin);
        vector<int> rcl;
        for (size_t q = 0; q < cand.size(); q++) if (cc[q] >= thr - 1e-12) rcl.push_back(q);
        int q = rcl[rng() % rcl.size()];
        insertAt(I, s, cand[q], cp[q]);
    }
    return s;
}
