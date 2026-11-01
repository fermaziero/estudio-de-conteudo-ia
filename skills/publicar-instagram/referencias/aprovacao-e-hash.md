# Aprovação, hash e status

A regra de ouro do estúdio é que **a pessoa aprova e a IA prepara**. Esta página explica como a aprovação fica registrada de um jeito que não dá para burlar sem querer: ela vale para **uma versão** de **um post**, qualquer mudança a cancela, e ela só vale se estiver **assinada** pelo comando `aprovar`, depois do clique da pessoa.

## O que a pessoa precisa dizer

Algo claro como **"pode publicar `<id>`"**, com o id do post (ou, no mínimo, uma frase que cite o id). O script `aprovar` recusa:

- frase com menos de 8 caracteres;
- frase que não cita o id do post;
- `--por` vazio.

O agente grava a frase **literal**, do jeito que a pessoa escreveu (`--frase`), e o nome dela (`--por`). Ele nunca escreve a frase por conta própria, nunca aproveita um "ok" dado a outro post e nunca aprova vários posts com uma só frase. Um "pode seguir" genérico, uma aprovação em outra ferramenta ou um comentário não valem.

## A confirmação na janela (barreira humana)

A frase vai pela linha de comando, e quem roda o comando é o agente. Por isso a frase sozinha **não basta**: nada distinguiria a pessoa de um agente que escreveu a frase. O `aprovar` só grava depois de uma confirmação que o agente não consegue dar:

1. **Janela local.** O comando abre uma janela no computador da pessoa com: marca, id do post, título interno, formato e número de artes, **início da legenda**, o agendamento (se houver), a versão (começo do hash), quem aprova e **a frase que o agente registrou**. Há dois botões, **Aprovar** e **Cancelar**; o foco inicial é o Cancelar, Enter não aprova, e a janela se fecha sozinha, sem gravar nada, em 5 minutos.
2. **Sem janela** (computador sem tela ou sem o recurso gráfico do Python): se existir um **terminal interativo de verdade**, o comando mostra o mesmo resumo e pede que a pessoa digite o id do post. Qualquer outra resposta cancela.
3. **Sem janela e sem terminal interativo** (é o caso de um agente rodando comandos por conta própria): o comando **recusa** com "rode este comando você mesma, num terminal". Nada é gravado.

Não existe opção de linha de comando, variável de ambiente ou arquivo de configuração que pule essa confirmação. Os testes automáticos trocam a função de confirmação **dentro do próprio processo de teste**, e só ali. O agente prepara o comando e avisa a pessoa; **quem confirma é ela**, e ele nunca clica por ela.

A mesma confirmação vale para duas ações que podem duplicar um post: `publicar --de-novo` (mostra o link do post que já está no ar) e `conferir --confirmo-que-nao-foi-ao-ar` (pergunta se ela abriu o feed e o post não está lá). A rotina `agendados` não pede confirmação: ela só publica o que a pessoa já aprovou na janela e agendou.

Limite honesto: a janela barra um agente que só tem o canal de texto. Ela não impede quem tem controle total do computador (por exemplo, um agente com ferramentas de controle de tela que clique no botão). Por isso a regra do projeto é que o agente nunca clica na janela de aprovação.

## A assinatura: o arquivo do post sozinho não prova nada

A janela protege o **comando** `aprovar`. Mas o post é um arquivo de texto e o hash não tem chave: quem escrevesse à mão `"status": "aprovado"` e um hash calculado enganaria o publicador. Por isso a aprovação também é **assinada**.

**Em uma frase:** a aprovação só vale com uma assinatura (HMAC-SHA256, um selo que só quem tem a chave consegue refazer) que o `aprovar` grava depois do clique da pessoa, feita com uma chave secreta criada na primeira aprovação e guardada fora do projeto; sem assinatura válida, o post é tratado como não aprovado.

- **A chave.** Na primeira aprovação, o script cria 32 bytes aleatórios (`secrets.token_bytes(32)`, gravados em hexadecimal) em `~/.config/estudio-de-conteudo/<marca>/aprovacao.key` (Windows: `%USERPROFILE%\.config\estudio-de-conteudo\<marca>\aprovacao.key`; `ESTUDIO_CONFIG` troca a pasta base), com permissão só do dono, como as credenciais. Ela **nunca é impressa** (o filtro de segredos a mascara) e **nunca é copiada para o projeto**: não fica em `marcas/`, não entra no git nem na cópia de segurança das marcas.
- **A assinatura.** Depois da confirmação da pessoa, o `aprovar` grava em `aprovacao.assinatura` um HMAC-SHA256 com essa chave sobre cinco dados, em JSON canônico: o **hash da versão**, o **id do post**, a **frase**, a **data** e **quem aprovou**. Trocar qualquer um deles, ou levar a assinatura para outro post, a invalida.
- **A conferência.** `simular`, `agendar`, `publicar`, `agendados` e `conferir` recalculam a assinatura e comparam com `hmac.compare_digest`. A lista do `situacao` marca os posts `aprovado` ou `agendado` cuja assinatura não vale.
- **Sem assinatura, ou com assinatura inválida, o post vale como não aprovado.** O comando recusa e explica: "aprovação sem assinatura válida: rode `aprovar` de novo; ele abre a janela para você confirmar". Se a chave existe e a assinatura falta ou não confere, a aprovação cai: o histórico registra, `aprovacao` é limpa e o post volta para `arte_pronta`. Se o problema é a própria chave, o post **não é alterado**: o comando só recusa e explica.

| Situação | O que acontece |
|---|---|
| Aprovação escrita à mão (hash certo, sem assinatura) ou com assinatura inventada | recusa; com a chave presente, o post volta para `arte_pronta` |
| Assinatura copiada de outra versão ou de outro post, ou campo (`hash`, `frase`, `data`, `por`) alterado | recusa; com a chave presente, o post volta para `arte_pronta` |
| **A chave sumiu** (computador novo, arquivo apagado, outra pasta em `ESTUDIO_CONFIG`) | nenhuma aprovação anterior vale; os posts ficam como estão, o `simular` explica e a pessoa roda `aprovar` de novo (vale também para um post `agendado`), o que cria uma chave nova |
| Chave com defeito (arquivo cortado ou alterado) | o próximo `aprovar` guarda o arquivo de lado (`aprovacao.key.defeituosa-AAAAMMDD-HHMMSS`) e cria outra |
| Chave que não consigo ler (arquivo em uso, sem permissão) | recusa sem alterar nada; feche o programa que a usa e rode de novo |

**Perdi a chave. E agora?** As aprovações antigas perdem a validade e a pessoa aprova de novo, post por post, na janela. Posts já **publicados** não são afetados. A chave não viaja com a pasta `marcas/` nem com a cópia de segurança dela: ao trocar de computador, aprovar de novo é o caminho (não copie a chave).

**Limite honesto.** A assinatura barra quem só consegue **escrever texto**, como um agente que edita o JSON do post. Não barra quem **executa código no computador da pessoa**: um agente com controle total poderia ler a chave e assinar sozinho. As regras do projeto proíbem isso: o agente nunca abre a pasta `~/.config/estudio-de-conteudo/` (a chave está lá, junto das credenciais), nunca copia a chave e nunca clica na janela de aprovação.

## O que é gravado em `aprovacao`

```json
"aprovacao": {
  "por": "Nome de quem aprovou",
  "frase": "pode publicar 2026-11-03-1-habitos",
  "data": "2026-11-04T09:12:00-03:00",
  "hash": "<64 caracteres hexadecimais>",
  "assinatura": "<64 caracteres hexadecimais>"
}
```

e o `status` passa para `aprovado`. O `historico` ganha uma linha ("aprovado por ..., confirmado pela pessoa na janela ou no terminal, e assinado com a chave deste computador"). Tudo isso só é gravado pelo script `publicar.py aprovar`, depois da confirmação acima. A `assinatura` fica fora do hash da versão, como todo o bloco `aprovacao`.

## Como o hash é calculado

O hash identifica a versão exata que a pessoa viu: o texto do post **e** cada arte. Qualquer pessoa consegue recalcular. Em Python:

```python
import hashlib, json

def sha256(b): return hashlib.sha256(b).hexdigest()

CAMPOS_DE_CONTROLE = {"status", "historico", "aprovacao", "agendado_para", "publicacao", "revisao"}

def hash_da_versao(post: dict, artes_png: list[bytes]) -> str:
    conteudo = {k: v for k, v in post.items() if k not in CAMPOS_DE_CONTROLE}
    canonico = json.dumps(conteudo, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    texto = "post:" + sha256(canonico) + "\n"
    for n, png in enumerate(artes_png, 1):          # 01.png, 02.png... na ordem dos slides
        texto += f"arte-{n:02d}:" + sha256(png) + "\n"
    return sha256(texto.encode("utf-8"))
```

- O JSON canônico tem as chaves em ordem alfabética, sem espaços e com acentos preservados (UTF-8). Por isso mudar só a formatação do arquivo não muda o hash.
- As artes entram **pelos bytes do arquivo PNG**, na ordem dos slides. Mudar um único pixel muda o hash.
- Ficam **fora** do hash os campos que mudam durante o ciclo de vida sem alterar o que a pessoa viu: `status`, `historico`, `aprovacao`, `agendado_para`, `publicacao` e `revisao`.

## O que invalida a aprovação

| Mudança depois do ok | Efeito |
|---|---|
| Texto de slide, legenda, hashtags, chamada, fontes, `confirmar`, formato, proporção... | o hash muda |
| Qualquer arte regenerada ou editada | o hash muda |
| Só `status`, `historico`, `agendado_para`, `publicacao` ou `revisao` | o hash não muda |

Quando `publicar`, `agendar` ou `agendados` percebem que o hash mudou, **recusam**, gravam no histórico "aprovação invalidada", limpam `aprovacao` e devolvem o post para `arte_pronta`. Aí o agente roda `simular`, mostra a nova versão e pede um novo ok. O mesmo acontece quando a assinatura falta ou não confere (seção acima).

## Quem muda o status

| De | Para | Quem | Quando |
|---|---|---|---|
| `arte_pronta`, `erro` ou `aprovado` | `aprovado` | `aprovar` | a pessoa disse "pode publicar `<id>`", o post está sem problemas e ela **confirmou na janela**; o script **assina** a aprovação (o `simular` só diz PRONTO nestes casos) |
| `agendado` com aprovação sem assinatura válida | `aprovado` | `aprovar` | a chave sumiu ou a aprovação foi mexida; a pessoa aprova de novo na janela e o agendamento cai (use `agendar` depois) |
| `aprovado` | `agendado` | `agendar` | horário futuro e hash conferido |
| `agendado` | `aprovado` | `desagendar` | a pessoa cancelou o agendamento |
| `aprovado` ou `agendado` | `publicado` | `publicar` / `agendados` / `conferir` | a Meta confirmou; o link foi gravado |
| `aprovado` ou `agendado` | `erro` | `publicar` / `agendados` | falha, janela de atraso perdida ou resposta sem clareza |
| `erro` | `aprovado` | `conferir` | ficou provado que o post **não** foi ao ar e a assinatura da aprovação vale (sem assinatura válida, o post vai para `arte_pronta`, ou fica em `erro` se o problema é a chave) |
| `aprovado` ou `agendado` | `arte_pronta` | `publicar` / `agendar` / `agendados` | o hash não confere mais, ou a assinatura falta ou não confere com a chave presente |

Os demais status (`rascunho`, `em_revisao`, `texto_aprovado`, `arte_pronta`) pertencem às outras skills. De `erro`, a pessoa precisa dizer "pode publicar `<id>`" de novo, depois de saber o que houve.

## Por que `aprovar` e não "só publicar"

Porque o ok precisa ficar escrito, com a frase da pessoa, a hora e a versão, antes de qualquer coisa sair. Assim, se alguém perguntar "quem autorizou isto?", o post responde: está em `aprovacao` e no `historico`.
