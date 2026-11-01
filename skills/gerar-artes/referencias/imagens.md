# Imagens nas artes

Leia este arquivo quando um slide precisar de foto, de imagem gerada por IA, de prompt, de recorte ou de uma imagem que não pode ser cortada (print, gráfico, logo de terceiros). Se o `padrao-visual.md` da marca disser outra coisa, ele vale mais que este texto.

## Dois tipos de imagem

| Tipo | O que é | De onde vem |
|---|---|---|
| `foto` | foto real: da pessoa, da equipe, do produto, do espaço | arquivo **autorizado** em `marcas/<marca>/assets/fotos/` (campo `arquivo`, relativo à marca ou ao lote) |
| `gerada` | imagem ilustrativa criada por IA | prompt escrito por `imagens.py prompts`, gerado numa ferramenta de imagem e importado |

O campo `imagem` do slide é `{"tipo", "arquivo", "descricao", "prompt"}`. Para `gerada`, o `arquivo` fica `""` até a imagem existir; o importador preenche.

## Regras para qualquer imagem

1. **Sem texto dentro da imagem**: nem letras, números, legendas, marcas d'água ou telas com texto legível. O texto da arte é sempre desenhado pelo código.
2. **Sem logo dentro da imagem.** O logo da marca é colocado pelo código, e logo de terceiros só como arquivo oficial (veja "Imagem inteira").
3. **Sem rosto de pessoa real gerado por IA.** Se a cena precisa de gente, só mãos, silhuetas ou pessoas de costas, sem identificar ninguém. Pessoa de verdade só em foto real autorizada.
4. **Foto de pessoa só com autorização.** Clientes, alunos, menores e terceiros só se a autorização estiver registrada em `regras.md`. Na dúvida, pare e pergunte.
5. **Nunca refaça nem "melhore" rostos** com IA. Para aproximar uma foto, mude o enquadramento (`--foco`); a ampliação não cria detalhe que a foto não tem.
6. **Texto nunca sobre rosto.** Por isso a capa com foto usa a variante `faixa`.
7. **Nada de ícone, pictograma, vetor ou ilustração plana** a menos que o `padrao-visual.md` da marca peça. O padrão recomendado é imagem realista ou fundo limpo.
8. **Uma cena diferente por imagem no mesmo lote.** Duas capas não repetem o mesmo objeto.
9. Para não parecer imagem genérica de IA, prefira objetos e cenas concretos do trabalho da pessoa e evite clichês (robôs, cérebros, cadeados, neon) a menos que a marca peça.

## Prompts

```
python -X utf8 skills/gerar-artes/scripts/imagens.py prompts --marca <marca> --lote <lote> [--post <id>] [--todos]
```

Para cada slide com imagem `gerada` que ainda não existe (ou todos, com `--todos`), o script escreve em `artes/<id>/imagens/prompts.md`:

- a **área exata** que a imagem ocupa na arte e a proporção mais próxima para pedir à ferramenta;
- o comando de importação, já preenchido;
- um prompt em português, montado com a `descricao` e o `prompt` do post, estilo realista, a paleta da marca (códigos de cor), a composição (na capa com `degrade`, o terço de baixo mais limpo para o título) e as **proibições fixas** (sem texto, sem logo, sem rosto de pessoa real, sem ícones).

Quem escreve o `prompt` no post é a skill `criar-conteudo`: cena, enquadramento e luz, terminando com "Sem texto, sem letras, sem logos." O texto do slide não entra no prompt.

Se a ferramenta funcionar melhor em inglês, traduza o prompt mantendo todas as proibições. Ferramentas de imagem, planos e regras de uso mudam rápido: confira na própria ferramenta o que ela oferece (proporções, tamanho, uso comercial) antes de prometer algo à pessoa.

## Gerar e conferir

1. Gere uma imagem por prompt na ferramenta que a pessoa tiver (ChatGPT, Gemini, Codex ou outra). Peça a proporção mais próxima da indicada.
2. Salve o arquivo no computador (PNG, JPG ou WebP).
3. **Abra a imagem e confira**: sem letras ou números em lugar nenhum (telas, papéis, placas), sem logo, sem rosto de pessoa real, assunto longe das bordas, na paleta. Se falhar, gere de novo reforçando a proibição. Não conserte com retoque.
4. Tamanho: quanto maior, melhor. Menor que a área da arte (por exemplo, 1080 x 1350 px numa capa de tela cheia) é ampliada e a skill avisa que pode ficar borrada.

## Importar

```
python -X utf8 skills/gerar-artes/scripts/imagens.py importar --marca <marca> --lote <lote> --post <id> --slide <n> <arquivo> [--foco "0.5 0.4"]
```

- O original vai para `artes/<id>/imagens/slide-NN-original.<ext>`; a versão recortada para a área do layout vai para `artes/<id>/imagens/slide-NN.png`; o caminho é gravado em `imagem.arquivo` do post (e registrado no `historico`).
- Trocar a imagem de novo guarda a anterior em `artes/<id>/imagens/_antes-<motivo>-slide-NN/`.
- Mudar o enquadramento: importe de novo o original que está na pasta, com outro `--foco`.
- Se o texto do slide mudar num layout `imagem`, a área pode mudar: importe de novo a partir do original.
- Imagem inválida (arquivo corrompido, formato sem suporte): o comando falha **antes de mexer em qualquer arquivo**; a imagem anterior, o original guardado e o post continuam como estavam.
- Post aprovado ou agendado: use `--refazer-aprovado` (a aprovação e o agendamento deixam de valer).

Depois rode o `renderizar.py`. O importador não desenha nada; só prepara o arquivo.

## Fotos reais

- Coloque em `marcas/<marca>/assets/fotos/` e aponte em `imagem.arquivo` (por exemplo, `assets/fotos/equipe.jpg`). JPG, PNG e WebP funcionam; HEIC não (converta).
- O corte padrão mantém mais o alto da foto (ponto de foco `0.5 0.4`), pensando em retratos. Se cortar a cabeça ou o assunto, ajuste com `--foco`.
- Em capas, o padrão é `faixa`: a foto em cima e o título numa faixa sólida embaixo. Para uma foto sem pessoas, `--variante degrade` deixa a imagem em tela cheia.
- Varie as fotos do mesmo lote (pose, cenário, enquadramento) e confira o acervo antes de repetir uma.
- Tratamento de luz e cor, retoque e remoção de elementos não fazem parte desta skill.

## Imagem inteira: prints, gráficos e logos de terceiros

Use o layout `imagem` e o encaixe `conter`: a imagem entra **inteira, sem corte**, centralizada num cartão neutro.

```
python -X utf8 skills/gerar-artes/scripts/renderizar.py --marca <marca> --lote <lote> --post <id> --slide <n> --encaixe conter --motivo "print inteiro"
```

- Arquivos dentro de `assets/logo/`, com "logo" no nome ou PNG com transparência já entram assim sozinhos. Prints e gráficos precisam de `--encaixe conter`.
- **Logo de terceiros: só o arquivo oficial**, baixado do site da própria empresa e liberado pela pessoa (se os termos de uso pedirem aceite ou aprovação, pare e pergunte). Fica sobre fundo neutro, nunca dentro de quadrado colorido e nunca logo escuro sobre fundo escuro. Sem arquivo oficial, escreva o nome em texto simples. A IA nunca desenha logo de terceiros.
- Dado visível num print ou gráfico (nomes, valores, e-mails): confira se não expõe informação de terceiros antes de usar.
