# Segurança

## Como relatar um problema

Achou uma falha que pode expor credenciais, publicar sem aprovação ou apagar arquivos? Não abra uma issue pública com os detalhes.

1. Use o relato privado do GitHub, na aba **Security** do repositório, em **Report a vulnerability**, se estiver ativado.
2. Se não estiver, abra uma issue curta pedindo um contato privado, sem descrever a falha.

Inclua: o que acontece, como reproduzir com dados fictícios e qual versão (commit) você usa. Nunca mande token, chave ou dado de cliente, nem para mostrar o problema.

## Como o projeto se protege

- **Credenciais fora do projeto.** Token e chaves ficam em `~/.config/estudio-de-conteudo/<marca>/`, gravados por uma janela local do `credenciais.py configurar`. Os scripts não imprimem segredos, e as mensagens de erro passam por um filtro que mascara tokens.
- **Aprovação com confirmação local e assinatura.** O agente de IA prepara o post, mas a aprovação final só é gravada depois de a pessoa confirmar numa janela do próprio computador (ou digitando o código do post num terminal). O `aprovar` assina a aprovação com uma chave secreta guardada fora do projeto; sem assinatura válida, o post é tratado como não aprovado, então editar o arquivo do post à mão não aprova nada. A aprovação vale só para aquela versão: qualquer mudança no texto ou nas artes invalida o ok.
- **Limite honesto.** Um programa com controle total do computador ainda poderia contornar essas travas, por exemplo lendo a chave. As regras do projeto proíbem o agente de fazer isso; mantenha o agente com permissões normais, que pedem a sua confirmação antes de rodar comandos.
- **Travas contra duplicidade.** O publicador não publica o mesmo post duas vezes, e uma publicação sem resposta clara bloqueia novas tentativas até a conferência.
- **Só APIs oficiais.** A publicação usa a API oficial do Instagram, e as imagens vão para um armazenamento compatível com S3 por URL assinada. A pesquisa de referências só lê páginas públicas, no navegador da própria pessoa, e avisa sobre os termos da Meta antes de começar.
- **Dados da marca fora do git.** A pasta `marcas/` não é versionada, exceto a marca fictícia `exemplo`.
- **Checagem antes de compartilhar.** `python -X utf8 ferramentas/checar_segredos.py` procura tokens, chaves, CPF, CNPJ e caminhos pessoais nos arquivos que o git vai versionar. A verificação automática do repositório roda o mesmo teste a cada envio.

## Se um token vazou

Trate como comprometido: revogue o acesso do app no Instagram, gere um token novo e grave só pela janela do `credenciais.py configurar`. O passo a passo está em [docs/instagram-api.md](docs/instagram-api.md). Chave do armazenamento: troque no painel do serviço ([docs/armazenamento-imagens.md](docs/armazenamento-imagens.md)).
