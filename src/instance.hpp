// Leitura e representação de instâncias do GCOP.
//
// Formato do grafo (o mesmo das instâncias TSPLIB publicadas por Álvarez-Miranda et al.):
//   Nodes n
//   Clusters k            (informativo; os clusters são inferidos pelos rótulos)
//   V id cluster x y      (cluster = -1 => nó não pertence a nenhum cluster)
//   E i j d               (distância simétrica; grafo completo)
//   P id premio           (opcional; usado pelo esquema de prêmio "file")
// O orçamento B e o esquema de prêmios são passados pela linha de comando.
#pragma once
#include <bits/stdc++.h>
using namespace std;

struct Inst {
    string name;
    int n = 0, K = 0;
    vector<double> D;              // matriz n x n
    vector<double> p;              // prêmios
    vector<double> x, y;           // coordenadas (podem ser 0)
    vector<vector<int>> clusters;  // membros de cada cluster
    vector<vector<int>> nodeCl;    // clusters de cada nó
    double B = 0;
    double minP = 1, maxP = 1, avgD = 1;

    inline double d(int i, int j) const { return D[(size_t)i * n + j]; }
};

// Esquemas de prêmio do artigo: uniforme e pseudo-aleatório p_i = 1 + (7213 i mod 100).
// "clus": mesmo prêmio pseudo-aleatório para todos os nós de um cluster (cenário Pokémon).
inline Inst readInstance(const string& path, const string& profit) {
    ifstream in(path);
    if (!in) { cerr << "nao foi possivel abrir " << path << "\n"; exit(1); }
    Inst I;
    I.name = path;
    string tok;
    vector<int> label;
    vector<pair<int, double>> fileP;
    while (in >> tok) {
        if (tok == "Nodes") {
            in >> I.n;
            I.D.assign((size_t)I.n * I.n, 0.0);
            label.assign(I.n, -1);
            I.x.assign(I.n, 0); I.y.assign(I.n, 0);
        } else if (tok == "Clusters") {
            int k; in >> k;
        } else if (tok == "V") {
            int id, c; double xx, yy; in >> id >> c >> xx >> yy;
            label[id] = c; I.x[id] = xx; I.y[id] = yy;
        } else if (tok == "E") {
            int i, j; double w; in >> i >> j >> w;
            I.D[(size_t)i * I.n + j] = w; I.D[(size_t)j * I.n + i] = w;
        } else if (tok == "P") {
            int id; double v; in >> id >> v; fileP.push_back({id, v});
        } else {
            string rest; getline(in, rest);
        }
    }
    // rótulos -> clusters 0..K-1 (somente rótulos >= 0)
    map<int, int> remap;
    for (int i = 0; i < I.n; i++) if (label[i] >= 0 && !remap.count(label[i])) {
        int id = (int)remap.size(); remap[label[i]] = id;
    }
    I.K = (int)remap.size();
    I.clusters.assign(I.K, {});
    I.nodeCl.assign(I.n, {});
    for (int i = 0; i < I.n; i++) if (label[i] >= 0) {
        int c = remap[label[i]];
        I.clusters[c].push_back(i);
        I.nodeCl[i].push_back(c);
    }
    I.p.assign(I.n, 1.0);
    if (profit == "rand") {
        for (int i = 0; i < I.n; i++) I.p[i] = 1 + (7213LL * i) % 100;
    } else if (profit == "clus") {
        for (int i = 0; i < I.n; i++) {
            long long key = label[i] >= 0 ? label[i] + 1 : I.n + i;
            I.p[i] = 1 + (7213LL * key) % 100;
        }
    } else if (profit == "file") {
        for (auto& [id, v] : fileP) I.p[id] = v;
    }
    I.minP = *min_element(I.p.begin(), I.p.end());
    I.maxP = *max_element(I.p.begin(), I.p.end());
    double s = 0;
    for (int i = 0; i < I.n; i++) for (int j = i + 1; j < I.n; j++) s += I.d(i, j);
    I.avgD = I.n > 1 ? s / (I.n * (I.n - 1) / 2.0) : 1.0;
    return I;
}
