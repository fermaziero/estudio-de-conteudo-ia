# Aprendizados da skill

Memória das coletas. Leia no início de cada execução; escreva no fim, seguindo `skills/pesquisar-referencias/referencias/autoavaliacao.md`. Registre só o que serve a qualquer marca: sem nomes de perfis e sem dados da marca.

## A confirmar na primeira coleta real

Revisados em 2026-10-28 e testados só numa página simulada. Quando um item funcionar no Instagram de verdade, apague-o desta lista (ele já está em "Práticas atuais"); se falhar, registre a armadilha em `referencias/coleta-instagram.md`.

- Passo 1: clique no "mais" da bio e aviso de perfil privado ou indisponível.
- Passo 2: `perg` e `hash` guardados antes da limpeza; `semLegenda` como sinal de conta deslogada.
- Passo 2b: aderência ao assunto da marca.
- Passo 4: abrir cada post pelo código salvo; colab (dois perfis no cabeçalho do post) e rótulo de IA; contagem de comentários visíveis (só com permissão).
- Opções com permissão: abrir o link da bio e ler comentários para inferir tema.

## Práticas atuais

- Só a interface do Instagram, nunca os endereços `/api/v1`.
- Cada agente usa a própria aba (o grid fica guardado nela) e a fecha ao terminar.
- Views: regex `(mil|mi)`, nesta ordem; interface em inglês (`K`, `M`) também é lida.
- "Curtido por X e outras N pessoas" vale N+1 curtidas. O nome de quem curtiu nunca é registrado.
- Legendas longas: ler também o fim, onde costuma estar a chamada para ação.
- Cada agente relata passos repetidos e armadilhas novas; isso alimenta a autoavaliação.
- O benchmark entra no `referencias.csv` pelo `scripts/registrar_referencia.py` (que entende "100 mil", "1,5 mi") e é conferido contra o Anexo pelo `scripts/conferir_perfil.py`.
- Foco extra tem passo próprio (5), seção própria no modelo do perfil e na síntese.
- As definições de mediana, posts por semana e % de chamada para ação ficam no modelo do perfil, e o Anexo lista todos os posts do grid. Posts por semana exige a data do primeiro e do último post sem fixado.
- Brief do agente: um subagente por perfil, modelo de porte médio, comparação 5 × 5 (ou 3 × 3) só com reels do grid, leitura de `regras.md`, resposta de até 250 palavras.
- O passo 3 para com erro se o grid da aba estiver vazio.
- O passo 4 abre cada post pelo código salvo no grid (o grid é virtualizado), compara o caminho lido na página e usa uma função `san` única para limpar links.
- A aderência ao assunto da marca é medida logo depois do grid (passo 2b). Abaixo de 20% o agente para e pergunta. O nicho vai para o `referencias.csv`.
- O passo 2 guarda, antes da limpeza, se a legenda tem pergunta e quantas hashtags (a função `san` apaga `?` e `#`).
- O passo 4 registra colab e rótulo de IA de cada post aberto.
- O passo 1 expande a bio antes de ler o cabeçalho.
- Abrir o link da bio e contar comentários são opções que exigem permissão da pessoa; o padrão é não.
- A autoavaliação tem critério de focos pedidos, recorrência das propostas e média de custo explícita.

## Lições técnicas

- Os endereços `/api/v1` do Instagram devolveram 429 já na primeira chamada.
- Logado, o `alt` das imagens do grid é a legenda: é a forma mais barata de ler 36 legendas. Deslogado, vem vazio.
- Curtidas aparecem em formatos diferentes: número, "e outras N pessoas" (N+1) ou oculto. Perfis grandes costumam ocultar.
- As datas do post aberto vêm em UTC.
- O grupo de abas do Chrome sumiu duas vezes numa coleta. Recriar a aba e refazer a partir do grid resolveu.
- O grid do Instagram é virtualizado: acesso por índice falha depois do 30º post.
- Três agentes em paralelo funcionaram sem bloqueio. Cada perfil levou cerca de 10 minutos e 150 mil tokens (ordem de grandeza em coletas de 36 posts; varia com o modelo e a ferramenta).
- O mesmo reel de colab aparece nos dois perfis: na síntese, conta como uma peça só.
- Amostras caem com frequência em período de lançamento. Registrar o período evita tomar o mix de campanha como rotina.
- Comparar por proporção (views ÷ seguidores, % de chamada para ação) ajuda mais que comparar números absolutos.
- Um perfil indicado pode não ser do assunto da marca. A análise continua útil para formato, ritmo e chamadas, mas precisa ser marcada como adjacente, e o aviso deve vir cedo (passo 2b).
- Perfis grandes com legenda de uma frase deixam o tema no vídeo. Os comentários públicos ajudam a inferir o tema (marcar como inferência, sem nomes, só com permissão).

## Registro de execuções

| Data | Perfis (quantidade) | Nota (de 14) | Tokens por perfil | Tempo por perfil | Problemas | Propostas |
|---|---|---|---|---|---|---|

## Melhorias propostas

| # | Data | Proposta | Prioridade | Recorrência | Status |
|---|---|---|---|---|---|
