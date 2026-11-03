// Testes dos componentes comuns (etapa E6 do artigo): compara todo custo incremental com o
// recálculo direto e verifica as invariantes de REPARA, BL, AGITA e das heurísticas.
//   testes <grafo tsplib> <grafo poke>
#include "../codigo_geral/orcamento.hpp"
#include "../heuristicas/mspd/mspd.hpp"
#include "../heuristicas/mspd_ls/mspd_ls.hpp"
#include "../heuristicas/vns/vns.hpp"
#include "../heuristicas/ils/ils.hpp"
#include "../heuristicas/ils_c/ils_c.hpp"
#include "../heuristicas/alns/alns.hpp"
#include "../heuristicas/ma/ma.hpp"

static int falhas = 0, total = 0;
#define CHECA(c) do { total++; if (!(c)) { falhas++; printf("FALHA linha %d: %s\n", __LINE__, #c); } } while (0)

static bool consistente(const Inst& I, const Sol& s) {
    Sol r = s;
    recalcula(I, r);
    return fabs(r.L - s.L) < 1e-6 && fabs(r.P - s.P) < 1e-6 && r.descobertos == s.descobertos &&
           r.cob == s.cob && r.dentro == s.dentro;
}

static void testaInstancia(const string& caminho, const string& premio, double B) {
    Inst I = leInstancia(caminho, premio);
    I.B = B;
    RNG g(7);
    printf("== %s n=%d K=%d B=%.2f\n", caminho.c_str(), I.n, I.K, B);

    // delta+ e delta- contra o recálculo direto; inserção e remoção mantêm os campos
    for (int rep = 0; rep < 200; rep++) {
        Sol s = grasp(I, g);
        CHECA(consistente(I, s));
        CHECA(s.descobertos == 0);
        int v = sorteia(g, 0, I.n - 1);
        if (!s.dentro[v]) {
            auto [c, pos] = melhorInsercao(I, s, v);
            double L0 = comprimento(I, s.rota);
            for (int q = 0; q <= s.m(); q++) {
                vector<int> t = s.rota;
                t.insert(t.begin() + q, v);
                CHECA(comprimento(I, t) - L0 >= c - 1e-6);
            }
            insereEm(I, s, v, pos);
            CHECA(fabs(comprimento(I, s.rota) - L0 - c) < 1e-6);
            CHECA(consistente(I, s));
        }
        int idx = sorteia(g, 0, s.m() - 1);
        double L0 = comprimento(I, s.rota), dm = deltaMenos(I, s, idx);
        removeEm(I, s, idx);
        CHECA(fabs(L0 - comprimento(I, s.rota) - dm) < 1e-6);
        CHECA(consistente(I, s));
    }

    // O cache de inserção após trocas coincide com o recálculo; custo da troca é exato
    for (int rep = 0; rep < 60; rep++) {
        Sol s = grasp(I, g);
        for (int v = 0; v < I.n && s.m() < 30; v += 7) if (!s.dentro[v]) insereMelhor(I, s, v);
        CacheInsercao ca(I);
        ca.constroi(s);
        for (int t = 0; t < 10; t++) {
            int idx = sorteia(g, 0, s.m() - 1), u = s.rota[idx], v = sorteia(g, 0, I.n - 1), m = s.m();
            if (s.dentro[v]) continue;
            int pu = s.rota[idx == 0 ? m - 1 : idx - 1], nu = s.rota[idx + 1 == m ? 0 : idx + 1];
            auto e = ca.semU(v, u, pu, nu);
            Sol y = s;
            removeEm(I, y, idx);
            auto [c, pos] = melhorInsercao(I, y, v);
            CHECA(fabs(c - e.custo) < 1e-6);
            double L2 = s.L - deltaMenos(I, s, idx) + e.custo;
            ca.aplicaTroca(s, u, v, e);
            CHECA(fabs(comprimento(I, s.rota) - L2) < 1e-6);
            CHECA(consistente(I, s));
            for (int w = 0; w < I.n; w++)
                if (!s.dentro[w]) CHECA(fabs(ca.deltaMais(w) - melhorInsercao(I, s, w).first) < 1e-6);
        }
    }

    // REPARA, OTIMIZAROTA e BL: nunca pioram e entregam solução viável e consistente
    for (int rep = 0; rep < 30; rep++) {
        Sol s = grasp(I, g);
        vector<int> X0;
        if (!repara(I, s)) continue;
        CHECA(s.viavel(I)); CHECA(consistente(I, s));
        Sol a = s; otimizaRota(I, a);
        CHECA(a.L <= s.L + 1e-6); CHECA(fabs(a.P - s.P) < 1e-9); CHECA(consistente(I, a));
        Sol b = a; buscaLocal(I, b);
        CHECA(b.viavel(I)); CHECA(!melhor(a, b) || fabs(a.P - b.P) < 1e-9); CHECA(consistente(I, b));
        CHECA(verifica(I, b.rota));
        // AGITA: nenhum vértice removido volta durante REPARA e o resultado é viável
        Sol c = b;
        if (agita(I, c, 3, g)) { CHECA(c.viavel(I)); CHECA(consistente(I, c)); }
    }

    // REPARA respeita o conjunto proibido X
    for (int rep = 0; rep < 30; rep++) {
        Sol s = grasp(I, g);
        vector<char> X(I.n, 0);
        int idx = sorteia(g, 0, s.m() - 1), v = s.rota[idx];
        X[v] = 1;
        removeEm(I, s, idx);
        if (repara(I, s, &X)) { CHECA(!s.dentro[v]); CHECA(s.viavel(I)); }
    }

    // Refino sigma preserva a consistência dos campos
    for (int rep = 0; rep < 10; rep++) {
        Sol s = grasp(I, g);
        refinoSigma(I, s);
        CHECA(consistente(I, s));
    }

    // Todos os métodos: viáveis, dentro do tempo e reprodutíveis em iterações suficientes
    vector<pair<string, void (*)(Executor&)>> metodos = {
        {"MSPD", executaMSPD}, {"MSPD-LS", executaMSPDLS}, {"VNS", executaVNS}, {"ILS", executaILS},
        {"ILS-C", executaILSC}, {"ALNS", executaALNS}, {"MA", executaMA}};
    for (auto& [nome, f] : metodos) {
        relogio().inicia(1.0);
        Executor R(I, 1);
        f(R);
        double t = relogio().decorrido();
        relogio().limite = 1e18;
        printf("  %-8s P=%.1f L=%.2f m=%d iter=%lld t=%.3f\n", nome.c_str(), R.best.P, R.best.L, R.best.m(), R.iter, t);
        CHECA(R.tem);
        CHECA(verifica(I, R.best.rota));
        CHECA(consistente(I, R.best));
        CHECA(t < 1.5);
    }
}

int main(int argc, char** argv) {
    if (argc < 3) { cerr << "uso: testes <tsplib> <poke>\n"; return 1; }
    // Caso minúsculo com solução conhecida: quadrado de lado 1 com um vértice distante.
    {
        Inst I; I.n = 5; I.K = 2; I.D.assign(25, 0);
        double xy[5][2] = {{0, 0}, {1, 0}, {1, 1}, {0, 1}, {10, 10}};
        for (int i = 0; i < 5; i++) for (int j = 0; j < 5; j++) I.D[i * 5 + j] = hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]);
        I.p = {1, 1, 1, 1, 100};
        I.clusters = {{0, 1}, {2, 3}};
        I.cl = {{0}, {0}, {1}, {1}, {}};
        I.B = 4.0;
        RNG g(1);
        Sol s; s.inicia(I);
        s.rota = {0, 2, 1, 3};
        recalcula(I, s);
        otimizaRota(I, s);
        CHECA(fabs(s.L - 4.0) < 1e-9);  // 2-opt desfaz o cruzamento
        Sol a; a.inicia(I);
        a.rota = {0, 1, 2}; recalcula(I, a);
        buscaLocal(I, a);
        CHECA(a.viavel(I)); CHECA(fabs(a.P - 4) < 1e-9);  // o vértice distante não cabe
        Sol b; b.inicia(I); b.rota = {0, 2}; recalcula(I, b);
        CHECA(!b.viavel(I));  // ciclo exige três vértices
        CHECA(rhoMais(2, -1) == 2 / EPS_RAZAO);
        CHECA(rhoMenos(2, -1) == -0.5);
        Sol c = a;
        vector<char> X(5, 0);
        CHECA(melhor(a, b));
    }
    {
        Inst T = leInstancia(argv[1], "rand");
        RNG g(3);
        TSPRapido tsp(T);
        double Ltsp = tsp.resolve(1.0, g);
        CHECA(fabs(comprimento(T, tsp.t) - Ltsp) < 1e-6);
        vector<char> vis(T.n, 0);
        for (int v : tsp.t) vis[v] = 1;
        CHECA(accumulate(vis.begin(), vis.end(), 0) == T.n);
        double G = resolveGTSP(T, 1.0, g);
        CHECA(G > 0 && G < Ltsp);
        printf("TSP=%.2f GTSP=%.2f\n", Ltsp, G);
        testaInstancia(argv[1], "rand", G + 0.5 * (Ltsp - G));
        testaInstancia(argv[1], "unif", G + 0.25 * (Ltsp - G));
    }
    testaInstancia(argv[2], "arquivo", 10.0);
    printf("%d verificacoes, %d falhas\n", total, falhas);
    return falhas ? 1 : 0;
}
