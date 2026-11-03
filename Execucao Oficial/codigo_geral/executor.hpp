// Registro comum a todas as heurísticas: melhor solução, tempo até ela, iterações do laço
// principal e tempo acumulado da fase de melhoria (medidas de H1 e H2).
#pragma once
#include "perturbacao.hpp"

struct Executor {
    const Inst& I;
    RNG g;
    Sol best;
    bool tem = false;
    double tBest = 0;
    long long iter = 0;
    long long nMelhoria = 0;
    double tMelhoria = 0;
    map<string, double> extras;

    Executor(const Inst& I_, unsigned semente) : I(I_), g(semente) { best.inicia(I); }

    void considera(const Sol& s) {
        if (!s.viavel(I)) return;
        if (!tem || melhor(s, best)) { best = s; tem = true; tBest = relogio().decorrido(); }
    }
};

// Ponto de partida dos métodos de trajetória. Se INICIAL não for viável em nenhuma das três
// construções, recorre a GRASP + REPARA + BL até obter solução viável (ou esgotar o tempo).
inline bool partida(Executor& R, Sol& T) {
    const Inst& I = R.I;
    if (solucaoInicial(I, T)) { R.considera(T); return true; }
    while (!tempoEsgotado()) {
        T = grasp(I, R.g);
        if (repara(I, T)) {
            buscaLocal(I, T);
            if (T.viavel(I)) { R.considera(T); return true; }
        }
    }
    return false;
}
