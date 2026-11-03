// Cache das melhores posições de inserção dos vértices de fora da rota (Seção 3.1).
// Guarda as três arestas mais baratas de cada vértice: uma troca remove o vértice u e, com
// ele, duas arestas, logo ao menos uma entrada segue válida e o custo da troca é exato em
// O(1). A cada movimento só são recalculados os vértices cujas arestas guardadas mudaram.
#pragma once
#include "solucao.hpp"

struct CacheInsercao {
    struct Top { double c[3]; int a[3], b[3]; };
    const Inst& I;
    vector<Top> t;

    explicit CacheInsercao(const Inst& I_) : I(I_), t(I_.n) {}

    static void limpa(Top& x) { for (int q = 0; q < 3; q++) { x.c[q] = 1e300; x.a[q] = x.b[q] = -1; } }

    void oferece(int w, int a, int b) {
        Top& x = t[w];
        double c = I.d(a, w) + I.d(w, b) - I.d(a, b);
        if (c >= x.c[2]) return;
        for (int q = 0; q < 3; q++) if (x.a[q] == a && x.b[q] == b) return;
        x.c[2] = c; x.a[2] = a; x.b[2] = b;
        for (int q = 2; q > 0 && x.c[q] < x.c[q - 1]; q--) {
            swap(x.c[q], x.c[q - 1]); swap(x.a[q], x.a[q - 1]); swap(x.b[q], x.b[q - 1]);
        }
    }

    void calcula(const Sol& s, int w) {
        limpa(t[w]);
        int m = s.m();
        for (int k = 0; k < m; k++) oferece(w, s.rota[k], s.rota[k + 1 == m ? 0 : k + 1]);
    }

    void constroi(const Sol& s) {
        for (int w = 0; w < I.n; w++) if (!s.dentro[w]) calcula(s, w);
    }

    // Atualiza após remover as arestas de "sai" e criar as de "entra".
    void atualiza(const Sol& s, const vector<pair<int, int>>& sai, const vector<pair<int, int>>& entra) {
        for (int w = 0; w < I.n; w++) {
            if (s.dentro[w]) continue;
            bool refaz = s.m() <= 3;
            for (int q = 0; q < 3 && !refaz; q++)
                for (auto& e : sai) if (t[w].a[q] == e.first && t[w].b[q] == e.second) { refaz = true; break; }
            if (refaz) { calcula(s, w); continue; }
            for (auto& e : entra) oferece(w, e.first, e.second);
        }
    }

    double deltaMais(int w) const { return t[w].c[0]; }

    // Posição (índice em rota) que realiza delta+(w).
    int posicao(const Sol& s, int w) const {
        if (s.m() == 0) return 0;
        return indiceDe(s, t[w].a[0]) + 1;
    }

    // Melhor inserção de v na rota sem o vértice u (vizinhos pu e nu): a nova aresta (pu, nu)
    // ou a primeira das três guardadas que não toca em u.
    struct PosTroca { double custo; int a, b; };
    PosTroca semU(int v, int u, int pu, int nu) const {
        PosTroca r{I.d(pu, v) + I.d(v, nu) - I.d(pu, nu), pu, nu};
        const Top& x = t[v];
        for (int q = 0; q < 3 && x.a[q] >= 0; q++) {
            if (x.a[q] == u || x.b[q] == u) continue;
            if (x.c[q] < r.custo) { r.custo = x.c[q]; r.a = x.a[q]; r.b = x.b[q]; }
            break;
        }
        return r;
    }

    // Aplica a troca de u por v na posição calculada por semU e atualiza o cache.
    void aplicaTroca(Sol& s, int u, int v, const PosTroca& e) {
        int idx = indiceDe(s, u), m = s.m();
        int pu = s.rota[idx == 0 ? m - 1 : idx - 1], nu = s.rota[idx + 1 == m ? 0 : idx + 1];
        removeEm(I, s, idx);
        insereEm(I, s, v, indiceDe(s, e.a) + 1);
        calcula(s, u);
        vector<pair<int, int>> sai = {{pu, u}, {u, nu}, {e.a, e.b}}, entra = {{e.a, v}, {v, e.b}};
        if (!(e.a == pu && e.b == nu)) entra.push_back({pu, nu});
        atualiza(s, sai, entra);
        s.L = comprimento(I, s.rota);
    }
};
