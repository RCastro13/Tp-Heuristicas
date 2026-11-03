// Limite de tempo de relógio único por execução: t(n) inclui a construção inicial, então
// a busca local, o reparo e os métodos consultam o mesmo prazo.
#pragma once
#include <chrono>

struct Relogio {
    std::chrono::steady_clock::time_point t0 = std::chrono::steady_clock::now();
    double limite = 1e18;
    void inicia(double lim) { t0 = std::chrono::steady_clock::now(); limite = lim; }
    double decorrido() const { return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count(); }
    bool esgotado() const { return decorrido() >= limite; }
};

inline Relogio& relogio() { static Relogio r; return r; }
inline bool tempoEsgotado() { return relogio().esgotado(); }
