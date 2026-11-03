// Comprimentos de referência do orçamento B = alpha*TSP + (1-alpha)*GTSP. As distâncias dos
// arquivos dos autores não são as arredondadas da TSPLIB, então TSP e GTSP são calculados
// sobre elas por ILS (melhor conhecido); toda rota obtida é um limitante superior válido,
// o que garante B >= GTSP ótimo e, portanto, a viabilidade.
#pragma once
#include "construcao.hpp"

// ILS para o TSP: 2-opt e Or-opt com listas de vizinhos e bits "não olhe", e perturbação por
// double-bridge local [Martin, Otto & Felten, 1991].
struct TSPRapido {
    const Inst& I;
    int n;
    vector<int> t, pos;
    vector<vector<int>> viz;
    vector<char> sujo;
    vector<int> fila;

    explicit TSPRapido(const Inst& I_) : I(I_), n(I_.n), t(n), pos(n), viz(n), sujo(n, 0) {
        int kv = min(10, n - 1);
        for (int i = 0; i < n; i++) {
            vector<int> o;
            for (int j = 0; j < n; j++) if (j != i) o.push_back(j);
            partial_sort(o.begin(), o.begin() + kv, o.end(), [&](int a, int b) { return I.d(i, a) < I.d(i, b); });
            viz[i].assign(o.begin(), o.begin() + kv);
        }
    }
    int suc(int v) const { return t[pos[v] + 1 == n ? 0 : pos[v] + 1]; }
    int pre(int v) const { return t[pos[v] == 0 ? n - 1 : pos[v] - 1]; }
    void marca(int v) { if (!sujo[v]) { sujo[v] = 1; fila.push_back(v); } }
    double comp() const { return comprimento(I, t); }

    // Inverte o trecho cíclico de i a j (posições), pelo lado mais curto.
    void inverte(int i, int j) {
        int tam = j - i; if (tam < 0) tam += n; tam++;
        if (tam * 2 > n) { int a = i; i = j + 1 == n ? 0 : j + 1; j = a == 0 ? n - 1 : a - 1; tam = n - tam; }
        for (int q = 0; q < tam / 2; q++) {
            int a = i + q; if (a >= n) a -= n;
            int b = j - q; if (b < 0) b += n;
            swap(t[a], t[b]); pos[t[a]] = a; pos[t[b]] = b;
        }
    }

    bool melhora(int a) {
        for (int dir = 0; dir < 2; dir++) {
            int b = dir == 0 ? suc(a) : pre(a);
            double dab = I.d(a, b);
            for (int c : viz[a]) {
                double g = dab - I.d(a, c);
                if (g <= EPS) break;
                int e = dir == 0 ? suc(c) : pre(c);
                if (c == b || e == a) continue;
                double delta = I.d(b, e) - I.d(c, e) - g;
                if (delta < -EPS) {
                    if (dir == 0) inverte(pos[b], pos[c]); else inverte(pos[c], pos[b]);
                    marca(a); marca(b); marca(c); marca(e);
                    return true;
                }
            }
        }
        // Or-opt: segmentos de 1 a 3 vértices iniciados em a, realocados junto a um vizinho.
        for (int T = 1; T <= 3 && T + 2 < n; T++) {
            int pa = pre(a), z = a;
            for (int q = 1; q < T; q++) z = suc(z);
            int nz = suc(z);
            double ganho = I.d(pa, a) + I.d(z, nz) - I.d(pa, nz);
            if (ganho <= EPS) continue;
            for (int ext = 0; ext < 2; ext++) {
                int x = ext == 0 ? a : z, y = ext == 0 ? z : a;
                for (int c : viz[x]) {
                    if (I.d(x, c) >= ganho) break;
                    int off = pos[c] - pos[a]; if (off < 0) off += n;
                    if (off < T) continue;
                    for (int lado = 0; lado < 2; lado++) {
                        int e = lado == 0 ? suc(c) : pre(c);
                        int oe = pos[e] - pos[a]; if (oe < 0) oe += n;
                        if (oe < T) continue;
                        double custo = I.d(c, x) + I.d(y, e) - I.d(c, e);
                        if (custo < ganho - EPS) {
                            vector<int> seg, novo;
                            for (int q = 0, v = a; q < T; q++, v = suc(v)) seg.push_back(v);
                            // o segmento entra entre c e e, com x adjacente a c
                            if (lado == 1) { if (ext == 0) reverse(seg.begin(), seg.end()); }
                            else if (ext == 1) reverse(seg.begin(), seg.end());
                            int ini = lado == 0 ? c : e;
                            for (int q = 0, v = suc(z); q < n - T; q++, v = suc(v)) {
                                novo.push_back(v);
                                if (v == ini) novo.insert(novo.end(), seg.begin(), seg.end());
                            }
                            t = novo;
                            for (int q = 0; q < n; q++) pos[t[q]] = q;
                            marca(pa); marca(nz); marca(a); marca(z); marca(c); marca(e);
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }

    void buscaFila() {
        while (!fila.empty()) {
            int v = fila.back(); fila.pop_back(); sujo[v] = 0;
            while (melhora(v)) {}
        }
    }

    double resolve(double seg, RNG& g) {
        Sol s0; s0.inicia(I);
        vector<char> usado(n, 0);
        int c = 0; t[0] = 0; usado[0] = 1;
        for (int i = 1; i < n; i++) {
            int b = -1;
            for (int j = 0; j < n; j++) if (!usado[j] && (b < 0 || I.d(c, j) < I.d(c, b))) b = j;
            t[i] = b; usado[b] = 1; c = b;
        }
        for (int i = 0; i < n; i++) pos[t[i]] = i;
        for (int v = 0; v < n; v++) marca(v);
        buscaFila();
        double atual = comp();
        vector<int> copia;
        auto t0 = chrono::steady_clock::now();
        int L = min(50, n / 4);
        while (L >= 1 && chrono::duration<double>(chrono::steady_clock::now() - t0).count() < seg) {
            copia = t;
            int p = sorteia(g, 0, n - 1), l1 = sorteia(g, 1, L), l2 = sorteia(g, 1, L);
            vector<int> viz4;
            auto at = [&](int q) { return t[(p + q) % n]; };
            viz4 = {at(0), at(1), at(l1), at(l1 + 1), at(l1 + l2), at(l1 + l2 + 1)};
            vector<int> bl;  // troca os dois blocos consecutivos
            for (int q = l1 + 1; q <= l1 + l2; q++) bl.push_back(at(q));
            for (int q = 1; q <= l1; q++) bl.push_back(at(q));
            for (int q = 1; q <= l1 + l2; q++) { int x = (p + q) % n; t[x] = bl[q - 1]; pos[t[x]] = x; }
            for (int v : viz4) marca(v);
            buscaFila();
            double novo = comp();
            if (novo < atual - EPS) atual = novo;
            else { t = copia; for (int q = 0; q < n; q++) pos[t[q]] = q; }
        }
        return atual;
    }
};

// Dado o ciclo de clusters, escolhe o melhor representante de cada um por programação
// dinâmica em camadas, a partir do menor cluster (otimização de clusters de Fischetti et al.).
inline double otimizaRepresentantes(const Inst& I, vector<int>& rota) {
    int K = rota.size();
    vector<int> ordem(K);
    int ini = 0;
    for (int q = 0; q < K; q++)
        if (I.clusters[I.cl[rota[q]][0]].size() < I.clusters[I.cl[rota[ini]][0]].size()) ini = q;
    for (int q = 0; q < K; q++) ordem[q] = I.cl[rota[(ini + q) % K]][0];
    double melhorC = 1e300;
    vector<int> melhorR;
    for (int v0 : I.clusters[ordem[0]]) {
        vector<vector<double>> f(K);
        vector<vector<int>> par(K);
        f[0] = {0.0}; par[0] = {-1};
        vector<int> antes = {v0};
        for (int q = 1; q < K; q++) {
            const auto& C = I.clusters[ordem[q]];
            f[q].assign(C.size(), 1e300); par[q].assign(C.size(), -1);
            for (size_t j = 0; j < C.size(); j++)
                for (size_t i = 0; i < antes.size(); i++) {
                    double x = f[q - 1][i] + I.d(antes[i], C[j]);
                    if (x < f[q][j]) { f[q][j] = x; par[q][j] = i; }
                }
            antes = C;
        }
        double bx = 1e300; int bj = -1;
        for (size_t j = 0; j < antes.size(); j++) {
            double x = f[K - 1][j] + I.d(antes[j], v0);
            if (x < bx) { bx = x; bj = j; }
        }
        if (bx < melhorC) {
            melhorC = bx;
            melhorR.assign(K, -1);
            int j = bj;
            for (int q = K - 1; q >= 1; q--) { melhorR[q] = I.clusters[ordem[q]][j]; j = par[q][j]; }
            melhorR[0] = v0;
        }
    }
    rota = melhorR;
    return melhorC;
}

// ILS para o GTSP: alterna ordem (2-opt/Or-opt), representantes (programação dinâmica) e
// reinserção de cada cluster na sua melhor posição, com perturbação por double-bridge.
inline double resolveGTSP(const Inst& I, double seg, RNG& g) {
    Sol s = insercaoGTSP(I, true, inicioPadrao(I));
    auto refina = [&](Sol& x) {
        for (;;) {
            double L0 = x.L;
            otimizaRota(I, x);
            otimizaRepresentantes(I, x.rota);
            recalcula(I, x);
            for (int q = 0; q < I.K; q++) {  // reinserção de cluster
                int u = x.rota[q];
                int k = I.cl[u][0];
                Sol y = x;
                removeEm(I, y, q);
                double bc = 1e300; int bv = -1, bp = 0;
                for (int v : I.clusters[k]) {
                    auto [c, pos] = melhorInsercao(I, y, v);
                    if (c < bc) { bc = c; bv = v; bp = pos; }
                }
                insereEm(I, y, bv, bp);
                if (y.L < x.L - EPS) x = y;
            }
            if (x.L >= L0 - EPS) break;
        }
    };
    refina(s);
    Sol melhorS = s;
    auto t0 = chrono::steady_clock::now();
    int K = I.K;
    while (K >= 4 && chrono::duration<double>(chrono::steady_clock::now() - t0).count() < seg) {
        Sol y = melhorS;
        vector<int> c = {sorteia(g, 1, K - 1), sorteia(g, 1, K - 1), sorteia(g, 1, K - 1)};
        sort(c.begin(), c.end());
        vector<int> r;
        r.insert(r.end(), y.rota.begin(), y.rota.begin() + c[0]);
        r.insert(r.end(), y.rota.begin() + c[1], y.rota.begin() + c[2]);
        r.insert(r.end(), y.rota.begin() + c[0], y.rota.begin() + c[1]);
        r.insert(r.end(), y.rota.begin() + c[2], y.rota.end());
        y.rota = r;
        recalcula(I, y);
        refina(y);
        if (y.L < melhorS.L - EPS) melhorS = y;
    }
    return melhorS.L;
}
