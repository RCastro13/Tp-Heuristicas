// Construções: inserção NI/FI [Fischetti et al., 1997], árvore de Steiner ST
// [Takahashi & Matsuyama, 1980], INICIAL e GRASP (Seção 3.1).
#pragma once
#include "reparo.hpp"

using RNG = mt19937;
inline int sorteia(RNG& g, int a, int b) { return uniform_int_distribution<int>(a, b)(g); }
inline double sorteiaReal(RNG& g, double a = 0, double b = 1) { return uniform_real_distribution<double>(a, b)(g); }

// Vértice inicial determinístico de INICIAL: menor índice do menor cluster.
inline int inicioPadrao(const Inst& I) {
    int bk = 0;
    for (int k = 1; k < I.K; k++) if (I.clusters[k].size() < I.clusters[bk].size()) bk = k;
    return *min_element(I.clusters[bk].begin(), I.clusters[bk].end());
}

// Escolhe o cluster descoberto mais próximo (NI) ou mais distante (FI) da rota e insere o
// seu vértice de menor delta+.
inline Sol insercaoGTSP(const Inst& I, bool maisProximo, int s0) {
    Sol s; s.inicia(I);
    insereEm(I, s, s0, 0);
    vector<double> md(I.n);
    for (int v = 0; v < I.n; v++) md[v] = I.d(s0, v);
    while (s.descobertos > 0) {
        int bk = -1; double bd = maisProximo ? 1e300 : -1;
        for (int k = 0; k < I.K; k++) {
            if (s.cob[k] > 0) continue;
            double dk = 1e300;
            for (int v : I.clusters[k]) dk = min(dk, md[v]);
            if ((maisProximo && dk < bd) || (!maisProximo && dk > bd)) { bd = dk; bk = k; }
        }
        double bc = 1e300; int bv = -1, bp = 0;
        for (int v : I.clusters[bk]) {
            auto [c, pos] = melhorInsercao(I, s, v);
            if (c < bc) { bc = c; bv = v; bp = pos; }
        }
        insereEm(I, s, bv, bp);
        for (int v = 0; v < I.n; v++) md[v] = min(md[v], I.d(bv, v));
    }
    return s;
}

// Steiner por caminhos mínimos, com um terminal por cluster; a rota é o percurso em
// pré-ordem da árvore a partir da raiz.
inline Sol steiner(const Inst& I, int raiz) {
    int n = I.n;
    vector<char> naArvore(n, 0), coberto(I.K, 0);
    vector<vector<int>> adj(n);
    int falta = I.K;
    auto adiciona = [&](int v) {
        naArvore[v] = 1;
        for (int c : I.cl[v]) if (!coberto[c]) { coberto[c] = 1; falta--; }
    };
    adiciona(raiz);
    vector<double> dist(n);
    vector<int> pai(n);
    vector<char> feito(n);
    while (falta > 0) {
        for (int v = 0; v < n; v++) { dist[v] = naArvore[v] ? 0 : 1e300; pai[v] = -1; feito[v] = 0; }
        int alvo = -1;
        for (int it = 0; it < n; it++) {
            int u = -1; double bd = 1e300;
            for (int v = 0; v < n; v++) if (!feito[v] && dist[v] < bd) { bd = dist[v]; u = v; }
            if (u < 0) break;
            feito[u] = 1;
            if (!naArvore[u]) {
                bool atinge = false;
                for (int c : I.cl[u]) if (!coberto[c]) { atinge = true; break; }
                if (atinge) { alvo = u; break; }
            }
            for (int v = 0; v < n; v++) if (!feito[v]) {
                double nd = dist[u] + I.d(u, v);
                if (nd < dist[v]) { dist[v] = nd; pai[v] = u; }
            }
        }
        int v = alvo;
        while (!naArvore[v]) {
            int u = pai[v];
            adj[u].push_back(v); adj[v].push_back(u);
            adiciona(v);
            v = u;
        }
    }
    Sol s; s.inicia(I);
    vector<char> vis(n, 0);
    vector<int> pilha = {raiz};
    while (!pilha.empty()) {
        int u = pilha.back(); pilha.pop_back();
        if (vis[u]) continue;
        vis[u] = 1; s.rota.push_back(u);
        vector<int> filhos;
        for (int w : adj[u]) if (!vis[w]) filhos.push_back(w);
        sort(filhos.begin(), filhos.end(), [&](int a, int b) { return I.d(u, a) > I.d(u, b); });
        for (int w : filhos) pilha.push_back(w);
    }
    recalcula(I, s);
    return s;
}

// GRASP: como a NI, mas sorteia o próximo cluster entre os três mais próximos da rota e a
// inserção entre os três vértices de maior rho+ do cluster.
inline Sol grasp(const Inst& I, RNG& g) {
    Sol s; s.inicia(I);
    int k0 = sorteia(g, 0, I.K - 1);
    int s0 = I.clusters[k0][sorteia(g, 0, (int)I.clusters[k0].size() - 1)];
    insereEm(I, s, s0, 0);
    vector<double> md(I.n);
    for (int v = 0; v < I.n; v++) md[v] = I.d(s0, v);
    vector<pair<double, int>> lista;
    while (s.descobertos > 0) {
        lista.clear();
        for (int k = 0; k < I.K; k++) {
            if (s.cob[k] > 0) continue;
            double dk = 1e300;
            for (int v : I.clusters[k]) dk = min(dk, md[v]);
            lista.push_back({dk, k});
        }
        sort(lista.begin(), lista.end());
        int k = lista[sorteia(g, 0, min(3, (int)lista.size()) - 1)].second;
        lista.clear();
        for (int v : I.clusters[k]) lista.push_back({-rhoMais(I.p[v], melhorInsercao(I, s, v).first), v});
        sort(lista.begin(), lista.end());
        int v = lista[sorteia(g, 0, min(3, (int)lista.size()) - 1)].second;
        insereMelhor(I, s, v);
        for (int w = 0; w < I.n; w++) md[w] = min(md[w], I.d(v, w));
    }
    return s;
}

// INICIAL: a melhor entre NI, FI e ST, cada uma seguida de REPARA e BL. Retorna false se
// nenhuma for viável.
inline bool solucaoInicial(const Inst& I, Sol& melhorS) {
    int s0 = inicioPadrao(I);
    bool tem = false;
    for (int c = 0; c < 3 && (c == 0 || !tempoEsgotado()); c++) {
        Sol s = c == 0 ? insercaoGTSP(I, true, s0) : c == 1 ? insercaoGTSP(I, false, s0) : steiner(I, s0);
        if (!repara(I, s)) continue;
        buscaLocal(I, s);
        if (s.viavel(I) && (!tem || melhor(s, melhorS))) { melhorS = s; tem = true; }
    }
    return tem;
}
