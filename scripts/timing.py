"""Complexidade empírica das construtivas e buscas locais: tempo médio (R repetições) em
uma instância por grafo (alpha = 0,5; prêmio pseudo-aleatório / por espécie).
Saída: results/timing.jsonl. Uso: python scripts/timing.py"""
import csv
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = os.path.join(ROOT, "bin", "gcop_timing.exe")
VARIANTS = [f"{c}{s}" for c in ["NI", "FI", "ST", "TSPD"] for s in ["", "-SR", "-LS"]]


def main():
    with open(os.path.join(ROOT, "data", "instances.csv")) as f:
        rows = [r for r in csv.DictReader(f)
                if (r["set"] == "TSPLIB" and r["alpha"] == "0.5" and r["profit"] == "rand")
                or (r["set"] == "POKE" and r["B"] == "15" and r["profit"] == "file")]
    out = open(os.path.join(ROOT, "results", "timing.jsonl"), "w")
    for r in rows:
        n = int(r["n"])
        reps = 50 if n <= 100 else 10 if n <= 200 else 5
        for a in VARIANTS:
            p = subprocess.run([EXE, "solve", os.path.join(ROOT, r["graph"]), "--profit", r["profit"], "--budget", r["B"],
                                "--algo", a, "--reps", str(reps), "--name", r["name"]], capture_output=True, text=True, check=True)
            d = json.loads(p.stdout)
            d.pop("tour", None); d.pop("trace", None)
            out.write(json.dumps(d) + "\n")
        print(r["name"], flush=True)


if __name__ == "__main__":
    main()
