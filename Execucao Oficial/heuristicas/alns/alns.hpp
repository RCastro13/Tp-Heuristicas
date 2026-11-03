// ALNS (Algoritmo 4) [Ropke & Pisinger, 2006]: destrói uma fração q em [0,10; 0,40] da rota e a
// reconstrói com operadores escolhidos por roleta. Os removidos formam o conjunto proibido X.
#pragma once
#include "../../codigo_geral/executor.hpp"

// ---------------------------------------------------------------- destruição
inline void removeMarcando(const Inst& I, Sol& T, int idx, vector<char>& X) {
    X[T.rota[idx]] = 1;
    removeEm(I, T, idx);
}

inline void destroiAleatorio(const Inst& I, Sol& T, int q, RNG& g, vector<char>& X) {
    for (int i = 0; i < q && T.m() > 0; i++) removeMarcando(I, T, sorteia(g, 0, T.m() - 1), X);
}

// Pior razão: maior rho-, reavaliada a cada remoção.
inline void destroiPior(const Inst& I, Sol& T, int q, vector<char>& X) {
    for (int i = 0; i < q && T.m() > 0; i++) {
        int bi = 0; double br = -1e300;
        for (int idx = 0; idx < T.m(); idx++) {
            double r = rhoMenos(I.p[T.rota[idx]], deltaMenos(I, T, idx));
            if (r > br) { br = r; bi = idx; }
        }
        removeMarcando(I, T, bi, X);
    }
}

inline void destroiSegmento(const Inst& I, Sol& T, int q, RNG& g, vector<char>& X) {
    int ini = sorteia(g, 0, T.m() - 1);
    for (int i = 0; i < q && T.m() > 0; i++) removeMarcando(I, T, ini % T.m(), X);
}

// Radial: os mais próximos de um vértice sorteado da rota (incluindo ele).
inline void destroiRadial(const Inst& I, Sol& T, int q, RNG& g, vector<char>& X) {
    int c = T.rota[sorteia(g, 0, T.m() - 1)];
    vector<pair<double, int>> o;
    for (int v : T.rota) o.push_back({I.d(c, v), v});
    sort(o.begin(), o.end());
    for (int i = 0; i < q && i < (int)o.size(); i++) removeMarcando(I, T, indiceDe(T, o[i].second), X);
}

// Cluster (específico do GCOP): remove os vértices de clusters sorteados até atingir q.
inline void destroiCluster(const Inst& I, Sol& T, int q, RNG& g, vector<char>& X) {
    vector<int> ordem(I.K);
    iota(ordem.begin(), ordem.end(), 0);
    shuffle(ordem.begin(), ordem.end(), g);
    int removidos = 0;
    for (int k : ordem) {
        if (removidos >= q) break;
        for (int v : I.clusters[k])
            if (T.dentro[v]) {
                removeMarcando(I, T, indiceDe(T, v), X);
                removidos++;
            }
    }
}

// ---------------------------------------------------------------- reconstrução
// Regret: cobre primeiro o cluster com maior diferença entre suas duas inserções mais baratas.
inline bool cobreRegret(const Inst& I, Sol& T, const vector<char>& X) {
    while (T.descobertos > 0) {
        double bReg = -1; int bv = -1, bp = 0;
        for (int k = 0; k < I.K; k++) {
            if (T.cob[k] > 0) continue;
            double c1 = 1e300, c2 = 1e300; int v1 = -1, p1 = 0;
            for (int v : I.clusters[k]) {
                if (X[v]) continue;
                auto [c, pos] = melhorInsercao(I, T, v);
                if (c < c1) { c2 = c1; c1 = c; v1 = v; p1 = pos; }
                else if (c < c2) c2 = c;
            }
            if (v1 < 0) return false;
            double reg = c2 >= 1e299 ? 1e290 : c2 - c1;
            if (reg > bReg) { bReg = reg; bv = v1; bp = p1; }
        }
        insereEm(I, T, bv, bp);
    }
    return true;
}

inline void executaALNS(Executor& R) {
    const Inst& I = R.I;
    Sol T;
    if (!partida(R, T)) return;
    Sol Tb = T;
    const int ND = 5, NR = 3;
    const char* nomesD[ND] = {"aleatorio", "pior", "segmento", "radial", "cluster"};
    const char* nomesR[NR] = {"guloso", "regret", "ruidoso"};
    vector<double> pD(ND, 1), pR(NR, 1), piD(ND, 0), piR(NR, 0), thD(ND, 0), thR(NR, 0);
    double tau0 = 0.05 * T.P / log(2.0);
    double limite = relogio().limite;
    auto roleta = [&](const vector<double>& w) {
        double r = sorteiaReal(R.g) * accumulate(w.begin(), w.end(), 0.0);
        for (size_t i = 0; i < w.size(); i++) { r -= w[i]; if (r <= 0) return (int)i; }
        return (int)w.size() - 1;
    };
    vector<char> X(I.n);
    vector<double> fator(I.n);
    while (!tempoEsgotado()) {
        int d = roleta(pD), r = roleta(pR);
        double frac = sorteiaReal(R.g, 0.10, 0.40);
        Sol T2 = T;
        fill(X.begin(), X.end(), 0);
        int q = max(1, (int)lround(frac * T2.m()));
        if (d == 0) destroiAleatorio(I, T2, q, R.g, X);
        else if (d == 1) destroiPior(I, T2, q, X);
        else if (d == 2) destroiSegmento(I, T2, q, R.g, X);
        else if (d == 3) destroiRadial(I, T2, q, R.g, X);
        else destroiCluster(I, T2, q, R.g, X);

        bool ok;
        if (r == 0) {
            ok = cobreClusters(I, T2, &X);
            if (ok) insereRazao(I, T2, &X);
        } else if (r == 1) {
            ok = cobreRegret(I, T2, X);
            if (ok) insereRazao(I, T2, &X);
        } else {
            for (int v = 0; v < I.n; v++) fator[v] = sorteiaReal(R.g, 0.8, 1.2);
            ok = cobreClusters(I, T2, &X, &fator);
            if (ok) insereRazao(I, T2, &X, &fator);
        }
        ok = ok && repara(I, T2, &X);
        if (ok) otimizaRota(I, T2);
        ok = ok && T2.viavel(I);

        double tau = max(tau0 * (1 - relogio().decorrido() / limite), 1e-6);
        double U = sorteiaReal(R.g);
        double ponto = 0;
        R.iter++;
        if (ok) {
            if (melhor(T2, Tb)) {
                buscaLocal(I, T2);
                Tb = T = T2;
                R.considera(Tb);
                ponto = 33;
            } else if (melhor(T2, T)) {
                T = T2;
                ponto = 9;
            } else if (T2.P < T.P - EPS) {
                if (U < exp((T2.P - T.P) / tau)) { T = T2; ponto = 13; }
            } else if (T2.L <= T.L + EPS) {
                T = T2;  // mesmo prêmio e não mais longa
            }
        }
        piD[d] += ponto; thD[d]++;
        piR[r] += ponto; thR[r]++;
        if (R.iter % 100 == 0) {
            for (int i = 0; i < ND; i++) if (thD[i] > 0) { pD[i] = 0.9 * pD[i] + 0.1 * piD[i] / thD[i]; piD[i] = thD[i] = 0; }
            for (int i = 0; i < NR; i++) if (thR[i] > 0) { pR[i] = 0.9 * pR[i] + 0.1 * piR[i] / thR[i]; piR[i] = thR[i] = 0; }
        }
    }
    for (int i = 0; i < ND; i++) R.extras[string("peso_") + nomesD[i]] = pD[i];
    for (int i = 0; i < NR; i++) R.extras[string("peso_") + nomesR[i]] = pR[i];
}
