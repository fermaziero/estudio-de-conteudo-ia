# Modelo da síntese

Arquivo: `marcas/<marca>/referencias/SINTESE.md`. Reescreva inteiro a cada execução, com todos os perfis de `perfis/`, mantendo as seções. Antes de reescrever, copie a versão atual para `marcas/<marca>/referencias/_antes-sintese-AAAA-MM-DD/SINTESE.md` (se a pasta já existir, acrescente `-2`).

Os números vêm dos arquivos dos perfis e de `referencias.csv`, nunca de memória. Cada afirmação precisa ser rastreável a um perfil. O que o perfil novo acrescentou ou só confirmou fica explícito.

Os títulos "O que isso indica para a marca", "O que não copiar" e "Como entra no planejamento" são lidos pela skill `planejar-conteudo`; a coluna `alavanca` do `referencias.csv`, também. Não renomeie essas seções.

## Modelo

Todos os nomes e números do modelo abaixo são fictícios: servem só para mostrar o formato.

```markdown
# Síntese das referências — atualizada em AAAA-MM-DD

- **Nicho principal da marca:** `rótulo`
- **Perfis:** @a, @b, @c (3 no total)

Comparação com o perfil da marca. Escopo: texto, temas, tom e engajamento; o visual ficou de fora. Detalhes e números de cada perfil estão em `perfis/`.

## Objetivo e focos
Entender, de cada perfil: do que fala, como fala, quais posts engajam e como atrai e converte. Fora do escopo: o visual.
Focos extras já pedidos: <foco — data — perfis analisados sob ele>, ou "nenhum".

## Perfis analisados
| Perfil | Arquivo | Coleta | Nicho | Observação |
|---|---|---|---|---|
| @a | `perfis/a.md` | AAAA-MM-DD | `nutricao` | referência de assunto |
| @b | `perfis/b.md` | AAAA-MM-DD | `negocios` | referência adjacente (aderência 30%, fictício) |

## Lado a lado
| | @a | @b | A marca hoje |
|---|---|---|---|
| Nicho | | | |
| Seguidores | | | |
| Tipo | | | |
| Frequência na amostra | ~5 por semana (fictício) | | |
| Tema dominante | | | |
| Voz | | | |
| Mediana de views dos reels | 5 mil, 5% da base (fictício) | | |
| Chamada para ação | 50% dos posts (fictício) | | |
| Isca central | | | |
| Alavanca (o que mais dá alcance) | | | |

## O que se repete
Numerado. Cada item diz em quais perfis aparece. Colabs aparecem nos dois perfis: conte como uma peça só. Um dos itens trata das alavancas de alcance: o que os reels de maior alcance dos perfis têm em comum (a coluna `alavanca` do `referencias.csv` ajuda) e o que os de menor alcance têm em comum.
Rodada de AAAA-MM-DD: @novo confirmou os itens 1 e 3 e acrescentou o 5.

## O que isso indica para a marca
Numerado. Cada item liga um padrão a um pilar e a uma etapa do funil de `estrategia.json`, respeita `regras.md` e usa só as chamadas que `marca.md` lista. Diz se é novo ou se confirma um item anterior.

## O que não copiar
O que não combina com a marca (`marca.md`, `regras.md`) ou com o tamanho dela: ritmo de publicação que a pessoa não consegue sustentar, urgência ou promessa que a marca não pode cumprir, tema ou promessa que `regras.md` proíbe.

## Pontos de atenção
Opcional. Nomes parecidos com os da marca, risco de confusão, campanhas que distorcem a amostra.

## Focos extras
Só quando houver. Um parágrafo por foco, dizendo quais perfis foram analisados sob ele.

## Como entra no planejamento
Como a skill `planejar-conteudo` usa isto (padrões, pilares a testar, formatos) e como a skill `acompanhar-resultados` usa `referencias.csv` na comparação.

## Limites
Tamanho e período das amostras, campanhas de lançamento, o que não foi medido (comentários, salvamentos, compartilhamentos), impulsionamento pago e audiência de colab que não dá para separar. Os padrões são correlação observada, não causa comprovada.
```

## A coluna "A marca hoje"

Preencha só com dado que existe:

1. `marcas/<marca>/metricas/perfil.csv` (última linha) e `metricas/posts.csv`, se já houver coleta de métricas;
2. números que a pessoa informou nesta conversa;
3. senão, `não medido`. Não abra o Instagram da própria marca para preencher esta coluna.

Para a frequência da marca, use os posts publicados em `publicacao/publicados.csv`, se existir. O ritmo planejado de `estrategia.json` é meta, não resultado: não o escreva como se fosse o que a marca faz hoje.

## Conferência da síntese

Quem escreveu a síntese não a revisa. Peça a um subagente que confira (a) os números contra os arquivos dos perfis e o `referencias.csv`, (b) se cada padrão aparece mesmo nos perfis citados e (c) se nada contraria `regras.md`. Sem subagentes, faça uma passagem separada, relendo os arquivos dos perfis, e diga à pessoa que não houve revisão independente.
