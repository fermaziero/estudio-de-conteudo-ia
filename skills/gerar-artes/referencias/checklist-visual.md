# Checklist da conferência visual

Use este checklist depois de gerar as artes: você mesmo (passo 5 do `SKILL.md`) e, de preferência, um revisor independente (outro agente, subagente ou a pessoa). **Abra as imagens.** O que vale é o que se vê, não o que o comando disse.

## Como olhar

1. Abra a visão geral `marcas/<marca>/conteudo/<lote>/_conferencia/<id>.png`. Cada slide aparece com cerca de 28% do tamanho real, um pouco menor que num celular. Se o título e a hierarquia funcionam aqui, funcionam no feed.
2. Abra cada `artes/<id>/NN.png` em tamanho cheio e olhe as bordas, o logo e as imagens de perto.
3. Leia o manifesto (`artes/<id>/manifesto.json`) só para os avisos e os tamanhos de fonte usados.

## Itens

| # | Pergunta | Se falhar |
|---|---|---|
| 1 | O título de cada slide é legível na visão geral? | texto mais curto (com ok da pessoa) ou `tipografia` maior pela `configurar-marca` |
| 2 | Nada encosta nas bordas, nenhuma palavra foi cortada, as margens parecem iguais? | o renderizador não deixa cortar; se parecer apertado, encurte o texto |
| 3 | Os acentos estão corretos e não há quadradinhos? | trocar o símbolo ou o emoji por palavra |
| 4 | Há **uma ideia por slide**, sem título e texto repetindo um ao outro? | devolver o texto à `criar-conteudo` |
| 5 | O contraste entre texto e fundo é alto (na capa com foto, o texto está sobre área escura ou sobre a faixa)? | `--variante faixa`, outro `--foco` ou outra imagem |
| 6 | O logo aparece em todos os slides, no canto combinado, do mesmo tamanho, legível, **sem caixa nem halo**, na versão certa (clara/escura)? | `--foco`, trocar a imagem ou o tema; tamanho e canto pela `configurar-marca` |
| 7 | Não há rodapé, linha divisória, numeração `NN/TT` nem @ repetido (a menos que o `visual.json` peça)? | `numeracao` e `rodape` são da `configurar-marca` |
| 8 | A imagem combina com o texto e está nítida (sem borrão, sem pixel)? | trocar por uma maior ou refazer o prompt |
| 9 | **Nenhuma letra, número, logo ou marca d'água dentro das imagens geradas?** | gerar de novo reforçando a proibição |
| 10 | **Nenhum rosto de pessoa real gerado por IA?** Fotos de pessoas são arquivos autorizados? | trocar pela foto autorizada ou por uma cena sem gente |
| 11 | O texto **nunca** cai sobre um rosto, e rosto ou assunto não estão cortados? | `--variante faixa` e `--foco` |
| 12 | Capas e imagens do mesmo lote mostram cenas diferentes? | refazer um dos prompts |
| 13 | Os slides parecem da mesma família (margens, tamanhos, temas; alternar claro e escuro só de propósito)? | `--tema` em slides soltos |
| 14 | A capa promete só o que o post entrega? | devolver à `criar-conteudo` |
| 15 | O último slide tem **uma** chamada, igual à do fim da legenda? | devolver à `criar-conteudo` |
| 16 | Nenhum dado sensível (clientes, menores, e-mails, valores de terceiros) em prints ou fotos? Nenhuma "Fonte:" na arte? | trocar a imagem; a fonte fica no JSON |
| 17 | O manifesto não tem avisos de atenção e todas as artes têm a mesma proporção? | resolver cada aviso (`problemas-comuns.md`) |
| 18 | O post tem `confirmar[]`? | a galeria mostra as pendências: o post não será publicado até a pessoa resolver |

## Parecer (para um revisor independente)

```
- Visão geral: <o que funciona e o que não funciona>
- Por slide: <n: problema ou "ok">
- Imagens: <texto/logo/rosto de pessoa real dentro de alguma? sim/não, qual>
- Logo e marca: <ok ou problema>
- Veredito: aprovar | ajustar (lista) | refazer (motivo)
```

Quem aprova a versão final é a pessoa. O parecer só diz se as artes estão em condição de ir para a aprovação dela.
