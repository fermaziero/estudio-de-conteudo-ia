# Campos do post: guia de preenchimento

O contrato completo está em `docs/arquitetura.md` (seção "Lote e post"). Este guia mostra **como preencher** cada campo. Se os dois divergirem, o contrato vale.

O arquivo é `marcas/<marca>/conteudo/<lote>/posts/<id>.json`, em UTF-8, com acentos normais (nada de `\u00e9`) e indentação de 2 espaços. Comece sempre copiando um modelo de `skills/criar-conteudo/modelos/`. Depois rode `validar_posts.py`: ele aponta o arquivo e o campo de cada problema.

## Identificação e direção

| Campo | Como preencher |
|---|---|
| `versao_esquema` | Sempre o número `1`. |
| `id` | `<data-do-lote>-<n>-<slug-curto>`, só letras minúsculas sem acento, números e hífen (3 a 80 caracteres). Tem de ser igual ao nome do arquivo e único em toda a marca. Exemplo: `2026-11-03-1-contas-separadas`. |
| `lote` | O nome da pasta do lote, `AAAA-MM-DD-slug`. |
| `titulo_interno` | Nome curto para a pessoa reconhecer o post na lista. Não aparece na arte. |
| `pilar` | O `id` de um pilar de `estrategia.json` (exemplo: `educativo`). |
| `formato` | `carrossel`, `post_unico` ou `reel`. |
| `proporcao` | `4:5` ou `1:1`. Use a `proporcao_padrao` de `visual.json`, se existir; senão `4:5`. Todas as artes do post usam a mesma. No reel o campo é obrigatório, mas não é usado: deixe `4:5`. |
| `etapa_funil` | `atracao`, `relacionamento` ou `conversao` (sem acento, assim mesmo). |
| `objetivo` | Uma frase: o que quem lê leva do post. |
| `de_onde_vem` | A origem real da pauta (referência, pergunta de cliente relatada pela pessoa, resultado anterior). Se a ideia foi sua, diga. |
| `chamada` | A **única** chamada para ação. Aparece no último slide (em versão curta) e no fim da legenda. No reel, uma chamada leve. |

## Slides

Carrossel: de 2 a 10 slides (prefira 6 a 9). Post único: exatamente 1 slide. Reel: `slides` fica `[]` e o texto vai em `roteiro`.

| Campo do slide | Como preencher |
|---|---|
| `n` | 1, 2, 3… sem buracos nem repetição. |
| `papel` | `capa` no primeiro; `cta` no último slide do carrossel; `conteudo` nos outros. |
| `layout` | Veja a tabela abaixo. |
| `titulo` | Frase completa. Na capa, até 12 palavras. |
| `texto` | Apoio que completa o título. Pode ser `""`. |
| `itens` | Lista de textos. Só para `lista` e `cartoes` (de 2 a 5 itens); nos outros layouts, `[]`. |
| `imagem` | `null` ou um objeto (veja "Imagens"). |
| `texto_alternativo` | Descrição do slide para quem usa leitor de tela: uma frase para a imagem (se houver) e o texto escrito no slide, transcrito. Não há limite de frases, mas seja curto e use português simples. |
| `fonte_interna` | De onde saiu o que o slide afirma (veja "Fontes"). `""` se o slide não afirma fato. |

### Layouts: qual usar

| Layout | Para quê | O que vai em cada campo |
|---|---|---|
| `capa` | Primeiro slide e post único | `titulo` é o gancho. `texto` vazio. `imagem` opcional (fundo) |
| `texto` | Uma ideia explicada | `titulo` é a ideia em frase completa; `texto` a explica em poucas linhas |
| `lista` | De 2 a 5 itens **em sequência** (passos, etapas). O gerador numera os itens | `titulo` diz o que a lista é; cada `itens[]` é uma frase curta |
| `cartoes` | De 2 a 5 itens **independentes**, lado a lado (sinais, opções, categorias, comparação) | `titulo` diz o que se compara; cada `itens[]` é um cartão |
| `citacao` | Uma frase de destaque da própria marca (princípio, lição em uma frase) | `titulo` é a frase; `texto` (opcional) diz de quem é, por exemplo o nome da marca |
| `imagem` | A imagem ajuda a entender e é a protagonista | `imagem` é obrigatória; `titulo` curto; `texto` opcional |
| `cta` | Último slide do carrossel | `titulo` é a chamada (cerca de 8 palavras); `texto` vazio ou uma linha curta |

Em `lista` e `cartoes`, um item escrito como `Título curto: explicação` é desenhado com o título em destaque e a explicação logo abaixo. Se não quiser isso, evite o sinal de dois-pontos no começo do item.

Dois detalhes do desenho do texto nas artes:

- Para destacar uma expressão, escreva `**assim**` (negrito na cor de destaque da marca). Use em uma ou duas expressões por slide, nunca numa frase inteira.
- A fonte das artes não desenha emoji nem símbolos como ✓ ou ★: eles saem como quadradinho. Nos slides, troque por palavras. (Na legenda, emoji vale se a marca usa.)

`citacao` nunca é depoimento de cliente, aluno ou pessoa real. Depoimento só existe com autorização registrada em `regras.md` e vai sempre para `confirmar[]` até a pessoa conferir o texto exato.

### Imagens

`imagem` é `null` ou um objeto:

```json
{"tipo": "gerada", "arquivo": "", "descricao": "Mesa de trabalho organizada, com duas pastas separadas", "prompt": "Mesa de escritório em luz natural, duas pastas lado a lado. Sem texto, sem letras, sem logos."}
```

- `tipo: "foto"`: foto real que a pessoa autorizou. `arquivo` é o caminho relativo à pasta da marca (exemplo: `assets/fotos/equipe.png`), com barras normais, sem `..` e sem `C:\`. Sem `prompt`.
- `tipo: "gerada"`: a skill `gerar-artes` cria a imagem a partir do `prompt`. `arquivo` fica `""` até a imagem existir. O `prompt` descreve a cena, o enquadramento e a luz e **termina com "Sem texto, sem letras, sem logos."** A IA nunca escreve texto nem desenha logo dentro de imagem. Se o texto do slide vai ficar sobre a imagem, peça uma área mais limpa onde ele entrará.
- Não peça pessoa real identificável, criança, nem marca de terceiros.
- `descricao` diz o que a imagem mostra, em português simples.

## Texto de divulgação

| Campo | Como preencher |
|---|---|
| `roteiro` | `null` em carrossel e post único. No reel, lista de blocos `{"tempo": "0-3s", "fala": "…", "tela": "…"}`. |
| `legenda` | Até 2.200 caracteres. Sem "Fonte:", sem links, sem hashtags no texto. Termina com a mesma `chamada`. |
| `hashtags` | Lista com 0 a 5 itens, **sem o `#`** (exemplo: `"contabilidade"`). Só letras, números e `_`. Quem publica acrescenta o `#`. |

## Fontes e dúvidas

| Campo | Como preencher |
|---|---|
| `fontes` | Fontes abertas que sustentam o post: `{"nome": "Nome da página ou do documento", "url": "https://…", "data": "AAAA-MM-DD"}`. A `data` é o dia em que você abriu e conferiu. Só endereço `http://` ou `https://`: nunca caminho de arquivo. Ficam só aqui, nunca na arte nem na legenda. |
| `fonte_interna` (por slide) | Texto livre: página e trecho de onde saiu o que o slide afirma, ou "Informado pela pessoa no chat em AAAA-MM-DD". Se o slide é exemplo, opinião ou frase nova escrita para o post, diga isso ("exemplo criado para o post"); não atribua a `marca.md` o que ela não diz. |
| `fontes_legenda_internas` | Lista de textos: de onde saiu cada afirmação da legenda. |
| `confirmar` | Pendências, cada uma no formato `"NÃO VERIFICADO: <o que> — <como confirmar>"`. Com item aqui, o texto pode ser aprovado, mas o post **não é publicado** até a pendência ser resolvida e o item removido. |

Exemplo de pendência: `"NÃO VERIFICADO: o dia de vencimento do imposto citado no slide 4 — conferir no portal oficial e registrar a fonte em fontes"`.

## Ciclo de vida

```
rascunho → em_revisao → texto_aprovado → arte_pronta → aprovado → agendado → publicado
                                                              ↘ erro
```

| Status | Quem muda | Quando |
|---|---|---|
| `rascunho` | `criar-conteudo` | ao criar o post, e quando um ajuste volta o post para cá |
| `em_revisao` | `criar-conteudo` | quando o post passa na validação e é enviado para a revisão independente |
| `texto_aprovado` | `criar-conteudo` | **só** depois de a pessoa aprovar o texto com palavras dela no chat |
| `arte_pronta` | `gerar-artes` | quando as artes foram geradas |
| `aprovado`, `agendado`, `publicado`, `erro` | `publicar-instagram` | na aprovação final, no agendamento, na publicação ou em falha |

| Campo | Quem escreve |
|---|---|
| `revisao` | `revisar-conteudo`: `{"data": "AAAA-MM-DD", "veredito": "aprovar", "pontos": []}` |
| `historico` | quem faz a mudança, sempre acrescentando: `{"data": "AAAA-MM-DD", "evento": "…", "por": "…"}`. Nada se apaga |
| `aprovacao`, `agendado_para`, `publicacao` | só `publicar-instagram`. Em `criar-conteudo` ficam `null` |

No `historico`, o campo `por` diz quem fez a mudança: o nome da skill (`criar-conteudo`, `revisar-conteudo`, `gerar-artes`, `publicar-instagram`) ou a pessoa que decidiu (o nome dela; se você não souber, `pessoa`). A `data` é `AAAA-MM-DD`; as skills de publicação gravam data e hora com fuso, e os dois formatos são aceitos.

Eventos típicos do `historico`:

- `Rascunho criado a partir da pauta 2`
- `Enviado para revisão independente`
- `Revisão independente: ajustar (2 pontos)`
- `Texto aprovado pela pessoa: "Pode seguir com as artes."` (com as palavras exatas dela)
- `Nova versão: capa mais curta. Versão anterior em posts/_antes-capa-mais-curta/`

## Nova versão de um post

Todo ajuste pedido vira nova versão e a anterior nunca é apagada:

1. Copie o JSON atual para `posts/_antes-<motivo>/<id>.<AAAA-MM-DD-HHMM>.json` (motivo curto, minúsculo, com hífen).
2. Altere o JSON original. Acrescente o evento ao `historico`, volte o `status` para `rascunho` e zere `revisao` (`null`): a revisão antiga valia para o texto antigo.
3. Valide, gere o `lote.md` e peça nova revisão.

As pastas `_antes-*` dentro de `posts/` não entram na validação nem no `lote.md`.
