# Conectar o Instagram: passo a passo

Este guia leva de 30 a 40 minutos na primeira vez. No fim você terá um **token de acesso**: uma "senha de máquina" que deixa o Estúdio de Conteúdo publicar no seu Instagram e ler os números dos posts, e nada além disso.

Conferido na documentação oficial da Meta em **2026-10-28**. O painel da Meta muda de nome e de lugar com frequência. Se uma tela estiver diferente, procure pelos termos em inglês que aparecem em **negrito** abaixo.

## Palavras que aparecem aqui

- **API**: a "porta oficial" que a Meta (dona do Instagram) abre para programas conversarem com o Instagram.
- **App da Meta**: um cadastro, no site de desenvolvedores da Meta, que representa o Estúdio de Conteúdo. Sem ele a Meta não deixa nenhum programa publicar.
- **Token de acesso**: um texto longo que começa com `IG`. Quem tem o token age como o app na sua conta. Por isso ele é secreto.
- **Conta profissional**: conta do Instagram do tipo *Empresa* (Business) ou *Criador de conteúdo* (Creator). Conta pessoal não funciona.

## Regras de segurança (leia antes)

1. **O token nunca vai no chat**, nem para o agente de IA, nem em e-mail, print ou commit. Você cola o token só na janela que o script `credenciais.py configurar` abre no seu computador.
2. Se você colou o token no chat sem querer, trate como vazado: gere outro (passo 5) e remova o app da conta (veja "E se o token vazou?").
3. O token vale **60 dias** e pode ser renovado. Veja "Renovar o token".

## O que você precisa ter

- A conta do Instagram da marca e a senha dela.
- Um navegador no computador.
- Uma conta da Meta para desenvolvedores. O cadastro é feito em **developers.facebook.com**; a documentação de criação do app parte do princípio de que você já o concluiu. A documentação que consultei não menciona cobrança para criar o app nem para usar a API de publicação.

## Passo 1: deixar a conta do Instagram como profissional

Se a conta já é *Empresa* ou *Criador*, pule para o passo 2.

No app do Instagram: **Mais > Configurações e atividade > Tipo de conta e ferramentas > Mudar para conta profissional**. Escolha *Criador* ou *Empresa* e siga as telas.

Atenção: se a conta estiver privada, ao virar profissional ela passa a ser **pública** (a ajuda do Instagram avisa isso). A documentação da Meta também pede conta pública para o teste do app.

Fonte: Central de Ajuda do Instagram, "Set up a professional Instagram account" (help.instagram.com/502981923235522), conferida em 2026-10-28.

## Passo 2: criar o app na Meta

1. Entre em **developers.facebook.com** com a sua conta da Meta e abra **My Apps** (Meus apps).
2. Clique em **Create App** (Criar app).
3. Em *Connect a business* (conectar uma empresa) você pode pular por enquanto.
4. Em *use case* (caso de uso), escolha **Other** (Outro). Em *app type* (tipo de app), escolha **Business** (Empresa). O tipo Business é obrigatório para usar o Instagram.
5. Dê um nome ao app (por exemplo, "Estudio de Conteudo") e informe um e-mail de contato. Clique em **Create app**.
6. No painel do app, role até **Instagram** e clique em **Set up** (Configurar).
7. Aparece **API setup with Instagram login** (API do Instagram com login do Instagram). É essa que usamos. **Não** use a opção "com login do Facebook".

Se o painel oferecer o caso de uso **Manage messaging & content on Instagram** (Gerenciar mensagens e conteúdo no Instagram), ele também serve: abra **Customize the use case** e escolha a configuração **API setup with Instagram login**. Cada app aceita um só tipo de login.

Você pode ter até 15 apps sem uma empresa verificada. Um só app pode servir várias marcas suas (adicione cada conta do Instagram no passo 4), mas cada marca tem o seu próprio token.

Fontes: Meta for Developers, "Creating a Meta App for the Instagram Platform" e "Customize the Manage messaging and content on Instagram Use Case", conferidas em 2026-10-28.

## Passo 3: conferir as permissões

O app precisa destas permissões. A tabela mostra para que cada uma serve.

| Permissão | Para que serve aqui | Obrigatória? |
|---|---|---|
| `instagram_business_basic` | ler a conta e renovar o token | sim |
| `instagram_business_content_publish` | publicar carrosséis e imagens | sim, para publicar |
| `instagram_business_manage_insights` | ler alcance, salvamentos e compartilhamentos | só para as métricas |

No painel, olhe a lista de permissões do caso de uso (ou do produto Instagram) e **adicione as que faltarem** antes de gerar o token. O token é gerado com as permissões que existem naquele momento: se você adicionar uma permissão depois, gere o token de novo.

Você não precisa pedir "App Review" (análise do app) nem "Advanced Access" para usar só as suas contas. A Meta diz que o acesso padrão (*Standard Access*) basta quando o app atende contas que você possui ou administra e adicionou ao app. A análise só é exigida para atender contas de terceiros. Mantenha o app em modo de desenvolvimento.

Fonte: Meta for Developers, "Instagram Platform Overview" (níveis de acesso) e "Instagram API with Instagram Login: Migration Guide", conferidas em 2026-10-28.

## Passo 4: adicionar a sua conta ao app

No painel, abra **Instagram > API setup with Instagram login**. Na seção **Generate access tokens** (Gerar tokens de acesso):

1. Clique em **Add account** (Adicionar conta).
2. Entre na conta do Instagram da marca quando a janela pedir e conclua.

Se a Meta pedir um convite de testador (**Instagram Tester**):

1. No painel, abra **App Roles > Roles** (Funções do app > Funções), seção **Instagram Testers**, clique em **Add** e digite o nome de usuário do Instagram.
2. Aceite o convite no Instagram pelo navegador (instagram.com): **Configurações > Permissões do site > Apps e sites > Tester Invites** (Convites de testador). A conta aparece na tabela do painel depois do aceite.

Dá para adicionar até 50 contas. "Test users" (usuários de teste) não funcionam: tem que ser uma conta de Instagram de verdade.

Fonte: Meta for Developers, "Instagram API with Instagram Login: Migration Guide" (passo 2) e "Creating a Meta App for the Instagram Platform" (passo 7), conferidas em 2026-10-28. O nome exato dos menus em português pode variar.

## Passo 5: gerar o token

1. Na mesma tela (**API setup with Instagram login**), clique em **Generate token** (Gerar token) ao lado da sua conta.
2. Entre no Instagram se pedir.
3. **Copie o token** (Ctrl+C). Ele aparece **uma única vez**: se fechar a tela sem copiar, gere outro.

O token gerado no painel é de **longa duração: vale 60 dias**. (Os tokens do fluxo de login para usuários de um app valem só 1 hora; não são esses.)

Fontes: Meta for Developers, "Get started" do Instagram API with Instagram Login (validade) e "Migration Guide" (o token aparece uma só vez), conferidas em 2026-10-28.

## Passo 6: guardar o token sem passar pelo chat

Na raiz do projeto, peça ao agente para rodar (ou rode você):

```
python -X utf8 skills/publicar-instagram/scripts/credenciais.py configurar --marca <sua-marca>
```

Uma janela abre no seu computador (o comando fica esperando até você salvar). Cole o token no campo "Token de acesso do Instagram", confira a data em "Token gerado em" (deixe a de hoje se acabou de gerar) e clique em **Salvar**. Na mesma janela ficam os dados do armazenamento de imagens; veja `docs/armazenamento-imagens.md`.

O token é gravado em `~/.config/estudio-de-conteudo/<marca>/instagram.env` (no Windows, `%USERPROFILE%\.config\estudio-de-conteudo\<marca>\`), fora do projeto e com acesso só para o seu usuário.

Se a janela não abrir (computador sem tela ou sem o recurso gráfico do Python), rode o mesmo comando com `--modelo`: ele cria os arquivos vazios e mostra o caminho. Abra num editor de texto (Bloco de Notas, TextEdit), cole o valor depois de `IG_ACCESS_TOKEN=`, preencha `IG_TOKEN_VALIDO_ATE=` com a data de hoje mais 60 dias (AAAA-MM-DD) e salve. Sem essa data o `verificar` avisa, e a renovação automática só passa a funcionar depois do primeiro `credenciais.py renovar` (que descobre e grava a data certa).

## Passo 7: conferir

Antes, abra `marcas/<sua-marca>/visual.json` e confira que o campo `"arroba"` tem a conta desta marca (por exemplo, `"@seuperfil"`). Ela é a trava que impede de publicar com o token de outra marca: **sem a `arroba`, o `verificar` aponta problema e a skill se recusa a publicar.** O valor de exemplo `@perfil` não vale.

```
python -X utf8 skills/publicar-instagram/scripts/credenciais.py verificar --marca <sua-marca>
```

Você deve ver a conta (`@seuperfil`), a validade estimada do token, `Publicar ... OK` com a cota usada nas últimas 24 horas e a linha das métricas. Se aparecer `FALTA a permissão no token`, volte ao passo 3 e gere o token de novo.

Depois de configurar o armazenamento, rode a prova completa (nada é publicado):

```
python -X utf8 skills/publicar-instagram/scripts/credenciais.py verificar --marca <sua-marca> --completo
```

## Renovar o token

- O token precisa ser renovado antes de **60 dias**. A renovação exige que ele tenha **mais de 24 horas** e **não tenha vencido**. Cada renovação vale mais 60 dias. Token que passa 60 dias sem renovar vence de vez e você precisa repetir o passo 5.
- Manual: `python -X utf8 skills/publicar-instagram/scripts/credenciais.py renovar --marca <sua-marca>`.
- Automático: a rotina de agendamento e de métricas (`rotina.py`) renova sozinha quando faltam 10 dias ou menos, e registra no log.
- A data guardada em `IG_TOKEN_VALIDO_ATE` é estimada. Quem manda é a Meta: se ela responder que o token venceu, gere outro.

Fontes: Meta for Developers, "Refresh Access Token" e "Business Login for Instagram" (tokens de longa duração), conferidas em 2026-10-28.

## E se o token vazou?

A documentação da Meta que consultei não descreve um comando para cancelar um token. Faça o seguinte:

1. No Instagram pelo navegador: **Configurações > Permissões do site > Apps e sites > Ativos**, e clique em **Remover** ao lado do seu app. A ajuda do Instagram diz que o app removido só acessa informações públicas.
2. Na Meta, gere um token novo (passo 5) e grave com `credenciais.py configurar`. Se o susto foi grande, apague o app e crie outro.
3. Se o vazamento envolveu a senha do Instagram, troque a senha.

Fonte: Central de Ajuda do Instagram, "Manage the privacy settings for apps and websites that you've logged into or connected on Instagram", conferida em 2026-10-28.

## Problemas comuns

| O que aparece | O que fazer |
|---|---|
| `O token do Instagram venceu ou é inválido` (erro 190) | Gere outro token (passo 5) e rode `configurar`. |
| `FALTA a permissão no token` (erro 10 ou 200 a 299) | Adicione a permissão no painel (passo 3) e gere o token de novo. |
| O botão **Generate token** não aparece ou dá erro | Confirme que a conta é profissional e pública (passo 1) e que foi adicionada (passo 4). |
| Token começa com `EA` | É token do login do Facebook. Esta skill usa o login do Instagram: gere o token em **API setup with Instagram login**. |
| Erro 4, 17, 32, 613 ou 80002 | Excesso de chamadas à Meta. Espere e rode de novo mais tarde. |
| `Limite diário de publicações` (erro 9, subcódigo 2207042) | A conta atingiu o limite de publicações pela API em 24 horas. Tente amanhã. |
| A conta do token é diferente da marca | O `verificar` avisa. Gere o token logado na conta certa. |

Mais códigos de erro estão em `skills/publicar-instagram/referencias/erros-comuns.md`.

## O que este guia não cobre

- Contas de **clientes ou de terceiros**: exigem Advanced Access, App Review e verificação da empresa. Fora do escopo.
- **Reels e Stories**: esta versão publica só carrossel e imagem única no feed.
- Publicar o app (modo ativo): não é necessário para usar só as suas contas.

## Fontes consultadas (todas em 2026-10-28)

- Instagram Platform Overview: https://developers.facebook.com/documentation/instagram-platform/overview
- Create a Meta App for the Instagram Platform: https://developers.facebook.com/documentation/development/create-an-app/other-app-types/instagram-apis
- Customize the Manage messaging and content on Instagram Use Case: https://developers.facebook.com/documentation/development/create-an-app/instagram-use-case
- Instagram API with Instagram Login, Get started: https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/get-started
- Instagram API with Instagram Login, Migration Guide: https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/migration-guide
- Business Login for Instagram: https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/business-login
- Refresh Access Token: https://developers.facebook.com/documentation/instagram-platform/reference/refresh_access_token
- Ajuda do Instagram: https://help.instagram.com/502981923235522 e https://help.instagram.com/1144624522593085
