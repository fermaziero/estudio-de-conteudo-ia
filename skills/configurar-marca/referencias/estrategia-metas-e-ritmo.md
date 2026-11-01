# Estratégia, metas e ritmo

Leia este arquivo no último bloco da entrevista e sempre que a pessoa quiser mudar objetivo, pilares, ritmo ou metas. Ele ensina a montar o `estrategia.json` com a pessoa. Quem decide é ela: você propõe, ela aprova. Os exemplos são fictícios.

## Ordem de trabalho

1. Objetivo.
2. Pilares de conteúdo e pesos.
3. Ritmo.
4. Metas.
5. Funil.
6. Movimentos dos próximos 30 dias.
7. Resumo, correções e aprovação.

O arquivo nasce com `status: "rascunho"`. Só vira `"vigente"` depois que a pessoa diz que aprova.

## Perguntas do primeiro check-in

Um check-in é uma conversa curta para atualizar o "momento" da pessoa. Se ela estiver sem tempo, faça só estas cinco perguntas, em duas rodadas (no máximo 3 por vez). Pergunta em branco não trava nada: marque o item como "não definido".

| Pergunta | Onde a resposta entra |
|---|---|
| 1. O que aconteceu de importante nos últimos meses (lançamento, evento, conquista)? | contexto para o objetivo e para os movimentos; só vira fato em `marca.md` se ela autorizar |
| 2. O que vem nas próximas semanas (datas, abertura de vendas, palestra, promoção)? | `movimentos`, com data em `ate` |
| 3. Qual pilar deve pesar mais agora e por quê? | `pilares[].peso` |
| 4. O que evitar neste momento? | `regras.md`, em "Temas proibidos ou só sob pedido", com a data até quando vale |
| 5. Quanto tempo por semana existe para produzir conteúdo? | `ritmo` |

Tudo o que a pessoa não souber fica como lacuna: liste ao final, começando pelo que mais afeta o conteúdo.

## 1. Objetivo

Uma frase com o que o perfil precisa gerar nos próximos meses: verbo, resultado e prazo.

| Bom | Fraco |
|---|---|
| "Receber 10 conversas por mês de donos de loja pequena, em 3 meses." (fictício) | "Crescer no Instagram." |

Se vier fraco, pergunte: "Se o perfil der muito certo daqui a 3 meses, o que terá acontecido na sua semana?".

## 2. Pilares

Pilar é um grande assunto fixo do perfil. Servem para variar as pautas e medir o que funciona.

- De 3 a 5 pilares. Cada um com `id`, `nome`, `descricao` e `peso`. O `id` é um slug: só minúsculas, números e hífen, sem sublinhado nem espaço (`bastidores-equipe`, não `bastidores_equipe`).
- Os pesos somam 100.
- Parta dos temas (bloco 6) e da oferta (bloco 2). Garanta pelo menos um pilar que atrai gente nova (conteúdo útil), um que cria relação (bastidores, histórias, opinião) e um que apresenta o que a pessoa vende.
- Peso é a fatia dos posts. Proponha uma divisão inicial (por exemplo 50, 20 e 30), explique que é um ponto de partida e deixe a pessoa mexer.
- A descrição diz do que o pilar fala e por que importa para o público, em frase completa.

| Bom | Fraco |
|---|---|
| `educativo`: "Explica impostos do dia a dia em linguagem simples, com exemplos de loja pequena." | `dicas`: "Dicas." |

Os `id` são usados nos posts (campo `pilar`). Depois que existirem posts, não renomeie um pilar sem avisar a pessoa e conferir os posts que o usam.

## 3. Ritmo

- `posts_por_semana`: o que a pessoa consegue sustentar, não o que ela gostaria. Pergunte o tempo real por semana. É melhor começar com menos e subir. É um número maior que zero e aceita decimal: `2.5` vale para cinco posts a cada duas semanas.
- `formatos`: quantos de cada por semana, em números inteiros. `carrossel` e `post_unico` viram artes; `reel` é só roteiro, não é publicado automaticamente. A soma dos formatos deve ser igual a `posts_por_semana`; com um ritmo decimal ela não bate e o validador só avisa.

## 4. Metas

Cada meta tem `id`, `descricao`, `indicador`, `base`, `alvo` e `prazo` (AAAA-MM-DD). O `id` é um slug, como o dos pilares (`novos-seguidores`, sem sublinhado).

| `indicador` | O que mede | De onde vem |
|---|---|---|
| `seguidores` | seguidores do perfil | coleta de métricas |
| `posts_por_semana` | frequência de publicação | histórico de publicações |
| `alcance_medio` | alcance médio por post | coleta de métricas |
| `salvamentos_medio` | salvamentos médios por post | coleta de métricas |
| `comentarios_medio` | comentários médios por post | coleta de métricas |
| `compartilhamentos_medio` | compartilhamentos médios por post | coleta de métricas |
| `manual` | qualquer número que a pessoa mede sozinha (conversas, orçamentos, vendas) | a pessoa informa: o valor vai em `atual` e a data da medição em `atual_em` (campos opcionais da meta) |

Regras:
- **A base é medida ou informada pela pessoa.** Para seguidores, ela olha o número no perfil. Nunca estime a base. Se ela não souber, use `manual`, escreva "a medir" na descrição e combine quando ela informa o valor (`atual` e `atual_em`).
- **O alvo é escolha da pessoa.** Para ajudar, proponha três cenários como hipóteses (cauteloso, moderado, ousado) a partir da base dela, e diga que são hipóteses, não previsões. Não cite médias de mercado sem pesquisar; se citar, registre fonte e data.
- **Poucas metas.** De 2 a 4, e pelo menos uma que meça o objetivo (conversas, pedidos), não só vaidade (seguidores).
- **Prazo realista.** Em geral de 60 a 120 dias, com data exata.
- Meta de dado que o projeto não coleta usa `manual`.

## 5. Funil

Três frases curtas, uma por etapa, ligadas às chamadas disponíveis em `marca.md`.

- `atracao`: que conteúdo faz uma pessoa nova parar, salvar e seguir.
- `relacionamento`: o que mantém quem já acompanha por perto (comentar, mandar para alguém).
- `conversao`: qual é o passo para virar cliente (direct, WhatsApp, link na bio).

## 6. Movimentos

De 2 a 4 ações para os próximos 30 dias, cada uma com `o_que`, `indicador` e `ate` (data). Ações concretas, que a pessoa consiga fazer ("responder todo comentário em até 1 dia útil"), e não intenções ("melhorar o engajamento").

## 7. Resumo e aprovação

Mostre um resumo curto, em tabela ou lista, com objetivo, pilares e pesos, ritmo, metas e funil. Pergunte o que a pessoa quer mudar. Quando ela disser que está bom, pergunte: "Posso marcar esta estratégia como vigente?". Só com um sim claro:

1. Guarde a versão anterior (`guardar_versao.py --motivo estrategia-aprovada estrategia.json`).
2. Troque `status` para `"vigente"` e `atualizado_em` para a data de hoje.
3. Rode `validar_marca.py --so estrategia`. Em `vigente`, o validador exige objetivo, pilares, ritmo maior que zero, metas e funil preenchidos.

## Mudar a estratégia depois

- **Só a pessoa muda metas.** Se outra skill (por exemplo `acompanhar-resultados`) sugerir um ajuste, apresente a proposta e espere o ok explícito no chat antes de gravar.
- Em toda mudança: guarde a versão anterior, atualize `atualizado_em`, rode o validador e conte à pessoa o que mudou.
- Mudança grande (objetivo ou pilares): pergunte se ela quer manter o `status` como `vigente` ou voltar para `rascunho` até revisar tudo.
- Se a mudança veio de uma reclamação ou preferência da pessoa, registre também em `feedback.md`.
