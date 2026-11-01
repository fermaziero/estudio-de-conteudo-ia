# Metas: como ler o status e como propor ajuste

Leia este arquivo antes de propor qualquer mudança de meta (Passo 5 do `SKILL.md`). Só a pessoa muda metas: você mostra os números, sugere e espera o ok. Os exemplos com números são fictícios.

## O que é uma meta

Cada meta de `estrategia.json` tem `id`, `descricao`, `indicador`, `base` (de onde partiu), `alvo` (aonde quer chegar) e `prazo` (AAAA-MM-DD).

| Indicador | O que mede | De onde vem o "atual" |
|---|---|---|
| `seguidores` | Total de seguidores | Última coleta de `perfil.csv` |
| `posts_por_semana` | Frequência de publicação | Média das últimas semanas completas (`posts.csv` e `publicados.csv`) |
| `alcance_medio` | Contas alcançadas por post | Média dos posts maduros dos últimos 28 dias |
| `salvamentos_medio`, `comentarios_medio`, `compartilhamentos_medio` | Média por post | Idem |
| `manual` | Qualquer número que só a pessoa mede (conversas, orçamentos, vendas) | Campo `atual` da própria meta |

Para `manual`, o contrato não define onde fica o valor de hoje. O painel e o `validar_estrategia.py` aceitam dois campos opcionais na meta: `atual` (número) e `atual_em` (data AAAA-MM-DD). Sem eles, a meta aparece como "não medido".

## O que cada status quer dizer e o que propor

| Status | Significa | O que propor |
|---|---|---|
| **Atingida** | O número de hoje passou do alvo. | Parabenize com o número. Sugira um novo alvo e um novo prazo, ou encerrar a meta. Se a média vier de um post só (o painel avisa), diga que o resultado é frágil e sugira esperar mais posts antes de subir o alvo. |
| **No caminho** | O ritmo recente é igual ou maior que o necessário. | Manter. Diga o que está ajudando (com n) e que vale conferir de novo na próxima leitura. |
| **Atenção** | O ritmo recente é de 60% a 99% do necessário. | Manter e agir na causa, ou ajustar o prazo. Mostre as duas contas (abaixo). |
| **Crítico** | O ritmo recente é menos de 60% do necessário, ou está negativo. | Conversar com calma: manter e mudar a tática, mover o prazo ou reduzir o alvo. A decisão é dela. |
| **Sem base para o ritmo** | Há o número de hoje, mas falta tendência confiável (poucas coletas, poucos posts, um post dominante, diferença menor que a variação normal). | Não ajuste meta com base nisso. Diga o que falta (a nota na meta explica) e marque quando olhar de novo. |
| **Amostra pequena** | Menos de 3 posts maduros no período. | Não ajuste. Espere mais posts. |
| **Não medido** | Sem dado. | Troque o indicador por outro que o projeto mede, ou combine com a pessoa como ela informa o número (meta `manual`). |
| **Prazo vencido** | O prazo passou e o alvo não foi atingido. | Pergunte: renovar com novo prazo, trocar a meta ou encerrar. Não deixe meta vencida parada. |

A meta `posts_por_semana` é lida por outra regra: compara a média recente com o alvo (70% ou mais = Atenção; menos = Crítico). Antes de propor mais posts por semana, pergunte quanto tempo a pessoa tem (pergunta 5 do check-in).

## As contas que sustentam uma proposta

Use os números do painel (resumo do script):

- **Ritmo necessário** = (alvo − atual) ÷ semanas até o prazo.
- **Ritmo recente** = o que o painel mostrou (por semana).
- **Alvo possível no prazo** = atual + ritmo recente × semanas até o prazo.
- **Prazo possível para o alvo** = hoje + (alvo − atual) ÷ ritmo recente, em semanas. Só vale com ritmo recente maior que zero.

Exemplo fictício: 872 seguidores, alvo 1.200 em 13 semanas. Faltam 328: o necessário é +25 por semana. O ritmo recente é +17. Mantendo +17, chega a cerca de 1.090 no prazo. Ou chega a 1.200 em cerca de 19 semanas.

Quando propuser um **novo alvo depois de uma meta atingida**, mostre duas opções e diga o que mudaria no trabalho: uma que mantém o ritmo recente e uma mais ambiciosa. Algo como 1,5 vez o ritmo recente serve só de ponto de partida para a conversa; não é regra. Pergunte antes se a pessoa tem tempo, orçamento ou ideia nova para sustentar o ritmo maior.

## Regras ao propor

1. **Uma meta por vez**, em até três linhas: onde está, o que o ritmo diz, o que você sugere e por quê. Sempre inclua a opção de manter como está.
2. **Nunca com base em um pico, em uma coleta só ou em amostra pequena.**
3. **Nunca copie número de referência.** Perfil maior, de outro nicho ou com equipe maior não é régua de meta. Use a referência só como contexto.
4. **Poucas metas** (de 2 a 4). Se a pessoa tem sete, ajude a escolher as que ela realmente persegue.
5. **Meta sem esforço não existe.** Ligue o alvo ao que a pessoa consegue fazer por semana.
6. **Não ponha tudo em seguidores.** Seguidor mede só uma parte. Salvamentos e compartilhamentos mostram se o conteúdo vale guardar e passar adiante; conversas mostram se vira negócio.
7. **Meta de algo que o projeto não mede** vira `manual`, com data combinada para a pessoa informar o número.
8. **Mostre o efeito no painel** ("o ritmo necessário cai de +25 para +17 por semana").

## Registrar o valor de uma meta manual

Se a pessoa informar o número (por exemplo, "foram 7 conversas em outubro"), proponha gravar `"atual": 7` e `"atual_em": "AAAA-MM-DD"` na meta. É uma mudança em `estrategia.json`: vale a mesma regra de ok e de backup.

## Como aplicar (só com ok claro)

1. Guarde a versão atual: `python -X utf8 skills/configurar-marca/scripts/guardar_versao.py --marca <marca> --motivo ajuste-de-metas estrategia.json`.
2. Edite só as metas aprovadas e troque `atualizado_em` para hoje.
3. Valide: `python -X utf8 skills/acompanhar-resultados/scripts/validar_estrategia.py --marca <marca>`. Se der erro, restaure a versão guardada e conte o que aconteceu.
4. Registre: `python -X utf8 skills/configurar-marca/scripts/registrar_feedback.py --marca <marca> --frase "<fala da pessoa, literal>" --mudou "<o que mudou>" --arquivo estrategia.json`.
5. Monte o painel de novo e anote o ok na tabela "Proposta de ajuste de metas" da leitura.

## Aprovar a estratégia (rascunho para vigente)

Enquanto o `status` for `rascunho`, as metas valem como sugestão. Se a pessoa quiser aprovar, pergunte "Posso marcar esta estratégia como vigente?". Só com um sim claro: faça o backup, troque `status` para `vigente` e `atualizado_em` para hoje, valide e registre.

## Exemplos de proposta (fictícios)

> **Seguidores (872 → 1.200 até 31/01).** O ritmo necessário é +25 por semana; nas últimas 4 semanas foi +17. Mantendo assim, chega a cerca de 1.090. Posso (a) manter e testar mais um formato que costuma atrair gente nova, (b) mover o prazo para meados de março ou (c) baixar o alvo para 1.100. O que prefere?

> **Salvamentos por post (14,8 → 20).** Ainda não dá para dizer se o ritmo é bom: um post tem metade do total dos salvamentos do período e isso distorce a média. Sugiro manter a meta e olhar de novo daqui a duas semanas, com mais posts.

> **Conversas por mês (manual).** O painel mostra "não medido" porque ainda não tenho o número de hoje. Quantas conversas vieram este mês? Se quiser, grave como valor de hoje com a data.
