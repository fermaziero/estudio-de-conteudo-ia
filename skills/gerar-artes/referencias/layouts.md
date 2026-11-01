# Layouts, tamanhos e ajustes

Leia este arquivo quando for escolher ou ajustar o visual de um slide. As regras de produto (o que pode e o que não pode) estão no `SKILL.md`.

## Medidas comuns

- Arte de 1080 x 1350 px (`4:5`) ou 1080 x 1080 px (`1:1`). Todas as artes de um post usam a mesma proporção (campo `proporcao` do post; se faltar, vale `proporcao_padrao` do `visual.json`).
- O desenho é feito em 2x e reduzido com suavização, para as bordas ficarem limpas.
- **Área segura:** 72 px de margem nas laterais; 88 px em cima e embaixo. Se o logo está em cima, o conteúdo começa abaixo dele; se está embaixo, termina acima dele. Rodapé e numeração (quando o `visual.json` pede) também reservam espaço embaixo.
- O texto fica alinhado à esquerda. Nunca é cortado nem sai da área segura.

### Tamanhos de fonte (padrão)

| Elemento | Menor | Maior |
|---|---|---|
| Título dos slides de conteúdo | 44 px | 56 px |
| Texto de apoio | 24 px | 30 px |
| Chamada da capa e do último slide | 48 px | 62 px |
| Item de lista e título de cartão | 26 px | 34 px |

A marca pode mudar as faixas de título e apoio com o bloco opcional `tipografia` do `visual.json` (veja `visual-json.md`). A hierarquia vem do peso e da cor, não de letras gigantes.

### Como o texto é ajustado

1. Começa no maior tamanho e vai descendo, 1 px por vez. Os blocos do mesmo slide (por exemplo, título e apoio) descem juntos.
2. Títulos são quebrados em linhas de tamanho parecido; o apoio quebra do jeito normal, evitando uma última linha com uma palavra só.
3. Se não couber nem no menor tamanho, o post inteiro fica sem arte e o comando diz o slide, quanto falta de altura e qual o tamanho mínimo usado. **Nada é cortado.**
4. Uma palavra mais larga que a área (por exemplo, um endereço longo) também falha, com o nome da palavra.
5. Quebras de linha em `titulo`, `texto` e `itens` (`\n`) são respeitadas.

### Destaque dentro do texto

`**trecho**` vira negrito na cor de destaque da marca (ou na cor do texto, se o destaque tiver pouco contraste). Use em uma ou duas expressões por slide, nunca em frases inteiras. Asteriscos sem par são ignorados.

### Caracteres

A fonte que acompanha a skill (Manrope) desenha letras latinas com acento, aspas, travessões, reticências, `•`, `→`, `½`, `×`, `€`, `®`, `™` e `©`. Emojis e símbolos como `✓`, `★` e `▶` não existem nela: aparecem como quadradinho e geram um aviso de atenção. Troque por palavras.

Aspas retas (`"`) e apóstrofos no meio da palavra (`d'água`) viram aspas e apóstrofos curvos (`“ ”`, `’`) só no desenho; o texto do post não muda.

## Cada layout

### `capa`

- Só a **chamada** (`titulo`, até 12 palavras). O campo `texto` não é desenhado (aviso informativo).
- **Com imagem** (campo `imagem` e arquivo existente), duas variantes:
  - `faixa` (padrão para `foto`): a imagem ocupa a parte de cima (entre metade e dois terços da arte, conforme o tamanho do título) e o título fica numa faixa sólida embaixo. **O texto nunca cai sobre a imagem, então nunca cai sobre um rosto.**
  - `degrade` (padrão para imagem `gerada`): a imagem ocupa a arte toda e o título fica sobre um degradê escuro na parte de baixo. Use com imagens sem pessoas ou com o assunto na metade de cima.
  - Troque com `--variante faixa` ou `--variante degrade` (veja "Ajustes por slide").
- **Sem imagem**: fundo limpo escuro com um brilho suave na cor de destaque e o título grande.
- O logo fica no canto do `visual.json`, com a versão (clara ou escura) que tiver melhor contraste com o que está embaixo dele.

```json
{"n": 1, "papel": "capa", "layout": "capa", "titulo": "Sua semana de trabalho cabe em uma página", "texto": "",
 "itens": [], "imagem": {"tipo": "gerada", "arquivo": "", "descricao": "mesa de trabalho vista de cima", "prompt": "Mesa organizada em luz natural. Sem texto, sem letras, sem logos."},
 "texto_alternativo": "Mesa de trabalho organizada", "fonte_interna": ""}
```

### `texto`

Título e apoio, centralizados na vertical (um pouco acima do meio). Ideal para uma ideia por slide. Guia: título até 12 palavras e apoio até 35 palavras; acima de 60 palavras o validador avisa.

### `lista`

Título e de 2 a 5 itens numerados, com a numeração na cor de destaque. Se um item tem o formato `Título: explicação` (dois-pontos seguido de espaço, título de até 48 caracteres), o título sai em negrito de destaque e a explicação embaixo. Se sobrar espaço, os itens ganham respiro. Guia: até 12 palavras por item.

### `cartoes`

Título e de 2 a 5 cartões (retângulos de cantos arredondados, sem sombra). Mesmo padrão `Título: explicação`. Guia: até 18 palavras por cartão.

### `imagem`

Título (e apoio opcional) em cima, imagem embaixo com cantos arredondados, ocupando o espaço que sobra (no mínimo 34% da altura). Precisa do objeto `imagem`.

- `foto` e `gerada` são recortadas para preencher a área (`--encaixe cobrir`, o padrão), com o ponto de foco de `--foco`.
- Logos de terceiros (arquivo em `assets/logo/` ou com "logo" no nome) e imagens PNG com transparência entram **inteiros**, sobre um cartão neutro (`conter`). Para prints e gráficos, peça `--encaixe conter`.

### `citacao`

Aspas grandes na cor de destaque, a frase em `titulo` (aspas já escritas no começo e no fim são removidas) e a autoria em `texto` (um travessão é acrescentado).

### `cta`

Último slide do carrossel, escuro por padrão: avatar redondo, nome (`nome_exibicao`) e `arroba` do `visual.json` (o que existir), a **chamada** em `titulo` (até 10 palavras) e uma linha curta em `texto` (opcional, até 15 palavras). Uma ação só, escolhida pela etapa do funil.

## Temas

| Tema | Fundo | Padrão para |
|---|---|---|
| `claro` | `cores.fundo` | `texto`, `lista`, `cartoes`, `imagem`, `citacao` |
| `escuro` | `cores.fundo_escuro` | `capa`, `cta` |
| `destaque` | `cores.destaque` | nenhum (só com `--tema destaque`) |

- Cartões e bordas são derivados das cores da marca. Se a cor de destaque tem pouco contraste sobre o fundo escuro, nos slides escuros ela é usada mais clara (aviso informativo).
- **Só existe um logo?** Se o `visual.json` tem só o logo para fundo claro, os slides que seriam escuros saem no tema claro (e vice-versa), para o logo aparecer. O aviso diz para acrescentar o outro arquivo.
- Capas e imagens com foto: a cor do logo é escolhida pelo contraste com a imagem embaixo dele.

## Ajustes por slide

Ficam em `marcas/<marca>/conteudo/<lote>/artes/<id>/ajustes.json` e valem nas próximas gerações. O jeito normal é usar as opções do `renderizar.py` (exigem `--post` e `--slide`); `auto` apaga o ajuste.

| Opção | Valores | Efeito |
|---|---|---|
| `--variante` | `degrade`, `faixa`, `auto` | só `capa` com imagem |
| `--tema` | `claro`, `escuro`, `destaque`, `auto` | fundo do slide |
| `--foco "x y"` | dois números de 0 a 1, ou `auto` | centro do corte da imagem (`0 0` é o canto de cima à esquerda; `0.5 0.3` mantém mais o alto da imagem) |
| `--encaixe` | `cobrir`, `conter`, `auto` | layout `imagem` |

```json
{"versao_esquema": 1, "slides": {"1": {"variante": "faixa", "foco": [0.5, 0.3]}, "4": {"encaixe": "conter"}}}
```

## Rodapé e numeração

Desligados por padrão. Se o `visual.json` ligar `numeracao`, entra `NN/TT` embaixo; se ligar `rodape`, entram nome e @ da marca. Eles ficam ao lado do logo, nunca por cima, e saem do jeito mais curto que couber.
