// Metaheurísticas (todas limitadas por tempo de relógio).
#pragma once
#include "construct.hpp"

struct Runner {
    const Inst& I;
    double tlim;
    chrono::steady_clock::time_point t0;
    Sol best;
    bool has = false;
    double tBest = 0;
    long long iters = 0;
    vector<pair<double, double>> trace;
    map<string, double> extra;
    mt19937 rng;

    Runner(const Inst& I_, double tlim_, unsigned seed) : I(I_), tlim(tlim_), rng(seed) {
        t0 = chrono::steady_clock::now();
        best.init(I);
    }
    double el() const { return chrono::duration<double>(chrono::steady_clock::now() - t0).count(); }
    bool timeUp() const { return el() >= tlim; }
    void consider(const Sol& s) {
        if (!s.feasible(I)) return;
        if (!has || better(s, best)) {
            best = s; has = true; tBest = el();
            trace.push_back({tBest, s.prize});
        }
    }
    double urand() { return uniform_real_distribution<double>(0, 1)(rng); }
    int irand(int a, int b) { return uniform_int_distribution<int>(a, b)(rng); }
};

inline Inst perturbed(const Inst& I, mt19937& rng, double f = 0.2) {
    Inst P = I;
    uniform_real_distribution<double> U(1.0, 1.0 + f);
    for (int i = 0; i < I.n; i++)
        for (int j = i + 1; j < I.n; j++) {
            double v = I.d(i, j) * U(rng);
            P.D[(size_t)i * I.n + j] = v; P.D[(size_t)j * I.n + i] = v;
        }
    return P;
}

// Reaplica uma ordem de visita (construída com outra matriz) na instância original.
inline Sol rebase(const Inst& I, const Sol& s) {
    Sol r; r.init(I); r.tour = s.tour; recompute(I, r); return r;
}

// Solução inicial comum às metaheurísticas de trajetória: melhor entre NI, FI e ST + BL.
inline Sol initialSolution(Runner& R) {
    const Inst& I = R.I;
    int st = defaultStart(I);
    Sol best; bool has = false;
    for (int c = 0; c < 3; c++) {
        Sol s = c == 0 ? gtspInsertion(I, true, st) : c == 1 ? gtspInsertion(I, false, st) : steinerConstruct(I, st);
        repair(I, s);
        improve(I, s);
        R.consider(s);
        if (s.feasible(I) && (!has || better(s, best))) { best = s; has = true; }
        if (R.timeUp()) break;
    }
    if (!has) { best = R.best; }
    return best;
}

// ------------------------------------------------ MS-PD: multi-start com distâncias perturbadas
// Heurística de inicialização do artigo (controle): a cada iteração sorteia a construção
// NI ou Steiner sobre distâncias d~ ~ U[d, 1.2d] e aplica reparo + refinamento sigma.
inline void runMSPD(Runner& R, bool sigma = true) {
    const Inst& I = R.I;
    while (!R.timeUp()) {
        Inst P = perturbed(I, R.rng);
        int k = R.rng() % I.K;
        int st = I.clusters[k][R.rng() % I.clusters[k].size()];
        Sol c = (R.rng() % 2) ? gtspInsertion(P, true, st) : steinerConstruct(P, st);
        Sol s = rebase(I, c);
        routeOpt(I, s);
        if (sigma) sigmaRefine(I, s); else { repair(I, s); improve(I, s); }
        R.consider(s);
        R.iters++;
        if (R.iters == 10) R.extra["ms10_prize"] = R.has ? R.best.prize : 0, R.extra["ms10_time"] = R.el();
    }
}

// ------------------------------------------------ GRASP
inline void runGRASP(Runner& R) {
    const Inst& I = R.I;
    while (!R.timeUp()) {
        double alpha = 0.05 + 0.35 * R.urand();
        Sol s = graspConstruct(I, alpha, R.rng);
        if (!s.feasible(I)) repair(I, s);
        improve(I, s);
        R.consider(s);
        R.iters++;
    }
}

// ------------------------------------------------ ILS (perturbação por remoção de segmento)
// No estilo de Vansteenwegen et al. (2009): remove S visitas consecutivas a partir de uma
// posição aleatória; S cresce a cada iteração sem melhoria e volta a 1 quando há melhoria.
inline void runILS(Runner& R) {
    const Inst& I = R.I;
    Sol cur = initialSolution(R);
    int S = 1, noImp = 0;
    while (!R.timeUp()) {
        Sol s = cur;
        int m = s.m();
        int start = R.irand(0, max(0, m - 1));
        int cnt = min(S, max(1, m - 1));
        for (int q = 0; q < cnt && s.m() > 1; q++) removeAt(I, s, start % s.m());
        coverClusters(I, s, 0);
        if (!s.feasible(I)) repair(I, s);
        improve(I, s);
        R.iters++;
        if (s.feasible(I) && better(s, R.best)) { R.consider(s); S = 1; noImp = 0; cur = s; }
        else {
            if (s.feasible(I)) cur = s;
            S++; noImp++;
            if (S > max(2, cur.m() / 3)) S = 1;
            if (noImp % 100 == 0) cur = R.best;  // reinício a partir da melhor
        }
    }
}

// ------------------------------------------------ VNS
// Vizinhança N_k: remove k nós aleatórios e insere k nós aleatórios de fora, seguido de
// reparo e busca local (VNS básico de Mladenović & Hansen, 1997).
inline Sol shake(Runner& R, const Sol& base, int k) {
    const Inst& I = R.I;
    Sol s = base;
    for (int q = 0; q < k && s.m() > 2; q++) {
        int idx = R.irand(0, s.m() - 1);
        if (removable(I, s, s.tour[idx])) removeAt(I, s, idx);
    }
    vector<int> outs;
    for (int v = 0; v < I.n; v++) if (!s.in[v]) outs.push_back(v);
    shuffle(outs.begin(), outs.end(), R.rng);
    for (int q = 0; q < k && q < (int)outs.size(); q++) insertBest(I, s, outs[q]);
    if (!s.feasible(I)) repair(I, s);
    return s;
}

inline void runVNS(Runner& R, int kmax = 6) {
    const Inst& I = R.I;
    Sol cur = initialSolution(R);
    int k = 1;
    while (!R.timeUp()) {
        Sol s = shake(R, cur, k);
        improve(I, s);
        R.iters++;
        if (s.feasible(I) && better(s, cur)) { cur = s; R.consider(s); k = 1; }
        else k = k % kmax + 1;
    }
}

// ------------------------------------------------ ALNS
// Ropke & Pisinger (2006): operadores de destruição/reconstrução escolhidos por roleta com
// pesos adaptativos e aceitação por recozimento simulado.
inline void runALNS(Runner& R) {
    const Inst& I = R.I;
    Sol cur = initialSolution(R);
    const int ND = 5, NR = 3;
    const char* dn[ND] = {"random", "worst", "segment", "radial", "cluster"};
    const char* rn[NR] = {"greedy", "regret", "noisy"};
    vector<double> wD(ND, 1), wR(NR, 1), sD(ND, 0), sR(NR, 0), cD(ND, 0), cR(NR, 0);
    double T0 = 0.05 * max(1.0, cur.prize), Tf = 0.001 * max(1.0, cur.prize);
    auto roulette = [&](vector<double>& w) {
        double tot = accumulate(w.begin(), w.end(), 0.0), r = R.urand() * tot;
        for (size_t i = 0; i < w.size(); i++) { r -= w[i]; if (r <= 0) return (int)i; }
        return (int)w.size() - 1;
    };
    long long it = 0;
    while (!R.timeUp()) {
        int od = roulette(wD), orr = roulette(wR);
        Sol s = cur;
        int m = s.m();
        int q = max(1, (int)(m * (0.1 + 0.3 * R.urand())));
        if (od == 0) {  // aleatória
            for (int t = 0; t < q && s.m() > 1; t++) removeAt(I, s, R.irand(0, s.m() - 1));
        } else if (od == 1) {  // pior razão (aleatorizada)
            for (int t = 0; t < q && s.m() > 2; t++) {
                vector<pair<double, int>> sc;
                for (int idx = 0; idx < s.m(); idx++) sc.push_back({removalGain(I, s, idx) / I.p[s.tour[idx]], idx});
                sort(sc.rbegin(), sc.rend());
                int pick = (int)(pow(R.urand(), 4) * sc.size());
                removeAt(I, s, sc[pick].second);
            }
        } else if (od == 2) {  // segmento consecutivo
            int st = R.irand(0, m - 1);
            for (int t = 0; t < q && s.m() > 1; t++) removeAt(I, s, st % s.m());
        } else if (od == 3) {  // radial (região geográfica em torno de um nó sorteado)
            int c = R.irand(0, I.n - 1);
            vector<pair<double, int>> dd;
            for (int v : s.tour) dd.push_back({I.d(c, v), v});
            sort(dd.begin(), dd.end());
            for (int t = 0; t < q && t < (int)dd.size() && s.m() > 1; t++) removeAt(I, s, indexOf(s, dd[t].second));
        } else {  // cluster: remove os representantes de um cluster e seus vizinhos no tour
            int k = R.irand(0, I.K - 1);
            vector<int> rm;
            for (int v : I.clusters[k]) if (s.in[v]) rm.push_back(v);
            for (int v : rm) {
                int idx = indexOf(s, v);
                if (idx >= 0 && s.m() > 1) removeAt(I, s, idx);
            }
            // força o uso de outro representante: insere o membro não removido mais barato
            double bc = 1e300; int bv = -1;
            for (int v : I.clusters[k]) {
                if (s.in[v] || find(rm.begin(), rm.end(), v) != rm.end()) continue;
                double c = bestInsertion(I, s, v).first;
                if (c < bc) { bc = c; bv = v; }
            }
            if (bv >= 0) insertBest(I, s, bv);
            int extra = max(0, q - (int)rm.size());
            for (int t = 0; t < extra && s.m() > 1; t++) removeAt(I, s, R.irand(0, s.m() - 1));
        }
        // reconstrução
        if (orr == 0) { coverClusters(I, s, 0); routeOpt(I, s); insertPhase(I, s); }
        else if (orr == 1) { coverClusters(I, s, 1); routeOpt(I, s); insertPhase(I, s); }
        else { coverClusters(I, s, 0, &R.rng, 0.2); routeOpt(I, s); insertPhase(I, s, 0.3, &R.rng); }
        if (!s.feasible(I)) repair(I, s);
        routeOpt(I, s);
        insertPhase(I, s);
        R.iters++; it++;
        double score = 0;
        if (s.feasible(I)) {
            double frac = min(1.0, R.el() / R.tlim);
            double T = T0 * pow(Tf / T0, frac);
            if (better(s, R.best)) {
                Sol t = s; improve(I, t);
                cur = t; R.consider(t); score = 33;
            } else if (better(s, cur)) { cur = s; score = 9; }
            else if (R.urand() < exp((s.prize - cur.prize) / T)) { cur = s; score = 13; }
        }
        sD[od] += score; cD[od]++; sR[orr] += score; cR[orr]++;
        if (it % 100 == 0) {
            for (int i = 0; i < ND; i++) if (cD[i] > 0) wD[i] = 0.9 * wD[i] + 0.1 * sD[i] / cD[i], sD[i] = cD[i] = 0;
            for (int i = 0; i < NR; i++) if (cR[i] > 0) wR[i] = 0.9 * wR[i] + 0.1 * sR[i] / cR[i], sR[i] = cR[i] = 0;
            for (auto& w : wD) w = max(w, 0.05);
            for (auto& w : wR) w = max(w, 0.05);
        }
    }
    for (int i = 0; i < ND; i++) R.extra[string("w_") + dn[i]] = wD[i];
    for (int i = 0; i < NR; i++) R.extra[string("w_") + rn[i]] = wR[i];
}

// ------------------------------------------------ Simulated Annealing
// Movimentos: inserção, remoção, troca 1-1 e 2-opt (só melhoria de comprimento).
// f(s) = prêmio - (0,01 min p / B) * comprimento.
inline void runSA(Runner& R) {
    const Inst& I = R.I;
    Sol cur = initialSolution(R);
    double coef = 0.01 * I.minP / max(I.B, 1e-9);
    double meanP = accumulate(I.p.begin(), I.p.end(), 0.0) / I.n;
    double T0 = 0.5 * meanP, Tf = 0.01 * I.minP;
    double cycle = R.tlim / 3.0;
    while (!R.timeUp()) {
        for (int rep = 0; rep < 200; rep++) {
            double frac = fmod(R.el(), cycle) / cycle;
            double T = T0 * pow(Tf / T0, frac);
            double u = R.urand();
            int m = cur.m();
            R.iters++;
            if (u < 0.25) {  // inserção
                int j = R.irand(0, I.n - 1);
                if (cur.in[j]) continue;
                auto [c, pos] = bestInsertion(I, cur, j);
                if (cur.len + c <= I.B + 1e-9) insertAt(I, cur, j, pos);
            } else if (u < 0.45) {  // remoção
                if (m < 3) continue;
                int idx = R.irand(0, m - 1);
                int v = cur.tour[idx];
                if (!removable(I, cur, v)) continue;
                double df = -I.p[v] + coef * removalGain(I, cur, idx);
                if (df >= 0 || R.urand() < exp(df / T)) removeAt(I, cur, idx);
            } else if (u < 0.75) {  // troca
                if (m < 3) continue;
                int j = R.irand(0, I.n - 1);
                if (cur.in[j]) continue;
                int idx = R.irand(0, m - 1);
                int v = cur.tour[idx];
                if (!removable(I, cur, v, j)) continue;
                InsTop t = insTop(I, cur, j);
                double nl = swapNewLen(I, cur, t, j, idx);
                if (nl > I.B + 1e-9) continue;
                double df = I.p[j] - I.p[v] - coef * (nl - cur.len);
                if (df >= 0 || R.urand() < exp(df / T)) { removeAt(I, cur, idx); insertBest(I, cur, j); }
            } else {  // 2-opt aleatório (aceita apenas se não piora)
                if (m < 4) continue;
                int i = R.irand(0, m - 3), j = R.irand(i + 2, m - 1);
                if (i == 0 && j == m - 1) continue;
                int a = cur.tour[i], b = cur.tour[i + 1], c = cur.tour[j], e = cur.tour[(j + 1) % m];
                double delta = I.d(a, c) + I.d(b, e) - I.d(a, b) - I.d(c, e);
                if (delta <= 0) { reverse(cur.tour.begin() + i + 1, cur.tour.begin() + j + 1); cur.len += delta; }
            }
            R.consider(cur);
        }
        routeOpt(I, cur);
        R.consider(cur);
    }
    Sol b = R.best; improve(I, b); R.consider(b);
}

// ------------------------------------------------ Busca Tabu
// Vizinhança: adição, remoção e troca 1-1 (amostrada); tabu por atributo de nó
// (nó removido não pode voltar, nó inserido não pode sair) com critério de aspiração.
inline void runTS(Runner& R) {
    const Inst& I = R.I;
    Sol cur = initialSolution(R);
    vector<long long> tabuAdd(I.n, -1), tabuDrop(I.n, -1);
    long long it = 0, lastImp = 0;
    while (!R.timeUp()) {
        it++; R.iters++;
        // melhor movimento: (delta prêmio, -novo comprimento)
        int type = -1, mi = -1, mj = -1; double bdp = -1e300, bnl = 1e300;
        auto cmp = [&](double dp, double nl) { return dp > bdp + EPS || (fabs(dp - bdp) <= EPS && nl < bnl - 1e-9); };
        int m = cur.m();
        // adição
        for (int j = 0; j < I.n; j++) {
            if (cur.in[j]) continue;
            auto [c, pos] = bestInsertion(I, cur, j);
            double nl = cur.len + c;
            if (nl > I.B + 1e-9) continue;
            bool tabu = tabuAdd[j] > it, asp = cur.prize + I.p[j] > R.best.prize + EPS;
            if (tabu && !asp) continue;
            if (cmp(I.p[j], nl)) { bdp = I.p[j]; bnl = nl; type = 0; mj = j; }
        }
        // troca (amostra de até 60 candidatos de fora)
        if (m >= 3) {
            vector<int> outs;
            for (int v = 0; v < I.n; v++) if (!cur.in[v]) outs.push_back(v);
            shuffle(outs.begin(), outs.end(), R.rng);
            if (outs.size() > 60) outs.resize(60);
            for (int j : outs) {
                if (tabuAdd[j] > it && cur.prize + I.p[j] <= R.best.prize + EPS) continue;
                InsTop t = insTop(I, cur, j);
                for (int idx = 0; idx < m; idx++) {
                    int v = cur.tour[idx];
                    double dp = I.p[j] - I.p[v];
                    bool asp = cur.prize + dp > R.best.prize + EPS;
                    if ((tabuDrop[v] > it || tabuAdd[j] > it) && !asp) continue;
                    if (!removable(I, cur, v, j)) continue;
                    double nl = swapNewLen(I, cur, t, j, idx);
                    if (nl > I.B + 1e-9) continue;
                    if (cmp(dp, nl)) { bdp = dp; bnl = nl; type = 1; mi = idx; mj = j; }
                }
            }
        }
        // remoção (só se nenhuma adição/troca melhora)
        if (bdp <= EPS && m >= 3) {
            for (int idx = 0; idx < m; idx++) {
                int v = cur.tour[idx];
                if (tabuDrop[v] > it || !removable(I, cur, v)) continue;
                double nl = cur.len - removalGain(I, cur, idx);
                if (type < 0 || cmp(-I.p[v], nl)) { bdp = -I.p[v]; bnl = nl; type = 2; mi = idx; }
            }
        }
        if (type < 0) { cur = R.best; continue; }
        int ten = R.irand(5, 15);
        if (type == 0) { insertBest(I, cur, mj); tabuDrop[mj] = it + ten; }
        else if (type == 1) {
            int v = cur.tour[mi];
            removeAt(I, cur, mi); insertBest(I, cur, mj);
            tabuAdd[v] = it + ten; tabuDrop[mj] = it + ten;
        } else {
            int v = cur.tour[mi];
            removeAt(I, cur, mi); tabuAdd[v] = it + ten;
        }
        routeOpt(I, cur);
        double before = R.best.prize;
        R.consider(cur);
        // intensificação: volta à melhor solução após 200 iterações sem melhoria
        if (R.best.prize > before + EPS) lastImp = it;
        else if (it - lastImp > 200) {
            cur = R.best; lastImp = it;
            fill(tabuAdd.begin(), tabuAdd.end(), -1); fill(tabuDrop.begin(), tabuDrop.end(), -1);
        }
    }
}

// ------------------------------------------------ Algoritmo Memético
// População de soluções GRASP+BL; cruzamento por segmento do pai A + nós do pai B na ordem
// de B (tour gigante), seguido de 2-opt, remoções por razão até caber em B e busca local.
inline Sol dropToBudget(const Inst& I, Sol s) {
    routeOpt(I, s);
    while (s.len > I.B + 1e-9 && s.m() > 1) {
        double best = -1e300; int bi = -1; bool bRem = false;
        for (int idx = 0; idx < s.m(); idx++) {
            int v = s.tour[idx];
            bool r = removable(I, s, v);
            double sc = removalGain(I, s, idx) / I.p[v];
            if ((r && !bRem) || (r == bRem && sc > best)) { best = sc; bi = idx; bRem = r; }
        }
        removeAt(I, s, bi);
    }
    if (!s.feasible(I)) repair(I, s);
    return s;
}

inline void runMA(Runner& R, int P = 10) {
    const Inst& I = R.I;
    vector<Sol> pop;
    pop.push_back(initialSolution(R));
    while ((int)pop.size() < P && !R.timeUp()) {
        Sol s = graspConstruct(I, 0.05 + 0.35 * R.urand(), R.rng);
        if (!s.feasible(I)) repair(I, s);
        improve(I, s);
        R.consider(s);
        pop.push_back(s);
    }
    auto tour = [&]() {
        int a = R.irand(0, pop.size() - 1), b = R.irand(0, pop.size() - 1);
        return better(pop[a], pop[b]) ? a : b;
    };
    while (!R.timeUp()) {
        const Sol& A = pop[tour()];
        const Sol& Bp = pop[tour()];
        Sol c; c.init(I);
        int mA = A.m();
        int len = max(1, (int)(mA * (0.3 + 0.4 * R.urand())));
        int st = R.irand(0, mA - 1);
        for (int q = 0; q < len; q++) c.tour.push_back(A.tour[(st + q) % mA]);
        vector<char> used(I.n, 0);
        for (int v : c.tour) used[v] = 1;
        for (int v : Bp.tour) if (!used[v]) { c.tour.push_back(v); used[v] = 1; }
        recompute(I, c);
        c = dropToBudget(I, c);
        if (R.urand() < 0.2) c = shake(R, c, 2);
        improve(I, c);
        R.iters++;
        if (!c.feasible(I)) continue;
        R.consider(c);
        int worst = 0;
        for (int i = 1; i < (int)pop.size(); i++) if (better(pop[worst], pop[i])) worst = i;
        bool dup = false;
        for (auto& p : pop) if (fabs(p.prize - c.prize) < EPS && fabs(p.len - c.len) < 1e-6) { dup = true; break; }
        if (!dup && better(c, pop[worst])) pop[worst] = c;
    }
}
