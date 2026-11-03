// ILS-C (usado apenas na H4): idêntico ao ILS, exceto que, com probabilidade 0,5, a perturbação
// remove os vértices de ceil(m/2) clusters sorteados em vez de vértices consecutivos, forçando
// a troca de representantes em qualquer região da rota.
#pragma once
#include "../ils/ils.hpp"

inline void executaILSC(Executor& R) {
    const Inst& I = R.I;
    vector<int> ordem(I.K);
    iota(ordem.begin(), ordem.end(), 0);
    lacoILS(R, [&](Sol& T, int m, vector<char>& X) {
        if (sorteiaReal(R.g) >= 0.5) { removeConsecutivos(I, T, m, R.g, X); return; }
        shuffle(ordem.begin(), ordem.end(), R.g);
        int q = min((m + 1) / 2, I.K);
        for (int i = 0; i < q; i++)
            for (int v : I.clusters[ordem[i]])
                if (T.dentro[v]) {
                    X[v] = 1;
                    removeEm(I, T, indiceDe(T, v));
                }
    });
}
