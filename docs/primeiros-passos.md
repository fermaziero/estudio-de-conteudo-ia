# Primeiros passos: do zero à primeira conversa

Este guia leva você, no Windows ou no macOS, da instalação até a primeira conversa com o Estúdio de Conteúdo com IA. Não precisa saber programar. Cada passo diz o que fazer e como conferir se deu certo.

Conferido nas páginas oficiais em **2026-10-29**. Instaladores mudam com frequência: se uma tela ou um comando estiver diferente, vale a página oficial citada no passo. Use só os links e os comandos dessas páginas, nunca os de vídeos ou posts de terceiros.

## O caminho

1. Abrir o terminal.
2. Instalar o Python.
3. Instalar um agente de IA (Claude Code ou Codex).
4. Baixar o projeto.
5. Abrir a pasta no agente e instalar o Pillow.
6. Fazer a primeira conversa.

Palavras que aparecem aqui:

- **Terminal**: a janela onde você digita comandos (frases curtas que o computador executa).
- **Agente de IA**: o assistente com quem você conversa e que roda o estúdio por você.
- **Python**: a linguagem em que os scripts do estúdio são escritos. Você só precisa instalá-la.
- **Pillow**: uma biblioteca (um complemento do Python) que desenha as imagens.
- **Skill**: um roteiro de trabalho que o agente lê e segue, como "configurar a marca" ou "gerar as artes".

## Passo 1: o terminal em dois minutos

- **Windows:** aperte `Win + X` e escolha **Windows PowerShell** (ou **Terminal**). No começo de cada linha aparece `PS` e o caminho da pasta atual. Se aparecer só o caminho, sem o `PS`, você abriu o CMD: feche e abra o PowerShell.
- **macOS:** aperte `Cmd + Espaço`, digite `Terminal` e aperte `Enter`.
- **Colar um comando:** `Ctrl + V` (ou botão direito) no Windows; `Cmd + V` no macOS. Para executar, aperte `Enter`.

Fonte: https://code.claude.com/docs/en/terminal-guide (2026-10-29).

Se preferir não usar o terminal no dia a dia, os apps de desktop do Claude e do Codex (passo 3) abrem a pasta por menu. O Python, de qualquer jeito, se instala pelo site oficial.

## Passo 2: instalar o Python

O estúdio pede **Python 3.10 ou mais novo**.

### Windows

1. Abra https://www.python.org/downloads/. No Windows, o botão principal é **Download Python install manager**. Baixe o arquivo, dê duplo clique e escolha **Install** (Instalar). A página também oferece o instalador tradicional ("standalone installer"), e a documentação do Python cita a Microsoft Store como outro caminho.
2. Abra um PowerShell novo e digite `python --version`. Na primeira vez, o gerenciador pode baixar e instalar a versão mais recente do Python sozinho: espere terminar.
3. Deve aparecer algo como `Python 3.x.y`, com o segundo número 10 ou maior.
4. Se o PowerShell disser que `python` não é reconhecido, ou se abrir a Microsoft Store: em **Iniciar**, abra **Gerenciar aliases de execução de aplicativo** (em inglês, "Manage app execution aliases") e confira se os atalhos de "Python (default)" estão ligados. Se já estiverem, desligue e ligue de novo. Depois abra um PowerShell novo. O comando `py --version` também deve funcionar.

Fontes: https://www.python.org/downloads/ e https://docs.python.org/3/using/windows.html (2026-10-29). A documentação diz que a versão atual do Python funciona no Windows 10 ou mais novo.

### macOS

1. Abra https://www.python.org/downloads/ e baixe o instalador para macOS (arquivo `.pkg`). Abra-o e siga as telas.
2. No fim, abra a pasta **Python 3.x** dentro de Aplicativos e dê duplo clique em **Install Certificates.command** para completar a instalação. Ele abre uma janela do Terminal que instala os certificados SSL que o Python usa para falar com sites seguros; quando aparecerem `Successfully installed certifi` e `update complete`, feche a janela. Sem esse passo, publicar ou coletar números pode falhar com **erro de certificado SSL** (`CERTIFICATE_VERIFY_FAILED`). Se você já instalou o Python e pulou o passo, faça agora.
3. No Terminal, digite `python3 --version`. Deve aparecer `Python 3.10` ou mais novo. Se aparecer um número antigo, feche o Terminal e abra de novo. O macOS traz um `python3` próprio, mais antigo, que as ferramentas da Apple usam: nunca o apague nem o altere.

Fonte: https://docs.python.org/3/using/mac.html (2026-10-29). No macOS e no Linux, o comando é sempre `python3`.

## Passo 3: instalar um agente de IA

Escolha um. Os dois funcionam com o estúdio; o que decide é a conta que você tem. Cada um oferece um **app de desktop** (abre a pasta por menu, sem terminal) e uma **versão de terminal**. Cursor e Gemini CLI também servem: veja a seção 7 do [AGENTS.md](../AGENTS.md).

### Opção A: Claude Code

- **Conta:** o app de desktop pede uma assinatura Claude Pro, Max, Team ou Enterprise. O terminal aceita também uma conta do Claude Console. O plano gratuito do claude.ai não inclui o Claude Code. Você entra com a conta no primeiro uso.
- **Computador:** Windows 10 (versão 1809 ou mais nova) ou macOS 13 ou mais novo, com internet.
- **App de desktop:** baixe pelos botões da página https://code.claude.com/docs/en/desktop-quickstart (macOS e Windows), instale, abra, entre com a sua conta e clique na aba **Code**.
- **Terminal:**
  - Windows, no PowerShell: `irm https://claude.ai/install.ps1 | iex`
  - macOS, no Terminal: `curl -fsSL https://claude.ai/install.sh | bash`

  O comando não mostra progresso: espere terminar. Depois abra um terminal novo e confira com `claude --version`. No Windows, o Git para Windows (https://git-scm.com/downloads/win) é opcional, mas recomendado; sem ele, o Claude Code usa o PowerShell.

Fontes: https://code.claude.com/docs/en/quickstart, https://code.claude.com/docs/en/setup e https://code.claude.com/docs/en/desktop-quickstart (2026-10-29).

### Opção B: Codex

- **Conta:** entre com a sua conta do ChatGPT (a documentação recomenda os planos Plus, Pro, Business, Edu ou Enterprise) ou use uma chave de API, que exige configuração extra.
- **App de desktop:** no macOS, a página https://learn.chatgpt.com/docs/app oferece o botão "Download for macOS (Apple Silicon)". No Windows, a página https://learn.chatgpt.com/docs/windows/windows-app leva ao instalador da Microsoft. Entre com a conta do ChatGPT.
- **Terminal:**
  - Windows, no PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"`
  - macOS, no Terminal: `curl -fsSL https://chatgpt.com/codex/install.sh | sh`

  Depois digite `codex` e escolha **Sign in with ChatGPT**.

Fontes: https://github.com/openai/codex (README oficial), https://learn.chatgpt.com/docs/codex/cli, https://learn.chatgpt.com/docs/app e https://learn.chatgpt.com/docs/windows/windows-app (2026-10-29).

## Passo 4: baixar o projeto

- **Pelo ZIP (o mais simples):** na página do projeto no GitHub, clique em **Code** e em **Download ZIP**. Extraia o arquivo (Windows: botão direito e **Extrair tudo**; macOS: duplo clique). O nome da pasta pode vir com um sufixo, como `-main`, e no Windows o **Extrair tudo** pode criar uma pasta dentro de outra com o mesmo nome: abra a que contém o arquivo `AGENTS.md`, porque ela é a raiz do projeto. Fonte: https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives (2026-10-29).
- **Pelo git (opcional):** o Git é um programa que baixa e atualiza projetos (https://git-scm.com/install/). Com ele instalado, rode `git clone <endereço do repositório>`. Fonte: https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository (2026-10-29).

Onde guardar a pasta:

- **Extraia ou mova a pasta para a sua pasta pessoal, fora de Documentos e Mesa e fora do OneDrive:** `C:\Users\<seu-usuario>\estudio-de-conteudo-ia` no Windows e `~/estudio-de-conteudo-ia` no macOS (se quiser, tire o `-main` do nome). No Windows, o OneDrive pode sincronizar Mesa, Documentos e Imagens com a nuvem (https://www.microsoft.com/en-us/microsoft-365/onedrive/pc-cloud-backup, 2026-10-29), e o mesmo vale para pastas do iCloud Drive e do Google Drive: os seus arquivos, inclusive os dados da sua marca, iriam para lá.
- No macOS, Documentos e Mesa têm outro problema: o macOS pode bloquear a rotina de agendamento por privacidade (veja `skills/publicar-instagram/referencias/rotina.md`).
- **Não mude a pasta de lugar depois.** Se você instalar a rotina de agendamento, ela guarda o caminho completo da pasta.

## Passo 5: abrir a pasta no agente e instalar o Pillow

Abra a pasta que contém `skills/`, `marcas/` e o arquivo `AGENTS.md` (a raiz do projeto).

- **Claude Code, app:** na aba **Code**, abaixo da caixa de texto, escolha a primeira opção do grupo **Local** no primeiro seletor; depois, no controle da pasta ao lado, escolha **Open folder…** e a pasta do projeto.
- **Codex, app:** abra a pasta como projeto. No Windows, use **Add new project** (ou `Ctrl + O`); no macOS, a página do app fala em criar um projeto ou abrir uma pasta.
- **Terminal (os dois):** entre na pasta com `cd` e abra o agente com `claude` ou `codex`.
  - Windows, no PowerShell: `cd "$HOME\estudio-de-conteudo-ia"`. Dica: no Explorador de Arquivos, abra a pasta, clique na barra de endereço, copie o caminho com `Ctrl + C` e cole entre as aspas, no lugar de `$HOME\estudio-de-conteudo-ia`.
  - macOS: `cd ~/estudio-de-conteudo-ia`. Dica: no Finder, com a barra de caminho visível (menu **Visualizar**), clique na pasta com a tecla `Control` apertada e escolha **Abrir no Terminal** ("Open in Terminal").

Ajuste o caminho ao lugar e ao nome que a pasta do projeto tem no seu computador. Fonte da dica do Finder: https://support.apple.com/guide/terminal/open-new-terminal-windows-and-tabs-trmlb20c7888/mac (2026-10-29).

**Conferir se o agente enxergou o projeto:** pergunte "Que projeto é este e o que você pode fazer por mim?". Ele deve falar do Estúdio de Conteúdo com IA e de oito skills. No Claude Code, digitar `/` lista as skills; no Codex pelo terminal, use `/skills`. Não apareceu? Confira se abriu a pasta certa (a que tem o `AGENTS.md`) e reinicie o agente.

**Instalar o Pillow.** Com o terminal na pasta do projeto, rode:

- Windows: `python -m pip install -r requirements.txt`
- macOS: `python3 -m pip install -r requirements.txt`

Se preferir, peça ao agente: "Instale o que falta para o estúdio funcionar". Ele vai pedir o seu ok antes de rodar o comando (veja "O agente vai pedir permissão", no passo 6). Fonte: https://pillow.readthedocs.io/en/stable/installation/basic-installation.html (2026-10-29).

**Se o pip recusar a instalação** com uma mensagem que cita `externally-managed-environment` ("ambiente gerenciado externamente"): isso acontece quando o Python vem de um gerenciador de pacotes do sistema, como o Homebrew no macOS ou o Debian, o Ubuntu e o Fedora no Linux. Esses sistemas marcam o Python deles dessa forma (é a regra PEP 668) para você não bagunçar os programas do próprio sistema. O Python baixado do python.org, no passo 2, normalmente não tem essa trava. A saída é criar um **ambiente virtual**: uma pasta (`.venv`) com um Python só do projeto, onde o Pillow se instala sem mexer no resto do computador.

1. Na pasta do projeto, crie o ambiente. macOS e Linux: `python3 -m venv .venv`. Windows: `py -m venv .venv`. No Debian e no Ubuntu, pode ser preciso instalar antes o pacote `python3-full`, como a própria mensagem do sistema costuma indicar.
2. Instale o Pillow nele. macOS e Linux: `.venv/bin/python -m pip install -r requirements.txt`. Windows: `.venv\Scripts\python -m pip install -r requirements.txt`.
3. Daqui em diante, troque `python` (ou `python3`) por `.venv/bin/python` (Windows: `.venv\Scripts\python`) em todos os comandos do estúdio. Por exemplo: `.venv/bin/python -X utf8 skills/configurar-marca/scripts/validar_marca.py --marca exemplo`. Diga ao agente: "Neste projeto, use sempre o Python da pasta .venv".

Você não precisa "ativar" o ambiente: basta usar o caminho do Python dele. A pasta `.venv/` já está no `.gitignore`, então não vai para o git. Se mais adiante você instalar a rotina de agendamento, rode o `rotina.py instalar` com esse mesmo Python, para a tarefa agendada achar o Pillow. Fontes: https://peps.python.org/pep-0668/, https://packaging.python.org/en/latest/specifications/externally-managed-environments/, https://docs.brew.sh/Language-Runtimes-and-Packages e https://docs.python.org/3/library/venv.html (2026-10-29).

**Teste rápido** (não mexe em nada seu):

```
python -X utf8 skills/configurar-marca/scripts/validar_marca.py --marca exemplo
```

No macOS, troque `python` por `python3`. No fim deve aparecer `0 erro(s), 0 aviso(s)`. O comando `python -X utf8 skills/gerar-artes/scripts/autoteste.py` faz uma prova maior, com uma marca fictícia numa pasta temporária, e termina com `AUTOTESTE OK`.

## Passo 6: a primeira conversa

Escreva para o agente:

> Quero configurar minha marca.

O que acontece:

1. O agente confere se o ambiente está certo, explica o fluxo e pergunta se você quer ver antes a **marca de exemplo** ("Exemplo Contábil", um escritório fictício) para saber como fica. Pode responder que sim ou pedir a qualquer hora: "Mostre a marca de exemplo".
2. Começa a entrevista, com no máximo 3 perguntas por vez. Cada resposta vira um arquivo seu em `marcas/<seu-nome>/`, e o agente mostra o que gravou. Você pode pular o que não souber e corrigir depois.
3. **Nada é publicado nesta etapa.** Publicar só acontece bem mais adiante, e o agente não consegue aprovar um post sozinho: a aprovação final só é gravada quando você confirma numa janela que abre no seu computador.

**O agente vai pedir permissão.** Antes de rodar comandos, gravar arquivos ou usar a internet, o agente pode parar e perguntar. Isso é normal, depende do modo de permissão de cada agente e protege você (fontes: https://code.claude.com/docs/en/quickstart e https://learn.chatgpt.com/docs/agent-approvals-security, 2026-10-29). O que responder:

- Leia o que ele quer fazer; ele deve explicar o comando em uma frase.
- Pode aprovar os comandos do estúdio (`python` ou `python3` apontando para `skills/` ou `ferramentas/`) e a criação ou edição de arquivos dentro de `marcas/`. No começo, prefira aprovar uma vez por vez, em vez de "sempre".
- Na dúvida, pergunte "o que isso faz?" ou recuse. Recuse o que apagar arquivos, mexer fora da pasta do projeto ou pedir senha, token ou chave: esses dados nunca são digitados nem colados no chat.

Se tiver à mão, ajuda (não é obrigatório): o nome e o @ do perfil; o que você oferece e para quem; resultados reais que você pode mostrar, com a origem de cada um; o logo em PNG com fundo transparente (uma versão para fundo claro e outra para fundo escuro); fotos que você tem direito de usar; links oficiais; e o que você nunca quer dizer.

Depois da ficha pronta, você pode pedir:

- "Analise este perfil de referência: @perfil" (precisa do Chrome logado no Instagram; o agente explica).
- "O que eu posto essa semana?"
- "Escreva o carrossel da pauta 2."

Quando chegar a hora de publicar no Instagram, siga [instagram-api.md](instagram-api.md) e [armazenamento-imagens.md](armazenamento-imagens.md). É uma configuração única por marca. Na hora de aprovar cada post, o agente roda o comando e uma janela abre no seu computador, com o resumo do post: confira e clique em **Aprovar**. O clique tem de ser seu. Depois do clique, o programa assina a aprovação com uma chave secreta guardada fora do projeto; se você trocar de computador, a chave não vai junto, e você aprova de novo os posts que ainda não foram publicados.

## Se algo não funcionar

| O que aparece | O que fazer |
|---|---|
| `python` não é reconhecido, ou abre a Microsoft Store (Windows) | Passo 2, item 4. Teste também `py --version`. |
| `python3 --version` mostra uma versão antiga (macOS) | Feche o Terminal e abra de novo. Se continuar, confira se o instalador do python.org terminou. |
| `irm` não é reconhecido | Você está no CMD. Abra o PowerShell (`Win + X`). |
| `claude` não é reconhecido, ou "command not found" | Abra um terminal novo. Se continuar, siga https://code.claude.com/docs/en/troubleshoot-install.md#command-not-found-claude-after-installation (2026-10-29). |
| `pip` não é encontrado | Use `python -m pip` (no macOS, `python3 -m pip`). |
| O pip diz `externally-managed-environment` | Crie um ambiente virtual: veja "Se o pip recusar a instalação", no passo 5. |
| Erro de certificado SSL ao publicar ou coletar números (macOS) | Rode o **Install Certificates.command** (passo 2, macOS, item 2). |
| O agente não conhece o projeto, ou as skills não aparecem | Confira se abriu a pasta que contém o `AGENTS.md`, feche e abra o agente de novo. |
| Os acentos saem quebrados | Rode os scripts sempre com `python -X utf8`, como nos exemplos. |

Outros problemas, como token vencido ou imagem que não abre, estão na seção 10 do [AGENTS.md](../AGENTS.md).
