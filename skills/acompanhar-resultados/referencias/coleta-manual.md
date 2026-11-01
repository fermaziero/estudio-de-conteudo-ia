# Coleta manual das métricas

Use quando a coleta automática não está disponível (falta conectar o Instagram) ou quando a pessoa prefere informar os números. O painel funciona igual: ele só precisa dos dois arquivos CSV abaixo. Os exemplos são fictícios.

## O que preencher

Os modelos com só o cabeçalho estão em `modelos/perfil.csv` e `modelos/posts.csv`. Se o arquivo ainda não existir em `marcas/<marca>/metricas/`, copie o modelo para lá. Se já existir, **acrescente linhas no fim**: nunca altere linhas antigas, porque elas formam a história dos números.

**`perfil.csv`: uma linha por coleta**

| Coluna | O que colocar |
|---|---|
| `coletado_em` | Data da coleta, `AAAA-MM-DD` (pode incluir a hora). |
| `seguidores` | Total de seguidores naquele dia. |
| `seguindo` | Total de perfis que a conta segue (pode ficar vazio). |
| `publicacoes` | Total de publicações do perfil (pode ficar vazio). |

**`posts.csv`: uma linha por post em cada coleta**

| Coluna | O que colocar |
|---|---|
| `coletado_em` | A mesma data da linha do `perfil.csv`. |
| `media_id` | O identificador do post. Se não tiver, use o endereço do post (`permalink`) ou invente um nome curto e único, como `manual-01`. |
| `post_id` | Só se o post saiu deste projeto: o `id` que aparece em `publicacao/publicados.csv`. Deixe vazio para posts de fora. |
| `publicado_em` | Data em que foi ao ar, `AAAA-MM-DD` (com a hora, se souber). Sem ela o post não entra nas médias. |
| `tipo` | `carrossel`, `post_unico` ou `reel`. |
| `curtidas`, `comentarios`, `alcance`, `salvamentos`, `compartilhamentos`, `visualizacoes`, `interacoes` | Os números que a tela de estatísticas do post mostra. |
| `permalink` | Endereço do post (opcional, mas o painel usa para criar o link). |

**Regra de ouro: o que a tela não mostra fica vazio.** Vazio é "não medido". Nunca escreva 0 só para preencher, porque zero é um número de verdade e distorce as médias.

## Onde achar os números

Nas estatísticas (Insights) do Instagram, o perfil mostra o total de seguidores e cada publicação mostra seus números. Os nomes e a posição das telas mudam com o tempo: use o que a sua tela mostra e, se um número não aparecer, deixe vazio.

Se a pessoa mandar prints, transcreva só o que está visível. Pergunte sobre qualquer número ilegível ou que você não tenha certeza. Nunca complete por palpite.

## Quando coletar

Uma vez por semana, no mesmo dia e mais ou menos na mesma hora, de preferência. Em cada coleta, anote os posts das últimas 8 semanas. Posts com menos de 48 horas podem entrar, mas o painel os deixa fora das médias.

## Exemplo (fictício)

`perfil.csv`:

```
coletado_em,seguidores,seguindo,publicacoes
2026-10-20,857,317,71
2026-10-27,872,318,75
```

`posts.csv` (duas linhas da coleta de 27/10; o terceiro post não mostrou salvamentos, então a célula fica vazia):

```
coletado_em,media_id,post_id,publicado_em,tipo,curtidas,comentarios,alcance,salvamentos,compartilhamentos,visualizacoes,interacoes,permalink
2026-10-27,manual-11,,2026-10-20,carrossel,53,9,760,28,15,1010,105,
2026-10-27,manual-12,,2026-10-23,post_unico,22,14,430,5,3,560,44,
2026-10-27,manual-13,,2026-10-16,reel,41,3,1010,,18,1580,,
```

## Conferir depois de preencher

Rode `python -X utf8 skills/acompanhar-resultados/scripts/montar_painel.py --marca <marca> --simular` e leia os "avisos sobre os dados". Ele avisa de data inválida, número negativo, coluna ausente e linha ignorada, sem gravar nada. Corrija o CSV e rode de novo.

Se o arquivo for aberto e salvo pelo Excel, ele pode virar "ponto e vírgula" ou Windows-1252. O painel entende os dois e avisa, mas o melhor é salvar como "CSV UTF-8".
