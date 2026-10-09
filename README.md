# TP-Heurísticas — Generalized Clustered Orienteering Problem (GCOP)

Heurísticas, metaheurísticas e métodos de controle para o GCOP (Álvarez-Miranda et al., 2018).

- `docs/metodologia.md` — heurísticas propostas e de controle (origem, pseudocódigo, complexidade),
  ambiente, instâncias e hipóteses/experimentos.
- `docs/resultados.md` — resultados preliminares da bateria de testes.
- `src/` — implementação C++ (construtivas NI/FI/ST/TSPD, busca local, MSPD, GRASP, ILS, VNS, ALNS, SA, TS, MA).
- `scripts/` — instâncias (`build_instances.py`), métodos MIP com HiGHS (`mip.py`: BB-MTZ, EXACT-CUT, LBR),
  execução da bateria (`run_experiments.py`), complexidade (`timing.py`) e análise (`analyze.py`).
- `data/` — grafos TSPLIB-GCOP dos autores (`raw_download/`), instâncias POKE sintéticas (`poke/`) e `instances.csv`.
- `results/` — uma linha JSON por execução; `results/tables.md` com todas as tabelas.

## Reprodução

```
g++ -O2 -std=c++17 -static -o bin/gcop.exe src/main.cpp
g++ -O2 -std=c++17 -static -o bin/gcop_timing.exe src/main.cpp
python -m venv .venv && .venv/Scripts/pip install highspy numpy pandas scipy matplotlib tabulate
.venv/Scripts/python scripts/build_instances.py
.venv/Scripts/python scripts/run_experiments.py heur 6
.venv/Scripts/python scripts/run_experiments.py exact 2 600
.venv/Scripts/python scripts/run_experiments.py bb 3 600
.venv/Scripts/python scripts/run_experiments.py lbr 4 60
.venv/Scripts/python scripts/timing.py
.venv/Scripts/python scripts/analyze.py
```

Executar uma heurística isolada:

```
bin/gcop.exe solve data/raw_download/gcop-tsplib/gpctsp_tsplib/eil51p00005.tsp \
    --profit rand --budget 319.78 --algo ALNS --seed 1 --time 2
```
