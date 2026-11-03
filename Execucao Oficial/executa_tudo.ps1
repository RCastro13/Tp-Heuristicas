# Pipeline completo da execução oficial. Ver PIPELINE_EXECUCAO.txt.
#   powershell -ExecutionPolicy Bypass -File .\executa_tudo.ps1
#   powershell -ExecutionPolicy Bypass -File .\executa_tudo.ps1 -Etapa exato
# Pode ser interrompido e executado de novo: as execuções já gravadas são puladas.
param(
    [ValidateSet("tudo", "preparo", "piloto", "heur", "exato", "analise")]
    [string]$Etapa = "tudo",
    [int]$Processos = 5,
    [string]$OpcoesCompilacao = "-std=c++17 -static",
    [string]$Gpp = "g++"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"
$TempoExato = 600  # limite por instância da formulação exata, em segundos
# com -Gpp por caminho completo, as ferramentas do mesmo compilador (as, ld) têm de vir primeiro no PATH
$dirGpp = Split-Path -Parent $Gpp
if ($dirGpp) { $env:Path = "$dirGpp;$env:Path" }

function Confere($passo) {
    if ($LASTEXITCODE -ne 0) { throw "Falha em: $passo (codigo $LASTEXITCODE)" }
}

function VenvValido {
    if (-not (Test-Path $py)) { return $false }
    # uma .venv copiada de outra máquina existe, mas não executa
    $ErrorActionPreference = "Continue"
    try { & $py -c "import sys" *> $null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}

function Preparo {
    if (-not (VenvValido)) {
        python -m venv --clear .venv; Confere "venv"
    }
    & $py -m pip install -q -r requirements.txt; Confere "pip"
    New-Item -ItemType Directory -Force bin | Out-Null
    $op = $OpcoesCompilacao -split " "
    & $Gpp @op -o bin\gcop.exe codigo_geral\main.cpp; Confere "compilar gcop"
    & $Gpp @op -o bin\testes.exe testes\testes.cpp; Confere "compilar testes"
    if (-not (Test-Path dados\instancias.csv)) {
        & $py instancias\gera_instancias.py $Processos; Confere "instancias"
    }
    .\bin\testes.exe dados\tsplib\eil51p00005.tsp dados\poke\cidadeA.tsp | Select-Object -Last 1
    Confere "testes"
}

function Piloto {
    & $py experimentos\executa.py piloto $Processos; Confere "piloto"
    & $py experimentos\executa.py piloto_exato $Processos 60; Confere "piloto exato"
    & $py analise\analisa.py resultados\piloto\piloto.jsonl resultados\piloto\piloto_exato.jsonl resultados\piloto; Confere "analise piloto"
}

function Analise {
    & $py experimentos\registra_ambiente.py "$OpcoesCompilacao" $Processos $TempoExato; Confere "ambiente"
    & $py analise\analisa.py; Confere "analise"
    & $py analise\gera_documento.py; Confere "documento"
}

if ($Etapa -in "tudo", "preparo") { Preparo }
if ($Etapa -in "tudo", "piloto") { Piloto }
if ($Etapa -in "tudo", "heur") { & $py experimentos\executa.py heur $Processos; Confere "heuristicas" }
if ($Etapa -in "tudo", "exato") { & $py experimentos\executa.py exato $Processos $TempoExato; Confere "exato" }
if ($Etapa -in "tudo", "analise") { Analise }
