// ILS (Algoritmo 3) [Lourenço et al., 2003]: seguindo Vansteenwegen et al. (2009), a
// perturbação remove m vértices consecutivos a partir de uma posição sorteada e aplica
// REPARA proibindo-os; toda solução viável substitui a corrente (passeio aleatório).
#pragma once
#include "../../codigo_geral/executor.hpp"

// Remove m vértices consecutivos a partir de uma posição sorteada e marca-os em X.
inline void removeConsecutivos(const Inst& I, Sol& T, int m, RNG& g, vector<char>& X) {
    int ini = sorteia(g, 0, T.m() - 1);
    m = min(m, T.m());
    for (int q = 0; q < m; q++) {
        int idx = ini % T.m();
        X[T.rota[idx]] = 1;
        removeEm(I, T, idx);
    }
}

// Laço do Algoritmo 3, comum ao ILS e ao ILS-C: só a perturbação (linha 4) muda.
template <class Perturba>
inline void lacoILS(Executor& R, Perturba perturba) {
    const Inst& I = R.I;
    Sol T;
    if (!partida(R, T)) return;
    Sol Tb = T;
    int m = 1;
    long long f = 0;
    vector<char> X(I.n);
    while (!tempoEsgotado()) {
        Sol T2 = T;
        fill(X.begin(), X.end(), 0);
        perturba(T2, m, X);
        bool ok = repara(I, T2, &X);
        if (ok) buscaLocal(I, T2);
        ok = ok && T2.viavel(I);
        R.iter++;
        if (ok && melhor(T2, Tb)) {
            Tb = T = T2;
            R.considera(Tb);
            m = 1; f = 0;
        } else {
            if (ok) T = T2;
            m++;
            if (m > T.m() / 3) m = 1;
            f++;
            if (f % 100 == 0) T = Tb;
        }
    }
}

inline void executaILS(Executor& R) {
    const Inst& I = R.I;
    lacoILS(R, [&](Sol& T, int m, vector<char>& X) { removeConsecutivos(I, T, m, R.g, X); });
}
