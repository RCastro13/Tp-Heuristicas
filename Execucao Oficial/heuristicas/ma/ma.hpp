// MA (Algoritmo 5) [Moscato, 1989]: população de 10 soluções (INICIAL e 9 de GRASP, REPARA e
// BL), cruzamento por tour gigante, mutação AGITA(F, 2) com prob. 0,2 e BL em cada filho.
#pragma once
#include "../../codigo_geral/executor.hpp"

inline void executaMA(Executor& R) {
    const Inst& I = R.I;
    vector<Sol> pop;
    Sol T;
    if (solucaoInicial(I, T)) { pop.push_back(T); R.considera(T); }
    while ((int)pop.size() < 10 && !tempoEsgotado()) {
        T = grasp(I, R.g);
        if (!repara(I, T)) continue;
        buscaLocal(I, T);
        if (!T.viavel(I)) continue;
        pop.push_back(T);
        R.considera(T);
    }
    if (pop.empty()) return;
    auto torneio = [&]() {
        int a = sorteia(R.g, 0, (int)pop.size() - 1), b = sorteia(R.g, 0, (int)pop.size() - 1);
        return melhor(pop[a], pop[b]) ? a : b;
    };
    while (!tempoEsgotado()) {
        const Sol& P1 = pop[torneio()];
        const Sol& P2 = pop[torneio()];
        // Filho: trecho contíguo de 30% a 70% de P1 seguido dos vértices de P2 que ainda não
        // tem, na ordem de P2.
        Sol F; F.inicia(I);
        int m1 = P1.m();
        int tam = max(1, (int)lround(m1 * sorteiaReal(R.g, 0.3, 0.7)));
        int ini = sorteia(R.g, 0, m1 - 1);
        vector<char> usado(I.n, 0);
        for (int q = 0; q < tam; q++) { int v = P1.rota[(ini + q) % m1]; F.rota.push_back(v); usado[v] = 1; }
        for (int v : P2.rota) if (!usado[v]) F.rota.push_back(v);
        recalcula(I, F);
        otimizaRota(I, F);
        bool ok = repara(I, F);
        if (ok && sorteiaReal(R.g) < 0.2) ok = agita(I, F, 2, R.g);
        if (ok) buscaLocal(I, F);
        R.iter++;
        if (!ok || !F.viavel(I)) continue;
        int pior = 0;
        for (int i = 1; i < (int)pop.size(); i++) if (melhor(pop[pior], pop[i])) pior = i;
        if (!melhor(F, pop[pior])) continue;
        bool inedito = true;
        for (auto& x : pop) if (x.dentro == F.dentro) { inedito = false; break; }
        if (!inedito) continue;
        pop[pior] = F;
        R.considera(F);
    }
}
