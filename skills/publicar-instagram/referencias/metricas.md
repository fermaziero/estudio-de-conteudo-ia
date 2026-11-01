# Métricas: o que o `metricas.py` coleta

Conferido na documentação oficial da Meta em **2026-10-28** (API do Instagram com login do Instagram, `graph.instagram.com`, `v26.0`). Os nomes de métricas mudam: confira de novo antes de acrescentar uma coluna.

## Como funciona

`python -X utf8 skills/publicar-instagram/scripts/metricas.py coletar --marca <marca> [--dias 90] [--limite 200] [--simular]`

1. Lê o perfil (`GET /me`): seguidores, seguindo e quantidade de publicações.
2. Lista as mídias dos últimos `--dias` dias (`GET /<IG_ID>/media`, 25 por página, pela mais nova).
3. Para cada mídia, lê os insights (`GET /<MEDIA_ID>/insights?metric=...`).
4. **Acrescenta** linhas em `marcas/<marca>/metricas/perfil.csv` e `marcas/<marca>/metricas/posts.csv`. Nada se apaga: cada coleta é uma fotografia, e a série de fotografias mostra o crescimento.

Com `--simular`, lê tudo na Meta e não grava arquivo.

**CSV que já existe.** A coleta aceita o que o contrato permite e o que o Excel faz, sem perder dados: colunas extras no fim (ficam, com valor vazio nas linhas novas), nomes de coluna com maiúsculas, BOM no começo, separador `;` (Excel em português) e arquivo sem a quebra de linha final. Quando precisa reescrever o arquivo (por exemplo, trocar `;` por vírgula ou acrescentar uma coluna que faltava), a versão anterior fica em `metricas/_antes-formato-csv-AAAA-MM-DD/` e todas as linhas são mantidas. Só se faltarem as colunas essenciais (`coletado_em` e `media_id` em `posts.csv`; `coletado_em` e `seguidores` em `perfil.csv`) o arquivo é tratado como outro e vai inteiro para `_antes-cabecalho-AAAA-MM-DD/`, começando um novo.

A rotina (`rotina.py`) roda isto a cada 4 horas. Cada coleta usa cerca de `N + 3` chamadas (N = mídias). Para 60 mídias são ~63 chamadas, por volta de 380 por dia.

## Colunas

### `perfil.csv`

`coletado_em, seguidores, seguindo, publicacoes`

| Coluna | Campo da Meta (`GET /me`) |
|---|---|
| `coletado_em` | hora da coleta, ISO 8601 com fuso (`2026-11-05T07:00:00-03:00`) |
| `seguidores` | `followers_count` |
| `seguindo` | `follows_count` |
| `publicacoes` | `media_count` |

Colunas extras de insights da conta (alcance diário, visitas ao perfil etc.) **não são coletadas nesta versão**. Se forem acrescentadas, entram depois destas quatro e entram aqui documentadas. Quem lê os CSVs ignora colunas desconhecidas.

### `posts.csv`

`coletado_em, media_id, post_id, publicado_em, tipo, curtidas, comentarios, alcance, salvamentos, compartilhamentos, visualizacoes, interacoes, permalink`

| Coluna | De onde vem | Observações |
|---|---|---|
| `coletado_em` | hora da coleta | ISO 8601 com fuso |
| `media_id` | `id` da mídia | o mesmo `media_id` do `publicados.csv` |
| `post_id` | ligação pelo `media_id` com `publicacao/publicados.csv` | **vazio** para posts que não saíram deste projeto |
| `publicado_em` | `timestamp` da mídia | convertido para o fuso do computador |
| `tipo` | `media_type` e `media_product_type` | no vocabulário do campo `formato` dos posts: `carrossel` (`CAROUSEL_ALBUM`), `post_unico` (`IMAGE`), `reel` (`REELS`) ou `video` (`VIDEO` que não é reel) |
| `curtidas` | `like_count` | vazio se o dono esconde as curtidas |
| `comentarios` | `comments_count` | |
| `alcance` | insight `reach` | contas únicas que viram a mídia (estimado) |
| `salvamentos` | insight `saved` | |
| `compartilhamentos` | insight `shares` | |
| `visualizacoes` | insight `views` | vezes que a mídia foi reproduzida ou exibida no Instagram |
| `interacoes` | insight `total_interactions` | curtidas, salvamentos, comentários e compartilhamentos, menos os desfeitos |
| `permalink` | `permalink` | endereço do post |

**Valor indisponível fica vazio, nunca zero.** Zero só aparece quando a Meta devolve zero.

## Regras da Meta que explicam os vazios

- Sem dado, a API devolve **conjunto vazio em vez de 0**. O script grava vazio.
- Os dados podem **atrasar até 48 horas**: post novo tem insights vazios no começo.
- Insights de mídia que está **dentro de um carrossel** não existem; consulta-se o carrossel (álbum) inteiro, que é o que o script faz.
- Uma métrica que a mídia não aceita derruba o pedido inteiro com erro 100. O script então pede as métricas **uma a uma** e fica com as que vierem.
- Os dados de métricas ficam guardados por até 2 anos.
- `views` e `total_interactions` estão marcadas pela Meta como "em desenvolvimento": podem mudar.
- `impressions` foi descontinuada para mídia criada depois de 2024-07-02, e a Meta apresenta `views` como a substituta. `plays`, `video_views`, `clips_replays_count` e `ig_reels_aggregated_all_plays_count` não constam da lista atual de métricas de mídia. O script não pede nenhuma delas.
- Métricas só do Facebook Login (`total_likes`, `total_comments`, `total_views`) não existem neste login.
- Permissão: `instagram_business_manage_insights`. Sem ela, os insights ficam vazios, o resto da coleta segue e o script avisa.
- Excesso de chamadas (códigos 4, 17, 32, 613, 80002): o script **para**, grava o que já leu (as mídias que sobraram ficam com métricas vazias nesta coleta) e sai com código 3. A próxima coleta tenta de novo.
- O orçamento de chamadas da Meta depende das impressões da conta (4800 por impressão em 24 h). Conta nova, com quase nenhuma impressão, pode ter orçamento muito pequeno.

## Como ler a série

- Para o número "de agora" de um post, use a linha com o `coletado_em` mais recente daquele `media_id`.
- Para crescimento, compare linhas do mesmo `media_id` em datas diferentes.
- Ignore linhas de coleta anteriores à `publicado_em` do post.
- Um post com `post_id` vazio foi publicado fora do projeto: serve de comparação, mas não tem pilar nem etapa do funil.

## Fontes (consultadas em 2026-10-28)

- Instagram Media Insights (métricas, mídias suportadas, vazios, atraso, retenção): https://developers.facebook.com/documentation/instagram-platform/reference/instagram-media/insights
- Instagram Account Insights (métricas da conta, que esta versão não usa): https://developers.facebook.com/documentation/instagram-platform/api-reference/instagram-user/insights
- Campos de `GET /me` (`followers_count`, `follows_count`, `media_count`): https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/get-started
- Limites de chamadas: https://developers.facebook.com/docs/graph-api/overview/rate-limiting
