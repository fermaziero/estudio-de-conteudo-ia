# Comandos da skill

Rode sempre da raiz do projeto. No macOS e no Linux, troque `python` por `python3`. Todo comando tem `--help`. Os quatro scripts (`publicar.py`, `credenciais.py`, `metricas.py`, `rotina.py`) aceitam `--raiz <pasta do projeto>`, **só para testes**, como as outras skills; sem ela, vale a pasta onde a skill está instalada. `--marca <slug>` pode ser omitido quando só existe uma marca além de `exemplo`; com várias, o script para e lista as opções. Em `--post`, vale o id do post ou o caminho do `.json`.

```
python -X utf8 skills/publicar-instagram/scripts/<script>.py <comando> [opções]
```

Código de saída: `0` ok; `1` recusa ou erro (nada foi publicado, salvo aviso); `2` uso incorreto; `3` sem resposta clara da Meta ou coleta parcial.

Tudo o que os scripts imprimem passa por um filtro que mascara tokens, chaves e assinaturas. Mesmo assim, nunca cole saída de comando com dado suspeito no chat.

## `credenciais.py`: token e armazenamento

| Comando | O que faz | Arquivos |
|---|---|---|
| `configurar [--marca M] [--modelo]` | abre uma janela local com campos mascarados (o comando fica esperando até a pessoa salvar). `--modelo` só cria os arquivos vazios para preencher num editor. Campo secreto em branco mantém o valor atual. | grava `~/.config/estudio-de-conteudo/<marca>/instagram.env` e `armazenamento.env` (permissão só do dono; `ESTUDIO_CONFIG` troca a pasta base) |
| `verificar [--marca M] [--completo]` | mostra conta, tipo, validade estimada do token, cota de publicação e permissões (publicar e métricas, testadas por chamadas reais), confere o formato do armazenamento. Grava `IG_USER_ID` se estiver vazio. Compara a conta do token com a `arroba` de `visual.json`. | só lê (e grava o `IG_USER_ID`) |
| `verificar --completo` | também sobe uma imagem neutra, abre a URL como navegador e como `facebookexternalhit/1.1`, cria um contêiner **sem publicar** e apaga a imagem | usa o bucket; nada vai ao feed |
| `renovar [--marca M] [--se-faltar-dias N]` | renova o token de longa duração (precisa ter mais de 24 h e não ter vencido) | atualiza `instagram.env` |

Arquivos de credenciais (nomes das chaves):

- `instagram.env`: `IG_ACCESS_TOKEN`, `IG_USER_ID`, `IG_TOKEN_VALIDO_ATE` (data estimada: geração + 60 dias; quem manda é a Meta).
- `armazenamento.env`: `ARMAZENAMENTO_ENDPOINT`, `ARMAZENAMENTO_REGIAO`, `ARMAZENAMENTO_BUCKET`, `ARMAZENAMENTO_CHAVE_ID`, `ARMAZENAMENTO_CHAVE_SECRETA`, `ARMAZENAMENTO_URL_PUBLICA`.
- `aprovacao.key`: não é uma credencial da Meta nem do armazenamento; é a chave que assina as aprovações (32 bytes aleatórios em hexadecimal). Criada pelo `publicar.py aprovar` na primeira aprovação, na mesma pasta, só com permissão do dono. Ninguém precisa abri-la, copiá-la ou colá-la.

## `publicar.py`: aprovar, agendar, publicar, conferir

| Comando | O que faz | Muda |
|---|---|---|
| `simular --post P` | mostra o que vai sair (artes convertidas em JPEG com tamanhos, legenda final com hashtags, chamada), roda **todas** as checagens locais (inclui o validador de posts da skill `criar-conteudo`, se existir) e dá o veredito: **PRONTO para a pessoa aprovar** só quando o `aprovar` aceitaria de fato (status `arte_pronta`, `erro` ou `aprovado`, sem problemas); com status `texto_aprovado`, por exemplo, diz que ainda faltam as artes (`arte_pronta`) e sai com código 1. Mostra também JÁ APROVADO, AGENDADO e PUBLICADO. Falta de `arroba` no `visual.json` é um problema. **Sem rede.** | nada |
| `aprovar --post P --frase "..." --por "Nome"` | confere a frase (cita o id), o status e os problemas; **abre uma janela no computador da pessoa** com o resumo (post, título, início da legenda, artes, agendamento, hash, frase registrada) e botões Aprovar e Cancelar; só então grava `aprovacao` (por, frase, data, hash e **assinatura**) e muda o status para `aprovado`. A assinatura é um HMAC-SHA256 feito com uma chave aleatória criada na primeira aprovação (`aprovacao.key`, fora do projeto; veja `aprovacao-e-hash.md`). Sem janela, pergunta no terminal (só se for interativo; a pessoa digita o id); senão recusa com "rode este comando você mesma, num terminal". **Nenhuma opção ou variável de ambiente pula a confirmação.** | post (`status`, `aprovacao`, `historico`) e, na primeira vez, a chave em `~/.config/estudio-de-conteudo/<marca>/` |
| `agendar --post P --quando 2026-11-05T18:00:00-03:00` | exige `aprovado`, assinatura e hash conferidos; horário futuro; **sempre informe o fuso** (sem fuso, usa o do computador e avisa). Avisa se a rotina não está instalada. | post (`status` = `agendado`, `agendado_para`) |
| `desagendar --post P` | volta de `agendado` para `aprovado` (a aprovação continua valendo; se ela não tem assinatura válida, o comando avisa) | post |
| `publicar --post P [--de-novo]` | exige `aprovado` (ou `agendado`), assinatura e hash conferidos, `confirmar` vazio, sem trava e fora do `publicados.csv`. Converte PNG em JPEG, envia ao armazenamento, testa a URL pública (navegador e robô da Meta), cria os contêineres, espera `FINISHED`, publica, pega o link, registra, apaga as imagens. `--de-novo` só se a pessoa pedir outra publicação do mesmo post, e abre a janela de confirmação com o link do post que já está no ar. Recusa se a `arroba` do `visual.json` estiver vazia e, depois de pegar a trava, confere de novo status, aprovação e `publicados.csv` (outra execução pode ter publicado nesse meio tempo). | post (`publicacao`, `status`, `historico`), `publicados.csv`, bucket |
| `agendados [--janela-horas 2] [--simular]` | comando da rotina. Publica os `agendado` cujo horário chegou, se o atraso for de até a janela (padrão 2 h); passou disso, marca `erro` e registra. Sem nada vencido, **não usa a rede** e não escreve no log. Uma execução por vez (trava). Renova o token se faltarem 10 dias ou menos. Relê cada post depois de pegar a trava e pula o que deixou de estar `agendado` (a pessoa pode ter rodado `desagendar`) ou foi reagendado. | como `publicar`, mais `publicacao/logs/` |
| `conferir --post P [--confirmo-que-nao-foi-ao-ar]` | resolve publicação "sem resposta clara" (veja `erros-comuns.md`). `--confirmo-que-nao-foi-ao-ar` abre a janela que pergunta à pessoa se ela abriu o feed e o post não está lá. | post, `publicados.csv`, trava |
| `situacao [--todos]` | lista os posts da marca com status, horário e link, avisa de pendências de conferência e marca os `aprovado` ou `agendado` cuja aprovação não tem assinatura válida | nada |

Arquivos que o `publicar.py` usa em `marcas/<marca>/publicacao/`:

- `publicados.csv`: `publicado_em,post_id,lote,formato,media_id,permalink,hash`. Se estiver aberto em outro programa, o registro vai para `publicados-pendentes.jsonl` e entra no CSV na próxima gravação; os dois valem contra publicação duplicada. Se o arquivo foi salvo pelo Excel (separador `;`, maiúsculas, BOM), a leitura aceita e a próxima gravação o normaliza para vírgulas, guardando a versão anterior em `_antes-formato-csv-AAAA-MM-DD/`.
- `_em_andamento/<id>.json`: trava de um post em publicação ou sem resposta clara (etapa, contêiner, imagens enviadas). Nunca apague à mão: use `conferir`.
- `execucao.lock`: uma execução do `agendados` por vez (vence sozinha em 90 minutos).
- `logs/rotina-AAAA-MM.log`: registro mensal da rotina.

## `metricas.py`: números do perfil e dos posts

| Comando | O que faz |
|---|---|
| `coletar [--marca M] [--dias 90] [--limite 200] [--simular]` | acrescenta uma linha em `metricas/perfil.csv` e uma por mídia em `metricas/posts.csv`. Detalhes em `metricas.md`. Saída `3` = coleta parcial por limite de chamadas. |

## `rotina.py`: tarefas no computador

| Comando | O que faz |
|---|---|
| `mostrar [--marca M]` | mostra as duas tarefas, o comando de cada uma, se já estão instaladas e como instalar. **Não altera nada.** |
| `instalar [--marca M] [--python CAMINHO]` | cria as tarefas. **Quem roda é a pessoa.** |
| `remover [--marca M]` | remove as tarefas |

## Variáveis de ambiente

| Variável | Para que serve |
|---|---|
| `ESTUDIO_CONFIG` | troca a pasta base das credenciais e da chave de aprovação (padrão `~/.config/estudio-de-conteudo`). Se a pasta mudar, a chave antiga deixa de ser encontrada e as aprovações anteriores perdem a validade |
| `ESTUDIO_INSTAGRAM_TESTE` | só para o `autoteste.py`: aponta a API para um servidor falso neste computador. Só aceita `http://127.0.0.1...` ou `http://localhost...`; qualquer outro valor é ignorado e a API oficial é usada |

`python -X utf8 skills/publicar-instagram/scripts/autoteste.py` roda os testes da skill contra esse servidor falso. Nenhuma chamada sai do computador e nada toca as suas marcas ou credenciais.

## Ordem típica

```
credenciais.py configurar  ->  credenciais.py verificar --completo      (uma vez por marca)
publicar.py simular  ->  (a pessoa vê e diz "pode publicar <id>")  ->  publicar.py aprovar
publicar.py publicar            ou            publicar.py agendar  (+ rotina.py mostrar)
metricas.py coletar             (manual ou pela rotina, a cada 4 h)
```
