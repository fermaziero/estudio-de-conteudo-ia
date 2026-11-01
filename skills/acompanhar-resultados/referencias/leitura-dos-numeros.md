# Leitura dos números

Leia este arquivo antes de escrever a leitura (Passo 3 do `SKILL.md`). Ele diz o que cada número significa, como compará-los e como falar deles sem enganar a pessoa. Os exemplos com números são fictícios.

## 1. Os quatro números que não se misturam

| Número | O que é | Onde está | Erro comum |
|---|---|---|---|
| **Visualizações** | Quantas vezes o conteúdo foi visto. A mesma pessoa pode contar várias vezes. | `posts.csv`, coluna `visualizacoes` | Dizer "mil pessoas viram" quando são mil visualizações. |
| **Alcance** | Quantas contas diferentes viram o conteúdo. É o número mais próximo de "quantas pessoas". | `posts.csv`, coluna `alcance` | Somar o alcance de posts diferentes e chamar de "pessoas": quem viu os dois posts conta duas vezes. |
| **Seguidores ganhos** | Quem passou a seguir no período. O projeto não mede por post. | Só existe se a coleta trouxer colunas extras de ganhos e perdas no `perfil.csv`. | Atribuir um post ao salto de seguidores entre duas coletas. |
| **Crescimento líquido** | Quem entrou menos quem saiu: a diferença entre dois totais de seguidores. | `perfil.csv`, coluna `seguidores` | Dizer "ganhei 40 seguidores" quando o saldo foi +40 (pode ter entrado 60 e saído 20). |

Dois totais de seguidores mostram o saldo, nunca a causa. Um salto logo depois de um post pode vir de outro lugar (indicação, anúncio, parceria).

## 2. Compare por proporção

Número bruto favorece o post maior ou mais antigo. Para comparar, use taxas:

- **Taxa sobre o alcance** = quantidade ÷ alcance. Exemplo fictício: o post A teve 1.000 de alcance e 50 salvamentos (5%); o post B teve 200 de alcance e 20 salvamentos (10%). O A tem mais salvamentos, o B salva o dobro por pessoa alcançada.
- **Interação de valor** = (salvamentos + compartilhamentos + comentários) ÷ alcance. Curtida fica de fora porque é o gesto mais fraco. É uma definição deste painel, não do Instagram: diga isso se a pessoa perguntar.
- **Alcance ÷ seguidores** (alcance relativo): quanto da base cada post alcança. Acima de 100% quer dizer que o post chegou a mais contas do que o número de seguidores.
- **Views ÷ seguidores** (referências): quantas visualizações um post típico faz para cada seguidor.

O painel calcula a taxa de um grupo somando tudo e dividindo uma vez (soma dos salvamentos ÷ soma dos alcances). Assim um post pequeno com taxa enorme não puxa o grupo.

## 3. Maturidade e janelas

- **Post maduro:** a última coleta foi feita pelo menos 48 horas depois da publicação. Antes disso os números ainda estão subindo e distorcem a média. O painel mostra quantos posts ficaram de fora por isso.
- **Para decisões importantes**, espere 7 dias depois de publicar. É uma regra prática do projeto, não uma regra do Instagram.
- **Janelas do painel:** os cartões de resumo e as metas olham os últimos 28 dias e os 28 dias anteriores. As tabelas por pilar, formato e etapa olham as últimas 8 semanas.
- **Idade dos dados:** acima de 7 dias desde a última coleta, o painel avisa. Não decida com número velho.

## 4. Tamanho da amostra

| Posts maduros no grupo | Como falar |
|---|---|
| 0 | "Ainda não dá para medir." Não afirme nada. |
| 1 ou 2 | "Só uma pista." Não compare com outros grupos. |
| 3 ou 4 | "Amostra pequena." Pode citar, com o n, e sem concluir. |
| 5 ou mais | "Base razoável." Ainda não é prova: é o mínimo para falar em tendência. |

Mais três cuidados:

- **Post dominante.** Se um único post concentra mais da metade do alcance (ou do total) do grupo, a média engana. Diga isso, cite a mediana (o valor do meio) e descreva o grupo sem esse post.
- **Três repetições.** Um pico é uma pista. Uma abordagem só vira regra depois de aparecer em pelo menos 3 ocasiões comparáveis (mesmo formato, mesma fase, sem campanha no meio). Isso é uma regra prática, não significância estatística.
- **Mostre a dispersão.** Ao lado da média, diga a mediana e quantos posts tiveram zero ou ficaram abaixo do esperado. Média sozinha esconde o que aconteceu com cada post.

## 5. O que o painel não sabe (pergunte no check-in)

- **Anúncio pago.** Alcance pago e orgânico vêm misturados. Resultado com anúncio não prova crescimento orgânico. Se houve impulsionamento, deixe o post fora das conclusões ou marque a leitura.
- **Parceria ou colaboração** (a audiência do parceiro entra no alcance).
- **Eventos:** feriado, notícia, lançamento, viagem, pausa na publicação.
- **Conversas, cliques e vendas.** O projeto não mede. Só a pessoa informa.
- **Quem é o público.** Alcance não diz se quem viu é o cliente que a marca quer.

## 6. Perguntas de sanidade antes de afirmar

1. Quantos posts sustentam isso (n)?
2. Um post só explica a diferença?
3. Os posts são comparáveis (formato, idade, fase, campanha)?
4. Existe outra explicação (evento, anúncio, parceria)?
5. O que me faria mudar de ideia?

Se a resposta à 1 for "poucos", à 2 for "sim" ou à 3 for "não", escreva como hipótese ou deixe de fora.

## 7. Como escrever cada parte da leitura

Frases-modelo (números fictícios):

- **Base:** "Esta leitura usa 12 posts maduros de 8 semanas; 2 posts recentes ficaram de fora. Dá para ver a tendência de seguidores, mas só pistas sobre pilar e etapa."
- **Funcionou:** "Os carrosséis educativos tiveram 3,3% de salvamentos sobre o alcance, 1,3 vez a média da conta (n=5)."
- **Não funcionou:** "Os posts únicos de bastidores ficaram em 0,6 vez a média da conta em salvamentos (n=3, amostra pequena)."
- **Hipótese:** "Pode ser que o formato lista seja o que a pessoa guarda. O que sustenta: 2 dos 3 posts mais salvos eram lista. Para testar: publicar mais 3 listas e 3 textos corridos no mesmo pilar. Faltam 3 repetições."
- **Recomendação:** "Repetir o carrossel de passo a passo no pilar educativo, com outro assunto. Confiança média (n=5). Saberemos que funcionou se a taxa de salvamentos ficar acima da média da conta em 3 posts seguidos."

Regras de linguagem:

- Troque o jargão pelo gesto: em vez de "engajamento", escreva "quem guardou, compartilhou ou comentou".
- Um número, uma frase. Sempre com o n.
- "Funcionou" só para o que passou nas perguntas de sanidade. O resto é "pista" ou "hipótese".
- Nunca prometa resultado. Escreva "pode ajudar", "vale testar".

## 8. Quando a pergunta depende de como o Instagram funciona

Se a explicação para um resultado exigir saber como o Instagram distribui conteúdo, ou o que um recurso novo faz, pesquise e cite fonte e data, ou diga que não sabe. Prefira fonte oficial da Meta ou do Instagram. Relatos de criadores e estudos de ferramentas de gestão servem para levantar hipóteses: são observacionais e vendem produto. Não transforme média de mercado em meta da pessoa.
