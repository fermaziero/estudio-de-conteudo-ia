# Revisão do lote 2026-11-03-exemplo

> Exemplo fictício: a marca, as pessoas e as frases do lote não existem. Este parecer mostra o formato da revisão independente, com duas rodadas (a primeira, com os dois posts em "ajustar", está em `_antes-revisao-2026-10-28/revisao.md`).

- **Data:** 2026-10-28
- **Quem revisou:** revisor independente (outro agente, que não escreveu os posts). Segunda rodada: a primeira está em `_antes-revisao-2026-10-28/revisao.md`.
- **Base consultada:** marca.md · regras.md · padrao-visual.md · feedback.md · estrategia.json · pautas.md · posts/*.json (versões novas; as da rodada anterior estão em posts/_antes-ajustes-da-revisao/). Também li visual.json, regras-de-escrita.md e campos-do-post.md.
- **Validação automática (`validar_posts.py`):** passou sem erros, antes e depois de gravar esta revisão (0 erros, 0 avisos, 1 pendência em confirmar[])
- **Fontes externas abertas:** nenhuma. A marca é fictícia e `fontes[]` está vazio nos dois posts. Abri de novo marca.md, regras.md, padrao-visual.md, feedback.md e estrategia.json em 2026-10-28 e conferi cada origem citada nas notas internas.

## Resumo

| # | Post | Veredito | Em uma linha |
|---|---|---|---|
| 1 | Separe a conta da empresa da sua (`2026-11-03-1-contas-separadas`) | aprovar | Os 8 ajustes da rodada anterior foram feitos e não criaram erro novo. O texto pode ir para a pessoa; o post só pode ser publicado depois de resolvida a exigência legal do slide 4. |
| 2 | Conversa de diagnóstico de 20 minutos (`2026-11-03-3-conversa-de-diagnostico`; é a pauta 3) | aprovar | Os 4 ajustes foram feitos: a capa leva só a pergunta, "regime tributário" é explicado e a chamada é uma só, no direct. Sem pendência. |

**Bloqueia a publicação:**
- Post 1: 1 pendência em confirmar[]. "NÃO VERIFICADO: a exigência legal de guardar notas fiscais e comprovantes por um prazo (slide 4, terceiro passo) — conferir na página oficial da Receita Federal, registrar a fonte em fontes e só então publicar".
- Post 2: nada.

A pendência do Post 1 não impede a pessoa de aprovar o texto, mas o post só sai quando ela for resolvida e o item sair de confirmar[]. Se a página oficial não for aberta a tempo, a alternativa é tirar a exigência legal do texto (por exemplo, "O seu contador diz por quanto tempo."); quem decide é a pessoa.

## Post 1 · Separe a conta da empresa da sua

**Veredito: aprovar**

**Conferência dos ajustes da rodada anterior** (todos feitos):

| # | O que foi pedido | Situação |
|---|---|---|
| 1 | Slide 4, 3º cartão: exigência legal sem fonte, sem prazo, "notas" ambíguo | Feito. Virou o 3º passo: "Guarde notas fiscais e comprovantes pelo prazo da lei. O seu contador diz qual é." A afirmação continua em confirmar[] (agora com "notas fiscais" e "terceiro passo") e quem lê sabe o que fazer. |
| 2 | Slide 5: título sem artigo | Feito, de outro jeito: a frase foi trocada por "A conta da empresa é da empresa. A sua conta é sua.", sem o problema de artigo. O texto alternativo acompanha. |
| 3 | Slide 4: layout e passo 2 | Feito. O slide 4 é lista numerada e o passo 2 diz de onde para onde transferir ("Defina quanto você tira por mês e transfira da conta da empresa para a sua…"). O slide 3 (sinais) passou a cartões, como o checklist novo pede. |
| 4 | Slide 6: "o relatório do mês" sem aviso | Feito. Agora é "o relatório mensal que a gente entrega", e o "resultado de verdade" deixou de se repetir no slide. |
| 5 | Nota de origem do slide 3 | Feito. Diz "exemplos criados para este post a partir da dor…", e a dor existe em marca.md (Para quem, Dores). |
| 6 | Nota de origem do slide 5 | Feito. Diz "frase nova escrita para este post, para a pessoa aprovar". |
| 7 | Legenda: "tipo da sua empresa" | Feito. Agora é "depende do caso da sua empresa", o que regras.md diz. Ver a sugestão sobre a nota. |
| 8 | Slide 6: prompt da imagem | Feito. Termina com "Sem texto, sem letras, sem logos."; a cena nova (carteira e pasta verde-petróleo) não pede pessoas, moedas nem dinheiro. |

Mudaram também, sem pedido: a legenda ficou mais curta, sem "É comum no começo" nem "Passe os slides, veja…, comece…"; "o caminho é simples" virou "são três passos"; o objetivo perdeu o "simples". Conferi: nada disso criou problema.

**Checklist completo na versão nova:**

| Item | Resultado | Observação |
|---|---|---|
| Fatos e fontes | ok (pendência registrada) | Abri marca.md, regras.md e estrategia.json e conferi as origens citadas: a dor "misturar a conta pessoal com a da empresa" (marca.md, Para quem) existe e sustenta os exemplos do slide 3 e a legenda; o relatório mensal em linguagem simples (slide 6) é prova autorizada, informada em 2026-10-20 (8 dias atrás); "cada empresa é um caso" está em regras.md; o movimento "Publicar 3 carrosséis…" está em estrategia.json. Frase nova e exemplos aparecem declarados como tais. A exigência legal do slide 4 ("pelo prazo da lei") está em confirmar[]: não a verifiquei e não posso dizer que está certa. |
| Promessa da capa × entrega | ok | A capa (9 palavras) promete que a pessoa vai reconhecer se mistura as contas. O slide 3 entrega quatro sinais e o slide 4 entrega três passos, como a pauta prometia. Nenhum número ou resultado é prometido. |
| Clareza (teste do leigo) | ok | Passos numerados, com objeto claro; sinais em cartões; o slide 6 diz de quem é o relatório. Sem termo solto, e os slides 5 e 6 dizem coisas diferentes (princípio e benefício). Ver a sugestão sobre "mostra o que é da empresa". |
| Português | ok | Reli todos os textos novos (títulos, itens, legenda e textos alternativos): sem erro de concordância, crase, pontuação, artigo ou gerundismo; tratamento "você" em todo o post. |
| Regras da marca | ok | Sem palavra proibida, promessa vetada nem tema proibido. Tom de balcão ("sem enrolação", "na prática"); o pilar educativo existe; a capa tem só a pergunta (feedback de 2026-10-22); a imagem não pede moedas, dinheiro nem pessoas. A legenda não usa mais "é simples" nem "é comum", que as regras de escrita pedem para evitar sem origem. |
| Dados sensíveis e LGPD | ok | Sem nome, documento, cliente, equipe ou dado de terceiros. Os sinais do slide 3 são hipóteses em segunda pessoa. O prompt não pede pessoas, marcas de terceiros, moedas nem dinheiro. |
| Chamada × etapa do funil | ok | "Salvar" é chamada de atração e consta em marca.md. A mesma frase está em chamada e no fim da legenda, e o slide 7 traz a versão curta (8 palavras). O parágrafo antes da chamada não manda fazer nada. |
| Tamanhos e limites | ok | Validação sem erros nem avisos. Capa com 9 palavras (máximo 12); legenda com 527 de 2.200 caracteres e primeira linha com 94; 3 hashtags, sem "#" e sem repetir no texto; 7 slides, cartões com 4 itens, lista com 3; sem "Fonte:" nem link; o prompt termina com "Sem texto, sem letras, sem logos." O slide mais cheio é o 4 (54 palavras; o validador avisa a partir de 60). |
| Texto alternativo | ok | Presente nos 7 slides, descreve o que aparece e o texto escrito, e acompanha as mudanças (cartões, lista numerada, frase nova, imagem nova). Único ponto: o do slide 6 tem três frases (ver sugestão). |

**Sugestões** (opcionais, não bloqueiam):

- Slide 6, apoio: "mostra o que é da empresa" ficou vago. "Mostra só o que é da empresa" ou "mostra o resultado da empresa" diz mais e combina com o título.
- Slide 6, texto alternativo: tem três frases (imagem, título e apoio) e o checklist pede uma ou duas. Una título e apoio numa frase só.
- Nota em fontes_legenda_internas, 2º item: liga "o contador ajuda a definir" a regras.md, mas regras.md diz "sem orientação individual" e "a resposta é convidar para conversar no direct". Mandar a pessoa ao contador é escolha editorial, para manter uma chamada só; vale escrever isso na nota.
- Slide 5: são duas frases numa citação que o guia descreve como "uma frase". "A conta da empresa é da empresa; a sua conta é sua." resolve.
- Slide 4: ficou com 54 palavras; o passo 2 tem 19 palavras e o passo 3 tem duas frases. Encurtar deixa o slide mais leve.
- Textos alternativos das capas (dos dois posts): o nome do escritório aparece no canto e não está descrito.

## Post 2 · Conversa de diagnóstico de 20 minutos

**Veredito: aprovar**

**Conferência dos ajustes da rodada anterior** (todos feitos):

| # | O que foi pedido | Situação |
|---|---|---|
| 1 | Capa com pergunta e convite | Feito. A capa tem só a pergunta ("Dúvida sobre o regime tributário da sua empresa?", 8 palavras) e o texto alternativo acompanha. O convite foi para o fim da legenda. A mudança está registrada em pautas.md. |
| 2 | "Respondemos" quebrando o "a gente" | Feito, por remoção: o parágrafo sobre resposta no WhatsApp saiu junto com o canal, e o texto fala só em "a gente". |
| 3 | "regime de imposto" sem explicação | Feito. O termo virou "regime tributário" (o de marca.md) e é explicado no 2º parágrafo: "O regime tributário é a forma como a empresa paga imposto." |
| 4 | Chamada sem caminho até o WhatsApp | Feito, trocando o canal: "Chame no direct e conte o que a sua empresa faz." No direct não há caminho a explicar, e "chamar no direct" consta em Chamadas disponíveis (conversão). |

Mudaram também, sem pedido, e conferi: "sozinho" virou "sem ajuda"; "por ela" virou "por você"; saiu "Você conta como a sua empresa funciona" (detalhe que marca.md não traz); o objetivo passou a dizer "regime tributário".

**Checklist completo na versão nova:**

| Item | Resultado | Observação |
|---|---|---|
| Fatos e fontes | ok | Abri marca.md e regras.md: a conversa de diagnóstico de 20 minutos (O que oferece, item 4) e a dor "dúvida se o regime tributário atual é o melhor" (Para quem) existem; "cada empresa é um caso", "sem orientação individual" e "sem promessa de redução de imposto" estão em regras.md. A frase "O regime tributário é a forma como a empresa paga imposto" é uma definição geral, declarada como escrita para o leigo, sem lei, prazo nem valor; não a verifiquei em fonte oficial e não a trato como dado. Saiu o prazo de resposta no WhatsApp, que só valia para o WhatsApp. Sem pendência. |
| Promessa da capa × entrega | ok | A capa pergunta sobre o regime tributário da empresa; a legenda explica o termo, avisa que um post não indica o regime de ninguém e oferece a conversa de diagnóstico. Não promete economia nem resposta pronta. |
| Clareza (teste do leigo) | ok | O termo central é explicado na legenda (a capa só pode ter a pergunta, pela regra da marca). "Diagnóstico" é explicado na mesma frase. Ver a sugestão sobre a frase longa do 3º parágrafo. |
| Português | ok | Reli capa, legenda e texto alternativo: sem erro de concordância, crase, pontuação ou artigo; tratamento "você" e voz "a gente" sem mistura com "nós". |
| Regras da marca | ok | Sem palavra proibida, promessa de redução de imposto nem orientação individual. A capa tem só a pergunta, como a regra de 2026-10-22 (padrao-visual.md) e o feedback pedem, e a arte não leva chamada (post único). Tom de balcão e "sem enrolação"; o pilar ofertas existe. |
| Dados sensíveis e LGPD | ok | Sem nome, telefone, e-mail, cliente ou dado de terceiros. Sem imagem. |
| Chamada × etapa do funil | ok | "Chamar no direct" é chamada de conversão e consta em marca.md. É uma só, igual em chamada e no fim da legenda. Post único não tem último slide, e a capa leva só o gancho. Nenhum pedido antes da chamada. |
| Tamanhos e limites | ok | Validação sem erros nem avisos. Capa com 8 palavras (máximo 12); legenda com 469 de 2.200 caracteres e primeira linha com 97; 2 hashtags, sem "#" e sem repetir no texto; 1 slide, como post único pede; sem "Fonte:" nem link. |
| Texto alternativo | ok | Presente, em uma frase, e descreve o fundo e a pergunta da capa. |

**Sugestões** (opcionais, não bloqueiam):

- Ao pedir a aprovação, lembre à pessoa que a capa e o canal da chamada mudaram em relação à pauta que ela aprovou (o convite saiu da capa e o WhatsApp virou direct). A explicação está em pautas.md, "Ajuste na escrita".
- Legenda, 3º parágrafo: a frase "O que a gente faz é uma conversa de diagnóstico…" tem 30 palavras e parece dizer que é só isso que o escritório faz (marca.md lista outros serviços). Algo como "A gente oferece uma conversa de diagnóstico de 20 minutos. Ela serve para entender a situação da sua empresa e dizer o que a gente pode fazer por você." fica mais curto e numa voz só.
- O post não diz se a conversa tem custo nem como ela acontece (vídeo, telefone ou presencial), e marca.md também não; a pauta já avisa. Não escreva "grátis" nem "sem compromisso" sem a pessoa confirmar.
- pautas.md diz que marca.md "não define o caminho até o WhatsApp", mas marca.md lista o número em "Links oficiais". A escolha do direct continua válida (a legenda não leva link e a arte não leva chamada); só o motivo escrito está impreciso.
- Texto alternativo da capa: o nome do escritório aparece no canto e não está descrito.
