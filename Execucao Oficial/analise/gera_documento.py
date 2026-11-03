"""Gera RESULTADOS.md a partir de resultados/resumo.json, resultados/tabelas e resultados/ambiente.json.

Os vereditos e números vêm só dos dados: nada é escrito antes de a análise existir, e o que faltar
(por exemplo, a formulação exata) aparece como pendente.

Uso: python analise/gera_documento.py [pasta_resultados] [arquivo_saida]
"""
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "resultados")
DESTINO = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "RESULTADOS.md")
ESPERADAS = 408 * 6 * 10 + (96 + 18) * 10

REFERENCIAS = """
Do artigo:

1. Álvarez-Miranda, E.; Luipersbeck, M.; Sinnl, M. Gotta (efficiently) catch them all: Pokémon GO meets orienteering problems. *European Journal of Operational Research*, 265(2):779-794, 2018.
2. Croes, G. A. A method for solving traveling-salesman problems. *Operations Research*, 6(6):791-812, 1958.
3. Fischetti, M.; Salazar-González, J. J.; Toth, P. A branch-and-cut algorithm for the symmetric generalized traveling salesman problem. *Operations Research*, 45(3):378-394, 1997.
4. Lourenço, H. R.; Martin, O. C.; Stützle, T. Iterated local search. In *Handbook of Metaheuristics*, p. 320-353. Kluwer, 2003.
5. Mladenović, N.; Hansen, P. Variable neighborhood search. *Computers & Operations Research*, 24(11):1097-1100, 1997.
6. Moscato, P. On evolution, search, optimization, genetic algorithms and martial arts: towards memetic algorithms. Technical Report C3P 826, Caltech, 1989.
7. Or, I. *Traveling Salesman-Type Combinatorial Problems and Their Relation to the Logistics of Regional Blood Banking*. PhD thesis, Northwestern University, 1976.
8. Penicka, R.; Faigl, J.; Saska, M. Variable neighborhood search for the set orienteering problem and its application to other orienteering problem variants. *European Journal of Operational Research*, 276(3):816-825, 2019.
9. Ropke, S.; Pisinger, D. An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows. *Transportation Science*, 40(4):455-472, 2006.
10. Sevkli, Z.; Sevilgen, F. E. Variable neighborhood search for the orienteering problem. In *ISCIS 2006*, LNCS 4263, p. 134-143. Springer, 2006.
11. Takahashi, H.; Matsuyama, A. An approximate solution for the Steiner problem in graphs. *Mathematica Japonica*, 24(6):573-577, 1980.
12. Tsiligirides, T. Heuristic methods applied to orienteering. *Journal of the Operational Research Society*, 35(9):797-809, 1984.
13. Vansteenwegen, P.; Souffriau, W.; Vanden Berghe, G.; Van Oudheusden, D. Iterated local search for the team orienteering problem with time windows. *Computers & Operations Research*, 36(12):3281-3290, 2009.

Acrescentadas para os testes:

14. Friedman, M. The use of ranks to avoid the assumption of normality implicit in the analysis of variance. *Journal of the American Statistical Association*, 32(200):675-701, 1937.
15. Holm, S. A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2):65-70, 1979.
16. Huangfu, Q.; Hall, J. A. J. Parallelizing the dual revised simplex method. *Mathematical Programming Computation*, 10(1):119-142, 2018. (HiGHS)
17. Martin, O.; Otto, S. W.; Felten, E. W. Large-step Markov chains for the traveling salesman problem. *Complex Systems*, 5(3):299-326, 1991. (perturbação do ILS que calcula o orçamento)
18. Pratt, J. W. Remarks on zeros and ties in the Wilcoxon signed rank procedures. *Journal of the American Statistical Association*, 54(287):655-667, 1959.
19. Reinelt, G. TSPLIB: a traveling salesman problem library. *ORSA Journal on Computing*, 3(4):376-384, 1991.
20. Wilcoxon, F. Individual comparisons by ranking methods. *Biometrics Bulletin*, 1(6):80-83, 1945.
"""

DECISOES = """
Pontos em que o artigo não define um detalhe, ou em que a execução difere dele:

- **Formulação exata:** o texto cita a "Seção 1.2", que não existe no PDF. Foi usada a formulação de arestas do artigo base com cortes de subciclo gerados iterativamente. A melhor rota das heurísticas entra como solução inicial do solver. Isso só acelera a prova: não altera o ótimo nem o limitante.
- **Número de clusters:** os arquivos dos autores têm um rótulo a mais que o cabeçalho (eil51: `Clusters 11`, 12 rótulos). Vale o rótulo de cada vértice, então K é o número de rótulos distintos.
- **Distâncias:** o texto diz "euclidianas", mas parte dos grafos vem de matrizes explícitas ou coordenadas geográficas da TSPLIB. Foram usadas as distâncias dos arquivos.
- **TSP e GTSP do orçamento:** os arquivos usam distâncias sem o arredondamento da TSPLIB, então os valores publicados não se aplicam diretamente. Os dois comprimentos vêm de um ILS sobre as distâncias dos arquivos (`dados/orcamento.csv`). Toda rota encontrada é um limitante superior válido, o que preserva a garantia B ≥ GTSP.
- **POKE:** as espécies obrigatórias são sorteadas entre as que têm ao menos duas ocorrências, para haver escolha de representante. O prêmio inverso à frequência é p = f_max / f_espécie.
- **REPARA:** sem vértice removível, aplica OTIMIZAROTA mais uma vez antes de declarar a solução inviável, porque a rota pode caber depois de encurtada.
- **Partida:** se INICIAL não for viável nas três construções, usa GRASP + REPARA + BL até obter solução viável ou esgotar o tempo.
- **ALNS:** uma solução de mesmo prêmio e mesmo comprimento é aceita sem pontuar, pois o Algoritmo 4 não a classifica. Os pesos não têm piso mínimo.
- **MA:** a melhor solução é sempre a melhor da população. Um filho com o mesmo conjunto de vértices de um indivíduo é rejeitado mesmo que seja mais curto, como no critério "inédito".
- **Interrupção por tempo:** a BL interrompida devolve a solução viável corrente; um REPARA interrompido descarta a solução.
"""


def tabela(nome):
    caminho = os.path.join(RES, "tabelas", f"{nome}.md")
    if not os.path.exists(caminho):
        return "*Pendente: tabela ainda não gerada.*\n"
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def figura(nome, legenda):
    if os.path.exists(os.path.join(RES, "figuras", f"{nome}.png")):
        return f"![{legenda}](resultados/figuras/{nome}.png)\n\n*{legenda}*\n"
    return f"*Pendente: {legenda}.*\n"


def fp(p):
    return "n/d" if p is None else ("< 0,0001" if p < 1e-4 else f"{p:.4f}".replace(".", ","))


def fn(x, c=3):
    return "n/d" if x is None else f"{x:.{c}f}".replace(".", ",")


def main():
    with open(os.path.join(RES, "resumo.json"), encoding="utf-8") as f:
        r = json.load(f)
    amb = {}
    if os.path.exists(os.path.join(RES, "ambiente.json")):
        with open(os.path.join(RES, "ambiente.json"), encoding="utf-8") as f:
            amb = json.load(f)
    h1, h2, h3, h4 = r.get("H1", {}), r.get("H2", {}), r.get("H3", {}), r.get("H4", {})
    completa = r["execucoes"] == ESPERADAS
    d = ["# Resultados e conclusões: heurísticas para o GCOP\n"]
    d.append("Documento gerado por `analise/gera_documento.py` a partir dos resultados brutos.\n")
    if not completa:
        d.append(f"> **Atenção: bateria incompleta.** Há {r['execucoes']} execuções de {ESPERADAS} previstas; os vereditos abaixo são parciais.\n")

    d.append("## 1. Vereditos\n")
    d.append("| Hipótese | Veredito | Evidência |\n|---|---|---|")
    d.append(f"| H1: BL reduz o gap em relação ao refinamento σ | **{h1.get('veredito', 'pendente')}** | Wilcoxon p = {fp(h1.get('p'))}; classes em que o MSPD-LS perde: {', '.join(h1.get('classes_pior', [])) or 'nenhuma'} |")
    d.append(f"| H2: metaheurísticas vencem o MSPD | **{h2.get('veredito', 'pendente')}** | Friedman p = {fp(h2.get('friedman_p'))}; vencem o MSPD: {', '.join(h2.get('vencem_mspd', [])) or 'nenhuma'} |")
    d.append(f"| H2: o MA é o melhor | **{'confirmada' if h2.get('ma_e_o_melhor') else 'não confirmada'}** | menor rank médio: {h2.get('melhor_rank', 'n/d')} |")
    if "veredito" in h3:
        d.append(f"| H3: distância ao ótimo de {h3['melhor']} | **{h3['veredito']}** | gap médio {fn(h3['gap_medio'])}%; {fn(h3['pct_otimas'], 1)}% de execuções ótimas; {h3['provadas']} ótimos provados |")
    else:
        d.append("| H3: distância ao ótimo | **pendente** | formulação exata ainda não executada |")
    d.append(f"| H4: clusters espalhados exigem troca de representante | **{h4.get('veredito', 'pendente')}** | degradação do ILS maior que a do VNS e a do ALNS: {'sim' if h4.get('cond_i') else 'não'}; ILS-C < ILS em PK: p = {fp(h4.get('p_ilsc'))} |\n")

    d.append("## 2. Ambiente e execução\n")
    if amb:
        d.append("| Item | Valor |\n|---|---|")
        for k, v in amb.items():
            d.append(f"| {k} | {v} |")
        d.append("")
    else:
        d.append("*`resultados/ambiente.json` não encontrado.*\n")
    d.append(f"- Execuções analisadas: {r['execucoes']} de {ESPERADAS} previstas; {r['instancias']} instâncias com os seis métodos.")
    d.append(f"- Falhas de execução: {r['erros_execucao']}. Execuções sem solução viável (gap de 100%): {r['inviaveis']}.")
    d.append(f"- Rotas divergentes na reavaliação independente em Python: {r['rotas_divergentes']}.")
    d.append(f"- Instâncias em que uma heurística superou um ótimo declarado: {r['heuristica_acima_do_otimo']} (deve ser 0).")
    d.append(f"- Excesso sobre t(n): percentil 99 de {fn(r['excesso_tempo_p99_s'])} s e máximo de {fn(r['excesso_tempo_max_s'])} s.\n")
    d.append("**Desvio de compilação em relação ao artigo:** o artigo especifica `-O2`; esta execução usou as opções registradas acima. Sem otimização, cada método faz menos iterações em t(n), o que afeta os valores absolutos de gap e pode afetar a comparação com o solver, que é um binário otimizado. Se o limite da formulação exata for diferente de 3.600 s, menos ótimos podem ser provados e os limitantes tendem a ser mais fracos.\n")

    d.append("## 3. Hipótese 1\n")
    d.append(tabela("h1_por_classe"))
    d.append(figura("h1_dispersao", "Gap do MSPD (x) e do MSPD-LS (y) por instância; cor e marcador indicam a classe"))
    d.append("Critério: confirmada se p < 0,05 e o MSPD-LS não for pior em nenhuma classe; parcial se p < 0,05 mas pior em alguma; refutada se p ≥ 0,05. As colunas de iterações e de tempo de melhoria indicam se um ganho vem de uma melhoria mais eficaz ou de mais reinícios.\n")

    d.append("## 4. Hipótese 2\n")
    d.append(tabela("h2_medidas"))
    d.append(tabela("h2_wilcoxon"))
    d.append(tabela("h2_gap_por_classe"))
    d.append(figura("h2_boxplot", "Distribuição do gap médio por instância"))
    d.append(figura("h2_acumulada", "Porcentagem de instâncias com gap até τ"))
    if h2.get("ranks"):
        d.append("Rank médio: " + ", ".join(f"{k} {fn(v, 2)}" for k, v in sorted(h2["ranks"].items(), key=lambda x: x[1])) + ".\n")

    d.append("## 5. Hipótese 3\n")
    d.append(tabela("h3_gap_otimo"))
    d.append(tabela("h3_exato"))
    if h3.get("apenas_descritiva"):
        d.append("Como a otimalidade foi provada em menos de 30 instâncias, a avaliação é apenas descritiva, conforme o artigo.\n")
    d.append("A conclusão não se estende às classes T4 e PK, em que a formulação exata não é executada.\n")

    d.append("## 6. Hipótese 4\n")
    d.append(tabela("h4_degradacao"))
    d.append(figura("h4_barras", "Gap médio por método nas classes T4 e PK"))
    if h4:
        d.append(f"Vitórias/empates/derrotas do ILS-C contra o ILS em PK: {'/'.join(map(str, h4['vde_ilsc_ils']))}. Como PK tem 18 instâncias e difere de T4 em mais de um aspecto, um efeito é atribuído à combinação dessas características, e não a uma delas isoladamente.\n")

    d.append("## 7. Conclusões\n")
    d.append("*Síntese automática dos critérios do artigo; a interpretação dos mecanismos deve ser feita pela equipe a partir das tabelas acima.*\n")
    d.append(f"- **H1 {h1.get('veredito', 'pendente')}.** Com o mesmo multi-start e o mesmo tempo, a troca do refinamento σ pela BL obteve p = {fp(h1.get('p'))}.")
    d.append(f"- **H2 {h2.get('veredito', 'pendente')}.** {len(h2.get('vencem_mspd', []))} de 4 metaheurísticas venceram o MSPD com p de Holm < 0,05. O menor rank médio foi de {h2.get('melhor_rank', 'n/d')}, e a afirmação de que o MA é o melhor {'foi confirmada' if h2.get('ma_e_o_melhor') else 'não foi confirmada'}.")
    if "veredito" in h3:
        d.append(f"- **H3 {h3['veredito']}.** {h3['melhor']} ficou a {fn(h3['gap_medio'])}% do ótimo em média e atingiu o ótimo em {fn(h3['pct_otimas'], 1)}% das execuções, nas {h3['provadas']} instâncias com ótimo provado.")
    else:
        d.append("- **H3 pendente.** A formulação exata ainda não foi executada.")
    d.append(f"- **H4 {h4.get('veredito', 'pendente')}.**\n")

    d.append("## 8. Decisões de implementação e divergências\n")
    d.append(DECISOES)
    d.append("## 9. Referências\n")
    d.append(REFERENCIAS)
    with open(DESTINO, "w", encoding="utf-8") as f:
        f.write("\n".join(d))
    print(DESTINO, "gerado")


if __name__ == "__main__":
    main()
