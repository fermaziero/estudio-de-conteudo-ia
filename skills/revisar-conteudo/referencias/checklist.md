# Checklist da revisão independente

Use este arquivo ao revisar cada post. Para cada item, o resultado é `ok`, `ajustar` ou `refazer`. Toda observação diz **onde** (slide, campo ou trecho) e **como corrigir**.

Ordem sugerida: validação, fatos, capa × entrega, clareza, português, regras da marca, dados sensíveis, chamada, limites, texto alternativo.

## 1. Fatos e fontes

**O que olhar:** números, datas, prazos, regras e leis, preços, nomes de ferramentas, planos e recursos, estudos, afirmações sobre empresas ou pessoas.

**Como checar**

1. Liste cada afirmação que dá para conferir.
2. Ache a fonte dela em `fontes[]` (endereço e data), em `fonte_interna` do slide ou em `fontes_legenda_internas`.
3. Abra o endereço. Confirme que a página existe e diz isso mesmo, com os mesmos números, no mesmo período e para o mesmo universo.
4. O texto afirma mais do que a fonte? Exemplos: a fonte mede visitas e o texto fala de pessoas; a fonte mostra uma associação e o texto fala em causa; a fonte é de outro país ou ano.
5. Ferramenta, plano, preço e regra: a consulta tem menos de 30 dias? Se não, reconfira.
6. Opinião e experiência da marca aparecem como tal, e a pessoa as forneceu ("Informado pela pessoa em AAAA-MM-DD")?
7. `fontes[].url` começa com `http://` ou `https://` e a `data` é AAAA-MM-DD.
8. Origem em arquivo da marca (`fonte_interna` que cita `marca.md`, `regras.md`…): abra o arquivo e veja se ele diz mesmo aquilo. "Exemplo criado para o post" e "orientação editorial" valem para opinião, exemplo e recomendação geral, nunca para dado, caso real ou regra. Se a nota liga uma **escolha editorial** a uma regra do arquivo, ela precisa dizer que a escolha é editorial (a regra não manda aquilo, só não proíbe). Isso é sugestão, não ajuste, quando o texto do post está correto.
   Definição geral de um termo em linguagem simples ("regime tributário é a forma como a empresa paga imposto") não precisa de fonte, desde que não cite lei, prazo, valor nem número. Se citar, é afirmação conferível.
9. Afirmação que **já está em `confirmar[]`** não é "ajustar": marque `ok (pendência registrada)` e liste a pendência em "Bloqueia a publicação". Seu conhecimento próprio de lei, prazo ou valor não vale como fonte.

**Ajustar quando:** afirmação conferível sem fonte aberta e fora de `confirmar[]`; fonte que não confirma exatamente o que o texto diz; consulta antiga; conclusão além da fonte; origem inexistente ou exagerada em `fonte_interna`; dúvida real que deveria estar em `confirmar[]` como `NÃO VERIFICADO:`.

**Refazer quando:** número, caso, cliente, depoimento ou resultado sem origem nenhuma (inventado).

## 2. Promessa da capa × entrega

**Como checar**

1. Leia **só a capa** e escreva em uma frase o que ela promete.
2. Leia o resto e marque onde cada parte da promessa é cumprida, inteira e legível.
3. Capa que fala em "modelo", "planilha", "lista", "passo a passo" ou "N motivos": o item aparece completo nos slides? O número bate (a capa diz "5 erros" e há 5)?
4. A capa não pode prometer resultado que o post não entrega nem garantir ganho.
5. Compare o post com a pauta aprovada em `pautas.md`. Se o gancho, o formato ou a chamada mudaram, a mudança está registrada na pauta ("Ajuste na escrita")? Se não está, é ajuste. Se está, anote em `pontos` que o redator deve **avisar a pessoa** ao pedir o ok do texto.

**Ajustar quando:** a promessa não é cumprida. Diga se o conserto é mudar a capa ou completar o miolo.

## 3. Clareza e teste do leigo

**Como checar:** leia slide por slide como alguém sem base técnica no assunto e pergunte:

- Precisei reler? Então reescreva.
- Há termo solto, sigla ou jargão sem explicação no mesmo slide?
- Há imperativo sem objeto ("cole este pedido" sem mostrar o pedido)?
- O slide mistura duas ideias? Título e texto repetem um ao outro?
- O slide só faz sentido com o anterior?
- O layout combina com o conteúdo? Passos em sequência pedem `lista` (que numera); sinais, opções ou categorias lado a lado pedem `cartoes`; `citacao` é frase da própria marca, nunca depoimento.
- Dois slides seguidos dizem a mesma coisa com frases diferentes? (sugestão: juntar ou cortar um).

**Ajustar quando:** qualquer resposta acima for "sim" para um erro objetivo ou uma regra escrita. Indique o slide e proponha uma versão mais clara em uma linha.

## 4. Português

**Como checar:** concordância, regência, crase, pontuação, acentos, grafia, **artigo em título** ("O imposto está subindo?", não "Imposto está subindo?"), gerundismo ("vou estar enviando"), repetição de palavra, tratamento (você ou tu) igual no post todo, maiúsculas.

Leia a capa e os títulos duas vezes: o erro se esconde em manchete. Leia a legenda em voz alta.

**Ajustar quando:** houver qualquer erro. Liste cada um com o trecho e a correção.

## 5. Regras da marca

**Como checar**

- `regras.md`: promessas proibidas, temas proibidos ou "só sob pedido", quem pode ser citado e com qual autorização, limites de humor, política e religião.
- `marca.md`: tom de voz; palavras que usa e evita; **provas autorizadas** (só se pode citar uma prova que esteja lá, com origem); chamadas disponíveis.
- `padrao-visual.md`: o que vale para o texto da arte (apoio na capa, quantidade de texto) **e para as imagens** (o que a pessoa não quer ver; o `prompt` de imagem gerada respeita isso).
- `feedback.md`: o texto repete algo que a pessoa já corrigiu? Frase de feedback sobre a capa (exemplo: "quero só a pergunta") vale para todos os posts novos.
- Quando a regra da marca diverge da regra geral de escrita, vale a da marca.
- O `pilar` existe em `estrategia.json` e combina com o conteúdo?

**Refazer quando:** o post quebra uma regra proibitiva (promessa vetada, tema proibido).
**Ajustar quando:** tom fora do padrão, palavra evitada, prova não listada, erro já corrigido antes que voltou.

## 6. Dados sensíveis e LGPD

**Como checar:** procure em slides, legenda, roteiro, `descricao` e `prompt` de imagens:

- nomes de pessoas, fotos ou imagens de pessoas;
- CPF, CNPJ, telefone, e-mail, endereço;
- saúde, situação financeira, dados de crianças e adolescentes;
- clientes, alunos e equipe identificáveis, mesmo sem citar o nome (a história é reconhecível?).

Regras: dado de terceiros só com autorização registrada em `regras.md`. Sem registro, é problema. Exemplo hipotético tem de estar claro como hipótese e sem dado real. Caso "real" precisa de autorização e fica em `confirmar[]` até a pessoa conferir o texto exato. Em `imagem`, a foto está autorizada? O `prompt` de imagem gerada não pede pessoa real identificável nem marca de terceiros?

**Refazer quando:** há dado de terceiro identificável sem autorização.

## 7. Chamada × etapa do funil

**Como checar**

- É uma chamada só? A mesma frase está no campo `chamada`, no último slide (versão curta, cerca de 8 palavras) e no fim da legenda? Em **post único e reel não há último slide**: a chamada fica no campo `chamada` e no fim da legenda, e a capa leva só o gancho.
- Não confunda: o **gancho** é o título da capa; a **chamada para ação** é o convite do fim (campo `chamada`).
- Há pedidos demais antes da chamada (o penúltimo parágrafo já manda fazer algo)? Isso enfraquece a chamada.
- Combina com a etapa? Atração: salvar, compartilhar ou seguir. Relacionamento: comentar ou mandar para alguém. Conversão: link na bio, direct ou WhatsApp.
- Existe em "Chamadas disponíveis" de `marca.md`? "Comente PALAVRA" só vale com resposta automática por direct.
- No reel, a chamada é leve.
- O último slide não virou resumo nem textão.

**Ajustar quando:** duas ações, chamada incompatível com a etapa, chamada que a marca não oferece, último slide carregado.

## 8. Tamanhos e limites

**Como checar:** o `validar_posts.py` não mostra erros. Além dele, confira:

- capa com até 12 palavras; título do último slide com cerca de 8;
- legenda com até 2.200 caracteres e primeira linha que funcione sozinha antes do "mais" (cerca de 125 caracteres);
- hashtags: de 0 a 5, sem `#` no JSON e não repetidas no texto;
- carrossel com 2 a 10 slides; `lista` e `cartoes` com 2 a 5 itens;
- nenhum "Fonte:" na arte nem na legenda, nenhum link na legenda;
- slide com muito texto (uma ideia por slide);
- em slide com imagem gerada, o `prompt` termina com "Sem texto, sem letras, sem logos." e não pede pessoa real, dinheiro ou moedas se a marca não quer.

**Ajustar quando:** qualquer limite estourado ou aviso importante ignorado.

## 9. Texto alternativo

**Como checar:** todo slide tem `texto_alternativo`. Ele descreve o que a pessoa que não enxerga precisa saber: uma frase para a imagem (se houver) e o texto escrito no slide, transcrito. É curto e em português simples, e não é só a palavra "imagem".

**Ajustar quando:** ausente, vazio, genérico ou sem o texto escrito no slide. O tamanho, sozinho, não é motivo de ajuste: um slide com imagem, título e apoio leva naturalmente mais de duas frases. Se estiver longo demais, vira sugestão.

## Se for reel

Além dos itens acima: o primeiro bloco do `roteiro` tem um gancho claro? As falas são curtas e soam como fala? A `tela` de cada bloco diz o que aparece? Nada exige cenário, equipamento ou pessoa que a marca não tem? A chamada é leve? O roteiro cumpre o que o gancho promete?
