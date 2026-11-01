# Problemas comuns

Mensagens do `renderizar.py`, `imagens.py` e `marcar_pronta.py`, o que significam e o que fazer. `ERRO` interrompe; `ATENÇÃO` impede marcar o post como `arte_pronta`; `aviso` só informa.

## Antes de gerar

| Mensagem (resumo) | Causa | O que fazer |
|---|---|---|
| `ModuleNotFoundError: No module named 'PIL'` | falta o Pillow | `python -m pip install -r requirements.txt` (no macOS e no Linux, `python3 -m pip ...`) |
| `Há mais de uma marca` / `mais de um lote` | `--marca` ou `--lote` faltando | repita o comando com `--marca <slug>` e `--lote <nome>` (a mensagem lista as opções) |
| `Nada para gerar: nenhum post com status texto_aprovado` | nenhum post do lote espera arte | veja as linhas `Pulado`: se o texto não foi aprovado, a pessoa precisa aprovar (skill `criar-conteudo`); para refazer arte que já existe, use `--post <id>` ou `--refazer` |
| `o texto ainda não foi aprovado` / `já foi publicado` | status do post | não gere; explique à pessoa |
| `reel é só roteiro` | formato `reel` | reels não têm artes nesta skill |
| `Falta o arquivo ... visual.json` | marca sem configuração visual | rode a skill `configurar-marca` |
| `visual.json: cores.X inválida` / `falta cores.X` | cor fora do formato `#RRGGBB` ou ausente | `configurar-marca` |
| `a fonte '...' não existe` | `fontes.titulo` ou `fontes.texto` aponta para arquivo que não está na pasta | copie o arquivo para `assets/fontes/` ou troque por `null` (`configurar-marca`) |
| `aponta para fora da pasta da marca` | caminho com `..` ou de outro disco | copie o arquivo para dentro de `marcas/<marca>/assets/` e aponte para lá |
| `'n' dos slides deve ir de 1 a N` | numeração com buraco | corrija o post (`criar-conteudo`) |

## Texto

| Mensagem (resumo) | Causa | O que fazer |
|---|---|---|
| `o texto não cabe: faltam cerca de N px` | texto grande demais para o layout, mesmo no menor tamanho | mostre à pessoa o slide e quanto falta; proponha uma versão mais curta ou outro layout; só mude com o ok dela (`criar-conteudo`) |
| `a palavra '...' é mais larga que a área segura` | palavra ou endereço comprido | trocar ou dividir a palavra |
| `a fonte não desenha estes caracteres` | emoji ou símbolo que a fonte não tem | trocar por palavra |
| `o texto cita 'Fonte:'` | fonte escrita na arte | tirar do slide; a fonte fica em `fontes` e `fonte_interna` |
| `a chamada tem N palavras; o padrão é até 12` | capa longa | encurtar (`criar-conteudo`) |
| `o campo 'texto' da capa não é desenhado` | a capa mostra só a chamada | normal; se o apoio é importante, use um slide `texto` depois da capa |

## Imagens

| Mensagem (resumo) | Causa | O que fazer |
|---|---|---|
| `a imagem prevista não foi encontrada` | `foto` sem arquivo, ou `gerada` ainda não importada | para `foto`, ponha o arquivo em `assets/fotos/`; para `gerada`, `imagens.py prompts` e `importar` |
| `é ampliada Nx ... pode ficar borrada` | imagem menor que a área | gere ou use uma imagem maior |
| `Não consegui abrir a imagem` | arquivo corrompido ou formato sem suporte (HEIC, por exemplo) | converta para JPG ou PNG |
| `O slide ... usa uma foto aprovada, não uma imagem gerada` | `importar` em slide de foto | coloque a foto em `assets/fotos/` e aponte no post |
| `o layout 'X' não usa imagem; ela foi ignorada` | `imagem` em slide que não é `capa` nem `imagem` | mude o layout do slide ou tire a imagem |
| `a chamada tem contraste N:1 sobre a imagem` | imagem clara embaixo do título | `--variante faixa`, ou imagem mais escura embaixo |

## Marca, logo e cores

| Mensagem (resumo) | Causa | O que fazer |
|---|---|---|
| `o logo tem contraste N:1 ... quase não aparece` | o logo cai sobre uma parte da imagem de cor parecida | `--foco` para mudar o corte, outra imagem ou outro canto (`configurar-marca`). Sem caixa nem halo |
| `o logo tem pouco contraste (N:1)` | aviso informativo | confira no celular |
| `O visual.json só tem o logo para fundo claro` | falta a outra versão do logo | os slides saíram no tema que o logo aceita; para usar os dois temas, `configurar-marca` com o outro arquivo |
| `O arquivo do logo ... não existe` | caminho errado ou arquivo apagado | `configurar-marca` |
| `O logo X não tem transparência nem fundo de uma cor só` | logo com foto ou degradê atrás | use um PNG com fundo transparente |
| `O fundo liso do logo X foi removido` | o PNG tinha fundo de uma cor | informativo; o ideal é entregar PNG transparente |
| `As cores 'texto' e 'fundo' ... contraste N:1` | paleta com pouco contraste | `configurar-marca` |
| `A fonte X é variável` | arquivo com vários pesos | use os arquivos estáticos (Regular e Bold) |

## Depois de gerar

| Mensagem (resumo) | Causa | O que fazer |
|---|---|---|
| `NÃO MARCADO ... o texto, os itens ou o layout do slide mudaram depois da arte` | o post foi editado depois de gerar | rode o `renderizar.py` de novo para esse post |
| `NÃO MARCADO ... o visual da marca (visual.json, logo, fonte ou avatar) mudou depois desta arte` | a marca foi reconfigurada depois de gerar | `renderizar.py --refazer --motivo "<o que mudou>"` (a galeria também marca essas artes como desatualizadas) |
| `NÃO MARCADO ... o arquivo da arte mudou depois do manifesto` | alguém mexeu num PNG à mão | rode o `renderizar.py` de novo (a arte é sempre gerada pelo script) |
| `NÃO MARCADO ... a imagem foi trocada depois da arte` | outra imagem no lugar da usada | rode o `renderizar.py` de novo |
| `NÃO MARCADO ... aviso pendente` | há `ATENÇÃO` no manifesto | resolva o aviso; só use `--aceitar-avisos` se a pessoa decidir conviver com ele |
| `aprovação invalidada: as artes mudaram depois do ok da pessoa` | a arte de um post `aprovado` ou `agendado` mudou | normal: o post voltou para `arte_pronta`, sem `aprovacao` e sem `agendado_para` (o `historico` registra o hash antigo e o horário cancelado); precisa de nova aprovação e novo agendamento (publicar-instagram) |
| `já foi aprovado/agendado; refazer a arte invalida a aprovação` | post aprovado | só com pedido da pessoa e `--refazer-aprovado` |
| Galeria sem imagens | o `galeria.html` foi movido | deixe o arquivo dentro de `conteudo/<lote>/`, ao lado de `artes/`, ou gere de novo com `galeria.py` |
| `--raiz`, `--pasta-marcas` e `ESTUDIO_MARCAS` | uso avançado e testes | `--raiz <pasta do projeto>` usa `<pasta>/marcas`; `--pasta-marcas` e `ESTUDIO_MARCAS` apontam direto para a pasta das marcas. No uso normal, nenhum é necessário (não use `--raiz` e `--pasta-marcas` juntos) |

## Se nada ajudar

Rode com `--simular` e leia a saída inteira; abra o `manifesto.json` do post; confira o `visual.json`. Se desconfiar da instalação, rode `python -X utf8 skills/gerar-artes/scripts/autoteste.py`: ele gera artes de uma marca fictícia numa pasta temporária e diz o que falhou. Não edite PNGs à mão nem copie artes de outro lugar: a arte sempre vem do `renderizar.py`, para o manifesto e o hash de aprovação baterem.
