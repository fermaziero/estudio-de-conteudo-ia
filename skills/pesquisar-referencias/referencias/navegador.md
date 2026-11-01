# Ferramenta de navegador: como checar, instalar e o que fazer sem ela

Informações conferidas nas fontes oficiais em **2026-10-28**. Ferramentas de IA mudam rápido: se esta data tiver mais de três meses, confira de novo as fontes antes de orientar a pessoa e atualize a data aqui.

## O que a coleta precisa

1. Abrir uma aba no navegador da pessoa, **na conta dela, já logada no Instagram**.
2. **Rodar JavaScript** nessa aba e receber o resultado (os blocos de `coleta-instagram.md` fazem isso).
3. Fechar a aba no fim.

Sem o item 2, a coleta completa não funciona: use a análise reduzida (seção final).

## Como checar se existe

1. Olhe a lista de ferramentas que o agente tem. Procure uma de navegador que execute JavaScript: no Claude in Chrome é a `javascript_tool`; no Playwright, a `browser_evaluate`; no Chrome DevTools, a `evaluate_script`.
2. No Claude Code, rode `/chrome`. Deve aparecer "Status: Enabled" e "Extension: Installed". Para ver as ferramentas, rode `/mcp`, escolha `claude-in-chrome` e "View tools".
3. Teste de verdade: abra um perfil público do Instagram numa aba nova e rode o **passo 0** de `coleta-instagram.md`. Voltou um objeto com `idioma` e `menuLogado: true`: está pronto. Erro, ferramenta ausente ou `menuLogado: false`: veja abaixo.

## Opções

**1. Claude in Chrome (Claude Code).** É a opção testada nesta skill.
- Como funciona: o Claude Code usa a extensão Claude in Chrome, abre abas novas num grupo e compartilha o login do navegador. Em tela de login ou CAPTCHA, pausa e pede para a pessoa resolver.
- Requisitos: Google Chrome ou Microsoft Edge (a documentação do Claude Code diz que detecta também Brave, Arc, Vivaldi e Opera, mas a página de suporte da extensão diz que só o Chrome é suportado: use o Chrome); extensão na versão 1.0.36 ou mais nova; Claude Code atualizado; plano pago direto da Anthropic (Pro, Max, Team ou Enterprise); entrada com `/login` (chave de API não serve). Não funciona no WSL nem por Amazon Bedrock, Google Cloud ou Microsoft Foundry.
- Como ligar: instale a extensão na Chrome Web Store (https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn), depois inicie o Claude Code com `claude --chrome` ou rode `/chrome` (e escolha "Enabled by default" para ligar sempre). Se a extensão não for detectada na primeira vez, reinicie o Chrome. Se a conexão cair, rode `/chrome` e escolha "Reconnect extension". Extensão e Claude Code precisam estar na mesma conta e organização da Anthropic.
- Roda JavaScript? A ferramenta `javascript_tool` consta na lista do servidor `claude-in-chrome` (conferido na lista de ferramentas da sessão em 2026-10-28). A documentação descreve leitura de console e do DOM, mas não detalha a execução de JavaScript: confirme com o passo 0.
- Se as ferramentas `mcp__claude-in-chrome__*` aparecerem como "adiadas", carregue todas numa só chamada de busca de ferramentas, antes de usar.
- Fontes: https://code.claude.com/docs/en/chrome e https://support.claude.com/en/articles/12012173-getting-started-with-claude-in-chrome (2026-10-28).

**2. Playwright MCP com a extensão (Claude Code, Codex, Cursor, Gemini CLI e outros clientes MCP).**
- Com a opção `--extension`, conecta a um Chrome ou Edge já aberto e usa as sessões logadas. A ferramenta `browser_evaluate` roda JavaScript. Exige Node.js, o servidor `@playwright/mcp` e a extensão do Playwright; as etapas estão no README.
- Aviso do próprio projeto: não é uma barreira de segurança.
- Fonte: https://github.com/microsoft/playwright-mcp (2026-10-28).

**3. Chrome DevTools MCP (Claude Code, Cursor, VS Code com Copilot, Gemini CLI, Antigravity).**
- A ferramenta `evaluate_script` roda JavaScript na página. Para usar o seu Chrome já aberto e logado: opção `--autoConnect`, Chrome 144 ou mais novo, depuração remota ligada em `chrome://inspect/#remote-debugging` e a pessoa aceita o aviso de conexão no navegador.
- Aviso do próprio projeto: o servidor expõe o conteúdo do navegador ao agente.
- A página do projeto não lista o Codex entre os clientes, mas o servidor é MCP comum.
- Fontes: https://github.com/ChromeDevTools/chrome-devtools-mcp, `docs/tool-reference.md` e `docs/troubleshooting.md` do mesmo repositório (2026-10-28).

**4. Extensão do Codex para Chrome.** Instalada pelo app do Codex (Configurações, Computer Use). Lê e age em sites onde a pessoa já está logada; a pessoa escolhe o navegador com @ num chat novo. A documentação não cita execução de JavaScript nem uso pelo Codex CLI: rode o passo 0. Se não rodar JavaScript, use a opção 2 ou 3, ou a análise reduzida. Fonte: https://developers.openai.com/codex/app/chrome-extension (2026-10-28).

**5. Navegador embutido do Cursor.** O agente navega, clica, digita, rola, tira capturas e lê o console, e o login fica guardado por workspace. A documentação não cita execução de JavaScript, e a pessoa precisa entrar no Instagram dentro desse navegador. Rode o passo 0. Fonte: https://cursor.com/docs/agent/tools/browser (2026-10-28).

Outros agentes: qualquer cliente MCP aceita as opções 2 e 3.

## Login e segurança

- **A pessoa entra no Instagram sozinha**, na janela do navegador. O agente nunca pede, lê nem digita senha, código de verificação ou resposta de segurança. Também não pede cookies ou chaves.
- Tela de login, desafio, CAPTCHA, "Tente novamente mais tarde": pare, explique em uma frase e espere a pessoa resolver. Não tente contornar.
- A extensão enxerga os sites que a pessoa liberar. Sugira, se possível, um perfil do navegador só para a coleta, com poucas abas abertas (nada de banco ou e-mail), e que a pessoa só aprove sites do Instagram.
- O agente trabalha só na aba que criou e a fecha no fim.

## Se não existir ferramenta que rode JavaScript: análise reduzida

1. Diga em uma frase: "Não consigo ler o Instagram direto neste computador. Posso fazer uma análise reduzida com prints ou textos que você me enviar, ou você instala uma ferramenta de navegador e eu faço a completa."
2. Peça, nesta ordem de valor: (a) um print do topo do perfil (seguidores, bio, link); (b) prints do grid (formatos e legendas visíveis) e da aba Reels (views); (c) 5 a 10 posts abertos, em print ou com a legenda colada e as curtidas; (d) links de posts, se a pessoa quiser. Links do Instagram costumam exigir login e bloquear leitura automática: tente abrir uma vez e, se não abrir, volte aos prints. Não tente contornar bloqueios.
3. Analise só o que recebeu. Siga `modelo-perfil.md`, seção "Análise reduzida": o arquivo fica marcado como reduzido, o que faltou vira "não medido", e o `referencias.csv` recebe só o que aparece nos prints (seguidores, tipo, nicho).
4. Nunca peça a senha, o código de verificação nem acesso à conta da pessoa.
5. Se depois a ferramenta de navegador for instalada, refaça a coleta completa: o arquivo reduzido vai para `_antes-recoleta-AAAA-MM-DD/` e o novo registra o histórico.
