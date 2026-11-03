// MSPD (controle, Algoritmos 6 e 7): multi-start com distâncias perturbadas e refinamento
// sigma de Álvarez-Miranda et al. (2018), executado pelo mesmo tempo t(n) dos métodos propostos.
#pragma once
#include "../../codigo_geral/executor.hpp"

// sigma_i = min_{j em V_T \ {i}} d_ij / p_i, mantido de forma incremental para que o custo
// do controle não seja inflado pela implementação.
struct IndiceSigma {
    const Inst& I;
    vector<double> md;
    vector<int> perto;

    explicit IndiceSigma(const Inst& I_) : I(I_), md(I_.n), perto(I_.n) {}

    void calcula(const Sol& s, int v) {
        md[v] = 1e300; perto[v] = -1;
        for (int u : s.rota) if (u != v && I.d(u, v) < md[v]) { md[v] = I.d(u, v); perto[v] = u; }
    }
    void constroi(const Sol& s) { for (int v = 0; v < I.n; v++) calcula(s, v); }
    void aoInserir(const Sol& s, int w) {
        for (int v = 0; v < I.n; v++) if (v != w && I.d(w, v) < md[v]) { md[v] = I.d(w, v); perto[v] = w; }
        calcula(s, w);
    }
    void aoRemover(const Sol& s, int w) {
        for (int v = 0; v < I.n; v++) if (perto[v] == w) calcula(s, v);
    }
    double operator()(int v) const { return (md[v] >= 1e299 ? 0.0 : md[v]) / I.p[v]; }
};

// Algoritmo 7. Os passos seguem [1]: remoção, cobertura, inserção e troca guiadas por sigma.
inline void refinoSigma(const Inst& I, Sol& s) {
    IndiceSigma sg(I);
    sg.constroi(s);
    for (int rodada = 0; rodada < 10 && !tempoEsgotado(); rodada++) {
        double P0 = s.P, L0 = s.L;
        // enquanto L(T) > B: remove o maior sigma
        while (s.L > I.B + TOL_B && s.m() > 1) {
            int bi = 0;
            for (int idx = 1; idx < s.m(); idx++) if (sg(s.rota[idx]) > sg(s.rota[bi])) bi = idx;
            int w = s.rota[bi];
            removeEm(I, s, bi);
            sg.aoRemover(s, w);
        }
        // cobre clusters pelo menor sigma
        for (int k = 0; k < I.K; k++) {
            if (s.cob[k] > 0) continue;
            int bv = I.clusters[k][0];
            for (int v : I.clusters[k]) if (sg(v) < sg(bv)) bv = v;
            insereMelhor(I, s, bv);
            sg.aoInserir(s, bv);
        }
        // insere por sigma crescente, se couber
        CacheInsercao ca(I);
        ca.constroi(s);
        for (;;) {
            double folga = I.B - s.L + 1e-9;
            int bv = -1;
            for (int v = 0; v < I.n; v++)
                if (!s.dentro[v] && ca.deltaMais(v) <= folga && (bv < 0 || sg(v) < sg(bv))) bv = v;
            if (bv < 0) break;
            int pos = ca.posicao(s, bv), m = s.m();
            int a = s.rota[pos - 1], b = s.rota[pos % m];
            insereEm(I, s, bv, pos);
            ca.atualiza(s, {{a, b}}, {{a, bv}, {bv, b}});
            sg.aoInserir(s, bv);
        }
        // troca por vértices de sigma menor
        if (s.m() >= 3) {
            vector<double> f(I.n);
            for (int v = 0; v < I.n; v++) f[v] = sg(v);
            vector<int> dentro = s.rota, fora;
            for (int v = 0; v < I.n; v++) if (!s.dentro[v]) fora.push_back(v);
            sort(dentro.begin(), dentro.end(), [&](int a, int b) { return f[a] > f[b]; });
            sort(fora.begin(), fora.end(), [&](int a, int b) { return f[a] < f[b]; });
            for (int u : dentro) {
                for (int v : fora) {
                    if (f[v] >= f[u]) break;
                    if (s.dentro[v] || !removivel(I, s, u, v)) continue;
                    int idx = indiceDe(s, u), m = s.m();
                    int pu = s.rota[idx == 0 ? m - 1 : idx - 1], nu = s.rota[idx + 1 == m ? 0 : idx + 1];
                    auto e = ca.semU(v, u, pu, nu);
                    if (s.L - deltaMenos(I, s, idx) + e.custo > I.B + 1e-9) continue;
                    ca.aplicaTroca(s, u, v, e);
                    break;
                }
            }
            sg.constroi(s);
        }
        otimizaRota(I, s);
        if (!(s.P > P0 + EPS || s.L < L0 - 1e-6)) break;
    }
}

// Laço do Algoritmo 6, comum ao MSPD e ao MSPD-LS: só a fase de melhoria (linha 8) muda.
template <class Fase>
inline void multiStart(Executor& R, Fase melhoria) {
    const Inst& I = R.I;
    Inst P = I;  // matriz perturbada, reescrita a cada iteração
    uniform_real_distribution<double> U(1.0, 1.2);
    while (!tempoEsgotado()) {
        for (int i = 0; i < I.n; i++)
            for (int j = i + 1; j < I.n; j++) {
                double v = I.d(i, j) * U(R.g);
                P.D[(size_t)i * I.n + j] = v; P.D[(size_t)j * I.n + i] = v;
            }
        int s0 = sorteia(R.g, 0, I.n - 1);
        Sol T = sorteia(R.g, 0, 1) ? insercaoGTSP(P, true, s0) : steiner(P, s0);
        recalcula(I, T);  // reavalia com as distâncias reais
        double t0 = relogio().decorrido();
        melhoria(T);
        R.tMelhoria += relogio().decorrido() - t0;
        R.nMelhoria++;
        R.considera(T);
        R.iter++;
    }
}

inline void executaMSPD(Executor& R) {
    const Inst& I = R.I;
    multiStart(R, [&](Sol& T) {
        otimizaRota(I, T);
        refinoSigma(I, T);
    });
}
