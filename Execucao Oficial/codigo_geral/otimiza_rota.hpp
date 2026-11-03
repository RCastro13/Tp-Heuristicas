// OTIMIZAROTA: 2-opt [Croes, 1958] e Or-opt [Or, 1976] com primeira melhora; encurta a rota
// sem alterar os vértices visitados, liberando orçamento.
#pragma once
#include "relogio.hpp"
#include "solucao.hpp"

inline bool doisOpt(const Inst& I, Sol& s) {
    int m = s.m();
    if (m < 4) return false;
    bool algum = false, melhorou = true;
    while (melhorou && !tempoEsgotado()) {
        melhorou = false;
        for (int i = 0; i < m - 2; i++) {
            int a = s.rota[i], b = s.rota[i + 1];
            double dab = I.d(a, b);
            for (int j = i + 2; j < m; j++) {
                if (i == 0 && j == m - 1) continue;
                int c = s.rota[j], e = s.rota[j + 1 == m ? 0 : j + 1];
                double delta = I.d(a, c) + I.d(b, e) - dab - I.d(c, e);
                if (delta < -EPS) {
                    reverse(s.rota.begin() + i + 1, s.rota.begin() + j + 1);
                    s.L += delta;
                    melhorou = algum = true;
                    b = s.rota[i + 1]; dab = I.d(a, b);
                }
            }
        }
    }
    return algum;
}

// Realoca segmentos de 1 a 3 vértices consecutivos, com ou sem inversão.
inline bool orOpt(const Inst& I, Sol& s) {
    int m = s.m();
    if (m < 5) return false;
    bool algum = false;
    for (int T = 1; T <= 3; T++) {
        for (int ini = 0; ini + T <= m; ini++) {
            int a = s.rota[ini], b = s.rota[ini + T - 1];
            int ant = s.rota[(ini - 1 + m) % m], prox = s.rota[(ini + T) % m];
            double ganho = I.d(ant, a) + I.d(b, prox) - I.d(ant, prox);
            if (ganho <= EPS) continue;
            for (int k = 0; k < m; k++) {
                if (k >= ini - 1 && k <= ini + T - 1) continue;  // aresta toca o segmento
                if (ini == 0 && k == m - 1) continue;
                int c = s.rota[k], e = s.rota[k + 1 == m ? 0 : k + 1];
                double dce = I.d(c, e);
                double c1 = I.d(c, a) + I.d(b, e) - dce;
                double c2 = I.d(c, b) + I.d(a, e) - dce;
                bool inv = c2 < c1;
                double custo = inv ? c2 : c1;
                if (custo < ganho - EPS) {  // primeira melhora
                    vector<int> seg(s.rota.begin() + ini, s.rota.begin() + ini + T);
                    if (inv) reverse(seg.begin(), seg.end());
                    s.rota.erase(s.rota.begin() + ini, s.rota.begin() + ini + T);
                    int ci = indiceDe(s, c);
                    s.rota.insert(s.rota.begin() + ci + 1, seg.begin(), seg.end());
                    s.L += custo - ganho;
                    algum = true;
                    break;
                }
            }
        }
    }
    return algum;
}

inline void otimizaRota(const Inst& I, Sol& s) {
    for (;;) {
        bool a = doisOpt(I, s);
        bool b = orOpt(I, s);
        if ((!a && !b) || tempoEsgotado()) break;
    }
    s.L = comprimento(I, s.rota);  // elimina erro numérico acumulado
}
