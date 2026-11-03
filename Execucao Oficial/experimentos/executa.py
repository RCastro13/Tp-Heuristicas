"""Executa os experimentos e grava uma linha JSON por execução em resultados/brutos/<grupo>.jsonl.

Grupos:
  heur    MSPD, MSPD-LS, VNS, ILS, ALNS e MA nas 408 instâncias, com 10 sementes e t(n) = max(1, n/50)
          (H1, H2, H3), e ILS-C nas classes T4 e PK (H4).
  exato   Formulação exata nas classes T1 a T3 (H3); requer heur concluído para a rota inicial.
  piloto  Subconjunto de instâncias para a etapa E6, com saída própria e uma semente.

  piloto_exato  Formulação exata nas instâncias do piloto.

Uso: python experimentos/executa.py <grupo> [workers] [tempo_exato_s]
Execuções já gravadas são puladas, o que permite retomar. Cada processo fica preso a um núcleo físico,
mantendo o primeiro livre para o sistema. Sem energia na tomada, os grupos oficiais esperam: a
bateria alteraria a frequência da CPU e os limites de tempo de relógio. O piloto grava em
resultados/piloto, separado dos resultados oficiais.
"""
import csv
import ctypes
import json
import os
import queue
import random
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import psutil

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCOP = os.path.join(RAIZ, "bin", "gcop.exe")
BRUTOS = os.path.join(RAIZ, "resultados", "brutos")
PASTA_PILOTO = os.path.join(RAIZ, "resultados", "piloto")
METODOS = ["MSPD", "MSPD-LS", "VNS", "ILS", "ALNS", "MA"]
SEMENTES = list(range(1, 11))
PILOTO = ["burma14_a025_unif", "eil51_a050_rand", "kroA100_a075_unif", "ch150_a025_rand", "d198_a050_rand",
          "pcb442_a050_unif", "d493_a025_rand", "cidadeA_B10_unif", "cidadeB_B20_freq"]


def t_n(n):
    return max(1.0, n / 50.0)


def na_tomada():
    b = psutil.sensors_battery()
    return b is None or b.power_plugged


def mantem_acordado():
    # ES_CONTINUOUS | ES_SYSTEM_REQUIRED: impede a suspensão só enquanto este processo existir
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)


def pasta_de(grupo):
    return PASTA_PILOTO if grupo.startswith("piloto") else BRUTOS


def nucleos_livres(workers):
    """Uma CPU lógica por núcleo físico, sem o primeiro núcleo (livre para o sistema)."""
    logicos = psutil.cpu_count(logical=True)
    fisicos = psutil.cpu_count(logical=False) or logicos
    passo = max(1, logicos // fisicos)
    cpus = [k * passo for k in range(fisicos - 1, 0, -1)]
    if workers > len(cpus):  # mais processos que núcleos: usa todas as CPUs lógicas
        cpus = list(range(logicos - 1, -1, -1))
    return cpus[:workers]


def monta_tarefas(grupo, inst, tempo_exato):
    tarefas = []
    rotas = os.path.join(pasta_de(grupo), "melhores_rotas.json")
    for r in inst:
        n = int(r["n"])
        base = [GCOP, "resolve", os.path.join(RAIZ, r["grafo"]), "--premio", r["premio"], "--B", r["B"], "--nome", r["nome"]]
        if grupo == "piloto":
            if r["nome"] in PILOTO:
                for a in METODOS + ["ILS-C"]:
                    tarefas.append(((r["nome"], a, 1), base + ["--algo", a, "--semente", "1", "--tempo", str(t_n(n))], t_n(n)))
        elif grupo == "heur":
            for a in METODOS + (["ILS-C"] if r["classe"] in ("T4", "PK") else []):
                for s in SEMENTES:
                    tarefas.append(((r["nome"], a, s), base + ["--algo", a, "--semente", str(s), "--tempo", str(t_n(n))], t_n(n)))
        elif grupo in ("exato", "piloto_exato") and r["classe"] in ("T1", "T2", "T3"):
            if grupo == "piloto_exato" and r["nome"] not in PILOTO:
                continue
            cmd = [sys.executable, os.path.join(RAIZ, "exato", "formulacao_exata.py"), r["nome"], str(tempo_exato), rotas]
            tarefas.append(((r["nome"], "EXATO", 0), cmd, tempo_exato))
    return tarefas


def grava_melhores_rotas(pasta, arq_heur):
    """Melhor rota de cada instância nas heurísticas: rota inicial da formulação exata."""
    melhores = {}
    with open(os.path.join(pasta, arq_heur)) as f:
        for linha in f:
            d = json.loads(linha)
            if d.get("viavel") and (d["inst"] not in melhores or (d["P"], -d["L"]) > melhores[d["inst"]][:2]):
                melhores[d["inst"]] = (d["P"], -d["L"], d["rota"])
    with open(os.path.join(pasta, "melhores_rotas.json"), "w") as f:
        json.dump({k: v[2] for k, v in melhores.items()}, f)


def main():
    grupo = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    tempo_exato = float(sys.argv[3]) if len(sys.argv) > 3 else 600.0
    with open(os.path.join(RAIZ, "dados", "instancias.csv")) as f:
        inst = list(csv.DictReader(f))
    pasta = pasta_de(grupo)
    os.makedirs(pasta, exist_ok=True)
    saida = os.path.join(pasta, f"{grupo}.jsonl")
    feitas = set()
    if os.path.exists(saida):
        with open(saida) as f:
            for linha in f:
                try:
                    d = json.loads(linha)
                except json.JSONDecodeError:
                    continue
                if "erro" not in d:
                    feitas.add((d["inst"], d["algo"], d.get("semente", 0)))
    if grupo == "exato":
        grava_melhores_rotas(pasta, "heur.jsonl")
    elif grupo == "piloto_exato":
        grava_melhores_rotas(pasta, "piloto.jsonl")
    tarefas = [t for t in monta_tarefas(grupo, inst, tempo_exato) if t[0] not in feitas]
    if grupo in ("exato", "piloto_exato"):  # menores primeiro: as provas de otimalidade saem cedo
        ordem = {r["nome"]: int(r["n"]) for r in inst}
        tarefas.sort(key=lambda t: ordem[t[0][0]])
    else:  # ordem aleatória fixa: resultados parciais representativos e carga homogênea
        random.Random(2026).shuffle(tarefas)
    livres = queue.Queue()
    nucleos = nucleos_livres(workers)
    for c in nucleos:
        livres.put(c)
    workers = len(nucleos)
    total = sum(t[2] for t in tarefas)
    print(f"{len(tarefas)} execucoes pendentes ({grupo}); ate {total / 3600 / workers:.1f} h com {workers} processos", flush=True)
    trava = threading.Lock()
    cont = [0]
    t_ini = time.time()

    def trabalha(tarefa):
        chave, cmd, lim = tarefa
        while not grupo.startswith("piloto") and not na_tomada():
            time.sleep(30)
        cpu = livres.get()
        try:
            mantem_acordado()
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                psutil.Process(p.pid).cpu_affinity([cpu])
            except psutil.Error:
                pass
            try:
                out, err = p.communicate(timeout=lim * 3 + 120)
                linhas = out.strip().splitlines()
                linha = linhas[-1] if linhas else json.dumps(dict(inst=chave[0], algo=chave[1], semente=chave[2], erro=err[-500:]))
            except subprocess.TimeoutExpired:
                p.kill()
                p.communicate()
                linha = json.dumps(dict(inst=chave[0], algo=chave[1], semente=chave[2], erro="timeout"))
        finally:
            livres.put(cpu)
        with trava:
            with open(saida, "a") as f:
                f.write(linha + "\n")
            cont[0] += 1
            if cont[0] % 100 == 0 or cont[0] == len(tarefas):
                print(f"{cont[0]}/{len(tarefas)} em {(time.time() - t_ini) / 3600:.2f} h", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(trabalha, tarefas))
    print("concluido", flush=True)


if __name__ == "__main__":
    main()
