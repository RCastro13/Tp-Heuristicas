# Estado da execução oficial

Concluída em 06/11/2026. Branch: `execucao-oficial`. Compilação oficial: `-std=c++17 -static`, sem `-O2`.

- Heurísticas: 25.620 de 25.620 execuções, 0 falhas, 0 rotas divergentes (`resultados/brutos/heur.jsonl`).
- Formulação exata (referência para BKS e ótimo, 600 s por instância): 294 de 294 instâncias, 0 erros, 234 ótimos provados (`resultados/brutos/exato.jsonl`). As 208 primeiras rodaram com 5 processos; as 86 restantes, com 4, por falta de memória (cada HiGHS chega a centenas de MB nas instâncias de n = 200).
- Análise final: `RESULTADOS.md`, `resultados/tabelas/`, `resultados/figuras/` (inclui `artigo_painel.pdf`), `resultados/latex/`, `resumo.json` e `ambiente.json`.
- Seções 4 e 5 do artigo em LaTeX: `../artigo/secoes_4_5.tex`.

Hipóteses numeradas como em `tp3-heu.pdf`: H1 confirmada; H2 parcialmente confirmada com `brg180` (ALNS não vence o MSPD) e confirmada sem `brg180`; MA é o melhor, confirmado; H3 confirmada.

Decisão da equipe sobre `brg180`: manter os dados (VNS, ILS, ALNS e MA sem solução viável, gap de 100%) e apresentar a comparação com e sem essas instâncias (tabela `h2_sensibilidade_brg180`).

Para refazer só a análise: `powershell -ExecutionPolicy Bypass -File .\executa_tudo.ps1 -Etapa analise` (registra 5 processos no `ambiente.json`; a nota sobre 4 processos foi escrita à mão nesta execução).
