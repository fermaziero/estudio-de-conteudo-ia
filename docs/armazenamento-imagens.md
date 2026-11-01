# Armazenamento das imagens: criar o bucket, a URL pública e as chaves

Este guia mostra como preparar o lugar onde as imagens ficam por alguns minutos na hora de publicar. Usamos o **Cloudflare R2** como exemplo, e no fim há uma nota sobre outros serviços compatíveis com S3. Leva uns 20 minutos.

Conferido nas páginas oficiais da Cloudflare, da Meta e da AWS em **2026-10-28**. Os menus mudam com frequência: se uma tela estiver diferente, procure os termos em inglês em **negrito**.

## Por que isso é necessário

Para publicar uma imagem, a Meta não aceita o arquivo enviado direto pelo computador: ela baixa a imagem de um endereço da internet que qualquer pessoa consiga abrir. A documentação diz que a mídia precisa estar hospedada num servidor publicamente acessível no momento da tentativa e que a Meta busca o arquivo com cURL (um programa de download).

O Estúdio faz isto em cada publicação:

```
arte PNG -> JPEG -> sobe para o seu bucket -> testa a URL -> a Meta baixa -> publica -> o script apaga a imagem
```

- **Bucket**: uma "pasta na nuvem" do seu serviço de armazenamento.
- **URL pública**: o endereço pelo qual a Meta (e qualquer pessoa com o link) abre a imagem.
- **Chaves de acesso**: um par de códigos (Access Key ID e Secret Access Key) que permite ao script enviar e apagar arquivos naquele bucket. A chave secreta é segredo: nunca vai ao chat.

As imagens ficam no bucket só durante a publicação (alguns minutos). O nome de cada arquivo inclui um trecho aleatório (`ig/2026-11-05/<id-do-post>-<12 caracteres aleatórios>/01.jpg`), então o endereço não é adivinhável, e o script apaga tudo logo depois de confirmar a publicação. A regra de limpeza do passo 5 apaga o que sobrar.

> **Regra mais importante deste guia: use um bucket só para isto.** No Cloudflare R2, ligar a URL pública torna **o bucket inteiro** acessível pela internet: qualquer arquivo dele abre para quem souber o endereço exato. A Cloudflare não mostra a lista de arquivos de um bucket público, mas isso não protege nada: o arquivo abre se o nome for conhecido ou adivinhado. Por isso:
>
> 1. crie um bucket **novo e exclusivo** para o Estúdio, sem nenhum outro arquivo (nada de backups, documentos, contratos, fotos de clientes);
> 2. confira que ele está **vazio** antes de ligar a URL pública, e nunca guarde mais nada nele;
> 3. nunca aponte o Estúdio para um bucket que você já usa para outra coisa;
> 4. ligue a **regra de limpeza** do passo 5 e confira que ela funciona.

## Custos (Cloudflare R2)

Segundo a página de preços da Cloudflare, o armazenamento padrão tem uso gratuito de **10 GB-mês de armazenamento, 1 milhão de operações de escrita (classe A) e 10 milhões de operações de leitura (classe B) por mês**. A saída de dados (download) do R2 não é cobrada. Enviar um objeto é operação de classe A, ler é classe B, e **apagar é gratuito**. Um perfil que publica algumas vezes por semana fica muito abaixo desses limites. Passando deles, a cobrança é de US$ 0,015 por GB-mês, US$ 4,50 por milhão de operações A e US$ 0,36 por milhão de operações B.

A Cloudflare exige que você ative uma assinatura do R2 por um fluxo de pagamento ("checkout"); a documentação diz que o R2 é gratuito para começar, com uso mensal gratuito incluído, e não detalha a forma de pagamento. Pode ser que peçam um cartão. Confira os valores atuais em developers.cloudflare.com/r2/pricing antes de ativar.

## Passo 1: conta e R2

1. Crie uma conta em **dash.cloudflare.com**, se ainda não tiver.
2. No painel, abra **Storage & databases > R2 > Overview** e conclua o fluxo para **ativar o R2** (assinatura com uso gratuito incluído).

## Passo 2: criar o bucket (novo, exclusivo e vazio)

1. Em **R2 > Overview**, clique em **Create bucket**. **Crie um bucket novo**, só para o Estúdio. Não reaproveite um que já tenha arquivos.
2. Nome do bucket: só letras minúsculas (a-z), números e hífen; de 3 a 63 caracteres; sem começar nem terminar com hífen. Um nome que deixe claro o uso ajuda a não misturar: `minha-marca-midia-temporaria`.
3. Se a tela perguntar, deixe a localização em automático e a classe de armazenamento *Standard* (o uso gratuito vale só para a classe Standard).
4. Abra o bucket e confira, na aba de objetos, que ele está **vazio**. Só então siga para o passo 3.

## Passo 3: a URL pública

A Meta precisa conseguir abrir a imagem. Escolha **uma** das opções. As duas tornam **o bucket inteiro** público (por isso o bucket é exclusivo e está vazio, como pedido no passo 2).

### Opção A: domínio próprio (recomendada)

Use um endereço seu, como `midia.suaempresa.com.br`.

- Requisito: o domínio precisa estar cadastrado (como "zona") na mesma conta da Cloudflare. Se ele estiver em outro lugar, a documentação cita a configuração parcial por CNAME, que pode depender do plano contratado; para quem não tem conhecimento técnico, o caminho mais simples é pedir a quem cuida do seu site para apontar o domínio para a Cloudflare, ou usar a opção B só para começar.
- Passos: abra o bucket, vá em **Settings**, seção **Custom Domains**, clique em **Add**, digite o domínio (por exemplo `midia.suaempresa.com.br`), clique em **Continue** e depois em **Connect Domain**.
- O status passa de **Initializing** para **Active** em alguns minutos. Se não passar, use **Retry connection**.
- Use só caracteres ASCII no endereço (sem acento): a Meta avisa que URLs só com ASCII são as mais seguras.
- Não ative o acesso `r2.dev` junto, se quiser que só o domínio próprio funcione.

Na opção A, valem as proteções do seu domínio na Cloudflare (regras de firewall, cache, controle de acesso). Se alguma delas bloquear robôs, a Meta não consegue baixar a imagem: veja "Se a URL não abrir".

### Opção B: endereço `r2.dev` (para testar)

No bucket, em **Settings**, seção **Public Development URL**, clique em **Enable**, digite `allow` e confirme. A Cloudflare mostra uma URL no formato `https://pub-...r2.dev`.

Limites oficiais: a Cloudflare diz que esse endereço é **para desenvolvimento**, não para tráfego de produção, tem **limite de requisições** e não aceita cache, regras de firewall nem controle de acesso. Para testar o fluxo e para um perfil de pouco volume costuma bastar; se der falha de acesso ou lentidão, passe para a opção A.

Guarde a URL base (sem a barra final), por exemplo `https://midia.suaempresa.com.br`. Ela vai no campo "URL pública".

## Passo 4: criar as chaves de acesso

1. Em **Storage & databases > R2 > Overview**, ao lado de **API Tokens**, clique em **Manage**.
2. Clique em **Create Account API token** (ou **Create User API token**, que fica preso ao seu usuário).
3. Em **Permissions**, escolha **Object Read & Write**.
4. Marque **Apply to specific buckets only** e escolha só o bucket do passo 2. Assim a chave não alcança mais nada na sua conta.
5. Clique em **Create API Token**.
6. **Copie e guarde com cuidado** o **Access Key ID**, o **Secret Access Key** e o endereço do endpoint (`https://<ACCOUNT_ID>.r2.cloudflarestorage.com`). A chave secreta não pode ser vista de novo depois de fechar a tela.

Sobre apagar: a Cloudflare descreve "Object Read & Write" como ler, escrever e listar objetos nos buckets escolhidos e não cita o apagamento explicitamente. Um serviço de backup de terceiros (SimpleBackups) diz usar essa permissão para apagar objetos, mas a Cloudflare não confirma por escrito; o script tenta apagar e o teste do passo 6 mostra o resultado. Se o apagamento for negado, nada se perde: a regra do passo 5 faz a limpeza.

## Passo 5: regra de limpeza (obrigatória)

O script apaga cada imagem logo depois de publicar. Mas se a internet cair, o computador desligar ou a chave não tiver permissão para apagar, a imagem fica no bucket **com a URL pública ligada**. A regra de limpeza é o que garante que nada fique ali. **Não pule este passo.**

1. No bucket, abra **Settings > Object Lifecycle Rules** e clique em **Add rule**.
2. Ação: apagar os objetos depois de **1 dia**. Como o bucket é exclusivo, deixe o prefixo em branco para a regra valer para o bucket inteiro (assim, até um arquivo colocado ali por engano some). Se a tela exigir um prefixo, use `ig/`, que é onde o Estúdio grava.
3. Salve (**Save changes**) e volte à lista de regras para confirmar que a nova regra aparece como ativa.

A Cloudflare diz que os objetos costumam ser removidos em até 24 horas depois da data de expiração. Então um arquivo esquecido sai do bucket em no máximo cerca de dois dias.

**Confira de verdade:** depois de uns dois dias, abra o bucket. Ele precisa estar **vazio**. Se sobrou algum arquivo, a regra não está valendo: refaça este passo. O Estúdio não consegue checar isso por você, então acrescente ao seu calendário uma conferência do bucket uma vez por mês.

## Passo 6: gravar as chaves e testar

Na raiz do projeto:

```
python -X utf8 skills/publicar-instagram/scripts/credenciais.py configurar --marca <sua-marca>
```

Na janela que abrir, preencha o bloco "Armazenamento das imagens":

| Campo da janela | O que colocar | Exemplo fictício |
|---|---|---|
| Endereço (endpoint) | o endpoint do passo 4, sem o nome do bucket | `https://0123456789abcdef.r2.cloudflarestorage.com` |
| Região | `auto` | `auto` |
| Nome do bucket | o nome do passo 2 | `minha-marca-midia` |
| Access Key ID | do passo 4 | `a1b2c3...` |
| Secret Access Key | do passo 4 (campo oculto) | (segredo) |
| URL pública | a URL do passo 3, sem barra no final | `https://midia.suaempresa.com.br` |

Em seguida rode a prova completa. Ela envia uma imagem neutra, abre a URL como navegador e como o robô de prévia da Meta, cria um contêiner na Meta **sem publicar** e apaga a imagem:

```
python -X utf8 skills/publicar-instagram/scripts/credenciais.py verificar --marca <sua-marca> --completo
```

Resultado esperado: `OK: a URL pública abre como JPEG...`, `OK: a Meta baixou a imagem...` e `Imagem de teste apagada; a URL agora responde 404` (ou 403).

Os seis valores ficam em `~/.config/estudio-de-conteudo/<marca>/armazenamento.env` (no Windows, `%USERPROFILE%\.config\estudio-de-conteudo\<marca>\armazenamento.env`), fora do projeto: `ARMAZENAMENTO_ENDPOINT`, `ARMAZENAMENTO_REGIAO`, `ARMAZENAMENTO_BUCKET`, `ARMAZENAMENTO_CHAVE_ID`, `ARMAZENAMENTO_CHAVE_SECRETA` e `ARMAZENAMENTO_URL_PUBLICA`.

## Se a URL não abrir

O teste do robô da Meta usa o identificador `facebookexternalhit/1.1`, um dos robôs de prévia que a Meta lista oficialmente. A documentação de publicação diz apenas que a Meta busca a imagem com cURL e não informa o identificador exato, então o teste é uma boa aproximação, não uma garantia.

| O que o teste mostra | Causa provável | O que fazer |
|---|---|---|
| `facebookexternalhit: HTTP 403` e o navegador abre | Alguma proteção do domínio bloqueia robôs | No painel do domínio na Cloudflare, olhe regras de firewall (WAF), modo de proteção contra bots e proteção contra uso das imagens em outros sites. Crie uma exceção para o caminho `/ig/*`. Na opção B (`r2.dev`) essas regras não existem. |
| `HTTP 404` logo depois do envio | URL pública não corresponde ao bucket | Confira se o domínio está **Active** e aponta para este bucket, e se a URL base não tem pasta no final. |
| Falhas ou lentidão intermitentes na opção B | Limite de requisições do `r2.dev` | Passe para a opção A. |
| `TimeoutError` em uma das leituras | A borda às vezes trava uma leitura por dezenas de segundos | O script já tenta 3 vezes, cada uma com conexão nova. Se falhar sempre, rode de novo mais tarde. |
| A imagem continua abrindo depois de apagada | Cache no domínio | O script envia `Cache-Control: no-store`. Se você criou uma regra de "Cache Everything", exclua o caminho `/ig/*` dela. |
| Erro `SignatureDoesNotMatch` ao enviar | Chave secreta, região ou relógio do computador errados | Refaça o passo 4 e confira que o relógio do computador está certo. |
| Erro `AccessDenied` | A chave não é "Object Read & Write" ou não vale para este bucket | Crie outra chave no passo 4. |
| Erro `NoSuchBucket` | Nome do bucket ou endpoint errado | Confira o nome do passo 2 e o endpoint (sem o bucket no final). |

## Outros serviços compatíveis com S3

O script fala o padrão S3: envia com `PUT` e apaga com `DELETE` por **URL pré-assinada** (assinatura AWS Signature V4 na própria URL), no estilo de caminho `https://<endpoint>/<bucket>/<arquivo>`. Em teoria qualquer serviço que aceite isso serve. O único que este projeto documenta passo a passo é o R2; os demais não foram testados aqui.

| Serviço | Endpoint (exemplo) | Região | URL pública |
|---|---|---|---|
| Cloudflare R2 | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` | `auto` | domínio próprio ou `r2.dev` (o bucket inteiro fica público: use um bucket exclusivo) |
| Amazon S3 | `https://s3.<região>.amazonaws.com` | a região real, como `us-east-1` | `https://<bucket>.s3.<região>.amazonaws.com`, exige liberar leitura pública só do prefixo `ig/` |
| Backblaze B2 | `https://s3.<região>.backblazeb2.com` | a região da conta, como `us-west-004` | URL pública do bucket |

Cuidados:

- Na AWS, a documentação diz que o estilo de caminho continua aceito em todas as regiões, com o aviso de que pode ser descontinuado no futuro. Se o seu serviço só aceitar o estilo com o bucket no domínio, o script não funciona com ele.
- Na Backblaze, um texto da documentação diz que o envio por URL pré-assinada deve ser gerado por SDK compatível, e relatos antigos falam em incompatibilidades. Teste com `verificar --completo` antes de confiar.
- No R2, a URL pública vale para o bucket inteiro: use um bucket exclusivo, vazio e com a regra de limpeza. Em serviços que deixam liberar a leitura só de um prefixo (como o S3, com uma política por prefixo), libere **apenas** `ig/` e mantenha o resto privado. Nunca abra um bucket que guarde outros arquivos.
- Escolha sempre uma URL pública com `https://`.

## Fontes consultadas (todas em 2026-10-28)

- Meta, Content Publishing (mídia em servidor público; Meta busca com cURL; só JPEG): https://developers.facebook.com/documentation/instagram-platform/content-publishing
- Meta, IG User Media (JPEG até 8 MB, proporção, URLs só com ASCII): https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-user/media
- Meta, Web Crawlers (`facebookexternalhit/1.1`): https://developers.facebook.com/docs/sharing/webmasters/web-crawlers
- Cloudflare R2, Public buckets (domínio próprio e `r2.dev`, limites): https://developers.cloudflare.com/r2/buckets/public-buckets
- Cloudflare R2, API tokens (Object Read & Write, escopo por bucket): https://developers.cloudflare.com/r2/api/tokens
- Cloudflare R2, S3 API com tokens (endpoint, região `auto`): https://developers.cloudflare.com/r2/get-started/s3
- Cloudflare R2, Presigned URLs (SigV4, GET/HEAD/PUT/DELETE, não valem em domínio próprio): https://developers.cloudflare.com/r2/api/s3/presigned-urls
- Cloudflare R2, Object lifecycles: https://developers.cloudflare.com/r2/buckets/object-lifecycles
- Cloudflare R2, Create buckets (regras de nome): https://developers.cloudflare.com/r2/buckets/create-buckets
- Cloudflare R2, Pricing: https://developers.cloudflare.com/r2/pricing
- AWS, Virtual hosting of general purpose buckets: https://docs.aws.amazon.com/AmazonS3/latest/userguide/VirtualHosting.html
- Backblaze, Introduction to the S3-Compatible API: https://backblaze.com/apidocs/introduction-to-the-s3-compatible-api
