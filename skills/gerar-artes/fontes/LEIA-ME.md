# Fonte livre que acompanha a skill

A skill `gerar-artes` usa a fonte **Manrope** quando a marca não aponta uma fonte própria (`fontes: null` no `visual.json`).

| Arquivo | Peso | Uso no gerador |
|---|---|---|
| `Manrope-Regular.ttf` | 400 | textos de apoio e itens |
| `Manrope-Bold.ttf` | 700 | títulos e trechos em destaque |
| `Manrope-ExtraBold.ttf` | 800 | numerais de listas e aspas grandes |
| `OFL.txt` | — | licença SIL Open Font License 1.1, obrigatória junto com as fontes |

## Licença: diferente da licença do projeto

- O código do projeto é MIT (arquivo `LICENSE` na raiz). **As fontes desta pasta não são MIT**: têm licença própria, a **SIL Open Font License, Versão 1.1 (OFL)**, que vale para os três `.ttf` e está em `OFL.txt`.
- A OFL permite usar, copiar, modificar e redistribuir a fonte, inclusive em projetos comerciais, desde que cada cópia leve o `OFL.txt` e o aviso de direitos autorais e que a fonte não seja vendida sozinha.
- Quem redistribuir este projeto (ou só esta skill) deve manter a pasta `fontes/` inteira, com o `OFL.txt`.
- O texto da OFL diz que a exigência não vale para documentos criados com a fonte: **as artes geradas não herdam a licença da fonte**.
- O aviso oficial é "Copyright 2018 The Manrope Project Authors (https://github.com/googlefonts/manrope)". Ele não declara nenhum "Reserved Font Name", então manter o nome Manrope é permitido.

## Origem: distribuição pelo Google Fonts

A Manrope é distribuída pelo **Google Fonts sob a OFL 1.1**. Conferido em fontes oficiais:

| O que | Onde | Conferido em |
|---|---|---|
| Metadados da família: `name: "Manrope"`, `designer: "Mikhail Sharanda"`, `license: "OFL"`, `date_added: "2019-10-03"`, `repository_url: "https://github.com/googlefonts/manrope"` | https://github.com/google/fonts/blob/main/ofl/manrope/METADATA.pb | 2026-10-29 |
| Texto da licença (`OFL.txt`, 4.387 bytes, igual ao desta pasta) | https://github.com/google/fonts/blob/main/ofl/manrope/OFL.txt | 2026-10-28 |
| Mesmo `OFL.txt` no repositório do projeto (ramo `master`), comparado byte a byte com o do Google Fonts | https://github.com/googlefonts/manrope | 2026-10-28 |
| Página da família no Google Fonts | https://fonts.google.com/specimen/Manrope | 2026-10-28 |

## O que está gravado dentro dos TTF (tabela `name`)

Lida em **2026-10-29** com um leitor simples em Python puro (só `struct`; registros de Windows, inglês, UTF-16). Os três arquivos têm os mesmos valores, exceto o peso:

| Campo (`nameID`) | Valor nos três arquivos |
|---|---|
| Copyright (0) | Copyright 2019 The Manrope Project Authors (https://github.com/googlefonts/manrope) |
| Versão (5) | Version 4.505 |
| Fabricante (8) | Mikhail Sharanda |
| Designer (9) | Mikhail Sharanda |
| URL do fabricante (11) | http://gent.media |
| Descrição da licença (13) | This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org |
| URL da licença (14) | https://openfontlicense.org |
| Família tipográfica (16) | Manrope |
| Família (1) e nome completo (4) | Manrope ExtraLight (resíduo, veja abaixo) |
| Peso (`OS/2`, `usWeightClass`) | 400 (Regular), 700 (Bold) e 800 (ExtraBold) |
| Fonte variável (`fvar`) | não: são fontes estáticas |

O aviso de copyright dentro dos TTF diz 2019 e o `OFL.txt` oficial diz 2018. Os dois textos foram mantidos como vieram.

Para repetir a leitura (a partir da raiz do projeto):

```python
import struct
from pathlib import Path

def ler_nomes(caminho):
    dados = Path(caminho).read_bytes()
    tabelas = {}
    for i in range(struct.unpack(">H", dados[4:6])[0]):
        tag, _, desloc, tam = struct.unpack(">4sIII", dados[12 + 16 * i:28 + 16 * i])
        tabelas[tag.decode("latin-1")] = desloc
    base_nomes = tabelas["name"]
    _, quantos, inicio = struct.unpack(">HHH", dados[base_nomes:base_nomes + 6])
    nomes = {}
    for i in range(quantos):
        plataforma, _, idioma, id_nome, tam, rel = struct.unpack(">HHHHHH", dados[base_nomes + 6 + 12 * i:base_nomes + 18 + 12 * i])
        if plataforma == 3 and idioma == 0x409:
            nomes[id_nome] = dados[base_nomes + inicio + rel:base_nomes + inicio + rel + tam].decode("utf-16-be")
    return nomes

for arquivo in sorted(Path("skills/gerar-artes/fontes").glob("*.ttf")):
    nomes = ler_nomes(arquivo)
    print(arquivo.name, "|", nomes[0], "|", nomes[5], "|", nomes[9], "|", nomes[14])
```

## Integridade (SHA-256, conferido em 2026-10-29)

```text
17515a5d245264c889c32a1f53d2c9d2181f789a53f061f96c468ead9423e441  Manrope-Regular.ttf    (97.500 bytes)
9aa067a05fcb22d951542ad18479918ab77c01d924301ebb0552a3a6bb98894a  Manrope-Bold.ttf       (97.520 bytes)
69912b008bd3afb947383f151bca82fdddcd8890712676d6ec29699617f2f79c  Manrope-ExtraBold.ttf  (98.080 bytes)
58172e0c0fac2cda8a37b348164bb55e44b0e69051e557e92b1d3f6910141f7b  OFL.txt                (4.387 bytes)
```

## Como foi conferido que são mesmo Manrope (2026-10-28)

- Os campos acima (copyright, designer, URLs e licença) apontam para o projeto oficial da Manrope.
- As medidas de várias letras (largura e contorno de A, a, R, g, H, n, o, ã, Ç e 1) nos pesos 400 e 700 são idênticas às de uma cópia independente de Manrope 4.504 (webfonts).
- O desenho engorda de um arquivo para o outro, de acordo com o peso do `OS/2`. O nome interno "Manrope ExtraLight" nas famílias (1) e (4) é o nome do peso padrão da fonte variável original e não foi atualizado quando os arquivos estáticos foram gerados. O peso real é o da primeira tabela.
- Nenhum TTF novo foi baixado: os três arquivos desta pasta são os que a skill já trazia. Só se leu a tabela `name` e se conferiu a licença nas fontes oficiais.
- Para instalar a fonte no computador, prefira a família oficial: https://fonts.google.com/specimen/Manrope.

## Usar outra fonte

Coloque os arquivos `.ttf` ou `.otf` em `marcas/<marca>/assets/fontes/` e aponte para eles no `visual.json` (`fontes.titulo` para títulos e destaques, `fontes.texto` para o apoio). Use arquivos estáticos (um por peso) e só fontes com licença que permita o uso em imagens. Veja `skills/gerar-artes/referencias/visual-json.md`.
