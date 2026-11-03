// gcop: heurísticas do artigo para o Generalized Clustered Orienteering Problem.
//
// Uso:
//   gcop resolve <grafo> --premio unif|rand|arquivo --B B --algo ALG --semente S --tempo T --nome NOME
//   gcop orcamento <grafo> --tempo T          -> {"n","K","tsp","gtsp"} (melhores conhecidos)
//   gcop checaNI <grafo>                      -> comprimento de NI + OTIMIZAROTA (geração POKE)
// Algoritmos: MSPD, MSPD-LS, VNS, ILS, ILS-C, ALNS, MA.
#include "orcamento.hpp"
#include "../heuristicas/mspd/mspd.hpp"
#include "../heuristicas/mspd_ls/mspd_ls.hpp"
#include "../heuristicas/vns/vns.hpp"
#include "../heuristicas/ils/ils.hpp"
#include "../heuristicas/ils_c/ils_c.hpp"
#include "../heuristicas/alns/alns.hpp"
#include "../heuristicas/ma/ma.hpp"

int main(int argc, char** argv) {
    if (argc < 3) { cerr << "uso: gcop resolve|orcamento|checaNI <grafo> ...\n"; return 1; }
    string cmd = argv[1], caminho = argv[2];
    map<string, string> op;
    for (int i = 3; i + 1 < argc; i += 2) op[argv[i]] = argv[i + 1];
    auto pega = [&](const string& k, const string& d) { return op.count(k) ? op[k] : d; };

    Inst I = leInstancia(caminho, pega("--premio", "unif"));
    if (cmd == "orcamento") {
        double seg = stod(pega("--tempo", "10"));
        RNG g(12345);
        TSPRapido tsp(I);
        double T = tsp.resolve(seg, g);
        double G = resolveGTSP(I, seg, g);
        printf("{\"n\":%d,\"K\":%d,\"tsp\":%.6f,\"gtsp\":%.6f}\n", I.n, I.K, T, G);
        return 0;
    }
    if (cmd == "checaNI") {
        Sol s = insercaoGTSP(I, true, inicioPadrao(I));
        otimizaRota(I, s);
        printf("{\"n\":%d,\"K\":%d,\"L\":%.6f}\n", I.n, I.K, s.L);
        return 0;
    }
    I.B = stod(pega("--B", "0"));
    string algo = pega("--algo", "ILS");
    unsigned sem = stoul(pega("--semente", "1"));
    double tlim = stod(pega("--tempo", "1"));
    string nome = pega("--nome", caminho);

    relogio().inicia(tlim);
    Executor R(I, sem);
    if (algo == "MSPD") executaMSPD(R);
    else if (algo == "MSPD-LS") executaMSPDLS(R);
    else if (algo == "VNS") executaVNS(R);
    else if (algo == "ILS") executaILS(R);
    else if (algo == "ILS-C") executaILSC(R);
    else if (algo == "ALNS") executaALNS(R);
    else if (algo == "MA") executaMA(R);
    else { cerr << "algoritmo desconhecido: " << algo << "\n"; return 1; }
    double total = relogio().decorrido();

    string porque;
    bool ok = R.tem && verifica(I, R.best.rota, &porque);
    if (R.tem && !ok) cerr << "AVISO: solucao invalida: " << porque << "\n";
    printf("{\"inst\":\"%s\",\"algo\":\"%s\",\"semente\":%u,\"tlim\":%.3f,\"n\":%d,\"K\":%d,\"B\":%.6f,"
           "\"viavel\":%s,\"P\":%.6f,\"L\":%.6f,\"m\":%d,\"tempo\":%.4f,\"t_melhor\":%.4f,\"iter\":%lld,"
           "\"n_melhoria\":%lld,\"t_melhoria\":%.6f",
           nome.c_str(), algo.c_str(), sem, tlim, I.n, I.K, I.B, ok ? "true" : "false",
           ok ? R.best.P : 0.0, ok ? comprimento(I, R.best.rota) : 0.0, ok ? R.best.m() : 0,
           total, R.tBest, R.iter, R.nMelhoria, R.tMelhoria);
    for (auto& [k, v] : R.extras) printf(",\"%s\":%.6f", k.c_str(), v);
    printf(",\"rota\":[");
    if (ok) for (size_t i = 0; i < R.best.rota.size(); i++) printf("%s%d", i ? "," : "", R.best.rota[i]);
    printf("]}\n");
    return 0;
}
