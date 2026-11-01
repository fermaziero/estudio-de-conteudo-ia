# Como o painel calcula

Para quem precisa explicar um número do painel ou conferir uma conta. As constantes ficam no começo de `scripts/_analise.py`; se mudar uma, mude também este arquivo.

## Entradas e saída

| Arquivo (em `marcas/<marca>/`) | Para que serve | Se faltar |
|---|---|---|
| `estrategia.json` | Metas, pilares, ritmo, funil. Obrigatório e válido. | O script para e pede para corrigir. |
| `metricas/perfil.csv` | Seguidores ao longo do tempo (uma linha por coleta). | Seguidores e metas de seguidores ficam "não medido". |
| `metricas/posts.csv` | Desempenho de cada post (uma linha por post por coleta). Vale a coleta mais recente de cada post. | Desempenho, grupos e ranking ficam "não medido". |
| `publicacao/publicados.csv` | Posts publicados por este projeto. Completa o ritmo e o formato. | Os posts do projeto só são reconhecidos pelo `post_id` do `posts.csv`. |
| `conteudo/<lote>/posts/<id>.json` | Pilar, formato, etapa do funil e chamada de cada post do projeto. | O post entra nos totais, mas fica "sem classificação" em pilar e etapa. |
| `referencias/referencias.csv` | Perfis de referência. | O bloco de referências mostra como obter. |
| `visual.json` | Só o nome que aparece no título. | Usa o nome da pasta. |

Saída: `metricas/painel.html`. Um arquivo só, com os dados e os gráficos (SVG) dentro, sem biblioteca externa e sem internet. O mesmo conjunto de números vai embutido numa tag `<script type="application/json" id="dados-do-painel">`, e `--json` imprime o mesmo conteúdo no terminal. Chaves de primeiro nível: `marca`, `gerado_em`, `hoje`, `janela_dias`, `estrategia`, `dados` (última coleta, idade, arquivos lidos), `seguidores`, `kpis`, `metas`, `ritmo`, `grupos` (`conta`, `pilar`, `formato`, `etapa`), `funil`, `posts`, `ranking`, `referencias`, `qualidade` (avisos) e `alertas`.

## Datas e tempo

- **Hoje:** a data do computador (`--hoje` troca, útil para testar).
- **Fim dos dados:** a data mais recente entre a última coleta e a última publicação conhecida, nunca depois de hoje. Todas as janelas terminam aí, para que uma coleta velha não crie "dias sem post" que não foram medidos.
- **Fuso:** o dia de cada post é contado em `-03:00` (Brasília). `--fuso` troca.
- Data sem hora vale meio-dia: o erro máximo na maturidade é de 12 horas.
- Aceita `AAAA-MM-DD`, data com hora ISO 8601 (com `Z`, `+00:00` ou `-03:00`) e `dd/mm/aaaa`.

## Constantes

| Regra | Valor |
|---|---|
| Aviso de dado velho | mais de 7 dias desde a última coleta |
| Post maduro | coleta feita 48 horas ou mais depois da publicação |
| Janela dos cartões e das metas | 28 dias, comparada com os 28 anteriores |
| Janela dos grupos (`--janela-dias`) | 56 dias (8 semanas) |
| Tendência de seguidores | coleta mais próxima de 28 dias atrás, com no mínimo 14 dias de distância |
| Tamanho da amostra (posts maduros) | 1 ou 2 = só uma pista; 3 ou 4 = amostra pequena; 5 ou mais = base razoável |
| Ranking | pelo menos 6 posts maduros com o dado |
| Post dominante | mais de 50% do alcance (ou do total) do grupo, com 3 posts ou mais |
| Grupo acima ou abaixo da conta | índice de 1,25 ou mais / 0,75 ou menos, com 3 posts ou mais no grupo |
| Ritmo: média | últimas 4 semanas completas (mínimo 2) |
| Ritmo: status | 100% ou mais da meta = no ritmo; de 70% a 99% = abaixo; menos de 70% = bem abaixo |
| Meta: status por ritmo | ritmo recente ÷ necessário: 1 ou mais = no caminho; de 0,6 a 1 = atenção; menos de 0,6 = crítico |
| Pilar fora do peso | 20 pontos percentuais ou mais, com 6 posts classificados ou mais |
| Referência antiga | mais de 90 dias |

## Os blocos

**Pontos de atenção.** Lista em ordem de prioridade, gerada das regras abaixo. São observações, não conclusões.
- Alta: nenhuma coleta; coleta com mais de 7 dias; meta crítica ou com prazo vencido; ritmo de publicação abaixo de 70% da meta.
- Média: meta em atenção; ritmo entre 70% e 99%; pilar fora do peso; etapa do funil sem nenhum post; hipótese de gargalo; menos de 6 posts maduros.
- Baixa: meta sem medição; movimento da estratégia com prazo vencido; um post domina o alcance de um grupo; posts do projeto sem classificação; referência antiga.
- Aviso: posts com menos de 48 horas; estratégia em rascunho.

**Resumo.** Quatro cartões e o número de seguidores.
- *Seguidores:* última coleta; variação nos últimos dias medidos (crescimento líquido).
- *Posts por semana:* média das últimas semanas completas.
- *Alcance médio por post:* média dos posts maduros dos últimos 28 dias. A variação contra os 28 dias anteriores só aparece com 5 posts maduros em cada janela, sem post dominante e com diferença maior que um erro-padrão (a variação normal entre um post e outro). Senão, o cartão diz que não há base para comparar.
- *Interação de valor:* soma de salvamentos, compartilhamentos e comentários dividida pela soma dos alcances, só com os posts que têm os três números.
- *Alcance ÷ seguidores:* mediana do alcance de cada post dividido pelos seguidores na data da publicação (última coleta do perfil até aquele dia; se não houver coleta recente, o ranking marca "aprox.").

**Metas.** Base, onde está, alvo, prazo.
- *Onde está (atual):* `seguidores` = última coleta; `posts_por_semana` = média das últimas semanas completas; `alcance_medio`, `salvamentos_medio`, `comentarios_medio` e `compartilhamentos_medio` = média dos posts maduros dos últimos 28 dias (mínimo 3); `manual` = o campo `atual` da meta.
- *Ritmo necessário:* (alvo − atual) ÷ semanas até o prazo.
- *Ritmo recente:* para seguidores, a variação por semana entre a última coleta e a de uns 28 dias antes. Para as médias, a diferença entre a média dos últimos 28 dias e a dos 28 anteriores, dividida por 4, só quando `diferenca_confiavel` aprova (mesmas condições do cartão de alcance).
- *Status:* Atingida (o atual passou do alvo), No caminho, Atenção, Crítico, Prazo vencido, Sem base para o ritmo (falta tendência confiável), Não medido, Amostra pequena (menos de 3 posts maduros). A meta `posts_por_semana` não usa ritmo necessário: compara a média recente com o alvo (70% ou mais = Atenção; menos = Crítico).
- Metas em rascunho aparecem marcadas como sugestão.

**Movimentos do período.** As ações de `movimentos` da estratégia, cada uma com o prazo (dias que faltam ou "prazo vencido") e, quando o `indicador` é um dos nomes conhecidos (`seguidores`, `posts_por_semana`, `alcance_medio`, `salvamentos_medio`, `comentarios_medio`, `compartilhamentos_medio`), o valor de hoje desse indicador. Texto livre no `indicador` aparece como está e vale como "a pessoa informa".

**Evolução de seguidores.** Uma linha com as coletas. Quando existe meta de seguidores não atingida, o gráfico estende duas linhas até 6 semanas à frente (ou até o prazo, se vier antes): o *ritmo necessário* (laranja tracejada) e, se houver tendência, *se mantiver o ritmo recente* (cinza pontilhada, **hipótese**, nunca previsão). Cada ponto mostra o valor e a variação no passar do mouse ou do foco.

**Ritmo de publicação.** Colunas por semana (segunda a domingo), até 8 semanas, separando posts do projeto e posts de fora. A semana em curso e a primeira semana, se os dados começam no meio dela, aparecem mais claras e ficam fora da média. Sem `posts.csv`, só conta os posts do `publicados.csv` e avisa.

**Desempenho por pilar, formato e etapa.** Para cada grupo: posts (e quantos maduros), alcance médio e mediana, e para salvamentos, compartilhamentos e comentários a taxa sobre o alcance (número grande) e a média por post. ▲ e ▼ marcam grupos 25% acima ou abaixo da taxa da conta (só com 3 posts ou mais no grupo e nunca no grupo "sem classificação"). Pilar mostra *peso planejado → fatia real*; formato mostra *posts por semana planejados → média real*; etapa mostra a fatia dos posts. Posts de fora do projeto, ou sem arquivo em `conteudo/`, caem em "Sem classificação" nas tabelas de pilar e etapa; o formato vem do `tipo` do `posts.csv` (carrossel, post_unico, reel; `video` conta como reel).

**Funil.** Cada etapa tem uma métrica-chave comparada com a média da conta: atração = alcance relativo (mediana); relacionamento = salvamentos ÷ alcance; conversão = comentários ÷ alcance, que é só uma aproximação (cliques e conversas no direct não são medidos). Com 2 etapas ou mais com 3 posts maduros ou mais, a de menor índice vira **hipótese** de gargalo se ficar em 0,75 ou menos.

**Melhores e piores posts.** Dois rankings (alcance ÷ seguidores; interação de valor), três melhores e três piores de cada, só com 6 posts maduros ou mais. Comparam posts da mesma conta por proporção.

**Referências.** Barras de views ÷ seguidores (você em azul, referências em cinza) e tabela. Os números da conta vêm da mediana de visualizações dos posts maduros; o `% com chamada` vem do campo `chamada` dos posts do projeto. Referência é régua, não meta.

**Dados e como ler.** Arquivos lidos (linhas, data mais recente, idade), colunas extras de insights do perfil (se existirem), avisos sobre os dados e glossário.

## Tolerância dos arquivos CSV

- Aceita UTF-8 (com ou sem BOM) e Windows-1252 (avisa), separador vírgula, ponto e vírgula ou tab.
- Ignora colunas desconhecidas. Coluna ausente = "não medido". Célula vazia, `-`, `n/d` = "não medido".
- Número inteiro com ponto de milhar (`1.234`) vale 1234 nas colunas de contagem. Número negativo, texto ou decimal em coluna inteira vira "não medido" e gera aviso.
- Mais de uma coleta no mesmo dia: vale a última. Coleta com data no futuro: ignorada, com aviso.
- Chave de cada post: `media_id`; se faltar, `permalink`; se faltar, data de publicação + tipo.
- Colunas extras de insights do perfil que o painel reconhece (para os campos "alcance da conta", "visualizações da conta", "visitas ao perfil", "seguidores ganhos" e "seguidores perdidos"): `alcance`, `visualizacoes`, `visitas_perfil`, `seguidores_ganhos`, `seguidores_perdidos` (e apelidos como `novos_seguidores` ou `deixaram_de_seguir`). Aparecem em "Dados e como ler" com o valor da última coleta; o painel não soma coletas porque a janela de cada valor é a que a coleta registrou.

## Opções e códigos de saída

`montar_painel.py [--marca M] [--simular] [--json] [--saida ARQ] [--janela-dias N] [--hoje AAAA-MM-DD] [--fuso -03:00] [--raiz PASTA] [--ajuda]`. Saída 0 = montado; 1 = problema nos arquivos (por exemplo `estrategia.json` inválido); 2 = erro de uso. `validar_estrategia.py [--marca M] [--arquivo ARQ] [--hoje ...]` usa as mesmas saídas.

## O que o painel não faz

- Não separa alcance pago de orgânico.
- Não mede conversas, cliques nem vendas, e não atribui seguidores a posts.
- Não conclui nada com amostra pequena: só avisa.
- Não altera nenhum arquivo além do próprio `painel.html`.
