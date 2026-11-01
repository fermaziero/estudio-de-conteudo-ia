# Como o `visual.json` vira artes

O `visual.json` (em `marcas/<marca>/`) é escrito pela skill `configurar-marca`. Esta skill só lê. Leia este arquivo quando o resultado depender de cores, fonte, logo, avatar, proporção, rodapé ou tamanho de letra. Para **mudar** qualquer coisa aqui, use a `configurar-marca`.

O formato do arquivo está em `docs/arquitetura.md`. Caminhos são relativos à pasta da marca e **não podem sair dela** (`..` e caminhos de disco são recusados).

## Campos

| Campo | Como a skill usa |
|---|---|
| `nome_exibicao`, `arroba` | aparecem no último slide (`cta`) e, se `rodape` estiver ligado, no pé das artes |
| `proporcao_padrao` | `4:5` (1080 x 1350) ou `1:1` (1080 x 1080) quando o post não define `proporcao` |
| `cores.fundo`, `cores.texto`, `cores.suave` | slides claros: fundo, texto principal e texto secundário (autoria da citação, pé da arte). Nos slides escuros, o texto secundário é derivado de `texto_sobre_escuro` |
| `cores.destaque` | números das listas, aspas, títulos de cartão e trechos `**destaque**`; fundo do tema `destaque` |
| `cores.fundo_escuro`, `cores.texto_sobre_escuro` | capa sem foto, último slide e faixa da capa com foto |
| `fontes.titulo`, `fontes.texto` | arquivo `.ttf` ou `.otf` para títulos e destaques / para o texto de apoio. `null` usa a Manrope que acompanha a skill |
| `logo.fundo_claro`, `logo.fundo_escuro` | PNG do logo para ser usado sobre fundo claro / sobre fundo escuro |
| `logo.posicao` | `superior-esquerda`, `superior-direita`, `inferior-esquerda` ou `inferior-direita` |
| `logo.largura_px` | largura do logo numa arte de 1080 px (de 40 a 400; padrão 140). A altura nunca passa de 110 px |
| `avatar` | foto redonda no último slide. `null` omite |
| `numeracao`, `rodape` | `false` por padrão; `true` liga `NN/TT` e nome com @ no pé |

### `tipografia` (opcional)

Bloco que a skill aceita além do contrato, para mudar as faixas de tamanho de letra (em px, numa arte de 1080 px de largura). Se faltar, valem os padrões.

```json
"tipografia": {"titulo": [44, 56], "apoio": [24, 30]}
```

Limites aceitos: de 20 a 110 px, com o menor primeiro. Letra muito grande "grita" e reduz o quanto cabe; a recomendação do projeto é título entre 44 e 56 px e apoio entre 24 e 30 px.

## Cores

- Tudo é derivado das seis cores: o fundo dos cartões é uma versão mais clara (ou mais escura) do fundo, as bordas são uma mistura de fundo e texto.
- O gerador mede o contraste (razão WCAG) e avisa quando `texto` sobre `fundo`, ou `texto_sobre_escuro` sobre `fundo_escuro`, ficam abaixo de 4,5:1. O aviso impede marcar como pronta.
- `destaque` precisa de pelo menos 3,5:1 sobre o fundo para ser usada em texto; abaixo disso, os trechos em destaque saem na cor do texto. Sobre o fundo escuro ela é clareada automaticamente se preciso.
- Cores no formato `#RRGGBB` (ou `#RGB`).

## Fonte

- Sem `fontes`, a skill usa a **Manrope** (licença SIL OFL 1.1, em `skills/gerar-artes/fontes/`): Regular para o apoio, Bold para títulos e ExtraBold para numerais e aspas. Origem, licença e conferência: `fontes/LEIA-ME.md`.
- Fonte própria: copie os `.ttf` ou `.otf` para `marcas/<marca>/assets/fontes/` e aponte no `visual.json`. Use arquivos **estáticos** (um por peso). `fontes.titulo` deve ser a versão negrito e `fontes.texto` a regular; trechos em destaque no apoio usam a fonte do título.
- Fontes **variáveis** (um arquivo com vários pesos) geram um aviso de atenção: o Pillow mede a largura das letras sem considerar o peso e o texto pode sair apertado.
- Só use fonte cuja licença permita uso em imagens. A pessoa é responsável pela licença das fontes próprias.
- Sem a biblioteca de layout avançado do Pillow (`raqm`), o espaçamento entre pares de letras é o básico da fonte: o texto fica bom, mas pode ficar sem o ajuste fino de kerning.

## Logo

- **O ideal é um PNG com fundo transparente**, um para fundo claro (logo escuro) e outro para fundo escuro (logo claro). O arquivo original nunca é alterado.
- Se o PNG tiver um fundo de uma cor só (por exemplo, branco), a skill remove esse fundo ao desenhar, inclusive dentro das letras, preservando as bordas suaves. Partes do desenho que tenham exatamente a cor do fundo também somem. Fundo que não é liso (foto, degradê) não é removido e gera um aviso.
- O logo é recortado nas bordas transparentes e redimensionado para `largura_px`.
- Em cada slide, a skill escolhe a versão do logo pelo contraste com o que está embaixo dele (medido por trechos, não pela média). Contraste abaixo de 3:1 vira aviso informativo; abaixo de 1,7:1 vira aviso de atenção ("quase não aparece").
- Só uma versão do logo? Os slides que pediriam a outra saem no tema que a versão existente aceita (aviso informativo).
- Nunca há caixa, sombra ou halo atrás do logo, e ele nunca é redesenhado nem recolorido.
- Em capas com foto, o logo fica por cima da imagem. Se a foto for clara demais ou escura demais naquele canto, mude o enquadramento (`--foco`) ou a foto.

## Avatar

PNG ou JPG quadrado ou quase. É cortado em círculo, com o rosto um pouco acima do centro. Só aparece no `cta`.

## Rodapé e numeração

Com `numeracao: true` entra `NN/TT` (`03/08`). Com `rodape: true`, nome e arroba. Quando o logo está embaixo, o texto do pé fica do lado oposto e é encurtado (só o arroba) se não couber. A recomendação do projeto é deixar os dois desligados: nada de linha divisória, numeração ou @ repetido em todo slide.
