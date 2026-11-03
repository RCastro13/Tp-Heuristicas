"""Registra em resultados/ambiente.json a máquina, as versões e as opções da execução oficial.

Uso: python experimentos/registra_ambiente.py "<opções de compilação>" <processos> <tempo_exato_s>
"""
import json
import os
import platform
import subprocess
import sys

import highspy
import matplotlib
import numpy
import pandas
import psutil
import scipy

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cpu():
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return out or platform.processor()
    except (OSError, subprocess.SubprocessError):
        return platform.processor()


def main():
    gpp = subprocess.run(["g++", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    h = highspy.Highs()
    amb = {
        "CPU": cpu(),
        "Núcleos físicos / lógicos": f"{psutil.cpu_count(logical=False)} / {psutil.cpu_count(logical=True)}",
        "RAM (GB)": round(psutil.virtual_memory().total / 1e9, 1),
        "Sistema": platform.platform(),
        "Compilador": gpp,
        "Opções de compilação": sys.argv[1] if len(sys.argv) > 1 else "",
        "Processos simultâneos": sys.argv[2] if len(sys.argv) > 2 else "",
        "Limite da formulação exata (s)": sys.argv[3] if len(sys.argv) > 3 else "",
        "HiGHS": f"{h.version()}",
        "Python": platform.python_version(),
        "numpy / pandas / scipy / matplotlib": f"{numpy.__version__} / {pandas.__version__} / {scipy.__version__} / {matplotlib.__version__}",
    }
    os.makedirs(os.path.join(RAIZ, "resultados"), exist_ok=True)
    with open(os.path.join(RAIZ, "resultados", "ambiente.json"), "w", encoding="utf-8") as f:
        json.dump(amb, f, indent=1, ensure_ascii=False)
    print(json.dumps(amb, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
