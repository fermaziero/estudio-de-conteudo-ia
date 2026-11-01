@AGENTS.md

# Claude Code

O `AGENTS.md` importado acima é a fonte única das regras do projeto. Aqui fica só o que é específico do Claude Code. Conferido na documentação do Claude Code em 2026-10-29: https://code.claude.com/docs/en/skills, https://code.claude.com/docs/en/sub-agents, https://code.claude.com/docs/en/chrome, https://code.claude.com/docs/en/memory e https://code.claude.com/docs/en/tools-reference.

## Skills como `/nome`

- Abra o Claude Code na raiz do projeto, a pasta que contém `skills/` e `marcas/`. Ele carrega as skills de `.claude/skills/` da pasta onde foi iniciado.
- Cada skill é um comando: `/configurar-marca`, `/pesquisar-referencias`, `/planejar-conteudo`, `/criar-conteudo`, `/revisar-conteudo`, `/gerar-artes`, `/publicar-instagram` e `/acompanhar-resultados`. Digitar `/` lista todos. A pessoa também pode só conversar: o Claude Code usa a skill pela descrição.
- O Claude Code percebe mudanças em skills na mesma sessão. Depois de editar `skills/<nome>/SKILL.md`, rode `python -X utf8 ferramentas/sincronizar_atalhos.py` para regerar os atalhos de `.claude/skills/`.

## Subagentes (ferramenta Agent)

Cada subagente começa com a própria janela de contexto, limpa: é o que a revisão independente (regra 8 do `AGENTS.md`) pede. Use um subagente de uso geral, que carrega o `CLAUDE.md`; os integrados Explore e Plan não o carregam e não conheceriam as regras.

- **Revisão do texto.** Depois de `criar-conteudo`, abra um subagente e passe só o pedido do passo 7 de `skills/criar-conteudo/SKILL.md` (marca, lote, data de hoje e a instrução de seguir `skills/revisar-conteudo/SKILL.md`). Não diga ao revisor que o texto está bom.
- **Revisão das artes.** Em `gerar-artes`, um subagente abre a visão geral e as artes com `skills/gerar-artes/referencias/checklist-visual.md`. Passe só os caminhos e o checklist.
- **Pesquisa de referências.** Um subagente por perfil, no máximo 3 ao mesmo tempo, com o brief de `skills/pesquisar-referencias/referencias/brief-agente.md`. Confira que ele enxerga as ferramentas do navegador; se não enxergar, faça um perfil por vez no agente principal.
- Peça sempre retorno curto (o que fez, onde salvou, pendências) e conte à pessoa o essencial. Sem poder abrir subagentes, siga a regra 8 do `AGENTS.md`: passagem separada e aviso de que não houve revisão independente.

## Navegador: extensão Claude in Chrome

A coleta de `pesquisar-referencias` lê o Instagram no Chrome onde a pessoa já está logada, pela extensão Claude in Chrome ([Chrome Web Store](https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn)).

- **Requisitos:** extensão na versão 1.0.36 ou mais nova; plano Pro, Max, Team ou Enterprise direto da Anthropic; entrada no Claude Code com `/login` (chave de API não serve). Não funciona no WSL nem por Amazon Bedrock, Google Cloud ou Microsoft Foundry.
- **Ligar:** inicie com `claude --chrome`, ou rode `/chrome`. O painel deve mostrar "Status: Enabled" e "Extension: Installed". Se a extensão não for detectada, reinicie o Chrome ou use "Reconnect extension" em `/chrome`.
- **Login:** a pessoa entra no Instagram sozinha, na janela do Chrome. Em tela de login ou CAPTCHA, o Claude Code pausa e pede que ela resolva. Você nunca digita senha.
- **Se as ferramentas `mcp__claude-in-chrome__*` aparecerem como adiadas,** carregue todas numa só busca de ferramentas antes de usar.
- **Sem a extensão,** faça a análise reduzida. Passo a passo e alternativas: `skills/pesquisar-referencias/referencias/navegador.md`.

## Aprovação de posts

O `publicar.py aprovar` abre uma janela no computador da pessoa e, só depois do clique em **Aprovar**, grava a aprovação com uma assinatura (regra 1 do `AGENTS.md`). Sem assinatura válida o post vale como não aprovado: editar `status` ou `aprovacao` no JSON não aprova nada, então não faça isso. A chave da assinatura (`aprovacao.key`, em `~/.config/estudio-de-conteudo/<marca>/`) vale como credencial: não abra essa pasta, não leia nem copie a chave (regra 2). Avise antes de rodar o comando e deixe o clique com ela: não use controle de tela (como o computer use do Claude Code) para aprovar por ela. Se o comando recusar com "rode este comando você mesma, num terminal", mostre o comando completo e peça que ela o rode; se disser "aprovação sem assinatura válida", siga a seção 10 do `AGENTS.md`. Limite honesto: quem controla o computador inteiro ainda poderia contornar tudo isso, e as regras proíbem.

## Comandos demorados

O Bash do Claude Code (e a ferramenta PowerShell, que segue as mesmas regras) dá 2 minutos a cada comando e aceita no máximo 10. Ao estourar o prazo, o comando vai para o segundo plano em vez de ser encerrado, e o resultado diz "Command did not complete within its 120s timeout and was moved to the background". Fonte: https://code.claude.com/docs/en/tools-reference (seção Bash tool behavior), conferida em 2026-10-29.

- `publicar.py aprovar` espera até 5 minutos pelo clique da pessoa, e `publicar.py publicar` leva alguns minutos (envia as imagens e espera a Meta). Rode os dois com `timeout` de 10 minutos (600000 ms).
- `credenciais.py configurar` espera a pessoa colar os dados e salvar, sem limite fixo. Rode em segundo plano (`run_in_background`), avise a pessoa e leia a saída depois; `/tasks` lista o que está rodando.
- Se um comando foi movido para o segundo plano, ele continua rodando: não o repita, porque só atrapalha (outra janela, outra tentativa de publicar). Espere e leia a saída; se a publicação ficar incerta, siga a seção 10 do `AGENTS.md`.

## Contexto enxuto

- Leia só o `SKILL.md` da skill em uso; abra `referencias/` e `modelos/` quando o `SKILL.md` mandar.
- Entregue trabalho volumoso (coleta de perfis, revisões, conferência de números) a subagentes, com retorno curto.
- Não cole JSON, CSV, HTML nem saídas longas no chat. Use o resumo que os scripts imprimem (muitos têm `--simular`) e leia só o trecho de que precisa.
- O estado fica nos arquivos: `status` dos posts, `lote.md`, `publicar.py situacao`, `validar_marca.py`. Ao fechar uma etapa longa, a pessoa pode limpar a conversa com `/clear`, e você retoma lendo os arquivos.
- Deixe o Chrome ligado só quando for pesquisar referências (`claude --chrome`). Ligado por padrão, as ferramentas do navegador ocupam contexto em toda sessão.
- O Claude Code pede permissão antes de rodar comandos e editar arquivos. Isso é esperado: diga em uma frase o que o comando faz antes de a pessoa aceitar.
