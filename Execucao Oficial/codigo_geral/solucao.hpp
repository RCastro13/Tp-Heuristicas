// Solução T: sequência cíclica de vértices distintos, com L(T), P(T) e cobertura dos clusters.
#pragma once
#include "instancia.hpp"

constexpr double EPS = 1e-7;        // tolerância numérica de comparação
constexpr double TOL_B = 1e-6;      // tolerância do orçamento
constexpr double EPS_RAZAO = 1e-6;  // epsilon das razões rho+ e rho- (Seção 3.1)

struct Sol {
    vector<int> rota;
    vector<char> dentro;
    vector<int> cob;      // nº de vértices visitados de cada cluster
    int descobertos = 0;
    double L = 0, P = 0;

    void inicia(const Inst& I) {
        rota.clear(); dentro.assign(I.n, 0); cob.assign(I.K, 0);
        descobertos = I.K; L = 0; P = 0;
    }
    int m() const { return (int)rota.size(); }
    // Viável: cobre todos os clusters, cabe em B e é um ciclo (ao menos três vértices).
    bool viavel(const Inst& I) const { return descobertos == 0 && L <= I.B + TOL_B && m() >= 3; }
};

inline double comprimento(const Inst& I, const vector<int>& t) {
    if (t.size() < 2) return 0;
    double L = 0;
    for (size_t i = 0; i < t.size(); i++) L += I.d(t[i], t[i + 1 == t.size() ? 0 : i + 1]);
    return L;
}

// Reconstrói todos os campos a partir de s.rota (e reavalia com as distâncias de I).
inline void recalcula(const Inst& I, Sol& s) {
    vector<int> t = s.rota;
    s.inicia(I);
    s.rota = t;
    for (int v : t) {
        s.dentro[v] = 1; s.P += I.p[v];
        for (int c : I.cl[v]) if (s.cob[c]++ == 0) s.descobertos--;
    }
    s.L = comprimento(I, t);
}

// T é melhor que outra se tem maior prêmio ou, em caso de empate, menor comprimento.
inline bool melhor(const Sol& a, const Sol& b) {
    if (a.P > b.P + EPS) return true;
    if (a.P < b.P - EPS) return false;
    return a.L < b.L - EPS;
}

// delta+(v) na posição pos: inserção entre rota[pos-1] e rota[pos].
inline double deltaMaisEm(const Inst& I, const Sol& s, int v, int pos) {
    int m = s.m();
    if (m == 0) return 0;
    int a = s.rota[(pos - 1 + m) % m], b = s.rota[pos % m];
    return I.d(a, v) + I.d(v, b) - I.d(a, b);
}

// delta+(v) = min_(a,b) (d_av + d_vb - d_ab). Retorna {delta+, posição}.
inline pair<double, int> melhorInsercao(const Inst& I, const Sol& s, int v) {
    int m = s.m();
    if (m == 0) return {0, 0};
    double c = 1e300; int bp = 0;
    for (int i = 0; i < m; i++) {
        int a = s.rota[i], b = s.rota[i + 1 == m ? 0 : i + 1];
        double x = I.d(a, v) + I.d(v, b) - I.d(a, b);
        if (x < c) { c = x; bp = i + 1; }
    }
    return {c, bp};
}

inline void insereEm(const Inst& I, Sol& s, int v, int pos) {
    s.L += deltaMaisEm(I, s, v, pos);
    s.rota.insert(s.rota.begin() + pos, v);
    s.dentro[v] = 1; s.P += I.p[v];
    for (int c : I.cl[v]) if (s.cob[c]++ == 0) s.descobertos--;
}

inline void insereMelhor(const Inst& I, Sol& s, int v) { insereEm(I, s, v, melhorInsercao(I, s, v).second); }

// delta-(v) = d_av + d_vb - d_ab: redução exata ao retirar a posição idx (pode ser negativa).
inline double deltaMenos(const Inst& I, const Sol& s, int idx) {
    int m = s.m();
    if (m <= 1) return 0;
    int a = s.rota[idx == 0 ? m - 1 : idx - 1], v = s.rota[idx], b = s.rota[idx + 1 == m ? 0 : idx + 1];
    return I.d(a, v) + I.d(v, b) - I.d(a, b);
}

inline void removeEm(const Inst& I, Sol& s, int idx) {
    int v = s.rota[idx];
    s.L -= deltaMenos(I, s, idx);
    s.rota.erase(s.rota.begin() + idx);
    s.dentro[v] = 0; s.P -= I.p[v];
    for (int c : I.cl[v]) if (--s.cob[c] == 0) s.descobertos++;
    if (s.m() <= 1) s.L = 0;
}

inline int indiceDe(const Sol& s, int v) {
    for (int i = 0; i < s.m(); i++) if (s.rota[i] == v) return i;
    return -1;
}

// v é removível se todo cluster que o contém tem outro vértice em T
// (opcionalmente considerando que w entra no lugar de v).
inline bool removivel(const Inst& I, const Sol& s, int v, int w = -1) {
    for (int c : I.cl[v]) {
        if (s.cob[c] > 1) continue;
        bool cobre = false;
        if (w >= 0) for (int c2 : I.cl[w]) if (c2 == c) { cobre = true; break; }
        if (!cobre) return false;
    }
    return true;
}

// Razões da Seção 3.1, com epsilon para os casos sem desigualdade triangular.
inline double rhoMais(double p, double dMais) { return p / max(dMais, EPS_RAZAO); }
inline double rhoMenos(double p, double dMenos) { return dMenos / max(p, EPS_RAZAO); }

// Verificador independente, aplicado antes de reportar qualquer resultado.
inline bool verifica(const Inst& I, const vector<int>& t, string* porque = nullptr) {
    vector<char> visto(I.n, 0);
    if (t.size() < 3) { if (porque) *porque = "menos de tres vertices"; return false; }
    for (int v : t) {
        if (v < 0 || v >= I.n || visto[v]) { if (porque) *porque = "vertice repetido/invalido"; return false; }
        visto[v] = 1;
    }
    for (int k = 0; k < I.K; k++) {
        bool ok = false;
        for (int v : I.clusters[k]) if (visto[v]) { ok = true; break; }
        if (!ok) { if (porque) *porque = "cluster descoberto"; return false; }
    }
    if (comprimento(I, t) > I.B + TOL_B) { if (porque) *porque = "orcamento excedido"; return false; }
    return true;
}
