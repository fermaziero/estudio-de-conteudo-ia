# Transformar respostas vagas e feedback em regras verificáveis

Leia este arquivo quando a resposta da pessoa for vaga e sempre que for registrar um feedback. Uma regra só serve se outro agente, lendo só aquela linha, consegue produzir o que a pessoa quer e consegue conferir se foi obedecida. Os exemplos são fictícios.

## O que torna uma regra verificável

1. **Dá para conferir olhando o post ou a arte.** Tem algo observável: um número, uma palavra, a presença ou a ausência de um elemento.
2. **Tem alcance.** Diz onde vale: sempre, só em certo tipo de post, só neste post.
3. **Tem exceção quando existe.** "Sem emoji, exceto no último slide."
4. **Está escrita no positivo quando possível.** "Capa só com a chamada" ajuda mais do que "capa sem poluição".
5. **Tem data.** Quando mudou, para saber qual regra é mais nova.
6. **Passa no teste do outro agente:** se um agente que não viu a conversa seguir só esta linha, entrega o que a pessoa quer?

## Vago para verificável

| O que a pessoa disse | Regra verificável (depois de esclarecer) |
|---|---|
| "Ficou poluído." | Capa com no máximo 12 palavras e nenhum elemento além da imagem e do logo. |
| "Quero um tom mais humano." | Frases de até 20 palavras; fala com "você"; sem "prezados" nem "outrossim". |
| "Não prometa resultado." | Nunca usar "garantido", "sem risco" nem "em X dias você terá"; descrever o que o serviço faz, não o que o cliente vai ganhar. |
| "Cuidado com cliente." | Nenhum nome, foto ou dado de cliente sem linha na tabela de autorizações de `regras.md`. |
| "Mais bonito." | Perguntar o que incomoda e propor 2 ou 3 mudanças concretas (cor, tamanho de letra, espaço) para a pessoa escolher. |
| "Não gosto dessa foto." | Ajuste pontual neste post: trocar a foto. Perguntar se há um tipo de foto a evitar sempre. |
| "Muito texto." | Perguntar em qual slide e o que cortar; regra possível: no máximo 30 palavras por slide interno. |
| "Fale menos de dinheiro." | Não usar cifrão, moeda nem valores nas artes; valores só na conversa no direct. |

## Como perguntar para esclarecer

Uma pergunta só, com opções para a pessoa escolher. Funciona melhor do que "o que você quis dizer?".

- "O que incomodou mais: a quantidade de texto, o tamanho das letras ou a imagem?"
- "Isso vale para todos os posts ou só para este tipo de post?"
- "Prefere que eu corte o texto ou que eu divida em dois slides?"
- "Tem alguma exceção, como o último slide?"

Se a pessoa não souber, proponha uma regra concreta, marque `(a confirmar)` e peça um sim ou um não.

## Alcance

| Alcance | Como escrever | Onde vai |
|---|---|---|
| Sempre | "Vale para todos os posts." | arquivo de regra correspondente |
| Um tipo de post | "Vale para carrosséis do pilar educativo." | arquivo de regra, com o alcance escrito |
| Só este post | "Ajuste pontual no post `<id>`." | só `feedback.md`, com o arquivo do post na coluna Arquivo (ou `—`) |

Não generalize além do que a pessoa disse. "Não gostei dessa foto" não é "nunca use fotos". Na dúvida, pergunte o alcance.

## Para onde vai cada tipo de feedback

| O feedback é sobre | Arquivo | Observação |
|---|---|---|
| cor, tamanho, posição, aparência da arte | `padrao-visual.md` (seção "Ajustes pedidos pela pessoa") e, se for um dado técnico, `visual.json` | cores, logo, proporção, rodapé, numeração e tamanho das letras (`tipografia`) moram em `visual.json` |
| jeito de escrever, palavras, emoji, humor | `marca.md` (Tom de voz) | |
| o que não pode ser dito, assunto proibido, dado ou pessoa que não aparece | `regras.md` | autorização de terceiros vai na tabela de `regras.md` |
| o que oferecer no fim do post, link, WhatsApp | `marca.md` (Chamadas disponíveis, Links oficiais) | |
| meta, ritmo, pilar, objetivo | `estrategia.json` | só com o ok explícito da pessoa; veja `estrategia-metas-e-ritmo.md` |
| um fato (novo serviço, novo link, mudança de endereço) | o arquivo do fato | não é feedback: atualize a data da ficha, sem linha em `feedback.md` |

## Passo a passo para registrar

1. **Copie a frase literal**, com os erros de digitação que ela tiver. Não resuma, não corrija, não traduza.
2. **Entenda o alcance** (pergunte se não estiver claro) e **o que exatamente incomodou**.
3. **Escreva a regra** de forma verificável, com data e alcance.
4. **Veja se já existe regra parecida ou contrária.** Se existir, a nova substitui a antiga no arquivo de regra e você avisa a pessoa; a linha antiga continua em `feedback.md`. Nunca deixe duas regras que se contradizem. Se a pessoa já disse a mesma coisa antes, a regra não foi aplicada ou ficou vaga: reescreva-a mais clara e diga isso a ela.
5. **Guarde a versão anterior** do arquivo que vai mudar (`guardar_versao.py`).
6. **Edite o arquivo de regra.** Mude só o necessário.
7. **Registre** (`registrar_feedback.py`) com a frase, o que mudou e o arquivo.
8. **Conte à pessoa em 2 ou 3 linhas:** a regra nova, onde ela vale e o que não muda sozinho (posts e artes que já existem não mudam; ofereça ajustar o lote atual).
9. Rode `validar_marca.py` se mexeu em `visual.json` ou `estrategia.json`.

## Exemplo completo

A pessoa diz: "nao gostei de capa com muita palavra, quero so a pergunta".

1. Frase literal: `nao gostei de capa com muita palavra, quero so a pergunta`.
2. Alcance: você pergunta "Vale para todos os posts?". Ela responde "sim".
3. Regra: "2026-10-22 (vale para todos os posts): a capa tem só a pergunta ou a chamada, com até 12 palavras, sem texto de apoio. O dado que sustenta a chamada vai para o segundo slide e para a legenda."
4. Conflito: o padrão recomendado já pede capa só com a chamada; a regra reforça e acrescenta "pergunta". Sem contradição.
5. Comandos:

```
python -X utf8 skills/configurar-marca/scripts/guardar_versao.py --marca minha-marca --motivo ajuste-capa padrao-visual.md
python -X utf8 skills/configurar-marca/scripts/registrar_feedback.py --marca minha-marca --frase "nao gostei de capa com muita palavra, quero so a pergunta" --mudou "capa só com a pergunta ou a chamada, até 12 palavras" --arquivo padrao-visual.md
```

6. Resposta à pessoa: "Anotei. A partir de agora a capa de todos os posts leva só a pergunta ou a chamada, com até 12 palavras. O dado vai para o segundo slide. Os posts que já estão prontos não mudam sozinhos: quer que eu ajuste a capa do lote atual?"
