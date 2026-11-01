# Revisão do lote 2026-11-03-exemplo

- **Data:** 2026-10-28
- **Quem revisou:** revisor independente (outro agente, que não escreveu os posts)
- **Base consultada:** marca.md · regras.md · padrao-visual.md · feedback.md · estrategia.json · pautas.md · posts/*.json. Também li visual.json e, para conferir as regras que quem escreveu devia seguir, criar-conteudo/referencias/regras-de-escrita.md e campos-do-post.md.
- **Validação automática (`validar_posts.py`):** passou sem erros, antes e depois de gravar esta revisão (0 erros, 0 avisos, 1 pendência em confirmar[])
- **Fontes externas abertas:** nenhuma. A marca é fictícia e os posts não registram endereço em `fontes[]`. Conferi cada afirmação contra marca.md, regras.md e pautas.md em 2026-10-28.

## Resumo

| # | Post | Veredito | Em uma linha |
|---|---|---|---|
| 1 | Separe a conta da empresa da sua (`2026-11-03-1-contas-separadas`) | ajustar | Sem promessa nem tema proibido, mas com 8 ajustes: a exigência legal do slide 4 está sem fonte (bloqueia a publicação) e falta o artigo no título do slide 5. |
| 2 | Conversa de diagnóstico de 20 minutos (`2026-11-03-3-conversa-de-diagnostico`; é a pauta 3, a pauta 2 foi adiada) | ajustar | A capa tem pergunta e convite (a regra da marca pede só um), "Respondemos" quebra a voz de "a gente" e a chamada não diz como chegar ao WhatsApp. |

**Bloqueia a publicação:**
- Post 1: 1 pendência em confirmar[]. "NÃO VERIFICADO: a exigência legal de guardar notas e comprovantes por um prazo (slide 4, terceiro cartão) — conferir na página oficial da Receita Federal, registrar a fonte em fontes e só então publicar".
- Post 2: nada em confirmar[].

Os dois posts precisam dos ajustes abaixo antes de a pessoa aprovar o texto.

## Post 1 · Separe a conta da empresa da sua

**Veredito: ajustar**

| Item | Resultado | Observação |
|---|---|---|
| Fatos e fontes | ajustar | Prova usada no slide 6 (relatório mensal em linguagem simples) está autorizada em marca.md, informada em 2026-10-20 (8 dias atrás). Pendente: a exigência legal do slide 4, sem fonte oficial. Está certo que esteja em confirmar[] como NÃO VERIFICADO; eu não a confirmei e não posso dizer que está certa. Origens mal descritas nos slides 3 e 5 e na legenda: ajustes 1, 5, 6 e 7. |
| Promessa da capa × entrega | ok | A capa (9 palavras) promete que a pessoa vai reconhecer se mistura as contas. O slide 3 entrega os sinais e o slide 4 entrega os três passos, como a pauta prometia. Nenhum número ou resultado é prometido. O 3º passo depende do ajuste 1. |
| Clareza (teste do leigo) | ajustar | Slide 4: o 3º cartão não diz qual prazo; "notas" pode ser lido como anotações; "Combine" e "transfira" não dizem com quem nem de onde para onde; passos em cartões, sem número. Slide 6: "o relatório do mês" aparece sem aviso. Ajustes 1, 3 e 4. |
| Português | ajustar | Slide 5: título sem artigo ("Dinheiro da empresa…" deve ser "O dinheiro da empresa…"), e o mesmo no texto alternativo. No resto não achei erro de concordância, crase, pontuação ou tratamento (é "você" em todo o post). Ajuste 2. |
| Regras da marca | ajustar | Não há palavra proibida, promessa vetada nem tema proibido. O tom é de balcão ("sem enrolação", "na prática"), o pilar educativo existe e a exigência legal foi para confirmar[], como regras.md manda. Ponto leve: a cena da imagem (mesa com pastas e plantas) é de banco de imagem, o que padrao-visual.md diz que a pessoa não quer, e o prompt não termina com "Sem texto, sem letras, sem logos." Ajuste 8. |
| Dados sensíveis e LGPD | ok | Sem nome, documento, cliente, equipe ou dado de terceiros. Os "sinais" do slide 3 são hipóteses em segunda pessoa, sem história reconhecível. O prompt da imagem não pede pessoas, marcas de terceiros, moedas nem dinheiro. |
| Chamada × etapa do funil | ok | "Salvar" é chamada de atração e consta em marca.md. A mesma frase está em chamada e no fim da legenda, e o slide 7 traz a versão curta (8 palavras) sem resumo. Ver a sugestão sobre o parágrafo antes da chamada. |
| Tamanhos e limites | ok | Validação sem erros nem avisos. Capa com 9 palavras (máximo 12); legenda com 665 de 2.200 caracteres; primeira linha com 94 caracteres (cabe antes do "mais"); 3 hashtags, sem "#" e sem repetir no texto; 7 slides, lista com 4 itens, cartões com 3; sem "Fonte:" nem link. O slide mais cheio é o 3 (48 palavras, uma ideia só). |
| Texto alternativo | ok | Presente nos 7 slides, descreve o que aparece e o texto escrito. Precisa acompanhar duas mudanças: slide 5 (título corrigido) e slide 6 (conferir de novo quando a imagem existir). |

**Ajustes pedidos** (só se o veredito for ajustar):

1. Slide 4, 3º cartão ("Guarde notas e comprovantes pelo prazo que a lei exige."): afirma uma exigência legal sem fonte oficial aberta e não diz qual é o prazo, então quem lê não sabe o que fazer. A pendência já está em confirmar[] como NÃO VERIFICADO e bloqueia a publicação. Abra a página oficial, registre em fontes[] (nome, endereço e data) e escreva o prazo exato, ou tire a exigência legal do texto, por exemplo: "Guarde notas fiscais e comprovantes num só lugar e pergunte ao seu contador por quanto tempo." Escreva "notas fiscais": só "notas" pode ser lido como anotações.
2. Slide 5, título: falta o artigo. "Dinheiro da empresa não é a sua conta corrente." deve ser "O dinheiro da empresa não é a sua conta corrente." Acerte também o texto_alternativo do mesmo slide.
3. Slide 4: os três itens são passos em sequência, mas o layout é cartoes (sem número). Troque para lista, que numera. No 2º passo, "Combine" não diz com quem e "transfira" não diz de onde para onde; sugestão: "Defina quanto você tira por mês e transfira esse valor da conta da empresa para a sua, sempre na mesma data."
4. Slide 6, apoio: "o relatório do mês" aparece sem aviso (relatório de quem?) e repete "resultado de verdade" do slide 2. Diga de quem é (por exemplo, "o relatório mensal que a gente entrega") ou use algo que quem não é cliente entenda, como "fica fácil ver o resultado do mês, em linguagem simples".
5. Nota de origem do slide 3 (fonte_interna): marca.md só registra a dor "misturar a conta pessoal com a da empresa"; as quatro situações não estão lá. Escreva que são exemplos criados para o post a partir dessa dor, sem dado nem caso real.
6. Nota de origem do slide 5 (fonte_interna): "Frase de posicionamento da marca" não existe em marca.md. Registre como frase nova escrita para este post, para a pessoa aprovar, ou use uma frase que já esteja em marca.md.
7. Legenda, 3º parágrafo: "O valor certo depende do tipo da sua empresa" é uma afirmação técnica sem origem registrada (a nota em fontes_legenda_internas explica só o "o contador ajuda a definir"). Use o que regras.md diz, "depende do caso da sua empresa", e corrija a nota.
8. Slide 6, imagem.prompt: termine com "Sem texto, sem letras, sem logos." (hoje termina em "Deixe o terço de baixo da imagem mais limpo."). A cena de mesa com pastas e plantas é de banco de imagem, o que padrao-visual.md diz que a pessoa não quer; troque por uma cena ligada à ideia de separar duas coisas.

**Sugestões** (opcionais, não bloqueiam):

- Os slides 5 e 6 dizem a mesma lição (separar) em duas frases de efeito seguidas. Considere juntar os dois ou cortar um.
- Slide 5: "dinheiro" e "conta corrente" são coisas diferentes na frase. "A conta da empresa não é a sua conta pessoal." diz o mesmo sem confundir.
- Legenda: "o caminho é simples" promete facilidade (as regras de escrita vetam "rápido e fácil"). "O caminho tem três passos" diz o mesmo sem prometer.
- Legenda: "É comum no começo" é uma generalização sem fonte. Se ficar, registre na nota de origem que é opinião da marca.
- Legenda: "Passe os slides, veja qual sinal é o seu e comece por um passo." tem três verbos antes da chamada de salvar. Deixe um só.
- Legenda e slides: várias frases têm de 22 a 27 palavras, e marca.md pede frases curtas. No slide 3, "O cliente paga por Pix na sua conta pessoal." é mais direto que "paga no Pix da sua conta pessoal".
- Texto alternativo da capa: o nome do escritório aparece no canto (o logo é só o nome escrito) e não está descrito.

## Post 2 · Conversa de diagnóstico de 20 minutos

**Veredito: ajustar**

| Item | Resultado | Observação |
|---|---|---|
| Fatos e fontes | ok | Tudo vem de marca.md e regras.md: conversa de diagnóstico de 20 minutos (O que oferece, item 4); resposta no WhatsApp em até 1 dia útil (prova autorizada, informada em 2026-10-20, 8 dias atrás); "cada empresa é um caso" (regras.md). Não há lei, prazo legal, alíquota nem número externo, então fontes[] e confirmar[] vazios estão coerentes. |
| Promessa da capa × entrega | ok | A capa promete uma conversa sobre a dúvida. A legenda entrega o que é, quanto dura, como funciona e em quanto tempo respondem. Não promete economia nem resposta pronta, e avisa que um post não indica o regime de ninguém. |
| Clareza (teste do leigo) | ajustar | "Regime de imposto" é o centro do post e não é explicado (marca.md fala em "regime tributário"). Ajuste 3. Ver também as sugestões sobre "por ela" e sobre custo e formato da conversa. |
| Português | ajustar | 4º parágrafo: "Respondemos" (nós) no meio de um texto todo em "a gente". Ajuste 2. No resto não achei erro de concordância, crase ou pontuação, e o tratamento é "você" em todo o post. |
| Regras da marca | ajustar | Não há palavra proibida, promessa de redução de imposto nem orientação individual (a legenda até avisa que "cada empresa é um caso"). Tom, pilar e prova usada estão certos. Problema: a capa tem uma pergunta e um convite, e a regra de 2026-10-22 (padrao-visual.md) e o feedback ("Quero só a pergunta.") pedem só um dos dois. Ajuste 1. |
| Dados sensíveis e LGPD | ok | Sem nome, telefone, e-mail, cliente ou dado de terceiros. Sem imagem. |
| Chamada × etapa do funil | ajustar | "Falar no WhatsApp" é chamada de conversão e consta em marca.md; é uma só, igual em chamada e no fim da legenda. Falta dizer como chegar ao WhatsApp (ajuste 4), e a arte diz "Converse com a gente" enquanto a chamada diz "Fale com a gente no WhatsApp…" (resolvido com o ajuste 1). |
| Tamanhos e limites | ok | Validação sem erros nem avisos. Capa com 10 palavras (máximo 12); legenda com 527 de 2.200 caracteres; primeira linha com 94 caracteres; 2 hashtags, sem "#" e sem repetir no texto; 1 slide, como post único pede; sem "Fonte:" nem link. |
| Texto alternativo | ok | Presente e descreve o fundo e o texto. Precisa acompanhar a capa quando ela mudar (ajuste 1). |

**Ajustes pedidos** (só se o veredito for ajustar):

1. Slide 1 (capa) e texto_alternativo: a arte tem uma pergunta e um convite ("Dúvida sobre o regime de imposto? Converse com a gente."). A regra de 2026-10-22 em padrao-visual.md e o feedback ("Quero só a pergunta.") pedem só a pergunta ou só a chamada, sem apoio. Deixe só a pergunta (por exemplo, "Dúvida sobre o regime de imposto da sua empresa?") e mantenha o convite no fim da legenda. A pauta aprovada trazia o gancho com os dois; se a pessoa quiser mantê-lo, ela confirma e a exceção é registrada em padrao-visual.md e feedback.md.
2. Legenda, 4º parágrafo: "Respondemos no WhatsApp em até 1 dia útil." muda a voz; o resto do texto fala em "a gente". Troque por "A gente responde no WhatsApp em até 1 dia útil."
3. Legenda, 1º parágrafo: "regime de imposto" é a ideia central do post e não é explicado em lugar nenhum (marca.md usa "regime tributário"). Explique em meia frase, por exemplo "O regime é a forma como a empresa paga imposto.", e escolha um dos dois termos para usar no post todo.
4. Chamada (campo chamada e fim da legenda): "Fale com a gente no WhatsApp" não diz como chegar lá, e quem lê no Instagram não sabe onde clicar nem qual número usar. A pessoa confirma qual caminho existe hoje (número no perfil, link da bio) e a chamada passa a dizê-lo, sem pôr link na legenda.

**Sugestões** (opcionais, não bloqueiam):

- "Você não precisa decidir isso sozinho.": "sozinho" supõe leitor homem. "Sem ajuda" serve para todos.
- 2º parágrafo: mistura "a gente" e "o escritório", e "por ela" pode ser lido como "a situação" ou "a empresa". "Diz o que a gente pode fazer pela sua empresa" fica mais claro.
- O post não diz se a conversa tem custo nem como ela acontece (vídeo, telefone ou presencial), e marca.md também não. Pergunte à pessoa. Não escreva "grátis" nem "sem compromisso" sem ela confirmar e sem registro em marca.md.
- "Você conta como a sua empresa funciona" detalha o que acontece na conversa; marca.md só diz "entender a situação da empresa". É paráfrase razoável, mas a pessoa deve confirmar que a conversa é assim.
- "Por isso um post não consegue dizer…" soa como aviso do próprio post. "Por isso não dá para dizer, em um post, qual regime serve para você" é mais natural.
- Texto alternativo da capa: o nome do escritório aparece no canto (o logo é só o nome escrito) e não está descrito.
