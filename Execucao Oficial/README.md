# Execução oficial: heurísticas para o GCOP

Implementação completa da metodologia do artigo *Heurísticas para o Problema de Orientação Agrupada Generalizada*. Para executar, veja [PIPELINE_EXECUCAO.txt](PIPELINE_EXECUCAO.txt).

## Organização

| Pasta | Conteúdo |
|---|---|
| `codigo_geral/` | Comum a todos os métodos: instância, solução, verificador, OTIMIZAROTA, cache de inserção, BL, REPARA, construções (NI, FI, ST, INICIAL, GRASP), AGITA, cálculo do orçamento e `main.cpp` |
| `heuristicas/mspd/` | Controle: MSPD e refinamento σ (Algoritmos 6 e 7) |
| `heuristicas/mspd_ls/` | MSPD-LS: ablação da busca local |
| `heuristicas/vns/` | VNS (Algoritmo 2) |
| `heuristicas/ils/` | ILS (Algoritmo 3) |
| `heuristicas/ils_c/` | ILS-C, usado só na H4 |
| `heuristicas/alns/` | ALNS (Algoritmo 4) |
| `heuristicas/ma/` | MA (Algoritmo 5) |
| `exato/` | Formulação exata no HiGHS, com geração iterativa de cortes (H3) |
| `instancias/` | Orçamentos TSPLIB-GCOP e geração das cidades POKE |
| `dados/` | 408 instâncias prontas |
| `experimentos/` | Executor resumível e registro do ambiente |
| `analise/` | Testes, tabelas, gráficos, vereditos e geração de `RESULTADOS.md` |
| `testes/` | Testes dos componentes comuns |
| `resultados/` | Saídas; `resultados/piloto/` guarda só a verificação do processo, não resultados do artigo |

## Da hipótese à saída

| Hipótese | Execuções | Tabelas | Figuras |
|---|---|---|---|
| H1 | MSPD e MSPD-LS, 408 instâncias | `h1_por_classe` | `h1_dispersao` |
| H2 | MSPD, MSPD-LS, VNS, ILS, ALNS e MA, 408 instâncias | `h2_medidas`, `h2_wilcoxon`, `h2_gap_por_classe` (complemento) | `h2_boxplot`, `h2_acumulada` |
| H3 | Formulação exata em T1 a T3 e execuções de H2 | `h3_gap_otimo`, `h3_exato` | |
| H4 | Execuções de H2 e ILS-C em T4 e PK | `h4_degradacao` | `h4_barras` |

## Executar um método isolado

```
bin\gcop.exe resolve dados\tsplib\eil51p00005.tsp --premio rand --B 298.53 --algo ALNS --semente 1 --tempo 1.02 --nome teste
```

Métodos: `MSPD`, `MSPD-LS`, `VNS`, `ILS`, `ILS-C`, `ALNS`, `MA`. Prêmios: `unif`, `rand`, `arquivo`.
