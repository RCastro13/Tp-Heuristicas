"""Executa a bateria de testes e grava uma linha JSON por execução em results/<grupo>.jsonl.

Grupos:
  heur   — construtivas (12 configurações, 1 execução) e metaheurísticas (5 sementes,
           tempo t(n) = max(1, n/50) s)
  bb     — baseline B&B (MTZ) com tempo fixo
  exact  — referência exata (CUT) com tempo fixo (n <= NMAX_EXACT)
  lbr    — matheurística MSPD + Local Branching (n <= NMAX_EXACT)

Uso: python scripts/run_experiments.py <grupo> [workers] [tempo] [asc]
Execuções já presentes no arquivo de saída são puladas (permite retomar).
"""
import csv
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCOP = os.path.join(ROOT, "bin", "gcop.exe")
PY = sys.executable
CONSTRUCTIVE = [f"{c}{s}" for c in ["NI", "FI", "ST", "TSPD"] for s in ["", "-SR", "-LS"]]
META = ["MSPD", "MSPD-LS", "GRASP", "ILS", "VNS", "ALNS", "SA", "TS", "MA"]
SEEDS = [1, 2, 3, 4, 5]
NMAX_EXACT = 200


def tlimit(n):
    return max(1.0, n / 50.0)


def main():
    group = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    tfix = float(sys.argv[3]) if len(sys.argv) > 3 else None
    with open(os.path.join(ROOT, "data", "instances.csv")) as f:
        insts = list(csv.DictReader(f))
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    out_path = os.path.join(ROOT, "results", f"{group}.jsonl")
    # 2º executor concorrente grava em arquivo próprio (evita escrita intercalada)
    paths = [out_path]
    if len(sys.argv) > 4 and sys.argv[4] == "asc":
        out_path = os.path.join(ROOT, "results", f"{group}_asc.jsonl")
        paths.append(out_path)
    done = set()
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    done.add((d["inst"], d["algo"], d["seed"]))
                except json.JSONDecodeError:
                    pass
    jobs = []
    for r in insts:
        n = int(r["n"])
        g = os.path.join(ROOT, r["graph"])
        base = [GCOP, "solve", g, "--profit", r["profit"], "--budget", r["B"], "--name", r["name"]]
        if group == "heur":
            for a in CONSTRUCTIVE:
                jobs.append(((r["name"], a, 1), base + ["--algo", a, "--seed", "1", "--time", "60"]))
            for a in META:
                for s in SEEDS:
                    jobs.append(((r["name"], a, s), base + ["--algo", a, "--seed", str(s), "--time", str(tlimit(n))]))
        elif group == "bb":
            jobs.append(((r["name"], "BB", 0), [PY, os.path.join(ROOT, "scripts", "mip.py"), "bb", r["name"], str(tfix or 120)]))
        elif group == "exact" and n <= NMAX_EXACT:
            jobs.append(((r["name"], "EXACT", 0), [PY, os.path.join(ROOT, "scripts", "mip.py"), "cut", r["name"], str(tfix or 300)]))
        elif group == "lbr" and n <= NMAX_EXACT:
            jobs.append(((r["name"], "LBR", 1), [PY, os.path.join(ROOT, "scripts", "mip.py"), "lbr", r["name"], str(tfix or 60), str(tlimit(n)), "1"]))
    jobs = [j for j in jobs if j[0] not in done]
    # maiores primeiro (melhor balanceamento); "asc" inverte, para um 2º executor concorrente
    asc = len(sys.argv) > 4 and sys.argv[4] == "asc"
    jobs.sort(key=lambda j: (1 if asc else -1) * next(int(r["n"]) for r in insts if r["name"] == j[0][0]))
    print(f"{len(jobs)} execucoes pendentes ({group})", flush=True)
    lock = threading.Lock()
    cnt = [0]

    def work(job):
        key, cmd = job
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            line = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else None
            if not line:
                line = json.dumps(dict(inst=key[0], algo=key[1], seed=key[2], error=p.stderr[-500:]))
        except subprocess.TimeoutExpired:
            line = json.dumps(dict(inst=key[0], algo=key[1], seed=key[2], error="timeout"))
        with lock:
            with open(out_path, "a") as f:
                f.write(line + "\n")
            cnt[0] += 1
            if cnt[0] % 50 == 0 or cnt[0] == len(jobs):
                print(f"{cnt[0]}/{len(jobs)}", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, jobs))


if __name__ == "__main__":
    main()
