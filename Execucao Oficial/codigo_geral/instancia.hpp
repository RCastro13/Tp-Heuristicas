// Leitura e representação de instâncias do GCOP (Seção 1 e "Descrição das instâncias" do artigo).
//
// Formato do grafo (o mesmo das instâncias TSPLIB publicadas por Álvarez-Miranda et al.):
//   Nodes n
//   Clusters k            (informativo; os clusters são inferidos pelos rótulos)
//   V id cluster x y      (cluster = -1 => vértice opcional, fora de qualquer cluster)
//   E i j d               (distância simétrica; grafo completo)
//   P id premio           (opcional; usado pelo esquema de prêmio "arquivo")
// O orçamento B e o esquema de prêmios são passados pela linha de comando.
#pragma once
#include <bits/stdc++.h>
using namespace std;

struct Inst {
    string nome;
    int n = 0, K = 0;
    vector<double> D;              // matriz n x n
    vector<double> p;              // prêmios
    vector<vector<int>> clusters;  // membros de cada cluster
    vector<vector<int>> cl;        // clusters de cada vértice
    double B = 0;

    inline double d(int i, int j) const { return D[(size_t)i * n + j]; }
};

// Esquemas de prêmio: "unif" (p_i = 1), "rand" (p_i = 1 + (7213 i mod 100)) e
// "arquivo" (linhas P do grafo; prêmio inversamente proporcional à frequência nas POKE).
inline Inst leInstancia(const string& caminho, const string& premio) {
    ifstream in(caminho);
    if (!in) { cerr << "nao foi possivel abrir " << caminho << "\n"; exit(1); }
    Inst I;
    I.nome = caminho;
    string tok;
    vector<int> rotulo;
    vector<pair<int, double>> pArq;
    while (in >> tok) {
        if (tok == "Nodes") {
            in >> I.n;
            I.D.assign((size_t)I.n * I.n, 0.0);
            rotulo.assign(I.n, -1);
        } else if (tok == "Clusters") {
            int k; in >> k;
        } else if (tok == "V") {
            int id, c; double x, y; in >> id >> c >> x >> y;
            rotulo[id] = c;
        } else if (tok == "E") {
            int i, j; double w; in >> i >> j >> w;
            I.D[(size_t)i * I.n + j] = w; I.D[(size_t)j * I.n + i] = w;
        } else if (tok == "P") {
            int id; double v; in >> id >> v; pArq.push_back({id, v});
        } else {
            string resto; getline(in, resto);
        }
    }
    map<int, int> mapa;
    for (int i = 0; i < I.n; i++) if (rotulo[i] >= 0 && !mapa.count(rotulo[i])) {
        int id = (int)mapa.size(); mapa[rotulo[i]] = id;
    }
    I.K = (int)mapa.size();
    I.clusters.assign(I.K, {});
    I.cl.assign(I.n, {});
    for (int i = 0; i < I.n; i++) if (rotulo[i] >= 0) {
        int c = mapa[rotulo[i]];
        I.clusters[c].push_back(i);
        I.cl[i].push_back(c);
    }
    I.p.assign(I.n, 1.0);
    if (premio == "rand") {
        for (int i = 0; i < I.n; i++) I.p[i] = 1 + (7213LL * i) % 100;
    } else if (premio == "arquivo") {
        if ((int)pArq.size() != I.n) { cerr << "linhas P ausentes em " << caminho << "\n"; exit(1); }
        for (auto& [id, v] : pArq) I.p[id] = v;
    } else if (premio != "unif") {
        cerr << "esquema de premio desconhecido: " << premio << "\n"; exit(1);
    }
    return I;
}
