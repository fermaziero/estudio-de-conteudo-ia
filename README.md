# Estúdio de Conteúdo com IA

Skills e scripts para criar conteúdo para o Instagram do começo ao fim. **Skill** é um roteiro de trabalho que o seu agente de IA (o assistente com quem você conversa, como o Claude Code ou o Codex) lê e segue. Você conversa em português; a IA prepara; **você decide e aprova**.

## O que dá para fazer

- Montar a ficha da sua marca (quem você é, tom de voz, regras, visual, metas) numa entrevista guiada.
- Estudar perfis de referência no Instagram, só lendo, e comparar com o seu.
- Planejar as pautas da semana e o calendário.
- Escrever carrosséis, posts únicos e roteiros de reel, com legenda e chamada para ação.
- Passar o texto por uma revisão independente: fatos, clareza, português, regras da marca e dados sensíveis.
- Gerar as artes com as suas cores, a sua fonte e o seu logo, com o texto desenhado pelo código.
- Publicar ou agendar no feed (carrossel e imagem única; reel fica só como roteiro).
- Acompanhar os resultados: painel, leitura do que funcionou, check-in e ajuste de metas.

**A aprovação final é sua.** O agente prepara o post, mas não consegue aprová-lo sozinho: a aprovação só vale com uma assinatura que o programa grava depois que você confirma, post a post, numa janela que abre no seu computador. Editar o arquivo do post à mão não aprova nada.

## O que você precisa

| Item | Para quê |
|---|---|
| Um computador com Windows, macOS ou Linux | O guia passo a passo cobre Windows e macOS |
| Um agente de IA que leia o `AGENTS.md`: Claude Code, Codex, Cursor, Gemini CLI e outros | É com ele que você conversa. Em geral exige uma conta, e alguns pedem plano pago: veja [docs/primeiros-passos.md](docs/primeiros-passos.md) |
| Python 3.10 ou mais novo | Roda os scripts do estúdio |
| Pillow (biblioteca de imagens do Python) | Desenha as artes. Instala com um comando, no passo 4 abaixo |
| Conta **profissional** do Instagram, um app na Meta e um bucket de imagens | Só para publicar e ler os números. Guias: [docs/instagram-api.md](docs/instagram-api.md) e [docs/armazenamento-imagens.md](docs/armazenamento-imagens.md) |
| Um navegador (de preferência o Chrome) com o Instagram aberto e logado | Só para pesquisar perfis de referência. O agente precisa de uma ferramenta que controle o navegador; o `AGENTS.md` explica |

**Publicar é a única parte que dá trabalho para configurar.** Criar o app na Meta e o *bucket* (a "pasta na nuvem" onde as imagens ficam por alguns minutos na hora de publicar) leva cerca de 1 hora na primeira vez: 30 a 40 minutos o guia do Instagram, uns 20 minutos o do armazenamento. O serviço de armazenamento pode pedir um cartão para ativar a conta; o guia tem uma seção sobre custos. **O resto do kit funciona sem isso.**

## Comece em 5 passos

1. **Instale o Python e um agente de IA.** O guia para quem nunca fez isso, no Windows e no macOS, está em [docs/primeiros-passos.md](docs/primeiros-passos.md).
2. **Baixe o projeto.** Na página dele no GitHub, clique em **Code** e em **Download ZIP**, e extraia a pasta. Quem usa git pode fazer `git clone`.
3. **Abra a pasta no seu agente de IA.** Tem de ser a pasta que contém `skills/` e `marcas/`.
4. **Instale o Pillow.** Peça ao agente ("instale o que falta para o estúdio funcionar") ou rode `python -m pip install -r requirements.txt` (no macOS e no Linux, `python3 -m pip install -r requirements.txt`). Se o pip recusar com "externally-managed-environment" (Python do Debian, Ubuntu ou Homebrew), crie um ambiente virtual: veja [docs/primeiros-passos.md](docs/primeiros-passos.md).
5. **Diga: "Quero configurar minha marca."** O agente faz perguntas curtas, no máximo 3 por vez, e grava a sua ficha em `marcas/<seu-nome>/`. Antes, se quiser ver como fica, peça: "Mostre a marca de exemplo".

Depois, é só conversar: "O que eu posto essa semana?", "Escreve o carrossel da pauta 2", "Gera as artes", "Como estão meus resultados?".

## O que cada skill faz

| Skill | Em uma linha |
|---|---|
| `configurar-marca` | Entrevista você e monta a ficha da marca (texto, regras, visual, metas); registra todo feedback para não repetir o erro |
| `pesquisar-referencias` | Analisa perfis de Instagram que são referência no seu assunto, só lendo, e guarda o que aprendeu |
| `planejar-conteudo` | Propõe as pautas e o calendário, com base na marca, nas referências e nos resultados |
| `criar-conteudo` | Escreve os posts das pautas que você aprovou, texto primeiro |
| `revisar-conteudo` | Faz uma revisão independente do texto antes de você aprovar |
| `gerar-artes` | Desenha as artes (PNG) na identidade da marca e abre uma galeria para você aprovar |
| `publicar-instagram` | Conecta a conta, publica ou agenda com o seu ok registrado, confere o resultado e coleta os números |
| `acompanhar-resultados` | Monta o painel, explica o que funcionou, faz o check-in e propõe ajustes de metas |

## Privacidade e segurança

- **Seus arquivos ficam no seu computador.** Tudo da sua marca fica em `marcas/`, pasta que o git do projeto ignora (só o `README.md` dela e a marca fictícia `exemplo` são versionados). Atualizar o projeto não mexe nas suas marcas. Faça cópia de segurança dessa pasta (veja [marcas/README.md](marcas/README.md)). Só na hora de publicar, as imagens do post sobem por alguns minutos para o armazenamento que você configurou ([docs/armazenamento-imagens.md](docs/armazenamento-imagens.md)).
- **Credenciais ficam fora do projeto,** em `~/.config/estudio-de-conteudo/<marca>/` (no Windows, `%USERPROFILE%\.config\estudio-de-conteudo\<marca>\`). O token do Instagram é colado só numa janela que o comando abre no seu computador, nunca no chat. Se você colar um token no chat sem querer, trate-o como vazado e gere outro.
- **A aprovação final pede a sua confirmação, no seu computador.** Para publicar, você diz "pode publicar" e o código do post, depois de ver as artes e a legenda finais. Aí o agente roda o comando de aprovação, e abre no seu computador uma janela com o resumo do post: a aprovação só é gravada se você clicar em **Aprovar** (sem janela, o comando pede que você digite o código do post num terminal; se o agente não tiver terminal interativo, ele pede que você rode o comando). Nenhuma opção pula essa confirmação, e o mesmo vale para publicar de novo um post que já está no ar. Depois do clique, o programa **assina** a aprovação com uma chave secreta que cria na primeira vez e guarda fora do projeto (`aprovacao.key`, na mesma pasta das credenciais). Sem assinatura válida, o post vale como não aprovado, então editar o arquivo do post à mão não aprova nada. A regra proíbe o agente de abrir ou copiar essa chave, que vale como uma credencial. Se a chave sumir (um computador novo, por exemplo), as aprovações antigas perdem a validade e você aprova de novo; posts já publicados não mudam. **Limite honesto:** quem controla o computador inteiro (um agente que clica na janela ou lê a chave) ainda poderia contornar tudo isso, e as regras do projeto proíbem. Por isso, se o seu agente controla a tela, não deixe que ele clique por você. Mudou algo depois? O ok perde a validade.
- **A IA que você usa lê os seus arquivos.** Ela processa o que você escreve conforme a política de privacidade do serviço dela; vale conhecer essa política antes de colocar dados de clientes. Dados de terceiros (clientes, alunos, menores) só entram com a autorização registrada em `regras.md`, em linha com a LGPD, a lei brasileira de proteção de dados pessoais.
- **A pesquisa de referências só lê o Instagram,** no seu navegador: não curte, não segue, não comenta. A Meta proíbe coleta automatizada sem permissão escrita dela, e o Instagram pode limitar a sua conta; a skill avisa antes de começar e só segue com o seu ok.
- **Fotos e logos:** só os que você tem direito de usar. Posts de referência servem de inspiração para o mecanismo, nunca para copiar texto ou imagem.
- **Antes de compartilhar o projeto,** rode `python -X utf8 ferramentas/checar_segredos.py`. Ele procura tokens, senhas e dados pessoais esquecidos. A cada envio ao repositório, uma verificação automática (`.github/workflows/verificar.yml`) roda no Windows, no macOS e no Linux, com Python 3.10 e 3.13: confere os atalhos das skills, procura segredos, valida o exemplo e roda os autotestes.
- **Achou uma falha de segurança?** Relate pelo caminho descrito em [SECURITY.md](SECURITY.md), sem expor os detalhes em público.

## Estrutura

```
estudio-de-conteudo-ia/
├── AGENTS.md      manual do agente de IA (vale para qualquer agente)
├── CLAUDE.md      complemento para o Claude Code
├── SECURITY.md    como relatar uma falha e como o projeto se protege
├── docs/          guias passo a passo e o contrato entre as skills
├── skills/        as 8 skills (SKILL.md, scripts, referências e modelos)
├── ferramentas/   sincronizar atalhos das skills e checar segredos
├── .github/       verificação automática (workflows/verificar.yml)
└── marcas/        os seus dados (fora do git) e a marca de exemplo
```

As pastas `.claude/skills/` e `.agents/skills/` guardam atalhos gerados para o Claude Code e o Codex acharem as skills; não edite à mão.

## Documentação

- [docs/primeiros-passos.md](docs/primeiros-passos.md): instalar tudo e fazer a primeira conversa.
- [docs/instagram-api.md](docs/instagram-api.md): conectar o Instagram (só para publicar e coletar números).
- [docs/armazenamento-imagens.md](docs/armazenamento-imagens.md): o lugar onde as imagens ficam por alguns minutos na hora de publicar (use um bucket novo, só para isso).
- [docs/arquitetura.md](docs/arquitetura.md): o contrato entre as skills (pastas, formatos, regras).
- [AGENTS.md](AGENTS.md): o manual que o agente de IA segue.

## Atualizar o projeto

Com `git clone`: `git pull` na pasta do projeto. Com o ZIP: baixe o novo, extraia em outra pasta e copie para lá a sua pasta `marcas/<seu-nome>`.

Se você instalou a rotina de agendamento, ela guarda o caminho completo da pasta velha e continua rodando de lá. Na pasta antiga, rode `python -X utf8 skills/publicar-instagram/scripts/rotina.py remover --marca <seu-nome>` e, na nova, `python -X utf8 skills/publicar-instagram/scripts/rotina.py instalar --marca <seu-nome>` (no macOS e no Linux, `python3`). Quem roda esses dois comandos é você, não o agente.

## Créditos

Criado por Fernando Maziero para os mentorados da Mentoria 1Advisor.

## Licença

O código do projeto é [MIT](LICENSE). **Exceção:** as fontes em `skills/gerar-artes/fontes/` (Manrope) têm licença própria, a SIL Open Font License 1.1 (OFL), e não a MIT; veja [skills/gerar-artes/fontes/LEIA-ME.md](skills/gerar-artes/fontes/LEIA-ME.md). Os nomes de produtos citados (Instagram, Meta, Claude, Codex, Cursor, Gemini e outros) pertencem aos seus respectivos donos; este projeto é independente e não tem vínculo com eles.
