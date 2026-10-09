// Representação da solução (tour) e operações elementares.
#pragma once
#include "instance.hpp"

constexpr double EPS = 1e-7;

struct Sol {
    vector<int> tour;     // sequência cíclica de nós visitados
    vector<char> in;      // in[v] = 1 se v está no tour
    vector<int> ccount;   // nº de nós visitados de cada cluster
    int uncovered = 0;    // nº de clusters sem nenhum nó visitado
    double len = 0, prize = 0;

    void init(const Inst& I) {
        tour.clear(); in.assign(I.n, 0); ccount.assign(I.K, 0);
        uncovered = I.K; len = 0; prize = 0;
    }
    int m() const { return (int)tour.size(); }
    bool feasible(const Inst& I) const { return uncovered == 0 && len <= I.B + 1e-6 && m() >= 1; }
};

inline int nxt(const Sol& s, int i) { return i + 1 == s.m() ? 0 : i + 1; }
inline int prv(const Sol& s, int i) { return i == 0 ? s.m() - 1 : i - 1; }

inline double tourLength(const Inst& I, const vector<int>& t) {
    if (t.size() < 2) return 0;
    double L = 0;
    for (size_t i = 0; i < t.size(); i++) L += I.d(t[i], t[(i + 1) % t.size()]);
    return L;
}

inline void recompute(const Inst& I, Sol& s) {
    vector<int> t = s.tour;
    s.init(I);
    s.tour = t;
    for (int v : t) {
        s.in[v] = 1; s.prize += I.p[v];
        for (int c : I.nodeCl[v]) if (s.ccount[c]++ == 0) s.uncovered--;
    }
    s.len = tourLength(I, t);
}

// Solução a é melhor que b? (prêmio maior; empate -> tour mais curto)
inline bool better(const Sol& a, const Sol& b) {
    if (a.prize > b.prize + EPS) return true;
    if (a.prize < b.prize - EPS) return false;
    return a.len < b.len - EPS;
}

// Custo de inserir v entre as posições pos-1 e pos (pos em [0, m]).
inline double insCostAt(const Inst& I, const Sol& s, int v, int pos) {
    int m = s.m();
    if (m == 0) return 0;
    if (m == 1) return 2 * I.d(s.tour[0], v);
    int a = s.tour[(pos - 1 + m) % m], b = s.tour[pos % m];
    return I.d(a, v) + I.d(v, b) - I.d(a, b);
}

// Melhor posição de inserção (inserção mais barata). Retorna {delta, pos}.
inline pair<double, int> bestInsertion(const Inst& I, const Sol& s, int v) {
    int m = s.m();
    if (m == 0) return {0, 0};
    if (m == 1) return {2 * I.d(s.tour[0], v), 1};
    double best = 1e300; int bp = 0;
    for (int i = 0; i < m; i++) {
        int a = s.tour[i], b = s.tour[i + 1 == m ? 0 : i + 1];
        double c = I.d(a, v) + I.d(v, b) - I.d(a, b);
        if (c < best) { best = c; bp = i + 1; }
    }
    return {best, bp};
}

inline void insertAt(const Inst& I, Sol& s, int v, int pos) {
    s.len += insCostAt(I, s, v, pos);
    s.tour.insert(s.tour.begin() + pos, v);
    s.in[v] = 1; s.prize += I.p[v];
    for (int c : I.nodeCl[v]) if (s.ccount[c]++ == 0) s.uncovered--;
}

inline void insertBest(const Inst& I, Sol& s, int v) {
    auto [c, pos] = bestInsertion(I, s, v);
    insertAt(I, s, v, pos);
}

// Ganho (redução de comprimento) ao remover o nó na posição idx.
inline double removalGain(const Inst& I, const Sol& s, int idx) {
    int m = s.m();
    if (m <= 1) return s.len;
    if (m == 2) return s.len;
    int a = s.tour[prv(s, idx)], v = s.tour[idx], b = s.tour[nxt(s, idx)];
    return I.d(a, v) + I.d(v, b) - I.d(a, b);
}

inline void removeAt(const Inst& I, Sol& s, int idx) {
    int v = s.tour[idx];
    s.len -= removalGain(I, s, idx);
    if (s.m() <= 2) s.len = 0;
    s.tour.erase(s.tour.begin() + idx);
    s.in[v] = 0; s.prize -= I.p[v];
    for (int c : I.nodeCl[v]) if (--s.ccount[c] == 0) s.uncovered++;
    if (s.m() == 1) s.len = 0;
}

inline int indexOf(const Sol& s, int v) {
    for (int i = 0; i < s.m(); i++) if (s.tour[i] == v) return i;
    return -1;
}

// v pode sair sem descobrir algum cluster? (opcionalmente considerando que w entra)
inline bool removable(const Inst& I, const Sol& s, int v, int w = -1) {
    for (int c : I.nodeCl[v]) {
        if (s.ccount[c] > 1) continue;
        bool wc = false;
        if (w >= 0) for (int c2 : I.nodeCl[w]) if (c2 == c) { wc = true; break; }
        if (!wc) return false;
    }
    return true;
}

// Verificação independente da solução (usada antes de reportar resultados).
inline bool verify(const Inst& I, const Sol& s, string* why = nullptr) {
    vector<char> seen(I.n, 0);
    for (int v : s.tour) {
        if (v < 0 || v >= I.n || seen[v]) { if (why) *why = "no repetido/invalido"; return false; }
        seen[v] = 1;
    }
    for (int k = 0; k < I.K; k++) {
        bool ok = false;
        for (int v : I.clusters[k]) if (seen[v]) { ok = true; break; }
        if (!ok) { if (why) *why = "cluster descoberto"; return false; }
    }
    if (tourLength(I, s.tour) > I.B + 1e-6) { if (why) *why = "orcamento excedido"; return false; }
    return true;
}
