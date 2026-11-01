# Erros comuns e o que fazer

Regra geral: **leia a mensagem inteira, não tente de novo em sequência e não contorne uma recusa.** Toda recusa do script existe para proteger a pessoa de publicar algo errado, duplicado ou sem ok. O código de saída diz a gravidade: `0` ok, `1` recusa ou erro (nada foi publicado, salvo aviso), `3` sem resposta clara (o post pode ter ido ao ar).

## Recusas do script (nada foi feito)

| Mensagem | Causa | O que fazer |
|---|---|---|
| `o post não tem aprovação registrada` | falta o `aprovar` | `simular`, mostre à pessoa, peça "pode publicar `<id>`" e rode `aprovar` |
| `` aprovação sem assinatura válida: rode `aprovar` de novo; ele abre a janela para você confirmar. Motivo: ... `` | o ok não foi gravado pelo `aprovar` neste computador: aprovação escrita ou mexida à mão, assinatura de outra versão ou de outro post, ou a chave de aprovação não existe aqui (computador novo, arquivo apagado, outra pasta em `ESTUDIO_CONFIG`) | não conserte o arquivo nem procure a chave: `simular`, mostre à pessoa e rode `aprovar` de novo; a janela abre e ela confirma. Com a chave perdida, todas as aprovações antigas perdem a validade e ela aprova de novo (posts já publicados não mudam). Explicação: `aprovacao-e-hash.md` |
| `a chave de aprovação deste computador está com defeito` / `não consegui ler a chave de aprovação` | arquivo cortado ou alterado, ou em uso por outro programa, ou sem permissão | em uso ou sem permissão: feche o programa que o usa e rode de novo. Com defeito: o próximo `aprovar` guarda o arquivo de lado e cria outra chave (as aprovações antigas perdem a validade) |
| `esta ação precisa da confirmação de uma pessoa ... rode este comando você mesma, num terminal` | não há janela nem terminal interativo para a pessoa confirmar | mostre o comando completo e peça que ela o rode no terminal dela; a janela abre no computador dela |
| `a pessoa não confirmou (cancelou ou fechou a janela)` | ela clicou em Cancelar, fechou a janela ou passaram 5 minutos | nada foi gravado; se ela quer aprovar, rode de novo e peça que clique em Aprovar |
| `o post mudou enquanto a janela estava aberta` | alguém editou o post ou as artes durante a confirmação | rode `simular`, mostre a nova versão e peça a confirmação de novo |
| `o campo id do JSON (...) é diferente do nome do arquivo` | o `id` dentro do JSON não é o nome do arquivo (ou tem barras e pontos) | por segurança nada é lido nem apagado; corrija o `id` para o nome do arquivo |
| `o arquivo X.json não é um JSON válido ... (linha N, coluna M)` | vírgula sobrando ou faltando, aspas ou chaves | abra o arquivo no ponto indicado, corrija e rode de novo |
| `falta a 'arroba' em marcas/<marca>/visual.json` | a marca não tem a conta registrada | preencha `"arroba": "@seuperfil"` no `visual.json` (o valor de exemplo `@perfil` não vale) |
| `AINDA NÃO DÁ PARA APROVAR: o status é 'texto_aprovado'` | as artes ainda não foram marcadas como prontas | termine a skill `gerar-artes` (status `arte_pronta`) e rode `simular` de novo |
| `o conteúdo mudou depois da aprovação ... O post voltou para 'arte_pronta'` | texto ou arte mudou depois do ok | `simular` de novo, mostre a nova versão, peça novo ok |
| `só se publica post 'aprovado' (o status é 'erro')` | houve falha antes | descubra o que houve (`historico` do post), corrija e peça novo ok com `aprovar` |
| `pendência em 'confirmar': ...` | o post tem item "NÃO VERIFICADO" | resolva com a pessoa (confirme a informação ou tire a afirmação), edite o post e volte ao `simular` |
| `Reels não são publicados nesta versão` | `formato: reel` | avise a pessoa; reel é só roteiro aqui |
| `falta a arte NN.png` / `as artes têm tamanhos diferentes` / `não é a proporção 4:5` | artes incompletas ou misturadas | rode a skill `gerar-artes` de novo |
| `carrossel precisa ter de 2 a 10 slides` / `post_unico precisa ter exatamente 1 slide` | formato e quantidade não combinam | ajuste o formato ou os slides |
| `legenda com N caracteres (máximo 2200, contando as hashtags)` | legenda longa | encurte (as hashtags da lista também contam) |
| `a legenda tem 'Fonte:'` | regra do projeto: fonte fica só no JSON | tire a fonte da legenda; ela já está em `fontes` |
| `hashtag inválida` | hashtag com espaço, hífen etc. | use só letras, números e `_` |
| `o validador de posts (criar-conteudo) apontou erros` | o JSON do post não segue o contrato | rode o validador, corrija os campos |
| `o campo id ... é diferente do nome do arquivo` | arquivo renomeado | volte o nome ou o id |
| `este post já foi publicado em ...` | já existe em `publicados.csv` ou `publicacao` | **não use `--de-novo` por conta própria.** Só se a pessoa pedir outra publicação do mesmo post |
| `há uma publicação deste post sem resposta clara` | existe trava em `publicacao/_em_andamento/` | rode `conferir` (veja abaixo) |
| `o token é da conta @x, mas esta marca usa @y` | token de outra marca | gere o token logado na conta certa e rode `configurar` |
| `o token é de outra conta do Instagram (o IG_USER_ID gravado é diferente)` | trocaram o token por o de outra conta | `configurar` de novo |
| `a cota de publicação da Meta acabou (N de M ...)` | limite de publicações em 24 h | espere a janela de 24 h passar |
| `o Instagram desta marca ainda não está configurado` / `o token do Instagram está vazio` | falta configurar | `credenciais.py configurar` e `docs/instagram-api.md` |
| `armazenamento com problema: ...` / `o armazenamento de imagens não está configurado` | seis campos do `armazenamento.env` faltando ou inválidos | `credenciais.py configurar` e `docs/armazenamento-imagens.md` |
| `não consegui ler publicacao/publicados.csv` | o CSV está aberto em outro programa (Excel) | feche e rode de novo |
| `falta a biblioteca Pillow` | dependência não instalada | `python -m pip install -r requirements.txt` |
| `nenhuma marca encontrada além de 'exemplo'` / `há mais de uma marca` | marca não escolhida | passe `--marca <slug>` |

## Falhas na hora de publicar (o post volta com status `erro`)

O script apaga as imagens enviadas, solta a trava e grava a mensagem no `historico`. Depois de corrigir a causa, peça um novo ok (`aprovar`) e publique de novo.

| Mensagem | Causa | O que fazer |
|---|---|---|
| `a URL pública da arte NN não abre direito (... facebookexternalhit: HTTP 403 ...)` | proteção do domínio bloqueia o robô da Meta | `docs/armazenamento-imagens.md`, seção "Se a URL não abrir" |
| `o armazenamento respondeu 403 ... a assinatura não confere` | chave secreta, região ou relógio errados | refaça a chave; confira o relógio do computador |
| `... a chave não tem permissão neste bucket` | chave sem "Object Read & Write" naquele bucket | crie outra chave |
| `A Meta recusou o contêiner: ...` | veja a tabela de códigos abaixo | siga a dica da mensagem |
| `O contêiner N terminou em ERROR: ...` | a Meta não conseguiu processar a imagem | confira a URL, o tamanho e o formato; tente de novo depois de corrigir |
| `O contêiner N continuou em 'IN_PROGRESS' depois de 300 s` | a Meta demorou | tente de novo mais tarde |
| `A Meta recusou a publicação: ...` | recusa definitiva | leia a dica; nada foi ao ar |

### Códigos da Meta (documentação de erros do Instagram, conferida em 2026-10-28)

| Código / subcódigo | Significado | Ação |
|---|---|---|
| 190 | token vencido ou inválido | gerar outro e `configurar` |
| 10, 200 a 299 | falta permissão | adicionar no painel e gerar o token de novo |
| 4, 17, 32, 613, 80002 | excesso de chamadas | esperar e tentar de novo |
| 368 | bloqueio temporário por política | esperar |
| 9 / 2207042 | limite diário de publicação | tentar amanhã |
| -1 / 2207001, -1 / 2207032 | erro do servidor / falha ao criar o contêiner | tentar de novo |
| -2 / 2207003 | a Meta demorou para baixar a imagem | tentar de novo; confira a URL |
| -2 / 2207020, 24 / 2207008 | contêiner expirado ou inexistente | tentar de novo (cada tentativa cria contêineres novos) |
| 24 / 2207006 | mídia não encontrada | conferir token e permissões |
| 25 / 2207050 | conta inativa, restrita ou em verificação | resolver no app do Instagram |
| 100 / 2207028 | quantidade de itens do carrossel inválida | usar de 2 a 10 |
| 100 / 2207040 | menções demais (máx. 20) | reduzir |
| 9004 / 2207052 | a Meta não conseguiu baixar a imagem da URL | URL pública, sem login e sem bloqueio de robô |
| 9007 / 2207027 | mídia ainda não está pronta | esperar `FINISHED` |
| 36000 / 2207004 | imagem acima de 8 MB | o script já reduz; confira a arte |
| 36001 / 2207005 | formato de imagem não aceito | só JPEG |
| 36003 / 2207009 | proporção fora de 4:5 a 1,91:1 | corrigir a arte |
| 36004 / 2207010 | legenda longa (2.200 caracteres, 30 hashtags, 20 menções) | encurtar |

## "SEM RESPOSTA CLARA" (código 3): o post pode ter ido ao ar

Acontece quando a conexão cai ou a Meta demora na hora de publicar. O script **trava** o post (nada é publicado de novo) e deixa as imagens no bucket.

1. **Não publique de novo.** Não mexa em `publicacao/_em_andamento/`.
2. Rode `publicar.py conferir --post <id>`. Ele consulta a Meta:
   - se achou o post: grava o link em `publicados.csv`, marca `publicado`, apaga as imagens e libera a trava;
   - se ficou provado que **não** foi ao ar: volta o post para `aprovado` (peça o ok da pessoa antes de tentar de novo);
   - se a tentativa tem menos de 2 minutos: espere e rode de novo;
   - se não dá para provar (contêiner `ERROR` ou `EXPIRED`): peça à pessoa para **olhar o feed do Instagram**. Se o post não está lá, rode `conferir --confirmo-que-nao-foi-ao-ar`. Se está, peça o link para registrar.
3. Só a pessoa diz que "não está no feed". O agente nunca usa `--confirmo-que-nao-foi-ao-ar` sem isso.

## Publicou duas vezes por acidente

O script nunca apaga posts. A pessoa apaga o repetido no app do Instagram. Depois, registre o motivo em `feedback.md` e, se foi falha da skill, avise quem mantém o projeto.

## Rotina e agendamento

| Sintoma | Causa | O que fazer |
|---|---|---|
| O post agendado não saiu | rotina não instalada, computador desligado ou sessão fechada | `rotina.py mostrar`; veja `publicacao/logs/rotina-AAAA-MM.log` |
| `perdeu a janela de 2 h ... NÃO publicado` | o computador ficou desligado além da janela | peça novo ok e novo horário |
| `Outra execução está em andamento` | duas execuções ao mesmo tempo | normal; a segunda sai sozinha. Se travar por mais de 90 min, a trava vence sozinha |
| `deixou de estar agendado ... pulei` | a pessoa rodou `desagendar` (ou reagendou) enquanto a rotina começava | normal: a rotina respeita o cancelamento |
| `o programa 'crontab' não existe neste computador` | Linux mínimo ou WSL sem o cron | instale o cron (`sudo apt install cron`) e deixe o serviço rodando, ou instale a rotina no Windows; veja `rotina.md` |
| `token renovado automaticamente` no log | o token estava a 10 dias ou menos de vencer | nada a fazer |
| `ATENÇÃO: ... a renovação automática falhou` | token vencido ou sem permissão | gerar outro token (`docs/instagram-api.md`) |
| `o arquivo do token não tem a data de validade (IG_TOKEN_VALIDO_ATE vazia)` | o arquivo foi preenchido à mão sem a data | `credenciais.py renovar` (token com mais de 24 h) descobre e grava a data; a rotina também tenta sozinha |

## Fontes (consultadas em 2026-10-28)

- Códigos do Instagram (2207xxx, 9004, 9007, 360xx): https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/error-codes
- Códigos gerais (4, 17, 190, 200 a 299, 368): https://developers.facebook.com/docs/graph-api/guides/error-handling
- Códigos de excesso de chamadas (80002, 613): https://developers.facebook.com/docs/graph-api/overview/rate-limiting
