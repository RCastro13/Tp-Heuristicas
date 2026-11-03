// MSPD-LS: ablação que isola o efeito da busca local. Idêntico ao MSPD (mesma construção,
// mesma perturbação, mesmo tempo), exceto pela fase de melhoria: REPARA seguido de BL.
#pragma once
#include "../mspd/mspd.hpp"

inline void executaMSPDLS(Executor& R) {
    const Inst& I = R.I;
    multiStart(R, [&](Sol& T) {
        if (repara(I, T)) buscaLocal(I, T);
    });
}
