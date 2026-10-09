# Heurísticas para o Problema de Orientação Agrupada Generalizada (GCOP) — Metodologia

> Documento de apoio às Seções 2 e 3 do projeto (TP). Cobre as heurísticas propostas e as de
> controle, com origem bibliográfica, descrição e pseudocódigo; o ambiente de execução; as
> instâncias; e o desenho experimental de cada hipótese. Os resultados preliminares estão em
> [`resultados.md`](resultados.md). O código está em `src/` (C++) e `scripts/` (Python).

## Sumário

1. [Notação e representação da solução](#1-notação-e-representação-da-solução)
2. [Visão geral das heurísticas](#2-visão-geral-das-heurísticas)
3. [Componentes básicos (operadores compartilhados)](#3-componentes-básicos-operadores-compartilhados)
4. [Heurísticas de controle (literatura)](#4-heurísticas-de-controle)
5. [Heurísticas propostas](#5-heurísticas-propostas)
6. [Resumo de complexidade](#6-resumo-de-complexidade)
7. [Ambiente de execução dos experimentos](#7-ambiente-de-execução-dos-experimentos)
8. [Instâncias de teste](#8-instâncias-de-teste)
9. [Hipóteses e experimentos](#9-hipóteses-e-experimentos)
10. [Referências](#10-referências)

---

## 1. Notação e representação da solução

- $G=(V,E)$ grafo completo não direcionado, $|V|=n$; $d_{ij}\ge 0$ distância (simétrica, não
  necessariamente métrica); $p_i\ge 0$ prêmio do nó $i$.
- $\mathcal C=\{C_1,\dots,C_K\}$ clusters (não necessariamente disjuntos; pode haver nós fora de
  qualquer cluster); $B$ orçamento de comprimento.
- **Solução**: sequência cíclica $T=(v_1,\dots,v_m)$ de nós distintos; $V_T$ é o conjunto de nós
  visitados, $L(T)=\sum_{q=1}^{m} d_{v_q v_{q+1}}$ (com $v_{m+1}=v_1$) e $P(T)=\sum_{i\in V_T}p_i$.
- **Viabilidade**: $V_T\cap C_k\neq\emptyset\ \forall k$ e $L(T)\le B$.
- **Comparação** entre soluções viáveis: maior $P(T)$; em empate, menor $L(T)$ (mais folga de
  orçamento para movimentos futuros).

Estruturas mantidas incrementalmente: vetor `in[v]`, contador `ccount[k]` de nós visitados por
cluster e número de clusters descobertos — o que torna em $O(|\mathcal C(v)|)$ o teste "remover
$v$ descobre algum cluster?".

Quantidades usadas por quase todos os operadores (custo $O(1)$ ou $O(m)$):

- custo de inserção de $v$ entre $a$ e $b$: $\Delta^{+}(v,a,b)=d_{av}+d_{vb}-d_{ab}$;
  inserção mais barata: $\Delta^{+}(v)=\min_{(a,b)\in T}\Delta^{+}(v,a,b)$ — $O(m)$;
- ganho de remoção de $v$ (com vizinhos $a$, $b$ no tour): $\Delta^{-}(v)=d_{av}+d_{vb}-d_{ab}$ — $O(1)$;
- escore $\sigma$ do artigo: $\sigma_i=\min_{j\in V_T\setminus\{i\}} d_{ij}/p_i$ — $O(m)$ por nó.

## 2. Visão geral das heurísticas

| Sigla | Tipo | Papel | Origem |
|---|---|---|---|
| NI, FI | construtiva | controle | Inserção mais próxima/distante para o GTSP (Fischetti et al., 1997), usada no artigo base |
| ST | construtiva | controle | Árvore de Steiner por caminhos mais curtos (Takahashi e Matsuyama, 1980) + pré-ordem, usada no artigo base |
| TSPD | construtiva | proposta (adaptação) | "Route-first": TSP sobre todos os nós + remoções por razão (inspirada na construção TSP do artigo e em heurísticas de remoção para o OP) |
| -SR | busca local | controle | Refinamento (a)–(e) baseado em $\sigma$ do artigo base |
| -LS | busca local | **proposta** | Busca local com custos exatos ($\Delta^+$, $\Delta^-$, troca 1-1 exata) |
| MSPD | metaheurística | controle | Multi-start com distâncias perturbadas $\tilde d\sim U[d,1{,}2d]$ (heurística de inicialização do artigo) |
| MSPD-LS | metaheurística | ablação | MSPD com a BL proposta no lugar do refinamento $\sigma$ |
| GRASP | metaheurística | **proposta** | Feo e Resende (1995); Campos et al. (2014) para o OP |
| ILS | metaheurística | **proposta** | Lourenço et al. (2003); perturbação de Vansteenwegen et al. (2009) |
| VNS | metaheurística | **proposta** | Mladenović e Hansen (1997); Sevkli e Sevilgen (2006) para o OP |
| ALNS | metaheurística | **proposta** | Ropke e Pisinger (2006); operadores geográfico e por cluster específicos do GCOP |
| SA | metaheurística | **proposta** | Kirkpatrick et al. (1983); Lin e Yu (2012) para o TOPTW |
| TS | metaheurística | **proposta** | Glover (1989); Gendreau et al. (1998) para o TSP seletivo |
| MA | metaheurística | **proposta** | Moscato (1989); Tasgetiren (2002) (AG para o OP) |
| LBR | matheurística | controle | MSPD + *Local Branching* (Fischetti e Lodi, 2003) com $k=2,4,6$, como no artigo |
| BB | exato truncado | **baseline** | Formulação compacta MTZ do artigo em *branch-and-bound* (HiGHS) por tempo fixo |
| EXACT | exato | referência | Formulação (CUT) do artigo com GSECs gerados sob demanda — fornece ótimos/limitantes |

As ideias do arquivo `ideias.md` (construtivas NI/FI, Steiner e TSP; reparo; inserção obrigatória
e opcional; troca; 2-opt/3-opt; multi-start perturbado; *local branching*; ILS/ALNS com ruína
geográfica e reconstrução por *regret*) estão todas implementadas. As ideias **adicionais**
propostas aqui são: a BL exata (-LS), a construção TSPD, GRASP, VNS, SA, Busca Tabu, Algoritmo
Memético, o operador de destruição por cluster do ALNS, a ablação MSPD-LS e o método EXACT como
fonte de ótimos de referência.

---

## 3. Componentes básicos (operadores compartilhados)

Implementação: `src/solution.hpp` e `src/localsearch.hpp`.

### 3.1 Otimização de rota: 2-opt e Or-opt

**Origem.** 2-opt (Croes, 1958); 3-opt (Lin, 1965); Or-opt (Or, 1976) — o caso restrito do 3-opt
que realoca segmentos de 1 a 3 nós consecutivos. O artigo base aplica "2-opt e 3-opt"
exaustivamente; usamos Or-opt como a variante de 3-opt, por ser $O(m^2)$ por passada em vez de $O(m^3)$.

```
procedimento OTIMIZA_ROTA(T)
    repita até 100 vezes
        a ← 2OPT(T);  b ← OROPT(T)
        se não a e não b: pare

procedimento 2OPT(T)                                   ▷ primeira melhoria, passada completa
    repita
        melhorou ← falso
        para i = 0 .. m−3, j = i+2 .. m−1 (exceto i=0, j=m−1)
            δ ← d(t_i,t_j) + d(t_{i+1},t_{j+1}) − d(t_i,t_{i+1}) − d(t_j,t_{j+1})
            se δ < 0: inverte t_{i+1..j}; L ← L + δ; melhorou ← verdadeiro
    até não melhorou

procedimento OROPT(T)
    para L = 1, 2, 3; para cada segmento S = t_s..t_{s+L−1} com vizinhos pr, nx
        g ← d(pr,t_s) + d(t_{s+L−1},nx) − d(pr,nx)          ▷ ganho ao retirar S
        (c,e,inv) ← aresta não adjacente a S que minimiza o custo de reinserir S (direto ou invertido)
        se custo < g: move S para entre c e e (invertido se inv)
```

Os movimentos só alteram a ordem — $V_T$ e $P(T)$ não mudam; o objetivo é liberar orçamento.

### 3.2 Cobertura de clusters (inserção obrigatória)

**Origem.** Passo (b) do refinamento do artigo; o critério *regret-2* vem de Ropke e Pisinger (2006).

```
procedimento COBRE_CLUSTERS(T, modo)
    enquanto existe cluster descoberto
        para cada cluster descoberto C_k: c1(k), c2(k) ← 1º e 2º menores Δ+(v), v ∈ C_k
        se modo = barato: k* ← argmin_k c1(k)            ▷ inserção mais barata global
        se modo = regret: k* ← argmax_k (c2(k) − c1(k))  ▷ maior arrependimento primeiro
        insere em T o nó de C_{k*} que realiza c1(k*), na melhor posição
```

### 3.3 Inserção por razão (inserção opcional)

**Origem.** Critério guloso prêmio/custo clássico do OP (Tsiligirides, 1984; Golden et al., 1987);
corresponde ao passo (c) do artigo, porém com o custo **exato** de inserção $\Delta^+(v)$ em vez de
$\sigma$. Um *cache* guarda, para cada nó fora do tour, a melhor aresta de inserção; após inserir
$v^*$ entre $a$ e $b$, só os nós cuja melhor aresta era $(a,b)$ são recalculados — os demais apenas
comparam as duas arestas novas.

```
procedimento INSERE_RAZAO(T, ruído ε = 0)
    para cada v ∉ T: (Δ+(v), aresta(v)) ← inserção mais barata
    repita
        F ← { v ∉ T : L + Δ+(v) ≤ B }
        se F = ∅: pare
        v* ← argmax_{v∈F} p_v / max(Δ+(v), τ) · U[1−ε, 1+ε]
        insere v* em aresta(v*); atualiza o cache
```

### 3.4 Troca 1-1 exata (swap)

**Origem.** Passo (d) do artigo (troca $i\in V_T$ por $j\notin V_T$). Na versão proposta, o novo
comprimento é **exato**: guardam-se as três melhores arestas de inserção de $j$, e após remover $i$
o custo de inserir $j$ é o mínimo entre a melhor dessas arestas não adjacente a $i$ e a nova aresta
$(\text{prev}(i),\text{next}(i))$ — $O(1)$ por par $(i,j)$.

```
procedimento TROCA(T)
    para cada j ∉ T em ordem decrescente de p_j
        top3 ← três melhores arestas de inserção de j                    ▷ O(m)
        i* ← argmax_{i∈T} (p_j − p_i, −L')  sujeito a:
              p_j ≥ p_i;  remover i não descobre cluster (exceto se j o cobre);
              L' = L − Δ−(i) + custo_exato(j | T∖{i}) ≤ B;
              se p_j = p_i então L' < L
        se i* existe: remove i*, insere j na melhor posição
```

### 3.5 Busca local exata proposta (sufixo -LS)

```
procedimento BL(T)
    repita até 50 vezes
        OTIMIZA_ROTA(T)
        a ← INSERE_RAZAO(T);  b ← TROCA(T)
        se não a e não b: pare
```

A BL só aceita movimentos que mantêm a viabilidade e nunca piora $(P,−L)$ — termina em um ótimo
local simultâneo das vizinhanças 2-opt, Or-opt, inserção e troca 1-1.

### 3.6 Reparo de viabilidade

**Origem.** Passos (a) e (b) do artigo, com o critério $\Delta^-(v)/p_v$ (remoção do nó que mais
encurta o tour por unidade de prêmio) e proteção dos nós que são o único representante do seu cluster.

```
procedimento REPARA(T)
    repita até 20 vezes
        OTIMIZA_ROTA(T)
        enquanto L > B
            v* ← argmax Δ−(v)/p_v entre nós removíveis (se não houver, entre todos)
            remove v*
        COBRE_CLUSTERS(T, barato)
        se T é viável: retorne verdadeiro
    retorne T é viável
```

---

## 4. Heurísticas de controle

São as heurísticas descritas por Álvarez-Miranda, Luipersbeck e Sinnl (2018) no próprio artigo que
define o GCOP — o único trabalho da literatura sobre o problema — além do *branch-and-bound* de
tempo fixo como *baseline*.

### 4.1 NI / FI — inserção do mais próximo / mais distante para o GTSP

**Origem.** Adaptação das heurísticas de inserção do TSP (Rosenkrantz et al., 1977) ao GTSP por
Fischetti, Salazar-González e Toth (1997); o artigo base as usa como esquema de construção 1. A
solução visita um conjunto mínimo de nós (um por cluster), por isso o prêmio é baixo e a fase de
refinamento é essencial.

```
procedimento GTSP_INSERCAO(modo ∈ {próximo, distante}, s)
    T ← (s);  dist(v) ← d(s,v) ∀v
    enquanto existe cluster descoberto
        δ_k ← min_{v∈C_k} dist(v) para cada C_k descoberto
        k* ← argmin_k δ_k (próximo)  ou  argmax_k δ_k (distante)
        v* ← argmin_{v∈C_{k*}} Δ+(v);  insere v* na melhor posição
        dist(v) ← min(dist(v), d(v*,v)) ∀v
    retorne T
```

Nó inicial determinístico: menor índice do menor cluster. Complexidade $O(K\,(n + |C|_{\max} K))$.

### 4.2 ST — construção por árvore de Steiner

**Origem.** Esquema 2 do artigo base, que generaliza a heurística MST do TSP (Rosenkrantz et al., 1977):
um grafo auxiliar recebe um terminal artificial $t_k$ ligado a todos os nós de $C_k$; uma árvore de
Steiner heurística é obtida pela heurística de caminhos mais curtos de Takahashi e Matsuyama (1980)
e o tour é o percurso em pré-ordem da árvore. Como no grafo auxiliar as arestas até $t_k$ têm custo
zero, "conectar $t_k$" equivale a alcançar o nó mais próximo de $C_k$ — implementado com Dijkstra
multi-fonte a partir da árvore (válido também sem desigualdade triangular, e os nós intermediários
dos caminhos também coletam prêmio).

```
procedimento STEINER(r)
    A ← árvore com o nó r
    enquanto existe cluster descoberto
        (dist, pai) ← DIJKSTRA com todas as fontes em A (custo 0)
        v* ← nó de cluster descoberto com menor dist
        adiciona a A o caminho de v* até A (pai[·])
    T ← pré-ordem de A a partir de r (filhos do mais próximo ao mais distante)
    OTIMIZA_ROTA(T);  retorne T
```

Complexidade $O(K n^2)$ (Dijkstra denso por cluster). O artigo usa distâncias escaladas pela
relaxação linear ($d_e(1-\tilde x_e)$); sem B&C, usamos $d$ (ou $\tilde d$ perturbada no MSPD).

### 4.3 Refinamento $\sigma$ do artigo (sufixo -SR)

**Origem.** Passos (a)–(e) do *primal heuristic* de Álvarez-Miranda et al. (2018), com
$\sigma_i=\min_{j\in V_T\setminus\{i\}} d_{ij}/p_i$ (menor é melhor). Repete-se enquanto o prêmio
aumenta ou o comprimento diminui, com no máximo 10 rodadas.

```
procedimento REFINO_SIGMA(T)
    para rodada = 1..10
        (a) enquanto L > B: remove argmax_{i∈V_T} σ_i
        (b) para cada C_k descoberto: insere argmin_{i∈C_k} σ_i (inserção mais barata)
        (c) repita: percorre v ∉ T em ordem crescente de σ e insere o primeiro que couber em B
        (d) para i ∈ T (σ decrescente): troca por j ∉ T com σ_j < σ_i se viável e cluster preservado
        (e) OTIMIZA_ROTA(T)                                     ▷ 2-opt e 3-opt (Or-opt)
        se P não aumentou e L não diminuiu: pare
```

Duas interpretações registradas: em (c) o artigo diz "enquanto $D(V_T\cup\{i^*\})\le B$"; adotamos
"inserir o primeiro de menor $\sigma$ que caiba" (menos restritivo). Em (d) o texto do artigo
escreve $\sigma_i<\sigma_j$; como $\sigma$ menor é melhor, a troca que faz sentido é $\sigma_j<\sigma_i$.

### 4.4 MSPD — multi-start com distâncias perturbadas

**Origem.** Heurística de inicialização do artigo base: 10 iterações de construção+refinamento com
$\tilde d_e\sim U[d_e, 1{,}2\,d_e]$. A cada chamada sorteia-se a construção NI ou ST (o artigo não
encontrou dominância entre elas). Aqui ela roda até o tempo limite $t(n)$; o prêmio após as 10
primeiras iterações (configuração original) também é registrado.

```
procedimento MSPD(tempo)
    T* ← ∅
    enquanto houver tempo
        d̃ ← d · U[1; 1,2] (simétrica)
        s ← nó aleatório de cluster aleatório
        T ← NI(d̃, s) ou STEINER(d̃, s) (50% cada)
        reavalia T com d; OTIMIZA_ROTA(T); REFINO_SIGMA(T)     ▷ MSPD-LS: REPARA + BL
        se T viável e melhor que T*: T* ← T
    retorne T*
```

### 4.5 LBR — *Local Branching* (matheurística)

**Origem.** Fischetti e Lodi (2003); aplicada pelo artigo base sobre a melhor solução do MSPD. Dada
a incumbente $T$, resolve-se o MIP restrito à vizinhança
$\sum_{i\notin V_T} y_i + \sum_{i\in V_T}(1-y_i)\le k$ acrescido do corte de melhoria
$\sum_i p_i y_i \ge P(T)+1$. Começa com $k=2$; sem melhoria em 20 s (ou vizinhança provada vazia),
$k\leftarrow k+2$ até 6; ao melhorar, $k$ volta a 2. O MIP é a formulação (CUT) (seção 4.7), e os
GSECs gerados ficam no modelo entre iterações (pool de cortes), como no artigo.

```
procedimento LBR(tempo_total)
    T ← MSPD(t(n));  k ← 2
    enquanto houver tempo e k ≤ 6
        adiciona LB(T,k) e corte de melhoria ao modelo CUT
        T' ← RESOLVE_CUT(limite 20 s, para na 1ª solução)
        remove LB e corte de melhoria
        se T' existe: T ← T'; k ← 2   senão: k ← k + 2
    retorne T
```

### 4.6 BB — *branch-and-bound* de tempo fixo (baseline)

**Origem.** Formulação compacta (MTZ) de Álvarez-Miranda et al. (2018, §3.2), extensão das
restrições de Miller, Tucker e Zemlin (1960) ao caso não enraizado: variáveis de arco $t_{ij}$,
nó $y_i$, escolha do nó inicial $z_i$ em $C_1$ (escolhemos o menor cluster) e posições $u_i$;
restrições (MTZ.1)–(MTZ.9), (CLUSTER+), (BUDGET), (GSEC-2) e (ASYM). É resolvida pelo B&B do
HiGHS (1 *thread*) com limite de tempo fixo; registram-se a melhor solução primal, o limitante dual
e o número de nós. É o "solver de prateleira" que um praticante usaria sem implementar heurísticas.

```
procedimento BB(tempo)
    monta o modelo MTZ; resolve com HiGHS até ótimo ou tempo
    retorne (melhor solução, limitante superior, nós explorados)
```

### 4.7 EXACT — referência exata (formulação CUT)

**Origem.** Formulação (CUT) do artigo (§3.3) com GSECs (Fischetti et al., 1997). Em vez de um
B&C completo com separação fracionária, usamos geração de linhas em soluções **inteiras**: resolve-se
o MIP com (DEGREE), (CLUSTER+), (BUDGET) e GSECs de tamanho 2; se a solução tiver mais de um ciclo,
para cada ciclo $S$ acrescentam-se (GSEC.1) se $S$ e $V\setminus S$ contêm clusters inteiros,
(GSEC.2) se só $V\setminus S$ contém, ou (GSEC) caso contrário; repete-se. É exato quando termina, e o
limitante dual de cada MIP é um limitante superior válido. Não é uma heurística: serve para medir o
gap ao ótimo.

---

## 5. Heurísticas propostas

Todas as metaheurísticas: limite de tempo $t(n)=\max(1, n/50)$ s, critério "melhor que" da §1,
registro da trajetória (tempo, melhor prêmio) e semente controlada. Solução inicial das
metaheurísticas de trajetória (ILS, VNS, ALNS, SA, TS e o 1º indivíduo do MA): a melhor entre
NI-LS, FI-LS e ST-LS (`INICIAL`).

### 5.1 TSPD — construção "route-first" com remoções

**Origem.** Esquema 3 do artigo (tour TSP ótimo sobre os nós promissores $\tilde y_i\ge 0{,}5$, com
Concorde) adaptado para não depender de relaxação linear nem de Concorde: toma-se $\tilde V = V$, um
tour TSP heurístico (vizinho mais próximo + 2-opt/Or-opt) e removem-se nós pela razão
$\Delta^-(v)/p_v$ — a estratégia de remoção ("drop") clássica de heurísticas para o OP, análoga ao
passo (a) do artigo, porém protegendo clusters.

```
procedimento TSPD()
    T ← VIZINHO_MAIS_PRÓXIMO(V); OTIMIZA_ROTA(T)
    enquanto L > B
        remove v* = argmax Δ−(v)/p_v entre removíveis
        a cada 10% de redução de |T|: OTIMIZA_ROTA(T)
    REPARA(T)
```

### 5.2 GRASP

**Origem.** Feo e Resende (1995); GRASP para o OP em Campos et al. (2014). Cada iteração constrói
uma solução gulosa-aleatorizada com lista restrita de candidatos (LRC) e aplica a BL proposta.
$\alpha\sim U[0{,}05; 0{,}40]$ por iteração (variante "reativa" simplificada).

```
procedimento GRASP(tempo)
    enquanto houver tempo
        α ← U[0,05; 0,40];  T ← (nó aleatório de cluster aleatório)
        enquanto existe cluster descoberto                         ▷ fase 1: cobertura
            c(v) ← Δ+(v) para v em clusters descobertos
            LRC ← { v : c(v) ≤ c_min + α (c_max − c_min) };  insere v ∈_R LRC
        repita                                                     ▷ fase 2: prêmio
            r(v) ← p_v/Δ+(v) para v ∉ T com L + Δ+(v) ≤ B
            LRC ← { v : r(v) ≥ r_max − α (r_max − r_min) };  insere v ∈_R LRC
        até não haver candidato
        BL(T); atualiza T*
```

### 5.3 ILS — busca local iterada

**Origem.** Lourenço, Martin e Stützle (2003); perturbação de Vansteenwegen et al. (2009) para o
TOPTW: remove $S$ visitas consecutivas a partir de uma posição aleatória; $S$ cresce a cada
iteração sem melhoria e volta a 1 ao melhorar. Implementa a ideia de "ruína e recriação" de `ideias.md`.

```
procedimento ILS(tempo)
    T ← INICIAL; S ← 1
    enquanto houver tempo
        T' ← T sem S nós consecutivos a partir de posição aleatória
        COBRE_CLUSTERS(T'); REPARA(T') se preciso; BL(T')
        se T' melhor que T*: T* ← T ← T'; S ← 1
        senão: T ← T' (se viável); S ← S + 1 (volta a 1 se S > |T|/3);
               a cada 100 falhas: T ← T*
```

### 5.4 VNS — busca em vizinhança variável

**Origem.** Mladenović e Hansen (1997); VNS para o OP por Sevkli e Sevilgen (2006). Vizinhança de
perturbação $N_k$: remover $k$ nós aleatórios (sem descobrir clusters) e inserir $k$ nós aleatórios
de fora, seguido de reparo; $k_{\max}=6$.

```
procedimento VNS(tempo)
    T ← INICIAL; k ← 1
    enquanto houver tempo
        T' ← AGITA(T, k): remove k nós aleatórios; insere k nós aleatórios ∉ T; REPARA
        BL(T')
        se T' melhor que T: T ← T'; k ← 1   senão: k ← (k mod 6) + 1
```

### 5.5 ALNS — busca adaptativa em vizinhança grande

**Origem.** Ropke e Pisinger (2006) (LNS de Shaw, 1998). Operadores de destruição (removem
$q\sim U[0{,}1m; 0{,}4m]$ nós): **aleatória**; **pior razão** (ordena por $\Delta^-/p$, escolhe com
viés $u^4$); **segmento** (consecutivos); **radial** (os $q$ nós do tour mais próximos de um nó
sorteado — a "remoção de um quadrante geográfico" de `ideias.md`); **cluster** (remove os
representantes de um cluster sorteado e insere outro membro dele — força a troca de representante,
específico do GCOP). Reconstrução: **gulosa** (cobertura barata + inserção por razão), **regret-2**
(cobertura por arrependimento + razão) e **ruidosa** (custos com ruído $\pm20\%$/$\pm30\%$). Seleção
por roleta com pesos adaptativos (pontuações 33/9/13, reação 0,1, segmentos de 100 iterações) e
aceitação por recozimento simulado com $T_0=0{,}05\,P(T_0)$ decaindo a $0{,}001\,P(T_0)$ ao longo do
tempo. A BL completa só é aplicada às novas melhores soluções.

```
procedimento ALNS(tempo)
    T ← INICIAL; pesos ← 1
    enquanto houver tempo
        escolhe destruição d e reconstrução r por roleta
        T' ← r(d(T)); REPARA(T') se preciso; OTIMIZA_ROTA(T'); INSERE_RAZAO(T')
        Temp ← T0 · (Tf/T0)^(tempo decorrido/tempo total)
        se T' melhor que T*: BL(T'); T* ← T ← T'; escore 33
        senão se T' melhor que T: T ← T'; escore 9
        senão se U < exp((P(T') − P(T))/Temp): T ← T'; escore 13
        a cada 100 iterações: peso ← 0,9·peso + 0,1·escore médio
```

### 5.6 SA — recozimento simulado

**Origem.** Kirkpatrick, Gelatt e Vecchi (1983); SA para o TOPTW em Lin e Yu (2012). Função
$f(T)=P(T)-\lambda L(T)$ com $\lambda=0{,}01\,p_{\min}/B$ (o prêmio domina; o comprimento só
desempata). Movimentos sorteados: inserção (25%, na melhor posição, só se couber), remoção (20%),
troca 1-1 exata (30%) e 2-opt aleatório (25%, só se não piorar $L$). Temperatura geométrica de
$T_0=0{,}5\bar p$ a $T_f=0{,}01\,p_{\min}$ em 3 ciclos (reaquecimentos); OTIMIZA_ROTA a cada 200
movimentos; BL na melhor solução ao final.

```
procedimento SA(tempo)
    T ← INICIAL
    enquanto houver tempo
        repita 200 vezes
            Temp ← T0 (Tf/T0)^(fração do ciclo atual)
            sorteia movimento μ ∈ {inserção, remoção, troca, 2-opt}; calcula Δf exato
            se μ viável e (Δf ≥ 0 ou U < exp(Δf/Temp)): aplica μ
            atualiza T*
        OTIMIZA_ROTA(T)
    BL(T*)
```

### 5.7 TS — busca tabu

**Origem.** Glover (1989); busca tabu para o TSP seletivo (≡ OP) em Gendreau, Laporte e Semet (1998).
Vizinhança: adição de qualquer $j\notin T$ que caiba, troca 1-1 exata (amostra de 60 nós de fora × todos
do tour) e, se nenhum movimento aumenta o prêmio, remoção. Escolhe-se o melhor movimento
não tabu por $(\Delta P, -L')$. Atributos tabu: nó removido não pode voltar e nó inserido não pode
sair por $\theta\sim U\{5..15\}$ iterações; aspiração se o movimento gera nova melhor solução;
intensificação: volta à melhor solução após 200 iterações sem melhoria.

```
procedimento TS(tempo)
    T ← INICIAL
    enquanto houver tempo
        M ← adições ∪ trocas(amostra) ∪ (remoções, se nenhum movimento aumenta P)
        μ* ← melhor movimento de M não tabu (ou que satisfaça a aspiração)
        aplica μ*; marca atributos tabu; OTIMIZA_ROTA(T); atualiza T*
        se 200 iterações sem melhoria: T ← T*; limpa listas tabu
```

### 5.8 MA — algoritmo memético

**Origem.** Moscato (1989); AG para o OP em Tasgetiren (2002). População de 10 soluções (INICIAL +
GRASP+BL). Cruzamento por "tour gigante": um segmento contíguo (30–70%) do pai A seguido dos nós do
pai B na ordem de B; o filho é otimizado em rota, reduzido ao orçamento por remoções $\Delta^-/p$,
reparado e melhorado pela BL; mutação (20%) = AGITA com $k=2$. Seleção por torneio binário;
o filho substitui o pior indivíduo se for melhor e não duplicado (mesmo $P$ e $L$).

```
procedimento MA(tempo)
    Pop ← {INICIAL} ∪ {GRASP+BL} até 10 indivíduos
    enquanto houver tempo
        A, B ← TORNEIO(Pop), TORNEIO(Pop)
        F ← segmento(A) ⧺ (nós de B ∉ segmento, na ordem de B)
        OTIMIZA_ROTA(F); remove por Δ−/p até L ≤ B; REPARA(F)
        com prob. 0,2: F ← AGITA(F, 2)
        BL(F)
        se F melhor que o pior e não duplicado: substitui o pior
```

---

## 6. Resumo de complexidade

$n$ nós, $K$ clusters, $m=|T|\le n$ nós no tour, $|C|_{\max}$ maior cluster. "Iteração" = um ciclo
do laço principal.

| Método | Custo (pior caso) | Observação |
|---|---|---|
| 2-opt / Or-opt (uma passada) | $O(m^2)$ | número de passadas limitado na prática |
| Inserção por razão | $O(nm + q\,n)$ | $q$ inserções; *cache* evita $O(q\,nm)$ |
| Troca 1-1 exata | $O(nm)$ | três melhores arestas por candidato |
| BL (-LS) | $O(r\,(m^2+nm))$ | $r\le 50$ rodadas |
| Refino σ (-SR) | $O(r\,q\,nm)$ | recalcula σ a cada inserção ⇒ mais caro que -LS |
| NI / FI | $O(K\,(n+|C|_{\max}K))$ | |
| ST | $O(K n^2)$ | Dijkstra denso por cluster |
| TSPD | $O(n^2)$ por passada de 2-opt + $O(n^2)$ remoções | |
| MSPD (iteração) | $O(n^2)$ (perturbação) + construção + refino σ | |
| GRASP (iteração) | $O(K|C|_{\max}m + q\,nm)$ + BL | |
| ILS / VNS / MA (iteração) | dominada pela BL | |
| ALNS (iteração) | $O(qm + nm + m^2)$; BL só em nova melhor | |
| SA (movimento) | $O(m)$ | milhões de movimentos por execução |
| TS (iteração) | $O(nm + 60m + m^2)$ | |
| LBR / BB / EXACT | exponencial (MIP) | limitados por tempo |

---

## 7. Ambiente de execução dos experimentos

| Item | Valor |
|---|---|
| CPU | AMD Ryzen 5 5500 — 6 núcleos / 12 *threads*, 3,6 GHz (até 4,2 GHz) |
| RAM | 16 GB |
| Sistema operacional | Windows 10 Pro 64 bits (build 19045) |
| Compilador | g++ 14.2.0 (MSYS2 UCRT64), `-O2 -std=c++17 -static` |
| Python | 3.11.8 (numpy 2.4.6, scipy 1.17.1, pandas 3.0.6, matplotlib 3.11.2) |
| Solver MIP | HiGHS 1.15.1 (highspy), 1 *thread* por execução |
| Paralelismo | execuções independentes em paralelo (6 processos para as heurísticas), cada uma *single-thread* |
| Medição de tempo | relógio de parede (`std::chrono::steady_clock`); tempo até a melhor solução registrado na trajetória |

Reprodução:

```
g++ -O2 -std=c++17 -static -o bin/gcop.exe src/main.cpp
python scripts/build_instances.py            # data/instances.csv (+ instâncias POKE)
python scripts/run_experiments.py heur 6     # construtivas + metaheurísticas
python scripts/run_experiments.py bb 6 600   # baseline B&B (MTZ)
python scripts/run_experiments.py exact 2 600
python scripts/run_experiments.py lbr 4 60
python scripts/analyze.py                    # results/tables.md e docs/figs/
```

---

## 8. Instâncias de teste

### 8.1 TSPLIB-GCOP (do artigo base)

Os grafos publicados pelos autores (`gcop-tsplib.zip`, página do GCOP em msinnl.github.io) foram
gerados a partir de 65 instâncias simétricas da TSPLIB (Reinelt, 1991) com $n\le 500$ pelo
procedimento CLUSTERING de Fischetti et al. (1997): $\lceil n/5\rceil$ centros escolhidos
iterativamente maximizando a distância aos centros já escolhidos, cada nó atribuído ao centro mais
próximo, com tamanho mínimo 2 por cluster. Cada rótulo de cluster do arquivo (inclusive o rótulo 0)
é tratado como um cluster; as distâncias são as do arquivo (euclidianas reais, não arredondadas).
Seguindo o artigo:

- **Orçamento**: $B=\alpha\,TSP + (1-\alpha)\,GTSP_{FEAS}$, $\alpha\in\{0{,}25; 0{,}5; 0{,}75\}$, onde
  $GTSP_{FEAS}$ é o comprimento de um tour pelo nó de menor índice de cada cluster. O artigo usa o
  TSP **ótimo** (Concorde); usamos o melhor de 5 partidas de vizinho mais próximo + 2-opt/Or-opt
  (valores ≈ 0–3% acima do ótimo; por exemplo, pcb442: 52.042 contra 50.778 da TSPLIB com distâncias
  arredondadas). Isso só desloca levemente $B$; todos os métodos usam o mesmo $B$.
- **Prêmios**: uniformes ($p_i=1$) e pseudo-aleatórios $p_i = 1 + (7213\,i \bmod 100)$.

Para a bateria preliminar usamos um subconjunto de 18 grafos cobrindo toda a faixa de tamanho:
ulysses22, bayg29, att48, eil51, berlin52, st70, eil76, pr76, kroA100, rd100, eil101, ch130,
kroA150, kroA200, gil262, a280, lin318 e pcb442 ($22\le n\le 442$, $6\le K\le 90$) ⇒
18 × 3 orçamentos × 2 esquemas de prêmio = **108 instâncias**. O experimento final usará os 65
grafos (390 instâncias), como no artigo.

### 8.2 POKE — sintéticas no estilo Pokémon GO

As instâncias reais de Viena, Londres e Budapeste não foram disponibilizadas (só as TSPLIB estão
no repositório dos autores). Para reproduzir as suas características — sem fabricar dados reais —
geramos três "cidades" sintéticas (`scripts/build_instances.py`, sementes fixas):

- 450 avistamentos em área de 4 km × 4 km: 70% em 4–7 pontos de interesse (gaussianas, desvio de
  150–450 m) e 30% uniformes — tamanho semelhante às cidades do artigo (437–484 locais);
- 100 espécies com frequências de cauda longa (Zipf, $s=0{,}9$); cada local tem uma espécie — clusters
  **espalhados no espaço** (ao contrário dos clusters geográficos da TSPLIB);
- distância = euclidiana × fator de desvio de rua $U[1{,}15; 1{,}40]$ por par — **não** satisfaz a
  desigualdade triangular, como as distâncias de rede viária do artigo; TSP ≈ 72–79 km (artigo: 75–212 km);
- apenas 14–15 espécies (com ≥ 2 locais) são obrigatórias — as demais tornam-se opcionais, como no
  cenário "realista" do artigo;
- $B\in\{10, 15, 20\}$ km e prêmios uniformes ou **por espécie** ($p = 1 + (7213(\text{espécie}+1) \bmod 100)$, igual para todos os locais da espécie).

3 cidades × 3 orçamentos × 2 prêmios = **18 instâncias**. Total da bateria preliminar: **126 instâncias**.

---

## 9. Hipóteses e experimentos

Medidas comuns:

- **BKS** (*best known solution*): maior prêmio encontrado por qualquer método em qualquer execução
  (incluindo BB, LBR e EXACT). **OPT**: valor ótimo quando o EXACT termina.
- **gap ao BKS** de uma execução: $100\,(BKS - P)/BKS$; por instância e método usa-se a média das 5 sementes.
- **gap ao ótimo**: $100\,(OPT-P)/OPT$ nas instâncias com ótimo provado.
- **tempo até a melhor** (s) e sua razão com o limite $t(n)$; **iterações**.
- Execuções: construtivas 1 vez (determinísticas); metaheurísticas 5 sementes com $t(n)=\max(1,n/50)$ s
  (1 s para $n\le 50$; ≈ 9 s para $n=450$); BB 600 s; EXACT 600 s ($n\le 200$; em POKE o modelo não gera limitantes úteis e usa-se o limitante dual do BB); LBR 60 s ($n\le 200$).
- Testes estatísticos (nível 5%): Wilcoxon pareado sobre instâncias; Friedman para $>2$ métodos com
  pós-teste de Wilcoxon e correção de Holm (Demšar, 2006).

### H1 — A busca local exata é melhor que o refinamento σ do artigo

**Enunciado.** Aplicada às mesmas soluções construtivas (NI, FI, ST, TSPD), a BL proposta (-LS)
obtém prêmio maior que o refinamento baseado em σ (-SR), sem custo de tempo maior.

**Experimento.** Cada construtiva é executada sem BL (raw), com -SR e com -LS, em todas as 126 instâncias.

- *Coletado*: prêmio, comprimento, tempo (ms), gap ao BKS.
- *Apresentação*: Tabela T1 — linhas = construtivas; colunas = gap médio (%) raw/SR/LS e tempo médio
  (ms) raw/SR/LS; Tabela T1b — gap por classe de tamanho; Figura F5 — barras agrupadas (eixo x:
  construtiva; eixo y: gap médio ao BKS; uma barra por variante).
- *Critério*: **confirmada** se, nos 504 pares (instância × construtiva), -LS tiver prêmio maior em
  mais pares do que -SR, Wilcoxon unilateral $p<0{,}05$, e tempo médio de -LS ≤ tempo médio de -SR.
  **Refutada** se $p\ge0{,}05$ ou -SR for melhor; **parcial** se -LS for melhor mas mais lenta.

### H2 — Metaheurísticas propostas superam o controle MSPD

**Enunciado.** Com o mesmo tempo $t(n)$, ao menos uma metaheurística proposta (GRASP, ILS, VNS, ALNS,
SA, TS, MA) obtém gap ao BKS significativamente menor que o MSPD do artigo.

**Experimento.** 9 métodos (MSPD, MSPD-LS e as 7 propostas) × 126 instâncias × 5 sementes.

- *Coletado*: gap ao BKS (médio, melhor semente, desvio entre sementes), % de execuções e de
  instâncias que atingem o BKS, tempo até a melhor, iterações, rank médio.
- *Apresentação*: Tabela T2 (linhas = métodos; colunas = as medidas acima); Tabela T2b (Wilcoxon de
  cada método contra MSPD: vitórias/derrotas/empates, $p$ bruto e $p$ de Holm); Figura F1 — *boxplot*
  do gap por método (eixo x: método; eixo y: gap médio por instância); Figura F4 — perfil de desempenho
  (eixo x: tolerância τ de gap em %; eixo y: % de instâncias com gap ≤ τ; uma curva por método).
- *Critério*: **confirmada** se Friedman tiver $p<0{,}05$ e ao menos um método proposto tiver gap médio
  menor que o MSPD com $p_{Holm}<0{,}05$. **Refutada** caso contrário.

### H3 — Heurísticas em segundos superam o B&B de tempo fixo

**Enunciado.** A melhor metaheurística proposta, em $t(n)\le 9$ s, obtém prêmio médio maior ou igual
ao do B&B (formulação MTZ) com 600 s em ao menos 90% das instâncias, e estritamente maior na maioria
das instâncias com $n>100$.

**Experimento.** BB (600 s) em todas as instâncias; comparação com as metaheurísticas de H2.

- *Coletado*: prêmio e limitante dual do BB, status (ótimo/tempo), nós de B&B; gap ao BKS de ambos.
- *Apresentação*: Tabela T6 — linhas = classe de tamanho; colunas = nº de instâncias, % em que o BB
  achou solução viável, gap BB→BKS, gap do BB ao seu próprio limitante, gap do ALNS e da melhor
  metaheurística; tabela de vitórias/empates/derrotas de cada método contra o BB; Figura F6 — dispersão
  (eixo x: $n$; eixo y: gap ao BKS em escala symlog; pontos: BB e ALNS).
- *Critério*: **confirmada** se ambos os percentuais forem atingidos; **refutada** caso contrário.

### H4 — As metaheurísticas são quase ótimas

**Enunciado.** Nas instâncias com ótimo provado, a melhor metaheurística proposta tem gap médio ao
ótimo ≤ 0,5% (valor de referência citado em `ideias.md` para as heurísticas do artigo).

**Experimento.** EXACT (CUT) com 600 s; gap ao ótimo das execuções de H2.

- *Coletado*: status e tempo do EXACT, OPT, gap ao ótimo, % de execuções que atingem o ótimo.
- *Apresentação*: Tabela T5 — linhas = métodos; colunas = gap médio ao ótimo e % de execuções ótimas;
  Tabela T0 com OPT/UB por instância.
- *Critério*: **confirmada** se o gap médio ao ótimo da melhor metaheurística proposta for ≤ 0,5%.

### H5 — A dificuldade cresce com o tamanho e a folga do orçamento

**Enunciado.** O gap das metaheurísticas cresce com $n$ e com $\alpha$ (mais orçamento ⇒ tours maiores
e mais combinações), e as instâncias POKE (clusters dispersos, sem desigualdade triangular) são mais
difíceis que as TSPLIB de tamanho semelhante.

**Experimento.** Mesmos dados de H2, agregados por classe de tamanho, $\alpha$ e esquema de prêmio.

- *Coletado*: gap médio por grupo; correlação de Spearman entre $n$ e gap.
- *Apresentação*: Tabela T3 (linhas = classes de tamanho; colunas = métodos); Tabela T4 (linhas =
  grupos α×prêmio e POKE); Figura F2 (eixo x: $n$; eixo y: gap médio; uma linha por método); Figura F3
  — curvas *anytime* (eixo x: fração do tempo limite, log; eixo y: gap médio ao BKS; painéis $n\le200$ e
  $n\ge262$).
- *Critério*: **confirmada** se a correlação de Spearman entre $n$ e gap for positiva com $p<0{,}05$ para a
  maioria dos métodos e o gap médio crescer de α=0,25 para α=0,75; a parte POKE é confirmada se o gap
  médio em POKE for maior que na classe 262–442.

### H6 — *Local branching* melhora o multi-start

**Enunciado.** O LBR melhora a solução do MSPD em ao menos 50% das instâncias com $n\le 200$.

**Experimento.** LBR (MSPD por $t(n)$ + LB por até 60 s no total, $k=2,4,6$, 20 s por vizinhança).

- *Coletado*: prêmio antes/depois do LB, nº de melhorias, vizinhanças provadas vazias, tempo.
- *Apresentação*: Tabela T7 — linhas = classe de tamanho; colunas = nº de instâncias, % melhoradas,
  gap do MSPD, gap do MSPD+LB, vizinhanças provadas vazias, tempo.
- *Critério*: **confirmada** se a fração de instâncias melhoradas for ≥ 50%; **refutada** caso contrário.

---

## 10. Referências

Formato SBC. *Recomenda-se conferir volume/páginas na versão final.*

Álvarez-Miranda, E., Luipersbeck, M., and Sinnl, M. (2018). Gotta (efficiently) catch them all: Pokémon GO meets orienteering problems. *European Journal of Operational Research*, 265(2):779–794.

Campos, V., Martí, R., Sánchez-Oro, J., and Duarte, A. (2014). GRASP with path relinking for the orienteering problem. *Journal of the Operational Research Society*, 65(12):1800–1813.

Croes, G. A. (1958). A method for solving traveling-salesman problems. *Operations Research*, 6(6):791–812.

Demšar, J. (2006). Statistical comparisons of classifiers over multiple data sets. *Journal of Machine Learning Research*, 7:1–30.

Dolan, E. D. and Moré, J. J. (2002). Benchmarking optimization software with performance profiles. *Mathematical Programming*, 91(2):201–213.

Feo, T. A. and Resende, M. G. C. (1995). Greedy randomized adaptive search procedures. *Journal of Global Optimization*, 6(2):109–133.

Fischetti, M. and Lodi, A. (2003). Local branching. *Mathematical Programming*, 98(1–3):23–47.

Fischetti, M., Salazar-González, J. J., and Toth, P. (1997). A branch-and-cut algorithm for the symmetric generalized traveling salesman problem. *Operations Research*, 45(3):378–394.

Fischetti, M., Salazar-González, J. J., and Toth, P. (1998). Solving the orienteering problem through branch-and-cut. *INFORMS Journal on Computing*, 10(2):133–148.

Gendreau, M., Laporte, G., and Semet, F. (1998). A tabu search heuristic for the undirected selective travelling salesman problem. *European Journal of Operational Research*, 106(2–3):539–545.

Glover, F. (1989). Tabu search — Part I. *ORSA Journal on Computing*, 1(3):190–206.

Golden, B. L., Levy, L., and Vohra, R. (1987). The orienteering problem. *Naval Research Logistics*, 34(3):307–318.

Huangfu, Q. and Hall, J. A. J. (2018). Parallelizing the dual revised simplex method. *Mathematical Programming Computation*, 10(1):119–142.

Kirkpatrick, S., Gelatt, C. D., and Vecchi, M. P. (1983). Optimization by simulated annealing. *Science*, 220(4598):671–680.

Lin, S. (1965). Computer solutions of the traveling salesman problem. *Bell System Technical Journal*, 44(10):2245–2269.

Lin, S.-W. and Yu, V. F. (2012). A simulated annealing heuristic for the team orienteering problem with time windows. *European Journal of Operational Research*, 217(1):94–107.

Lourenço, H. R., Martin, O. C., and Stützle, T. (2003). Iterated local search. In Glover, F. and Kochenberger, G. A., editors, *Handbook of Metaheuristics*, pages 320–353. Kluwer, Boston.

Miller, C. E., Tucker, A. W., and Zemlin, R. A. (1960). Integer programming formulation of traveling salesman problems. *Journal of the ACM*, 7(4):326–329.

Mladenović, N. and Hansen, P. (1997). Variable neighborhood search. *Computers & Operations Research*, 24(11):1097–1100.

Moscato, P. (1989). On evolution, search, optimization, genetic algorithms and martial arts: towards memetic algorithms. Technical Report C3P 826, Caltech Concurrent Computation Program.

Or, I. (1976). *Traveling salesman-type combinatorial problems and their relation to the logistics of regional blood banking*. PhD thesis, Northwestern University.

Reinelt, G. (1991). TSPLIB — a traveling salesman problem library. *ORSA Journal on Computing*, 3(4):376–384.

Ropke, S. and Pisinger, D. (2006). An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows. *Transportation Science*, 40(4):455–472.

Rosenkrantz, D. J., Stearns, R. E., and Lewis, P. M. (1977). An analysis of several heuristics for the traveling salesman problem. *SIAM Journal on Computing*, 6(3):563–581.

Sevkli, Z. and Sevilgen, F. E. (2006). Variable neighborhood search for the orienteering problem. In *Computer and Information Sciences – ISCIS 2006*, LNCS 4263, pages 134–143. Springer.

Shaw, P. (1998). Using constraint programming and local search methods to solve vehicle routing problems. In *Principles and Practice of Constraint Programming – CP98*, LNCS 1520, pages 417–431. Springer.

Takahashi, H. and Matsuyama, A. (1980). An approximate solution for the Steiner problem in graphs. *Mathematica Japonica*, 24(6):573–577.

Tasgetiren, M. F. (2002). A genetic algorithm with an adaptive penalty function for the orienteering problem. *Journal of Economic and Social Research*, 4(2):1–26.

Tsiligirides, T. (1984). Heuristic methods applied to orienteering. *Journal of the Operational Research Society*, 35(9):797–809.

Vansteenwegen, P., Souffriau, W., Vanden Berghe, G., and Van Oudheusden, D. (2009). Iterated local search for the team orienteering problem with time windows. *Computers & Operations Research*, 36(12):3281–3290.

Vansteenwegen, P., Souffriau, W., and Van Oudheusden, D. (2011). The orienteering problem: a survey. *European Journal of Operational Research*, 209(1):1–10.
