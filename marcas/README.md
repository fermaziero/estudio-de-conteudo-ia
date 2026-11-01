# Pasta marcas

Esta pasta guarda os dados de cada marca (pessoa ou negócio) que usa o Estúdio de Conteúdo com IA: quem você é, o tom de voz, as regras, o visual, as metas, os posts, as artes e as métricas. Cada marca fica na sua própria subpasta.

## O que entra no git e o que não entra

Esta pasta está no `.gitignore`. O git do projeto guarda só dois itens:

- este `README.md`;
- a marca fictícia `exemplo/`.

Todo o resto fica só no seu computador. Assim, dados de clientes, provas, estratégia e fotos não vão parar num repositório público por acidente. Atualizar o projeto com o git não mexe nas suas marcas.

## Como criar a sua marca

Peça ao seu agente de IA (Claude Code, Codex, Cursor ou outro): **"configurar minha marca"**. Ele vai fazer uma entrevista curta e criar a subpasta com o nome que você escolher. Esse nome usa só letras minúsculas, números e hífen, como `ana-souza`.

## Como é uma marca por dentro

```
marcas/ana-souza/
├── marca.md            quem você é, o que oferece, para quem, provas, tom de voz, temas, chamadas, links
├── regras.md           o que nunca prometer ou mostrar e quem pode ser citado
├── padrao-visual.md    regras visuais das artes, em palavras
├── visual.json         cores, logo, fontes e proporção, para o gerador de artes
├── estrategia.json     objetivo, pilares de conteúdo, ritmo e metas
├── feedback.md         tudo o que você pediu para ajustar, com a sua frase e a data
├── assets/             logo/, fotos/ e fontes/ (só o que você tem direito de usar)
├── referencias/        perfis de referência estudados
├── conteudo/           um lote de posts por pasta, com textos e artes
├── publicacao/         registro do que foi publicado
└── metricas/           números do perfil, painel e leituras de desempenho
```

As quatro últimas pastas aparecem quando as outras skills passam a usá-las.

## A marca de exemplo

`exemplo/` é uma marca fictícia ("Exemplo Contábil", um escritório de contabilidade que não existe). Serve para ver como uma marca configurada fica e para testar o fluxo inteiro sem usar dados seus. Tudo nela é inventado, inclusive números, links e pessoas. Não use para conteúdo real e não a edite: crie a sua.

## Guardar as suas marcas com segurança

Como esta pasta fica fora do git do projeto, cuide de uma cópia de segurança.

**Opção 1: cópia simples.** Copie a pasta da marca para um disco externo ou para uma nuvem pessoal de vez em quando.

**Opção 2: repositório privado.** Se você usa git, versione cada marca em um repositório **privado**, dentro da pasta dela. Assim você tem histórico de mudanças e cópia na nuvem.

1. No GitHub, GitLab ou outro serviço, crie um repositório vazio marcado como **privado**.
2. No terminal, entre na pasta da marca (não na pasta `marcas/` inteira) e rode:

```
cd marcas/ana-souza
git init
git add .
git commit -m "Primeira versão da marca"
git branch -M main
git remote add origin <endereço do seu repositório privado>
git push -u origin main
```

3. Antes do primeiro `git push`, confira no site do serviço que o repositório aparece como privado.

O git do projeto ignora tudo o que está dentro de `marcas/ana-souza/`, então os dois repositórios não se misturam. Artes e imagens geradas podem ficar pesadas; se quiser, ignore a pasta `conteudo/` no repositório da marca. Seu agente de IA pode fazer esses passos com você, mas é você quem confere se o repositório é privado.

## Credenciais nunca ficam aqui

Token do Instagram, chaves do armazenamento de imagens, senhas e qualquer outro segredo **não entram** nesta pasta, nem em arquivos `.env`, nem no chat com a IA. Eles ficam fora do projeto, em `~/.config/estudio-de-conteudo/<marca>/` (no Windows, `%USERPROFILE%\.config\estudio-de-conteudo\<marca>\`), e a skill `publicar-instagram` mostra como preenchê-los sem expor nada.

Para conferir se alguma pasta guarda um segredo esquecido:

```
python -X utf8 skills/configurar-marca/scripts/validar_marca.py --marca ana-souza --so segredos
python -X utf8 ferramentas/checar_segredos.py --tudo
```

## Privacidade e remoção

Os scripts do projeto não enviam o conteúdo desta pasta para lugar nenhum por conta própria. O agente de IA que você usa lê estes arquivos para trabalhar e processa o que você escreve no chat conforme a política de privacidade dele; vale conhecê-la antes de colocar dados de clientes. Para remover uma marca, apague a pasta dela. Não tem volta: se tiver dúvida, faça uma cópia antes.
