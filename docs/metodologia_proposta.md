# 3. Metodologia

> Proposta de metodologia para a etapa final do TP, restrita às **8 heurísticas selecionadas** a partir da
> bateria preliminar ([`resultados.md`](resultados.md)). A descrição completa de todas as heurísticas
> testadas na fase exploratória continua em [`metodologia.md`](metodologia.md).

## Visão geral

O GCOP pede uma rota fechada que **visite pelo menos um nó de cada cluster**, tenha **comprimento no
máximo $B$** e **colete o maior prêmio possível**. Há, portanto, duas decisões entrelaçadas: *quais* nós
visitar (inclusive qual "representante" escolher em cada cluster) e *em que ordem* visitá-los (para
gastar pouco do orçamento).

Foram selecionados 8 métodos, mais um método exato usado apenas como régua:

| # | Sigla | Papel | O que é, em uma frase | Por que foi selecionado |
|---|---|---|---|---|
| 1 | **BB** | *baseline* | Um *solver* de programação inteira genérico rodando por tempo fixo | Representa o que alguém faria sem projetar heurísticas; mostra até onde a abordagem exata alcança |
| 2 | **MSPD** | controle | A heurística de inicialização do artigo que define o GCOP, repetida até acabar o tempo | É a única heurística da literatura para o problema; toda proposta precisa superá-la |
| 3 | **LBR** | controle | O MSPD seguido de uma busca exata em uma vizinhança restrita (*local branching*) | É a matheurística do artigo base; testa se o *solver* ajuda a melhorar heurísticas |
| 4 | **MSPD-LS** | proposta (ablação) | O MSPD com a busca local do artigo trocada pela busca local proposta | Isola o efeito da busca local proposta: é a única diferença em relação ao MSPD |
| 5 | **ILS** | proposta | Destrói um trecho da rota, reconstrói e melhora, repetidamente | Bom desempenho geral, mas falha em clusters espalhados: revela uma característica do problema |
| 6 | **VNS** | proposta | Perturba a solução com intensidade crescente até achar melhoria | Destaca-se quando clusters são espalhados e os prêmios agrupados por cluster |
| 7 | **ALNS** | proposta | Escolhe, entre vários operadores de destruição/reconstrução, os que mais têm dado resultado | Segundo melhor e o mais estável; tem um operador específico do GCOP (troca de representante) |
| 8 | **MA** | proposta | População de soluções que se combinam (cruzamento) e são melhoradas por busca local | Melhor método em todas as medidas da fase preliminar |
| — | EXACT | referência | Formulação exata do artigo resolvida até a otimalidade | Não é heurística: fornece o valor ótimo para medir a qualidade das demais |

Além desses, três **variantes de diagnóstico** (§3.1.8) são usadas apenas para testar hipóteses
específicas: AG (MA sem busca local), ALNS−C (ALNS sem o operador por cluster) e ILS-C (ILS com
perturbação por cluster). Elas não contam entre as 8 heurísticas selecionadas.

### Notação e conceitos usados em todo o documento

- $G=(V,E)$: grafo completo com $n=|V|$ nós; $d_{ij}$: distância entre $i$ e $j$ (simétrica, mas **não
  necessariamente** respeita a desigualdade triangular); $p_i$: prêmio do nó $i$.
- $\mathcal C=\{C_1,\dots,C_K\}$: os $K$ clusters; $B$: orçamento (comprimento máximo da rota).
- **Solução** $T=(v_1,\dots,v_m)$: sequência cíclica de nós distintos (depois de $v_m$ volta-se a $v_1$).
  $L(T)$ é o comprimento e $P(T)$ o prêmio total. $T$ é **viável** se cobre todos os clusters e
  $L(T)\le B$.
- **Comparação de soluções**: $T_1$ é *melhor* que $T_2$ se tem maior prêmio; em caso de empate, se é
  mais curta (sobra mais orçamento para inserir nós depois).
- **Custo de inserção** de $v$ entre os vizinhos consecutivos $a,b$ da rota:
  $\Delta^+(v,a,b)=d_{av}+d_{vb}-d_{ab}$ (quanto a rota cresce). A **inserção mais barata**
  $\Delta^+(v)$ é o menor valor entre todas as posições.
- **Ganho de remoção** de $v$ (vizinhos $a,b$): $\Delta^-(v)=d_{av}+d_{vb}-d_{ab}$ (quanto a rota encurta).
- **Nó removível**: nó cuja saída não deixa nenhum cluster descoberto (o cluster tem outro nó na rota).
- **Busca local**: procedimento que aplica pequenas modificações à solução enquanto elas a melhoram,
  parando em um *ótimo local* (nenhuma modificação daquele tipo melhora mais).
- **Metaheurística**: estratégia de mais alto nível que escapa de ótimos locais (perturbando, recombinando
  ou aceitando pioras controladas) e repete o processo até um limite de tempo.

---

## 3.1 Heurísticas propostas

Todas as metaheurísticas propostas rodam pelo mesmo limite de tempo $t(n)=\max(1,\,n/50)$ segundos
(1 s para $n\le50$; 9 s para $n=450$), registram a trajetória (instante e valor de cada melhoria) e usam
semente aleatória controlada.

### 3.1.1 Componentes comuns

As heurísticas propostas são montadas a partir dos mesmos blocos. Descrevê-los uma vez evita repetição e
garante que as diferenças entre os métodos estejam só na estratégia de busca.

**(a) OTIMIZA_ROTA — 2-opt e Or-opt** (Croes, 1958; Or, 1976). Não muda *quais* nós são visitados,
só a *ordem*, para encurtar a rota e liberar orçamento. O **2-opt** remove duas arestas e reconecta os
dois trechos invertendo um deles (desfaz "cruzamentos"). O **Or-opt** retira um segmento de 1 a 3 nós
consecutivos e o reinsere, direto ou invertido, na melhor outra posição. Ambos são aplicados com
primeira melhoria até nenhum encurtar a rota.

```
procedimento OTIMIZA_ROTA(T)
    repita
        a ← 2OPT(T)          ▷ verdadeiro se encurtou T
        b ← OROPT(T)
    até não a e não b (no máximo 100 rodadas)
```

**(b) COBRE_CLUSTERS — inserção obrigatória.** Enquanto houver cluster sem nenhum nó visitado, insere
um nó dele. Dois critérios: *barato* (insere o nó de menor $\Delta^+$ entre todos os clusters
descobertos) e *regret* (Ropke e Pisinger, 2006: atende primeiro o cluster com maior diferença entre a
2ª e a 1ª opção mais barata — aquele que "mais se arrependeria" se fosse deixado para depois).

```
procedimento COBRE_CLUSTERS(T, modo)
    enquanto existe cluster descoberto
        para cada C_k descoberto: c1(k), c2(k) ← 1º e 2º menores Δ+(v), v ∈ C_k
        k* ← argmin c1(k)  (modo barato)   ou   argmax c2(k) − c1(k)  (modo regret)
        insere o nó de C_k* que realiza c1(k*), na sua melhor posição
```

**(c) INSERE_RAZAO — inserção opcional** (Tsiligirides, 1984). Enquanto couber no orçamento, insere o
nó fora da rota com maior razão *prêmio / custo exato de inserção*. Um *cache* guarda a melhor posição
de cada nó; após uma inserção, só os nós afetados são recalculados. Um ruído opcional $\varepsilon$
multiplica a razão por $U[1-\varepsilon,1+\varepsilon]$ (usado pelo ALNS).

```
procedimento INSERE_RAZAO(T, ε = 0)
    repita
        F ← { v ∉ T : L(T) + Δ+(v) ≤ B }                 ▷ candidatos que cabem
        se F = ∅: pare
        v* ← argmax_{v ∈ F} p_v / Δ+(v) · U[1−ε, 1+ε]
        insere v* na sua melhor posição; atualiza o cache
```

**(d) TROCA — troca 1-1 exata.** Tenta substituir um nó $i$ da rota por um nó $j$ de fora com
prêmio maior (ou igual, se encurtar a rota), desde que o resultado caiba em $B$ e não descubra cluster.
O comprimento após a troca é calculado **exatamente** (e não estimado), guardando as 3 melhores posições
de inserção de cada $j$.

```
procedimento TROCA(T)
    para cada j ∉ T, em ordem decrescente de prêmio
        i* ← melhor i ∈ T tal que p_j ≥ p_i, remover i não descobre cluster (salvo se j o cobre)
              e L(T) − Δ−(i) + custo exato de inserir j ≤ B
        se i* existe: troca i* por j
```

**(e) BL — busca local proposta (sufixo -LS).** Combina os três tipos de movimento até nenhum deles
melhorar a solução. A diferença para a busca local do artigo (§3.2.2) é que aqui os custos são
**exatos** ($\Delta^+$, $\Delta^-$), enquanto o artigo usa um índice aproximado $\sigma$.

```
procedimento BL(T)
    repita (no máximo 50 vezes)
        OTIMIZA_ROTA(T)
        a ← INSERE_RAZAO(T);  b ← TROCA(T)
    até não a e não b
```

**(f) REPARA — reparo de viabilidade.** Transforma uma solução inválida em válida: enquanto a rota
excede $B$, remove o nó com maior $\Delta^-(v)/p_v$ (o que mais encurta por unidade de prêmio
perdido), preferindo nós removíveis; depois cobre os clusters que faltam.

```
procedimento REPARA(T)
    repita (no máximo 20 vezes)
        OTIMIZA_ROTA(T)
        enquanto L(T) > B: remove argmax Δ−(v)/p_v (entre os removíveis, se houver)
        COBRE_CLUSTERS(T, barato)
        se T é viável: retorne
```

**(g) INICIAL — solução de partida.** A melhor entre três construções gulosas melhoradas pela BL:
NI-LS, FI-LS e ST-LS (construtivas descritas em §3.2.1). Usada por ILS, VNS, ALNS e como primeiro
indivíduo do MA.

**(h) AGITA(T, k) — perturbação aleatória.** Remove $k$ nós removíveis sorteados, insere $k$ nós de
fora sorteados e aplica REPARA. Usada pelo VNS e como mutação do MA.

### 3.1.2 MSPD-LS — ablação da busca local

**Origem.** Variante do controle MSPD (§3.2.3) criada para este trabalho.

**Ideia.** Uma *ablação* troca **um único componente** de um método e mantém todo o resto igual; assim,
qualquer diferença de resultado só pode ser atribuída a esse componente. O MSPD-LS é idêntico ao MSPD
(mesma construção, mesma perturbação das distâncias, mesmo tempo), exceto que a fase de melhoria usa
REPARA + BL (proposta) no lugar do refinamento $\sigma$ do artigo.

```
procedimento MSPD-LS(tempo)
    T* ← ∅
    enquanto houver tempo
        d̃_ij ← d_ij · U[1; 1,2]                     ▷ distâncias perturbadas (simétricas)
        s ← nó aleatório de um cluster aleatório
        T ← NI(d̃, s) ou ST(d̃, s), com 50% de chance cada
        reavalia T com as distâncias reais d
        REPARA(T); BL(T)                              ▷ única diferença em relação ao MSPD
        se T é viável e melhor que T*: T* ← T
    retorne T*
```

### 3.1.3 ILS — busca local iterada

**Origem.** Lourenço, Martin e Stützle (2003); perturbação de Vansteenwegen et al. (2009) para o
problema de orientação com janelas de tempo.

**Ideia.** Uma busca local para no primeiro ótimo local. O ILS "chacoalha" esse ótimo — remove $S$ nós
**consecutivos** a partir de uma posição sorteada — e aplica a busca local de novo, esperando cair em
um ótimo local melhor. O tamanho $S$ da perturbação cresce a cada tentativa sem sucesso (para escapar
de regiões mais "fundas") e volta a 1 quando há melhoria.

**Parâmetros.** $S$ inicial = 1; $S$ volta a 1 se exceder $|T|/3$; a cada 100 falhas seguidas, retorna
à melhor solução conhecida.

```
procedimento ILS(tempo)
    T ← INICIAL; T* ← T; S ← 1; falhas ← 0
    enquanto houver tempo
        T' ← T sem S nós consecutivos a partir de uma posição aleatória
        COBRE_CLUSTERS(T', barato); REPARA(T') se inviável; BL(T')
        se T' melhor que T*: T* ← T ← T'; S ← 1; falhas ← 0
        senão
            se T' viável: T ← T'
            S ← S + 1 (volta a 1 se S > |T|/3); falhas ← falhas + 1
            se falhas mod 100 = 0: T ← T*
    retorne T*
```

**Detalhe intrínseco.** Remover nós consecutivos funciona bem quando cada cluster ocupa uma região do
mapa (TSPLIB), mas não quando os membros de um cluster estão espalhados (POKE): o representante de um
cluster distante quase nunca é retirado, e a busca não consegue trocá-lo por outro. Essa limitação é
testada em H6.

### 3.1.4 VNS — busca em vizinhança variável

**Origem.** Mladenović e Hansen (1997); VNS para o problema de orientação em Sevkli e Sevilgen (2006).

**Ideia.** Em vez de um único tipo de perturbação, usa uma família $N_1,\dots,N_6$ de intensidade
crescente: $N_k$ = AGITA com $k$ nós removidos e $k$ inseridos, **sorteados em qualquer lugar da rota**.
Se a perturbação seguida de BL melhora a solução, volta à vizinhança mais suave ($k=1$); senão, tenta
uma mais forte ($k+1$).

**Parâmetros.** $k_{\max}=6$.

```
procedimento VNS(tempo)
    T ← INICIAL; k ← 1
    enquanto houver tempo
        T' ← AGITA(T, k); BL(T')
        se T' melhor que T: T ← T'; k ← 1
        senão: k ← (k mod 6) + 1
    retorne T
```

**Detalhe intrínseco.** Como os nós removidos não precisam ser vizinhos na rota, o VNS consegue
trocar representantes de clusters espalhados e "pacotes" de nós da mesma espécie — o motivo do seu
bom desempenho em POKE com prêmio por espécie.

### 3.1.5 ALNS — busca adaptativa em vizinhança grande

**Origem.** Ropke e Pisinger (2006), a partir do LNS de Shaw (1998).

**Ideia.** Cada iteração **destrói** uma parte grande da solução ($q$ nós, $10\%$–$40\%$ da rota) e a
**reconstrói**. Há vários operadores de cada tipo; a cada iteração sorteia-se um par por roleta, com
probabilidade proporcional a um *peso* que aumenta para os operadores que vêm produzindo boas
soluções. Assim, o método aprende sozinho quais operadores servem para cada instância.

**Operadores de destruição.**
- *aleatória*: $q$ nós sorteados;
- *pior razão*: nós com maior $\Delta^-/p$ (ocupam muito orçamento para pouco prêmio), com sorteio enviesado;
- *segmento*: $q$ nós consecutivos;
- *radial*: os $q$ nós da rota mais próximos de um nó sorteado (remove uma "região" do mapa);
- *cluster* (**específico do GCOP**): remove o(s) representante(s) de um cluster sorteado e insere
  outro membro do mesmo cluster — força a troca de representante.

**Operadores de reconstrução.** *gulosa* (COBRE_CLUSTERS barato + INSERE_RAZAO), *regret*
(COBRE_CLUSTERS regret + INSERE_RAZAO) e *ruidosa* (gulosa com $\varepsilon=0{,}2$ ou $0{,}3$).

**Aceitação.** Como no recozimento simulado: soluções piores são aceitas com probabilidade
$e^{(P(T')-P(T))/\text{Temp}}$, com a temperatura caindo de $0{,}05\,P(T_0)$ a $0{,}001\,P(T_0)$ ao longo
do tempo — no início aceita pioras para explorar; no fim, quase só melhorias.

**Adaptação dos pesos.** Pontuação 33 (nova melhor solução global), 9 (melhor que a atual) ou 13 (pior,
mas aceita); a cada 100 iterações, $\text{peso}\leftarrow0{,}9\,\text{peso}+0{,}1\,\text{pontuação média}$.

```
procedimento ALNS(tempo)
    T ← INICIAL; T* ← T; pesos ← 1
    enquanto houver tempo
        escolhe destruição d e reconstrução r por roleta dos pesos
        T' ← r(d(T)); REPARA(T') se inviável; OTIMIZA_ROTA(T'); INSERE_RAZAO(T')
        Temp ← T0 · (Tf/T0)^(tempo decorrido / tempo total)
        se T' melhor que T*: BL(T'); T* ← T ← T'; pontua 33
        senão se T' melhor que T: T ← T'; pontua 9
        senão se U(0,1) < exp((P(T') − P(T)) / Temp): T ← T'; pontua 13
        a cada 100 iterações: atualiza os pesos
    retorne T*
```

### 3.1.6 MA — algoritmo memético

**Origem.** Moscato (1989); algoritmo genético para o problema de orientação em Tasgetiren (2002).

**Ideia.** Um algoritmo **genético** mantém uma *população* de soluções e gera novas combinando duas
delas (*cruzamento*) e alterando-as aleatoriamente (*mutação*). O algoritmo **memético** acrescenta uma
busca local em cada nova solução: o cruzamento explora regiões novas e a busca local refina cada uma.

**Componentes.**
- *População*: 10 soluções — INICIAL e mais 9 construídas pelo GRASP (construção gulosa com sorteio
  entre os melhores candidatos) e melhoradas pela BL.
- *Seleção dos pais*: torneio binário (sorteiam-se duas soluções e fica a melhor), duas vezes.
- *Cruzamento por "tour gigante"*: o filho recebe um trecho contíguo (30–70%) da rota do pai A e, em
  seguida, todos os nós do pai B que ainda não estão no filho, na ordem em que aparecem em B. O resultado
  em geral excede o orçamento; ele é otimizado em rota e reduzido removendo os nós de maior
  $\Delta^-/p$ até caber em $B$, e reparado se preciso.
- *Mutação*: com probabilidade 0,2, AGITA($\cdot$, 2).
- *Busca local*: BL em todo filho.
- *Substituição*: o filho entra no lugar do pior indivíduo se for melhor que ele e não for duplicado
  (mesmo prêmio e comprimento de algum indivíduo).

```
procedimento MA(tempo)
    Pop ← {INICIAL} ∪ {GRASP + BL} até 10 indivíduos
    enquanto houver tempo
        A ← TORNEIO(Pop); Bp ← TORNEIO(Pop)
        F ← trecho de 30–70% de A ⧺ (nós de Bp fora do trecho, na ordem de Bp)
        OTIMIZA_ROTA(F); remove por Δ−/p até L(F) ≤ B; REPARA(F) se preciso
        com probabilidade 0,2: F ← AGITA(F, 2)
        BL(F)
        se F melhor que o pior de Pop e F não é duplicado: substitui o pior por F
    retorne o melhor de Pop
```

### 3.1.7 Resumo de complexidade das propostas

$m=|T|$ é o número de nós na rota ($m\le n$); $q$ é o número de nós removidos/inseridos.

| Componente / método | Custo por chamada / iteração |
|---|---|
| OTIMIZA_ROTA (uma passada) | $O(m^2)$ |
| INSERE_RAZAO | $O(nm + qn)$ com *cache* |
| TROCA | $O(nm)$ |
| BL | $O(r(m^2+nm))$, $r\le50$ rodadas |
| MSPD-LS | $O(n^2)$ (perturbação) + construção + BL |
| ILS, VNS, MA | dominado pela BL |
| ALNS | $O(qm + nm + m^2)$; BL só nas novas melhores |

### 3.1.8 Variantes de diagnóstico

Não são heurísticas selecionadas: existem apenas para testar se um componente específico é o
responsável por um efeito observado (ablações, ver §3.3.4).

| Variante | Diferença em relação ao original | Pergunta que responde | Hipótese |
|---|---|---|---|
| **AG** | MA sem a linha `BL(F)` e com a população inicial sem BL | Quanto do desempenho do MA vem da busca local? | H8 |
| **ALNS−C** | ALNS sem o operador de destruição *cluster* | O operador específico do GCOP faz diferença? | H6 |
| **ILS-C** | ILS em que, com 50% de chance, a perturbação remove os representantes de $\lceil S/2\rceil$ clusters sorteados em vez de nós consecutivos | Trocar representantes corrige a falha do ILS em POKE? | H6 |

---

## 3.2 Heurísticas de controle

São as heurísticas do artigo que define o GCOP (Álvarez-Miranda, Luipersbeck e Sinnl, 2018) — o único
trabalho da literatura sobre o problema — e o *branch-and-bound* de tempo fixo como *baseline*.

### 3.2.1 Construtivas usadas pelo controle (NI, FI, ST)

Usadas pelo MSPD e pela solução INICIAL. Todas constroem uma rota que visita **aproximadamente um nó
por cluster** (o mínimo para ser viável), ficando longe do prêmio ótimo — por isso dependem de uma fase
de melhoria.

- **NI / FI — inserção do mais próximo / mais distante** (Fischetti, Salazar-González e Toth, 1997).
  A partir de um nó inicial, repetidamente escolhe o cluster descoberto mais próximo (NI) ou mais
  distante (FI) da rota e insere seu nó mais barato na melhor posição.
- **ST — árvore de Steiner** (Takahashi e Matsuyama, 1980). Cresce uma árvore ligando, a cada passo, o
  cluster descoberto mais próximo pelo caminho mais curto (Dijkstra); a rota é a ordem de visita da
  árvore (pré-ordem), seguida de OTIMIZA_ROTA. Os nós intermediários dos caminhos também entram na rota.

```
procedimento NI_FI(modo, s)
    T ← (s)
    enquanto existe cluster descoberto
        δ_k ← menor distância de um nó de C_k a T, para cada C_k descoberto
        k* ← argmin δ_k (NI)  ou  argmax δ_k (FI)
        insere em T o nó de C_k* com menor Δ+, na melhor posição

procedimento ST(r)
    A ← árvore contendo só r
    enquanto existe cluster descoberto
        DIJKSTRA a partir de todos os nós de A
        v* ← nó de cluster descoberto mais próximo de A
        acrescenta a A o caminho mais curto até v*
    T ← pré-ordem de A; OTIMIZA_ROTA(T)
```

### 3.2.2 Refinamento σ do artigo (sufixo -SR)

Fase de melhoria do artigo base. Usa o índice $\sigma_i=\min_{j\in V_T\setminus\{i\}} d_{ij}/p_i$
(distância ao vizinho visitado mais próximo dividida pelo prêmio; **menor é melhor**) como estimativa
barata de quanto custa ter o nó $i$ na rota. É a contraparte da BL proposta (§3.1.1e), que usa o custo
exato.

```
procedimento REFINO_SIGMA(T)
    para rodada = 1..10
        (a) enquanto L(T) > B: remove o nó de maior σ
        (b) para cada cluster descoberto: insere seu nó de menor σ
        (c) insere nós de fora em ordem crescente de σ, enquanto couberem em B
        (d) troca nós da rota (σ alto) por nós de fora (σ menor) se viável
        (e) OTIMIZA_ROTA(T)
        se o prêmio não aumentou e o comprimento não diminuiu: pare
```

### 3.2.3 MSPD — multi-start com distâncias perturbadas (controle)

**Origem.** Heurística de inicialização de Álvarez-Miranda et al. (2018).

**Ideia.** Uma construção gulosa sempre dá o mesmo resultado. Para obter soluções diferentes, a cada
iteração as distâncias são multiplicadas por fatores aleatórios entre 1 e 1,2; constrói-se com essas
distâncias "distorcidas", reavalia-se com as reais e refina-se. Fica a melhor solução de todas as
iterações. O artigo executa 10 iterações; aqui o método roda pelo mesmo tempo $t(n)$ das propostas, e o
resultado após 10 iterações também é registrado (configuração original).

```
procedimento MSPD(tempo)
    T* ← ∅
    enquanto houver tempo
        d̃_ij ← d_ij · U[1; 1,2]
        s ← nó aleatório de um cluster aleatório
        T ← NI(d̃, s) ou ST(d̃, s), com 50% de chance cada
        reavalia T com d; OTIMIZA_ROTA(T); REFINO_SIGMA(T)
        se T é viável e melhor que T*: T* ← T
    retorne T*
```

### 3.2.4 LBR — *local branching* (controle, matheurística)

**Origem.** Fischetti e Lodi (2003); aplicado pelo artigo base sobre a solução do MSPD.

**Ideia.** Usa um *solver* de programação inteira, mas só dentro de uma vizinhança pequena da melhor
solução atual $T$: o modelo exato recebe a restrição "no máximo $k$ nós podem entrar ou sair em
relação a $T$" e um corte que exige prêmio maior que $P(T)$. Se o *solver* acha solução melhor, ela
vira a nova $T$ e $k$ volta a 2; se prova que não existe (ou estoura 20 s), $k$ aumenta em 2, até 6.

Com $y_i=1$ se o nó $i$ é visitado, a restrição de vizinhança é
$\sum_{i\notin V_T} y_i + \sum_{i\in V_T}(1-y_i)\le k$ e o corte de melhoria é
$\sum_i p_i y_i\ge P(T)+1$. O modelo é a formulação (CUT) do EXACT (§3.2.6).

```
procedimento LBR(tempo_total)
    T ← MSPD(t(n)); k ← 2
    enquanto houver tempo e k ≤ 6
        acrescenta ao modelo CUT: vizinhança(T, k) e corte de melhoria
        T' ← resolve o MIP por até 20 s (para na 1ª solução encontrada)
        remove as duas restrições
        se T' existe: T ← T'; k ← 2
        senão: k ← k + 2
    retorne T
```

### 3.2.5 BB — *branch-and-bound* de tempo fixo (*baseline*)

**Origem.** Formulação compacta (MTZ) de Álvarez-Miranda et al. (2018, §3.2), que estende as restrições
de Miller, Tucker e Zemlin (1960) ao caso em que a rota não tem ponto de partida fixo.

**Ideia.** Escreve o GCOP como um modelo de programação inteira (variáveis binárias para "o arco
$i\to j$ é usado" e "o nó $i$ é visitado", mais variáveis de posição que impedem sub-rotas) e entrega
ao *solver* HiGHS, que faz *branch-and-bound* por 600 s. Registra-se a melhor solução encontrada (se
houver), o **limitante superior** (nenhuma solução pode ter prêmio maior que ele) e se o ótimo foi
provado. É o que um praticante faria sem projetar heurísticas.

```
procedimento BB(tempo = 600 s)
    monta o modelo MTZ; resolve com HiGHS (1 thread) até provar o ótimo ou acabar o tempo
    retorne (melhor solução, limitante superior, status, nós explorados)
```

### 3.2.6 EXACT — referência exata (não é heurística)

Formulação (CUT) do artigo com restrições de eliminação de sub-rotas (GSECs) adicionadas sob demanda:
resolve-se o modelo sem elas; se a solução tiver mais de um ciclo, acrescentam-se as restrições que
proíbem aqueles ciclos e resolve-se de novo. Quando termina, o resultado é **comprovadamente ótimo**.
Serve exclusivamente para medir o gap ao ótimo (H4) e como modelo do LBR.

---

## 3.3 Ambiente de execução dos experimentos

### 3.3.1 Ambiente computacional

| Item | Valor |
|---|---|
| CPU | AMD Ryzen 5 5500 — 6 núcleos / 12 *threads*, 3,6 GHz (até 4,2 GHz) |
| RAM | 16 GB |
| Sistema operacional | Windows 10 Pro 64 bits (build 19045) |
| Linguagem / compilador | C++17, g++ 14.2.0 (MSYS2 UCRT64), `-O2 -std=c++17 -static` |
| Análise | Python 3.11.8 (numpy, scipy, pandas, matplotlib) |
| *Solver* MIP | HiGHS 1.15.1 (highspy), 1 *thread* por execução |
| Paralelismo | até 6 execuções independentes simultâneas, cada uma *single-thread*; execuções MIP e heurísticas **não** são misturadas no mesmo lote, para não competirem por CPU |
| Medição de tempo | relógio de parede (`std::chrono::steady_clock`) |

### 3.3.2 Instâncias de teste

**TSPLIB-GCOP (artigo base).** Os 65 grafos publicados pelos autores, derivados de instâncias da TSPLIB
(Reinelt, 1991) com $14\le n\le 493$ nós. Os clusters foram gerados pelo procedimento de Fischetti et
al. (1997): cerca de $n/5$ clusters **geograficamente compactos** (cada nó vai para o centro mais
próximo). Distâncias euclidianas. Para cada grafo, seguindo o artigo:

- **orçamento** $B=\alpha\cdot TSP+(1-\alpha)\cdot GTSP$, com $\alpha\in\{0{,}25;\ 0{,}5;\ 0{,}75\}$. $TSP$ é o
  comprimento de uma rota por todos os nós e $GTSP$ o de uma rota por um nó de cada cluster. Assim,
  $\alpha$ pequeno = orçamento apertado (pouco além do mínimo para cobrir os clusters) e $\alpha$
  grande = orçamento folgado (quase dá para visitar tudo);
- **prêmios** uniformes ($p_i=1$: maximizar o número de nós visitados) ou pseudo-aleatórios
  ($p_i=1+(7213\,i \bmod 100)$).

**POKE (sintéticas no estilo Pokémon GO).** As instâncias reais do artigo (Viena, Londres, Budapeste)
não foram disponibilizadas. Geramos 3 cidades sintéticas que reproduzem suas características:

- 450 locais em 4 km × 4 km: 70% concentrados em 4–7 pontos de interesse e 30% espalhados;
- 100 espécies com frequências de cauda longa; cada local tem uma espécie e **cada espécie é um
  cluster** — portanto clusters **espalhados pelo mapa**, ao contrário da TSPLIB;
- distância = distância euclidiana × fator de desvio de rua sorteado em $[1{,}15; 1{,}40]$ por par, o que
  **viola a desigualdade triangular** (como em redes viárias);
- só as 14–15 espécies com 2 ou mais locais são obrigatórias (as raras são opcionais);
- $B\in\{10, 15, 20\}$ km; prêmios uniformes ou **por espécie** (todos os locais da mesma espécie valem
  o mesmo).

**Total e classes.** 65 × 3 × 2 = 390 instâncias TSPLIB + 18 POKE = **408 instâncias**, agrupadas por
classe para a análise:

| Classe | Faixa de $n$ | Grafos | Instâncias |
|---|---|---|---|
| A | $n\le 52$ | 16 | 96 |
| B | $53\le n\le 101$ | 13 | 78 |
| C | $102\le n\le 200$ | 20 | 120 |
| D | $201\le n\le 493$ | 16 | 96 |
| E | POKE ($n=450$) | 3 cidades | 18 |

### 3.3.3 Protocolo comum a todas as hipóteses

**Execuções.**

| Método | Execuções por instância | Limite |
|---|---|---|
| MSPD, MSPD-LS, ILS, VNS, ALNS, MA (e variantes) | 10 sementes | $t(n)=\max(1,n/50)$ s |
| LBR | 1 | MSPD por $t(n)$ + LB até 60 s no total; classes A–C |
| BB | 1 | 600 s |
| EXACT | 1 | 3.600 s; classes A–C |

Os métodos estocásticos usam as **mesmas 10 sementes**, de modo que as comparações são pareadas.

**Medidas.** Todas são calculadas por instância (média das sementes) e depois agregadas.

- **BKS** (*best known solution*): o maior prêmio encontrado por qualquer método, em qualquer execução.
  **OPT**: o valor ótimo, quando o EXACT o prova.
- **Gap ao BKS** (%): $100\,(BKS-P)/BKS$ — quanto do melhor prêmio conhecido o método deixou de coletar.
  0% = encontrou o melhor conhecido. **Gap ao ótimo**: o mesmo com OPT no lugar de BKS.
- **Taxa de acerto**: % das execuções que atingem o BKS (ou o OPT).
- **Desvio entre sementes**: desvio-padrão do gap entre as 10 sementes (robustez do método).
- **Tempo até a melhor**: instante em que a melhor solução da execução foi encontrada, e sua fração do
  tempo limite (indica se o método converge cedo ou continua melhorando).
- **Iterações**: ciclos do laço principal executados no tempo disponível.
- **Rank médio**: em cada instância os métodos são ordenados (1 = menor gap); o rank médio resume o
  desempenho relativo sem ser dominado por poucas instâncias com gaps grandes.

**Testes estatísticos** (nível de significância de 5%; Demšar, 2006). Diferenças de média podem
aparecer por acaso; os testes indicam se a diferença é sistemática.

- **Wilcoxon pareado**: compara dois métodos instância a instância (cada instância é um "par") e diz se
  um costuma ser melhor que o outro. Não supõe distribuição normal.
- **Friedman**: verifica se existe *alguma* diferença entre 3 ou mais métodos, usando os ranks.
- **Correção de Holm**: ao fazer muitas comparações, a chance de algum falso positivo cresce; a correção
  ajusta os valores-$p$ para compensar.
- **Spearman** ($\rho$): correlação entre duas grandezas ordenáveis (por exemplo, $n$ e gap); $\rho>0$
  significa que uma tende a crescer junto com a outra.

**Gráficos de uso recorrente.**

- ***Boxplot***: para cada método, uma caixa com a mediana e os quartis do gap; os pontos isolados são
  instâncias atípicas. Mostra centro, dispersão e pior caso de uma vez.
- **Perfil de desempenho** (Dolan e Moré, 2002): eixo x = tolerância $\tau$ de gap (%); eixo y = % de
  instâncias em que o método tem gap $\le\tau$. A curva mais alta e à esquerda é a melhor; o valor em
  $\tau=0$ é a fração de instâncias em que o método achou o BKS.
- **Curva *anytime***: eixo x = fração do tempo limite (escala log); eixo y = gap médio da melhor solução
  encontrada *até aquele instante*. Mostra quão rápido cada método chega a boas soluções.

### 3.3.4 Hipóteses e experimentos

#### H1 — A busca local exata é melhor que o refinamento σ do artigo

**Enunciado.** Dentro do mesmo multi-start do artigo e com o mesmo tempo, substituir o refinamento
$\sigma$ pela busca local proposta (BL) reduz o gap ao BKS e permite mais iterações.

**Experimento.** MSPD × MSPD-LS em todas as 408 instâncias, 10 sementes pareadas. Como só a fase de
melhoria muda (ablação), a diferença mede o efeito da BL. Complementarmente, para isolar o custo, mede-se
o tempo médio de *uma* fase de melhoria (REFINO_SIGMA vs. REPARA+BL) aplicada às mesmas 100 soluções
construídas por instância, em uma instância de cada grafo ($\alpha=0{,}5$, prêmio uniforme).

- *Coletado*: gap ao BKS, iterações, tempo por fase de melhoria (ms).
- *Apresentação*:
  - **Tabela T1** — linhas = classes A–E e "Total"; colunas = gap médio MSPD, gap médio MSPD-LS, redução
    relativa (%), iterações MSPD, iterações MSPD-LS, vitórias/empates/derrotas do MSPD-LS e $p$ do
    Wilcoxon.
  - **Figura F1** — dispersão: eixo x = gap do MSPD; eixo y = gap do MSPD-LS; um ponto por instância,
    cor por classe; diagonal $y=x$ (pontos abaixo dela = MSPD-LS melhor).
  - **Figura F2** — tempo por fase de melhoria (ms, escala log) vs. $n$ (escala log), uma linha por
    variante, com o expoente $b$ do ajuste $t\approx c\,n^b$ na legenda.
- *Critério*: **confirmada** se o Wilcoxon unilateral (gap MSPD-LS < gap MSPD) tiver $p<0{,}05$ e o
  número médio de iterações do MSPD-LS for maior ou igual ao do MSPD. **Parcial** se o gap for menor
  com $p<0{,}05$ mas com menos iterações. **Refutada** se $p\ge0{,}05$ ou se o MSPD for melhor.

#### H2 — As metaheurísticas propostas superam o controle MSPD

**Enunciado.** Com o mesmo tempo $t(n)$, ILS, VNS, ALNS e MA obtêm gap ao BKS significativamente menor
que o MSPD; em particular, o MA é o melhor método.

**Experimento.** 6 métodos (MSPD, MSPD-LS, ILS, VNS, ALNS, MA) × 408 instâncias × 10 sementes.
Experimento complementar de **sensibilidade ao tempo**: repetição nas classes C, D e E com
$5\cdot t(n)$, para verificar se a ordem dos métodos se mantém quando há mais tempo.

- *Coletado*: gap médio, gap da melhor semente, desvio entre sementes, taxa de acerto do BKS, gap
  máximo, tempo até a melhor (absoluto e fração de $t(n)$), iterações, rank médio.
- *Apresentação*:
  - **Tabela T2** — linhas = métodos; colunas = as medidas acima.
  - **Tabela T3** — Wilcoxon de cada método contra o MSPD e do MA contra cada um dos demais:
    vitórias/empates/derrotas, $p$ bruto e $p$ corrigido por Holm.
  - **Tabela T4** — rank médio com $t(n)$ e com $5\cdot t(n)$, lado a lado, e a correlação de Kendall
    entre as duas ordenações.
  - **Figura F3** — *boxplot* do gap por método.
  - **Figura F4** — perfil de desempenho, $\tau\in[0,5]\%$.
  - **Figura F5** — curvas *anytime*, painéis por classe.
- *Critério*: **confirmada** se o Friedman tiver $p<0{,}05$ e cada uma das quatro propostas tiver gap
  menor que o MSPD com $p_{Holm}<0{,}05$. **Parcial** se apenas parte delas atingir isso. **Refutada** se
  nenhuma atingir. A afirmação "o MA é o melhor" é confirmada se o MA tiver o menor rank médio e vencer
  cada outro método com $p_{Holm}<0{,}05$. A ordem é considerada estável no tempo se Kendall $\ge0{,}7$.

#### H3 — Heurísticas em segundos superam um *solver* genérico em minutos

**Enunciado.** A melhor metaheurística proposta, em $t(n)\le 10$ s, obtém prêmio maior ou igual ao do BB
com 600 s em pelo menos 90% das instâncias, e estritamente maior na maioria das instâncias com $n>100$.

**Experimento.** BB (600 s) em todas as 408 instâncias; comparação com os resultados de H2.

- *Coletado*: prêmio e limitante superior do BB, status (ótimo provado / tempo esgotado / sem solução
  viável), tempo até o ótimo quando provado, nós de *branch-and-bound*.
- *Apresentação*:
  - **Tabela T5** — linhas = classes A–E; colunas = nº de instâncias, % em que o BB provou o ótimo,
    % em que achou solução viável, gap médio do BB ao BKS (100% se não achou solução), gap médio da
    melhor proposta, gap do BB ao próprio limitante.
  - **Tabela T6** — linhas = métodos; colunas = vitórias/empates/derrotas contra o BB, no total e em
    $n>100$.
  - **Figura F6** — dispersão: eixo x = $n$; eixo y = gap ao BKS (escala symlog); um ponto por instância
    para o BB e para a melhor proposta (instâncias sem solução do BB marcadas em 100%).
- *Critério*: **confirmada** se ambos os percentuais forem atingidos; **refutada** caso contrário.

#### H4 — As metaheurísticas propostas são quase ótimas

**Enunciado.** Nas instâncias com ótimo provado, a melhor metaheurística proposta tem gap médio ao ótimo
$\le0{,}5\%$, e atinge o ótimo em pelo menos 90% das execuções.

**Experimento.** EXACT (3.600 s) nas classes A–C; gap ao ótimo das execuções de H2 nas instâncias
resolvidas. Para as instâncias sem ótimo, mede-se a distância entre o BKS e o menor limitante superior
disponível (EXACT ou BB).

- *Coletado*: status e tempo do EXACT, OPT ou limitante superior, gap ao ótimo, taxa de acerto do ótimo.
- *Apresentação*:
  - **Tabela T7** — linhas = métodos; colunas = gap médio ao ótimo, gap máximo, % de execuções ótimas,
    por classe A/B/C e no total.
  - **Tabela T8** — linhas = classes; colunas = nº de instâncias, nº com ótimo provado, tempo médio do
    EXACT, distância média BKS → limitante nas não resolvidas.
- *Critério*: **confirmada** se ambos os limiares forem atingidos; **parcial** se só o primeiro;
  **refutada** se o gap médio for $>0{,}5\%$. Como as instâncias resolvidas tendem a ser as menores, o
  resultado é interpretado junto com a Tabela T8.

#### H5 — Tamanho e aperto do orçamento tornam o problema mais difícil

**Enunciado.** O gap das metaheurísticas (a) cresce com $n$ e (b) **diminui** com $\alpha$: orçamentos
apertados são mais difíceis, porque a cobertura dos clusters consome a maior parte de $B$ e a escolha
de quais representantes visitar passa a ser decisiva. (c) Prêmios uniformes são mais difíceis que os
pseudo-aleatórios, pois geram muitos empates e pouca informação para guiar a busca.

*Observação*: na fase preliminar (18 grafos) o efeito de $\alpha$ apareceu no sentido inverso ao
esperado inicialmente; a hipótese foi reformulada e será testada nos 65 grafos, dos quais 47 não foram
usados na fase preliminar.

**Experimento.** Dados de H2 (instâncias TSPLIB), agregados por $n$, $\alpha$ e esquema de prêmio.
Complementarmente, registra-se a fração do orçamento consumida apenas pela cobertura ($GTSP/B$) e a
fração dos nós visitados na melhor solução, para explicar o efeito de $\alpha$.

- *Coletado*: gap médio por grupo; $\rho$ de Spearman entre $n$ e gap; $GTSP/B$; fração de nós visitados.
- *Apresentação*:
  - **Tabela T9** — linhas = classes A–D; colunas = gap médio de cada método.
  - **Tabela T10** — linhas = combinações $\alpha$ × prêmio; colunas = gap médio de cada método,
    $GTSP/B$ médio e fração média de nós visitados.
  - **Figura F7** — eixo x = $n$; eixo y = gap médio; uma linha por método.
  - **Figura F8** — eixo x = $\alpha$; eixo y = gap médio; painéis por esquema de prêmio, uma linha por
    método.
- *Critério*: (a) confirmada se $\rho>0$ com $p<0{,}05$ para a maioria dos métodos; (b) confirmada se o
  Kruskal-Wallis entre os três níveis de $\alpha$ tiver $p<0{,}05$ e o gap médio decrescer de
  $\alpha=0{,}25$ para $\alpha=0{,}75$ na maioria dos métodos; (c) confirmada se o Wilcoxon pareado
  (mesmo grafo e $\alpha$, prêmio uniforme vs. aleatório) indicar gap maior com prêmio uniforme,
  $p<0{,}05$, para a maioria dos métodos. H5 é **confirmada** se (a), (b) e (c) forem; **parcial** se
  uma ou duas forem.

#### H6 — Clusters espalhados exigem movimentos que troquem o representante do cluster

**Enunciado.** Em instâncias com clusters espalhados e distâncias não métricas (POKE), métodos cuja
perturbação é **local na rota** (ILS: nós consecutivos) perdem mais desempenho que métodos que
**trocam representantes de clusters** (VNS: nós sorteados em qualquer posição; ALNS: operador por
cluster). Acrescentar a troca de representantes ao ILS corrige essa perda.

**Experimento.** Dados de H2 nas classes D (TSPLIB, $n$ semelhante) e E (POKE), mais as variantes de
diagnóstico ILS-C e ALNS−C (§3.1.8), 10 sementes, em D e E.

- *Coletado*: gap médio por método e classe; **degradação** = gap em E − gap em D; pesos finais de cada
  operador do ALNS por classe.
- *Apresentação*:
  - **Tabela T11** — linhas = ILS, ILS-C, VNS, ALNS, ALNS−C, MA; colunas = gap em D, gap em E,
    degradação, gap em E com prêmio uniforme e com prêmio por espécie.
  - **Tabela T12** — linhas = operadores do ALNS; colunas = peso final médio nas classes A–E.
  - **Figura F9** — barras agrupadas: eixo x = método; eixo y = gap médio; uma barra para D e outra para E.
- *Critério*: **confirmada** se (i) a degradação do ILS for maior que a do VNS e a do ALNS; (ii) ILS-C
  tiver gap menor que ILS em E (Wilcoxon, $p<0{,}05$) sem piorar em D ($p\ge0{,}05$ no teste contrário);
  e (iii) ALNS−C tiver gap maior que ALNS em D ou em E ($p<0{,}05$). **Parcial** se só (i) e mais um
  item forem atendidos. **Refutada** se (i) falhar.

#### H7 — *Local branching* melhora o multi-start do artigo

**Enunciado.** O LBR melhora a solução do MSPD em pelo menos 50% das instâncias com $n\le200$.

**Experimento.** LBR nas classes A–C (294 instâncias).

- *Coletado*: prêmio antes e depois do LB, nº de melhorias, nº de vizinhanças provadas vazias, tempo.
- *Apresentação*:
  - **Tabela T13** — linhas = classes A–C; colunas = nº de instâncias, % melhoradas, gap do MSPD, gap do
    MSPD+LB, vizinhanças provadas vazias (média), tempo médio, e gap da melhor proposta em $t(n)$ para
    comparação.
  - **Figura F10** — eixo x = $n$; eixo y = ganho de prêmio do LB (%); um ponto por instância.
- *Critério*: **confirmada** se a fração de instâncias melhoradas for $\ge50\%$ em cada uma das três
  classes; **parcial** se for em apenas uma ou duas; **refutada** se em nenhuma.

#### H8 — No algoritmo memético, a busca local é o componente determinante

**Enunciado.** Removendo a busca local do MA (AG puro), o gap aumenta significativamente; e o AG puro
não supera nem o MSPD-LS, o que indica que o cruzamento sozinho não explica o desempenho do MA.

**Experimento.** AG × MA × MSPD-LS em todas as 408 instâncias, 10 sementes pareadas.

- *Coletado*: gap médio, taxa de acerto do BKS, iterações (gerações), diversidade da população ao final
  (número médio de nós em que dois indivíduos diferem).
- *Apresentação*:
  - **Tabela T14** — linhas = classes A–E e Total; colunas = gap do AG, gap do MA, gap do MSPD-LS,
    iterações do AG e do MA, diversidade final do AG e do MA, $p$ dos Wilcoxon AG vs. MA e AG vs. MSPD-LS.
  - **Figura F11** — curvas *anytime* de AG, MA e MSPD-LS para as classes C–E.
- *Critério*: **confirmada** se o MA for melhor que o AG ($p<0{,}05$) e o AG não for melhor que o
  MSPD-LS ($p\ge0{,}05$ no teste unilateral AG < MSPD-LS). **Parcial** se o MA for melhor que o AG mas o
  AG também superar o MSPD-LS (o cruzamento contribui por si só). **Refutada** se o MA não for
  significativamente melhor que o AG.

#### Resumo das hipóteses

| Hipótese | Métodos envolvidos | Instâncias | Resultado principal |
|---|---|---|---|
| H1 | MSPD, MSPD-LS | todas | Tabela T1, Figuras F1–F2 |
| H2 | MSPD, MSPD-LS, ILS, VNS, ALNS, MA | todas (+ C–E com $5t(n)$) | Tabelas T2–T4, Figuras F3–F5 |
| H3 | BB × propostas | todas | Tabelas T5–T6, Figura F6 |
| H4 | EXACT × propostas | A–C | Tabelas T7–T8 |
| H5 | propostas | TSPLIB | Tabelas T9–T10, Figuras F7–F8 |
| H6 | ILS, ILS-C, VNS, ALNS, ALNS−C, MA | D, E | Tabelas T11–T12, Figura F9 |
| H7 | LBR, MSPD | A–C | Tabela T13, Figura F10 |
| H8 | AG, MA, MSPD-LS | todas | Tabela T14, Figura F11 |

---

## Referências

Álvarez-Miranda, E., Luipersbeck, M., and Sinnl, M. (2018). Gotta (efficiently) catch them all: Pokémon GO meets orienteering problems. *European Journal of Operational Research*, 265(2):779–794.

Croes, G. A. (1958). A method for solving traveling-salesman problems. *Operations Research*, 6(6):791–812.

Demšar, J. (2006). Statistical comparisons of classifiers over multiple data sets. *Journal of Machine Learning Research*, 7:1–30.

Dolan, E. D. and Moré, J. J. (2002). Benchmarking optimization software with performance profiles. *Mathematical Programming*, 91(2):201–213.

Fischetti, M. and Lodi, A. (2003). Local branching. *Mathematical Programming*, 98(1–3):23–47.

Fischetti, M., Salazar-González, J. J., and Toth, P. (1997). A branch-and-cut algorithm for the symmetric generalized traveling salesman problem. *Operations Research*, 45(3):378–394.

Lourenço, H. R., Martin, O. C., and Stützle, T. (2003). Iterated local search. In Glover, F. and Kochenberger, G. A., editors, *Handbook of Metaheuristics*, pages 320–353. Kluwer, Boston.

Miller, C. E., Tucker, A. W., and Zemlin, R. A. (1960). Integer programming formulation of traveling salesman problems. *Journal of the ACM*, 7(4):326–329.

Mladenović, N. and Hansen, P. (1997). Variable neighborhood search. *Computers & Operations Research*, 24(11):1097–1100.

Moscato, P. (1989). On evolution, search, optimization, genetic algorithms and martial arts: towards memetic algorithms. Technical Report C3P 826, Caltech Concurrent Computation Program.

Or, I. (1976). *Traveling salesman-type combinatorial problems and their relation to the logistics of regional blood banking*. PhD thesis, Northwestern University.

Reinelt, G. (1991). TSPLIB — a traveling salesman problem library. *ORSA Journal on Computing*, 3(4):376–384.

Ropke, S. and Pisinger, D. (2006). An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows. *Transportation Science*, 40(4):455–472.

Sevkli, Z. and Sevilgen, F. E. (2006). Variable neighborhood search for the orienteering problem. In *Computer and Information Sciences – ISCIS 2006*, LNCS 4263, pages 134–143. Springer.

Shaw, P. (1998). Using constraint programming and local search methods to solve vehicle routing problems. In *Principles and Practice of Constraint Programming – CP98*, LNCS 1520, pages 417–431. Springer.

Takahashi, H. and Matsuyama, A. (1980). An approximate solution for the Steiner problem in graphs. *Mathematica Japonica*, 24(6):573–577.

Tasgetiren, M. F. (2002). A genetic algorithm with an adaptive penalty function for the orienteering problem. *Journal of Economic and Social Research*, 4(2):1–26.

Tsiligirides, T. (1984). Heuristic methods applied to orienteering. *Journal of the Operational Research Society*, 35(9):797–809.

Vansteenwegen, P., Souffriau, W., Vanden Berghe, G., and Van Oudheusden, D. (2009). Iterated local search for the team orienteering problem with time windows. *Computers & Operations Research*, 36(12):3281–3290.
