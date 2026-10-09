Como desenvolvedor focado em problemas de otimização, apresento o projeto arquitetural detalhado para o desenvolvimento de métodos de solução heurística e metaheurística aplicados ao Generalized Clustered Orienteering Problem (GCOP).

Abaixo está o relatório detalhando a caracterização da solução, as opções algorítmicas (da construção de base até estratégias avançadas) e o esquema para a bateria de testes.

## 1. Caracterização do Problema e da Solução

O GCOP combina características do Orienteering Problem (OP) e do Generalized Traveling Salesman Problem (GTSP). O objetivo é encontrar um *tour* (ciclo) não enraizado que maximize a coleta de prêmios (receitas) associados aos nós, sujeito a duas restrições principais:

1. **Cobertura de Clusters:** O *tour* deve visitar obrigatoriamente pelo menos um nó de cada um dos $K$ clusters especificados.


2. **Orçamento de Roteamento:** A soma das distâncias percorridas não pode exceder um orçamento (budget) pré-definido $B$.



**A Estrutura da Solução:**
Uma solução válida é representada por um subgrafo $T = (V_T, E_T)$, caracterizando um ciclo simples onde a distância total satisfaz $\sum_{e \in E_T} d_e \le B$. A qualidade da solução (função objetivo) é medida por $\sum_{i \in V_T} p_i$, onde $p_i$ é o prêmio do nó $i$. Diferente do OP clássico, não há um nó de partida fixo, tornando o problema livre de origem/destino absoluto.

---

## 2. Abordagens Construtivas (Geração de Solução Inicial)

Para iniciar a exploração, precisamos de métodos que gerem soluções viáveis ou quase-viáveis rapidamente. Com base na estrutura do GCOP, propõem-se as seguintes heurísticas construtivas:

* **Heurística de Inserção do Mais Próximo/Mais Distante (Nearest/Farthest Insertion):** Adaptação de heurísticas do GTSP. Esta abordagem foca em visitar o conjunto mínimo de nós necessários para cobrir os clusters. Geralmente requer um refinamento posterior severo, pois o lucro coletado tende a ser baixo.


* **Construção Baseada em Árvore de Steiner:** Constrói-se um grafo auxiliar adicionando nós terminais artificiais conectados a todos os membros de cada cluster correspondente. Calcula-se uma árvore de Steiner heurística usando distâncias modificadas e, em seguida, define-se um *tour* escolhendo uma raiz aleatória e realizando uma travessia em pré-ordem na árvore. Isso assegura a cobertura dos clusters e alta probabilidade de respeitar o orçamento.


* **Construção Baseada em TSP:** Identifica-se um subconjunto promissor de nós (por exemplo, vértices com valor relaxado $\tilde{y}_i \ge 0.5$ em uma iteração de relaxação linear) e utiliza-se um *solver* TSP exato (como o Concorde) para encontrar a rota ótima entre eles. Esta estratégia costuma encontrar soluções próximas do ótimo, embora possa violar o limite $B$ ou as restrições de cluster inicialmente.



---

## 3. Heurísticas de Melhoria e Busca Local

Uma vez que o *tour* inicial $T = (V_T, E_T)$ é construído, aplicam-se movimentos inter-rotas e intra-rotas utilizando a métrica de "custo-benefício" $\sigma_i = \min_{j \in V_T \setminus \{i\}} d_{ij} / p_i$.

* **Reparo de Viabilidade (Deleção):** Exclusão iterativa do nó $i^* = \arg\max_{i \in V_T} \sigma_i$ enquanto o orçamento da distância exceder $B$.


* **Reparo de Clusters (Inserção Obrigatória):** Inserção do nó $i^* = \arg\min_{i \in C_k} \sigma_i$ para cada cluster $C_k$ que não possui interseção com o *tour* atual ($C_k \cap V_T = \emptyset$).


* **Maximização de Prêmio (Inserção Opcional):** Inserção do nó $i^* = \arg\min_{i \in V \setminus V_T} \sigma_i$ enquanto o limite de distância permitir ($D(V_T \cup \{i^*\}) \le B$).


* **Swap (Troca de Nós):** Substituição simultânea de um nó presente no *tour* por um de fora ($i \in V_T$ trocado por $j \notin V_T$) sempre que $\sigma_i < \sigma_j$, mantendo o cumprimento do orçamento e a restrição do cluster.


* **Otimização de Roteamento (2-opt e 3-opt):** Utilizados de forma exaustiva em $T$ para otimizar o sequenciamento dos nós e reduzir o consumo de distância percorrida, liberando margem no orçamento $B$ para futuras inserções.



---

## 4. Estratégias Metaheurísticas

Para evitar ótimos locais na bateria de testes, a estrutura base deve ser envolvida por abordagens de metaheurísticas e matheurísticas:

* **Multi-Start com Distâncias Perturbadas:** Repete a fase de construção várias vezes iterando sobre distâncias levemente randomizadas, onde o novo custo da aresta $\tilde{d}_e$ é selecionado de uma distribuição uniforme no intervalo $[d_e, 1.2d_e]$. Isso permite explorar diferentes caminhos durante as inserções gulosas.


* **Matheurística de Local Branching (Refinamento Principal):** Após a etapa heurística multi-start, formula-se um modelo de programação inteira restrito a uma vizinhança definida pela solução atual. Adiciona-se uma restrição limitando a diferença estrutural a um máximo de $k$ alterações de nós em relação à solução de incumbência (incumbente). A busca inicia com $k=2$ e, caso não haja melhora, expande progressivamente até $k=6$.


* **Iterated Local Search (ILS) / Adaptive Large Neighborhood Search (ALNS):** (Extensão Desenvolvedor) Como os movimentos dependem do raio espacial dos clusters, implementar operações de ruína (Remover todos os nós de um quadrante geográfico) e recriação (Reinserir priorizando nós de clusters não visitados baseados na função regret/arrependimento) ajudaria imensamente em rodadas de tempo estendido.

---

## 5. Análise de Aproximação da Solução

* **Velocidade vs Qualidade:** As rotinas de multi-start aliadas às operações de inserção/deleção demonstraram ser capazes de fornecer soluções com um gap de optimalidade (Primal Gap) dentro da faixa de 0.5% em relação ao limite inferior alcançado pelo método exato de *Branch-and-Cut*.


* **Sucesso em Soluções Ótimas:** Em instâncias baseadas no conjunto TSPLIB, a heurística de multi-start foi capaz de encontrar o *tour* ótimo em 12% dos casos independentemente do *solver*.


* **Eficiência do Local Branching:** Quando acoplado como ferramenta de refino, o Local Branching superou a barreira das heurísticas puras e encontrou o tour ótimo em 71% de todos os casos de instâncias do TSPLIB. No entanto, em instâncias de larga escala com topologias mais complexas (cenários reais de Pokémon GO), a melhora proporcionada pelo Local Branching torna-se menos pronunciada.



---

## 6. Proposta para a Bateria de Testes

A bateria de testes deverá isolar o impacto do número de clusters, folga do orçamento e estrutura de preços.

* **Conjunto TSPLIB Adaptado:** Converter 65 instâncias do TSPLIB simétricas (até 500 nós) distribuindo os vértices em clusters e garantindo um tamanho mínimo de cluster igual a 2.


* **Cálculo do Orçamento $B$ (TSPLIB):** Realizar varreduras paramétricas onde $B = \alpha \cdot TSP_{OPT} + (1 - \alpha) \cdot GTSP_{FEAS}$, variando $\alpha \in \{0.25, 0.5, 0.75\}$.


* **Conjunto "Mundo Real" Pokémon GO:** Construir grafos usando as ruas de cidades base (Viena, Londres e Budapeste) usando distâncias de caminhos mais curtos da rede viária real, sem assumir desigualdade triangular.


* **Esquemas de Lucro:** Rodar todas as instâncias utilizando (i) lucros uniformes e (ii) lucros aleatórios (ex: limitados entre 1 e 100) para cada espécie/cluster. Testar orçamentos práticos associados à realidade de percursos a pé (ex: $B \in \{10, 15, 20\}$ km) e omitir clusters inteiros randomicamente para simular espécies indesejadas pelo usuário.