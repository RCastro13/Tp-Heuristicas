# Continuar a execução oficial: formulação exata

Estado em 04/11/2026. Branch: `execucao-oficial`. Compilação oficial: `-std=c++17 -static`, sem `-O2`, por decisão da equipe.

## O que já foi feito

- Bateria de heurísticas completa: 25.620 de 25.620 execuções, 0 falhas, 0 rotas divergentes (`resultados/brutos/heur.jsonl`). Durou cerca de 5h09.
- Análise parcial, sem a exata: `resultados/parcial_sem_exata/` (tabelas, figuras e `resumo.json`).

## O que falta

### 1. Formulação exata (H3)

Rodar no PowerShell, de qualquer terminal. Nenhuma preparação é necessária se `.venv` e `bin` ainda existirem nesta máquina:

```powershell
cd "D:\Códigos-VS\UFMG\2026-2\heuristicas\TP\Execucao Oficial"
powershell -ExecutionPolicy Bypass -File .\executa_tudo.ps1 -Etapa exato
```

- São 294 instâncias (T1 a T3), com limite de 600 s por instância e 5 processos: **no máximo 9,8 h**. As instâncias terminam em ordem crescente de tamanho, então as últimas são as mais demoradas.
- Se for interrompida, execute a mesma linha de novo: o que já foi gravado é pulado, e a instância interrompida é refeita.
- Saída: `resultados/brutos/exato.jsonl`. A rota inicial vem de `heur.jsonl` e é gravada em `resultados/brutos/melhores_rotas.json`.
- Evite carga pesada na máquina durante a execução: o limite é de tempo de relógio.

Em uma máquina nova ou em um clone novo, rode antes `-Etapa preparo`. Ele exige g++ 14.2.0 no PATH e Python 3.11 nativo, localizado com `py -3.11`.

**Não use a etapa padrão `tudo` nem `-Etapa heur` sem necessidade.** Com a bateria completa, `heur` não refaz nada, mas `tudo` também recompila e roda o piloto.

### 2. Análise final

```powershell
powershell -ExecutionPolicy Bypass -File .\executa_tudo.ps1 -Etapa analise
```

Gera `RESULTADOS.md`, `resultados/tabelas/`, `resultados/figuras/`, `resultados/resumo.json` e `resultados/ambiente.json`. Use as opções padrão: a etapa registra as opções de compilação recebidas, e o padrão é o que foi usado na bateria.

### 3. Conferência

- `RESULTADOS.md`, seção 2: 25620 de 25620 execuções, 0 falhas, 0 rotas divergentes e 0 instâncias em que uma heurística superou um ótimo declarado.
- Tabela `h3_exato`: o total deve ser **294**. Falhas da exata não entram em nenhuma contagem, então verifique isso aqui. Se faltar instância, execute `-Etapa exato` de novo.
- Linhas com `"erro"` em `exato.jsonl` indicam instâncias a refazer. A nova execução as refaz sozinha.

### 4. Depois da análise

- Refazer a comparação com e sem `brg180` usando o BKS final, com a exata incluída (ver abaixo), e informá-la no artigo.
- Fazer commit e push de `resultados/brutos/exato.jsonl`, `melhores_rotas.json`, `resultados/tabelas`, `resultados/figuras`, `resumo.json`, `ambiente.json` e `RESULTADOS.md`.

## Decisão da equipe: `brg180`

VNS, ILS, ALNS e MA não encontram solução viável em nenhuma das 240 execuções nas 6 instâncias `brg180` (nem com 30 s, testado em `brg180_a025_unif`). MSPD e MSPD-LS encontram em todas. A causa não foi confirmada; a hipótese é que a construção inicial e o REPARA não conseguem evitar as arestas de 10.000 do grafo.

**Decisão: manter os dados como estão**, com gap de 100% nessas execuções, sem alterar o código. O artigo deve trazer a comparação com e sem `brg180`, porque o veredito da H2 depende disso.

Valores parciais, sem a exata no BKS:

| Medida | Com `brg180` (408) | Sem `brg180` (402) |
|---|---|---|
| Gap médio MSPD | 2,064% | 2,080% |
| Gap médio MSPD-LS | 1,282% | 1,288% |
| Gap médio VNS | 2,215% | 0,755% |
| Gap médio ILS | 2,082% | 0,621% |
| Gap médio ALNS | 3,130% | 1,684% |
| Gap médio MA | 1,906% | 0,442% |
| ALNS vence o MSPD (p de Holm) | Não (0,097) | Sim (0,032) |
| Veredito da H2 (metaheurísticas) | Parcialmente confirmada | Confirmada |

A comparação usa as funções `wilcoxon` e `holm` de `analise/analisa.py`, sobre a matriz de gap médio por instância e método, removendo as instâncias cujo nome começa com `brg180`.

## Vereditos parciais (sem a exata)

- H1: confirmada (p < 0,0001).
- H2, metaheurísticas vencem o MSPD: parcialmente confirmada (VNS, ILS e MA vencem; ALNS não).
- H2, o MA é o melhor: confirmada (rank médio 2,24).
- H3: pendente.
- H4: confirmada (ILS-C vence o ILS em PK, p = 0,0088).

Eles podem mudar um pouco, porque a exata pode melhorar o BKS.

## Pontos conhecidos, sem correção por enquanto

- "Falhas de execução" conta também falhas que deram certo em nova tentativa. Na bateria atual o valor é 0.
- A tabela de vereditos do `RESULTADOS.md` mostra `p = < 0,0001`, com o sinal duplicado.
