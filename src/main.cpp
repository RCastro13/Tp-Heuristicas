// gcop — heurísticas para o Generalized Clustered Orienteering Problem.
//
// Uso:
//   gcop budget <grafo>                        -> {"n","K","tsp","gtsp_feas"}
//   gcop solve <grafo> --profit unif|rand|clus|file --budget B --algo ALG
//              [--seed S] [--time T] [--name NOME]
// Algoritmos: NI, FI, ST, TSPD (construtivas + reparo); sufixos -SR (refinamento sigma
// do artigo) e -LS (busca local exata); MSPD, GRASP, ILS, VNS, ALNS, SA, TS, MA.
#include "meta.hpp"

static string jsonTour(const vector<int>& t) {
    string s = "[";
    for (size_t i = 0; i < t.size(); i++) s += (i ? "," : "") + to_string(t[i]);
    return s + "]";
}

int main(int argc, char** argv) {
    ios::sync_with_stdio(false);
    if (argc < 3) { cerr << "uso: gcop budget|solve <grafo> ...\n"; return 1; }
    string cmd = argv[1], path = argv[2];
    map<string, string> opt;
    for (int i = 3; i + 1 < argc; i += 2) opt[argv[i]] = argv[i + 1];
    auto get = [&](const string& k, const string& d) { return opt.count(k) ? opt[k] : d; };

    Inst I = readInstance(path, get("--profit", "unif"));
    if (cmd == "budget") {
        // TSP sobre todos os nós e tour GTSP viável pelo nó de menor índice de cada cluster
        mt19937 rng(12345);
        vector<int> all(I.n); iota(all.begin(), all.end(), 0);
        auto t = tspTour(I, all, 5, rng);
        vector<int> reps;
        for (auto& c : I.clusters) reps.push_back(*min_element(c.begin(), c.end()));
        sort(reps.begin(), reps.end()); reps.erase(unique(reps.begin(), reps.end()), reps.end());
        auto g = tspTour(I, reps, 5, rng);
        printf("{\"n\":%d,\"K\":%d,\"tsp\":%.6f,\"gtsp_feas\":%.6f}\n", I.n, I.K, tourLength(I, t), tourLength(I, g));
        return 0;
    }
    I.B = stod(get("--budget", "0"));
    string algo = get("--algo", "NI");
    unsigned seed = stoul(get("--seed", "1"));
    double tlim = stod(get("--time", "10"));
    string name = get("--name", path);
    replace(name.begin(), name.end(), '\\', '/');

    Runner R(I, tlim, seed);
    double rawPrize = -1, rawLen = -1;
    string base = algo.substr(0, algo.find('-'));
    string suf = algo.find('-') == string::npos ? "" : algo.substr(algo.find('-') + 1);

    if (base == "NI" || base == "FI" || base == "ST" || base == "TSPD") {
        // --reps R: repete a construtiva R vezes e reporta o tempo médio (medição de complexidade)
        int reps = stoi(get("--reps", "1"));
        for (int q = 1; q < reps; q++) {
            int st = defaultStart(I);
            mt19937 r2(seed);
            Sol s = base == "NI" ? gtspInsertion(I, true, st) : base == "FI" ? gtspInsertion(I, false, st)
                  : base == "ST" ? steinerConstruct(I, st) : tspDrop(I, r2);
            if (!s.feasible(I)) repair(I, s);
            if (suf == "SR") sigmaRefine(I, s); else if (suf == "LS") improve(I, s);
        }
        R.extra["reps"] = reps;
        int st = defaultStart(I);
        Sol s;
        if (base == "NI") s = gtspInsertion(I, true, st);
        else if (base == "FI") s = gtspInsertion(I, false, st);
        else if (base == "ST") s = steinerConstruct(I, st);
        else s = tspDrop(I, R.rng);
        if (!s.feasible(I)) repair(I, s);
        rawPrize = s.prize; rawLen = s.len;
        if (suf == "SR") sigmaRefine(I, s);
        else if (suf == "LS") improve(I, s);
        R.consider(s);
        R.iters = 1;
    } else if (algo == "MSPD") runMSPD(R, true);
    else if (algo == "MSPD-LS") runMSPD(R, false);
    else if (algo == "GRASP") runGRASP(R);
    else if (algo == "ILS") runILS(R);
    else if (algo == "VNS") runVNS(R);
    else if (algo == "ALNS") runALNS(R);
    else if (algo == "SA") runSA(R);
    else if (algo == "TS") runTS(R);
    else if (algo == "MA") runMA(R);
    else { cerr << "algoritmo desconhecido: " << algo << "\n"; return 1; }

    double total = R.el();
    if (R.extra.count("reps")) total /= R.extra["reps"];
    string why;
    bool ok = R.has && verify(I, R.best, &why);
    double L = R.has ? tourLength(I, R.best.tour) : 0;
    printf("{\"inst\":\"%s\",\"algo\":\"%s\",\"seed\":%u,\"tlim\":%.3f,\"n\":%d,\"K\":%d,\"B\":%.6f,"
           "\"feasible\":%s,\"prize\":%.6f,\"len\":%.6f,\"m\":%d,\"time\":%.7f,\"time_best\":%.6f,"
           "\"iters\":%lld,\"raw_prize\":%.6f,\"raw_len\":%.6f",
           name.c_str(), algo.c_str(), seed, tlim, I.n, I.K, I.B, ok ? "true" : "false",
           ok ? R.best.prize : 0.0, L, R.has ? R.best.m() : 0, total, R.tBest, R.iters, rawPrize, rawLen);
    for (auto& [k, v] : R.extra) printf(",\"%s\":%.6f", k.c_str(), v);
    printf(",\"trace\":[");
    for (size_t i = 0; i < R.trace.size(); i++) printf("%s[%.4f,%.6f]", i ? "," : "", R.trace[i].first, R.trace[i].second);
    printf("],\"tour\":%s}\n", R.has ? jsonTour(R.best.tour).c_str() : "[]");
    if (!ok && R.has) cerr << "AVISO: solucao invalida: " << why << "\n";
    return 0;
}
