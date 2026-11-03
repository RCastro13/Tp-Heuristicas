// Busca local proposta (BL, Algoritmo 1): OTIMIZAROTA + INSERERAZAO + TROCA, por no máximo
// 50 rodadas, com todos os custos de inserção, remoção e troca calculados exatamente.
#pragma once
#include "cache_insercao.hpp"
#include "otimiza_rota.hpp"

// INSERERAZAO [Tsiligirides, 1984]: enquanto algum vértice de fora couber em B, insere na
// melhor posição primeiro os de delta+ < 0 e depois o de maior rho+.
// proibido: vértices que não podem entrar (conjunto X da reconstrução do ALNS).
// fator: se não nulo, delta+ multiplicado por fator[v] na escolha (reconstrução ruidosa).
inline bool insereRazao(const Inst& I, Sol& s, const vector<char>* proibido = nullptr,
                        const vector<double>* fator = nullptr) {
    if (s.m() == 0) return false;
    CacheInsercao ca(I);
    ca.constroi(s);
    bool algum = false;
    for (;;) {
        double folga = I.B - s.L + 1e-9;
        int bv = -1; double bRho = -1, bNeg = 0;
        for (int v = 0; v < I.n; v++) {
            if (s.dentro[v] || (proibido && (*proibido)[v])) continue;
            double c = ca.deltaMais(v);
            if (c > folga) continue;
            if (c < -EPS) {
                if (c < bNeg) { bNeg = c; bv = v; }
            } else if (bNeg >= 0) {
                double r = rhoMais(I.p[v], fator ? c * (*fator)[v] : c);
                if (r > bRho) { bRho = r; bv = v; }
            }
        }
        if (bv < 0) break;
        int pos = ca.posicao(s, bv), m = s.m();
        int a = s.rota[pos - 1], b = s.rota[pos % m];
        insereEm(I, s, bv, pos);
        algum = true;
        ca.atualiza(s, {{a, b}}, {{a, bv}, {bv, b}});
    }
    return algum;
}

// TROCA, com melhor melhora: substitui u em T por v fora de T na melhor posição se o
// resultado couber em B, mantiver os clusters cobertos e for melhor. Como o critério
// desempata pelo comprimento, também aceita um v de mesmo prêmio que encurte a rota.
inline bool troca(const Inst& I, Sol& s) {
    if (s.m() < 3) return false;
    CacheInsercao ca(I);
    ca.constroi(s);
    bool algum = false;
    vector<double> dm;
    while (!tempoEsgotado()) {
        int m = s.m();
        dm.resize(m);
        for (int idx = 0; idx < m; idx++) dm[idx] = deltaMenos(I, s, idx);
        int bu = -1, bv = -1;
        CacheInsercao::PosTroca be{0, -1, -1};
        double bP = s.P, bL = s.L;
        for (int v = 0; v < I.n; v++) {
            if (s.dentro[v]) continue;
            for (int idx = 0; idx < m; idx++) {
                int u = s.rota[idx];
                double P2 = s.P - I.p[u] + I.p[v];
                if (P2 < bP - EPS) continue;
                int pu = s.rota[idx == 0 ? m - 1 : idx - 1], nu = s.rota[idx + 1 == m ? 0 : idx + 1];
                auto e = ca.semU(v, u, pu, nu);
                double L2 = s.L - dm[idx] + e.custo;
                if (L2 > I.B + 1e-9) continue;
                bool ganha = P2 > bP + EPS || L2 < bL - 1e-9;
                if (!ganha || !removivel(I, s, u, v)) continue;
                bu = u; bv = v; be = e; bP = P2; bL = L2;
            }
        }
        if (bu < 0) break;
        ca.aplicaTroca(s, bu, bv, be);
        algum = true;
    }
    return algum;
}

// Algoritmo 1.
inline void buscaLocal(const Inst& I, Sol& s) {
    for (int it = 0; it < 50 && !tempoEsgotado(); it++) {
        otimizaRota(I, s);
        bool a = insereRazao(I, s);
        bool b = troca(I, s);
        if (!a && !b) break;
    }
    s.L = comprimento(I, s.rota);
}
