// VNS (Algoritmo 2) [Mladenovic & Hansen, 1997]: vizinhanças N_1..N_6, em que N_k é AGITA(T, k).
#pragma once
#include "../../codigo_geral/executor.hpp"

inline void executaVNS(Executor& R) {
    const Inst& I = R.I;
    Sol T;
    if (!partida(R, T)) return;
    int k = 1;
    while (!tempoEsgotado()) {
        Sol T2 = T;
        bool ok = agita(I, T2, k, R.g);
        if (ok) buscaLocal(I, T2);
        R.iter++;
        if (ok && T2.viavel(I) && melhor(T2, T)) {
            T = T2;
            R.considera(T);
            k = 1;
        } else {
            k = k % 6 + 1;
        }
    }
}
