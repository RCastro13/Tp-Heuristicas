// REPARA(T, X): torna a solução viável sem usar os vértices do conjunto proibido X.
#pragma once
#include "busca_local.hpp"

inline bool emX(const vector<char>* X, int v) { return X && (*X)[v]; }

// Cobre cada cluster descoberto com o vértice de menor delta+ fora de X (com fator, delta+
// é multiplicado por fator[v] na escolha). Retorna false se um cluster não puder ser coberto.
inline bool cobreClusters(const Inst& I, Sol& s, const vector<char>* X = nullptr, const vector<double>* fator = nullptr) {
    while (s.descobertos > 0) {
        double bc = 1e300; int bv = -1, bp = 0;
        for (int k = 0; k < I.K; k++) {
            if (s.cob[k] > 0) continue;
            bool tem = false;
            for (int v : I.clusters[k]) {
                if (emX(X, v)) continue;
                tem = true;
                auto [c, pos] = melhorInsercao(I, s, v);
                if (fator) c *= (*fator)[v];
                if (c < bc) { bc = c; bv = v; bp = pos; }
            }
            if (!tem) return false;
        }
        insereEm(I, s, bv, bp);
    }
    return true;
}

// Enquanto L(T) > B, remove o vértice removível de maior rho- e aplica OTIMIZAROTA. Sem
// vértice removível, tenta encurtar a rota uma última vez e, se não couber, declara a
// solução inviável. Como só removíveis saem, sempre termina.
inline bool repara(const Inst& I, Sol& s, const vector<char>* X = nullptr) {
    if (!cobreClusters(I, s, X)) return false;
    while (s.L > I.B + TOL_B) {
        if (tempoEsgotado()) return false;
        double br = -1e300; int bi = -1;
        for (int idx = 0; idx < s.m(); idx++) {
            int v = s.rota[idx];
            if (!removivel(I, s, v)) continue;
            double r = rhoMenos(I.p[v], deltaMenos(I, s, idx));
            if (r > br) { br = r; bi = idx; }
        }
        if (bi < 0) {
            otimizaRota(I, s);
            break;
        }
        removeEm(I, s, bi);
        otimizaRota(I, s);
    }
    return s.viavel(I);
}
