# Limites e regras da API do Instagram usados pela skill

Todos os itens foram conferidos na documentação oficial da Meta em **2026-10-28** (API do Instagram com login do Instagram, host `graph.instagram.com`, versão `v26.0`). A coluna "No script" diz onde a regra é aplicada. As páginas citadas ficam em `developers.facebook.com/documentation/instagram-platform/...`. Quando a própria Meta se contradiz, está dito aqui.

Confira de novo antes de afirmar qualquer número a uma pessoa: a Meta muda limites sem aviso.

## Conta, permissões e tokens

| Regra | Valor | Fonte |
|---|---|---|
| Tipo de conta | Profissional: *Business* ou *Creator* (na API, `account_type` vem como `Business` ou `Media_Creator`). Conta pessoal não serve. Não exige Página do Facebook ligada. | Overview; Get started |
| Permissões | `instagram_business_basic` (ler a conta e renovar o token), `instagram_business_content_publish` (publicar), `instagram_business_manage_insights` (métricas) | content_publishing_limit; insights; Migration Guide |
| Acesso padrão (*Standard*) | Basta para app que atende só contas que você possui ou administra e adicionou ao app. Não exige App Review. | Overview |
| Acesso avançado (*Advanced*) | Para contas de terceiros. Exige App Review e verificação da empresa. **Fora do escopo.** | Overview |
| Token gerado no painel do app | Longa duração: **60 dias** | Get started |
| Token do fluxo de login de usuários | 1 hora | Get started; Business Login |
| Renovar | `GET graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=<token>`. O token precisa ter **mais de 24 h**, **não pode ter vencido** e o usuário precisa ter dado `instagram_business_basic`. Gera outro de 60 dias (`expires_in` em segundos). | refresh_access_token |
| Sem renovar | Token que fica 60 dias sem ser renovado vence e não pode mais ser renovado (é preciso gerar de novo). | Business Login |

No script: `credenciais.py renovar` e a renovação automática da rotina (quando faltam 10 dias ou menos).

## Publicação

| Regra | Valor | Fonte |
|---|---|---|
| Fluxo | `POST /<IG_ID>/media` (cria o contêiner) e `POST /<IG_ID>/media_publish` com `creation_id` (publica) | Content Publishing |
| Mídia pública | A mídia precisa estar num servidor **publicamente acessível** na hora; a Meta busca com cURL | Content Publishing |
| Formato da imagem | **Somente JPEG** | Content Publishing; IG User Media |
| Tamanho | até **8 MB** | IG User Media |
| Proporção | entre **4:5 e 1,91:1** | IG User Media |
| Largura | menor que 320 px é ampliada; maior que 1440 px é reduzida | IG User Media |
| Cor | sRGB; outros espaços são convertidos | IG User Media |
| Endereço da imagem | usar só caracteres ASCII (a Meta avisa que outros podem falhar) | IG User Media |
| Carrossel | Itens são contêineres filhos (`is_carousel_item=true`) e o pai usa `media_type=CAROUSEL` e `children`. **Divergência da Meta:** a página do parâmetro diz até 20 itens; a tabela de erros (subcódigo 2207028) manda usar de 2 a 10. O projeto usa **de 2 a 10 slides** (contrato). | IG User Media; Error Codes |
| Corte do carrossel | todas as imagens são cortadas pela proporção da **primeira** (padrão 1:1) | Content Publishing |
| Legenda | até **2.200 caracteres, 30 hashtags e 20 menções (@)**; não vale em itens de carrossel (a legenda vai no pai) | IG User Media |
| Texto alternativo (`alt_text`) | até **1.000 caracteres**; só para imagens (única ou item de carrossel); recurso lançado em 2025-03-24 | IG User Media; Content Publishing |
| Validade do contêiner | **24 horas** | IG User Media; IG Container |
| Contêineres criados | até **400** por conta em 24 h (rolante) | IG User Media |
| Estados do contêiner (`status_code`) | `IN_PROGRESS`, `FINISHED`, `PUBLISHED`, `ERROR` (o campo `status` traz o detalhe), `EXPIRED` | IG Container |
| Quando consultar o estado | a Meta recomenda uma vez por minuto, por no máximo 5 minutos (texto escrito para vídeo). O script consulta imagens em pausas curtas (2, 4, 8, depois 10 s) por até 300 s. | Content Publishing |
| Cota de publicação | **Divergência da Meta:** o guia de publicação diz 100 posts publicados pela API em 24 h (carrossel conta como um) numa seção e 50 noutra; a página do `content_publishing_limit` diz `quota_total` = 50 hoje (`quota_duration` 86400 s). **O script lê o valor real em `GET /<IG_ID>/content_publishing_limit?fields=config,quota_usage`** e não fixa número. | Content Publishing; content_publishing_limit |
| Agendamento | A documentação de publicação consultada **não traz parâmetro de agendamento** para o Instagram. Por isso o agendamento é feito neste computador (`rotina.py`). | Content Publishing |

No script: `analisar()` em `publicar.py` aplica legenda, hashtags, menções, proporção, largura e tamanhos; `converter_para_jpeg()` entrega JPEG sRGB até 1440 px e 8 MB; `_instagram.py` lê a cota e o estado dos contêineres.

## Limites de chamadas e erros

| Regra | Valor | Fonte |
|---|---|---|
| Orçamento de chamadas | chamadas em 24 h = 4800 × número de impressões da conta, por par app e usuário, janela rolante (limite do tipo *Business Use Case*) | Overview; Graph API rate limiting |
| Códigos de excesso | 80002 (Instagram), e também 4, 17, 32 e 613 | Graph API rate limiting; error handling |
| Cabeçalho de uso | `X-Business-Use-Case-Usage` (tipo `instagram`), com `estimated_time_to_regain_access` em minutos | Graph API rate limiting |
| Bloqueio temporário | código 368 | Graph API error handling |
| Token vencido | código 190 | Graph API error handling |
| Falta de permissão | código 10 ou 200 a 299 | Graph API error handling |

No script: `metricas.py` espaça as chamadas (0,5 s) e para no primeiro erro de excesso; `_instagram.tipo_erro()` classifica os códigos.

## Versão da API

- `v26.0` era a última versão listada na documentação em 2026-10-28. Os scripts a usam (`VERSAO_API` em `_instagram.py`).
- A Meta recomenda sempre informar a versão. Chamada sem versão usa a definida no painel do app.
- Cada versão é mantida por pelo menos 2 anos depois do lançamento e, quando expira, as chamadas passam para a próxima versão disponível. Revise `VERSAO_API` de tempos em tempos.
- O Instagram com login do Instagram usa o host `graph.instagram.com`. Seguir um guia de Facebook Login (host `graph.facebook.com`) com este token falha.

## Robô que baixa a imagem

A documentação de publicação diz só que a Meta busca a mídia com cURL, sem dizer o identificador (*user agent*). A página oficial de robôs da Meta lista `facebookexternalhit/1.1` como o robô que busca conteúdo compartilhado no Facebook, no Instagram e no Messenger. O script testa a URL pública com um identificador de navegador e com `facebookexternalhit/1.1`; é uma aproximação, não uma garantia. Fonte: Web Crawlers (`developers.facebook.com/docs/sharing/webmasters/web-crawlers`).

## O que a skill não faz (e por quê)

- **Reels e Stories**: a API suporta, mas esta versão não publica (precisam de vídeo, que o projeto não gera). Posts com `formato: reel` são recusados.
- **Marcar pessoas, local, colaboradores, produtos**: não suportado aqui.
- **Apagar um post publicado**: a skill nunca apaga posts. Para remover, a pessoa apaga no app do Instagram.
