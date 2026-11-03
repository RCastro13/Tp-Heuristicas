// AGITA(T, k): remove k vértices sorteados, insere k vértices de fora sorteados e aplica
// REPARA proibindo os removidos, o que força a troca do representante de um cluster descoberto.
#pragma once
#include "construcao.hpp"

inline bool agita(const Inst& I, Sol& s, int k, RNG& g) {
    vector<char> X(I.n, 0);
    vector<int> fora;
    for (int v = 0; v < I.n; v++) if (!s.dentro[v]) fora.push_back(v);
    for (int q = 0; q < k && s.m() > 0; q++) {
        int idx = sorteia(g, 0, s.m() - 1);
        X[s.rota[idx]] = 1;
        removeEm(I, s, idx);
    }
    shuffle(fora.begin(), fora.end(), g);
    for (int q = 0; q < k && q < (int)fora.size(); q++) insereMelhor(I, s, fora[q]);
    return repara(I, s, &X);
}
