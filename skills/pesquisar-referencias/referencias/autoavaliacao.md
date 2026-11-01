# Autoavaliação da execução

Faça ao fim de toda execução, depois da integração e antes do relatório final, que inclui o resultado desta avaliação. O objetivo é a skill ficar melhor a cada uso: cada problema vira evidência, e cada evidência repetida vira mudança na skill, com o ok da pessoa. Seja breve: a avaliação inteira cabe em poucas linhas no `aprendizados.md`.

## 1. Notas (0, 1 ou 2 por critério)

| Critério | 2 | 1 | 0 |
|---|---|---|---|
| Cobertura da coleta | 30 posts ou mais com legenda, views dos reels, 5 datas ou mais (as duas pontas entre elas) | faltou uma das três partes | a análise ficou sem base |
| Confiabilidade | nenhum passo repetido mais de 2 vezes, sem bloqueio, números conferidos pelo `conferir_perfil.py` | houve repetição ou correção de número | bloqueio, 429 ou número errado entregue |
| Fidelidade ao foco | sem análise visual, sem cópia de legenda, "não medido" onde faltou | um deslize corrigido na conferência | deslize chegou ao arquivo final |
| Focos pedidos | cada foco extra respondido com dado (ou "não aparece" verificado); sem foco pedido, vale 2 | respondido em parte | ignorado |
| Utilidade para a marca | 3 aprendizados acionáveis ou mais, ligados a pilares e etapas do funil, com o que é novo | aprendizados genéricos | repetiu a síntese |
| Integração | csv, síntese e relatório atualizados, scripts sem erro | um item pendente | dados inconsistentes entre arquivos |
| Custo | tokens e tempo por perfil até a média do registro | até 50% acima | mais que isso, sem motivo |

Total de 14. A média de custo é a das execuções registradas em `skills/pesquisar-referencias/aprendizados.md`. Enquanto não houver registro, use como referência cerca de 150 mil tokens e 10 minutos por perfil (ordem de grandeza em coletas de 36 posts; varia com o modelo e a ferramenta). Se o agente não informa tokens ou tempo, deixe o critério sem nota e diga isso.

## 2. O que deu errado ou poderia ser melhor

Use os relatos dos agentes (eles listam passos repetidos e armadilhas novas), o resultado do `conferir_perfil.py` e os números de custo. Para cada item:

- **Problema:** o que aconteceu.
- **Evidência:** onde se vê (passo, mensagem de erro, número). Sem nomes de perfis.
- **Mudança proposta:** arquivo da skill e o que muda (script, instrução, critério, modelo, brief).
- **Prioridade:** alta (gera erro ou dado errado), média (custa tempo), baixa (acabamento).

Uma armadilha nova vista uma vez entra como proposta. Se a mesma proposta já existe no registro, some 1 na coluna Recorrência em vez de duplicar; com recorrência 2, a prioridade sobe para alta.

## 3. Registro

Em `skills/pesquisar-referencias/aprendizados.md`:

1. uma linha na tabela "Registro de execuções" (quantidade de perfis, não nomes);
2. as propostas novas na tabela "Melhorias propostas", com status `proposta`;
3. lições que se confirmaram, em "Lições técnicas".

## 4. Aplicar com o ok da pessoa

Apresente as propostas no relatório final, numeradas e em linguagem simples, no máximo três. A mudança vale para todas as marcas deste projeto. Quando a pessoa aprovar (todas ou algumas), edite os arquivos da skill, mude o status para `aplicada em AAAA-MM-DD` e, se for uma armadilha, leve-a para a tabela de `referencias/coleta-instagram.md`. Se mudar o `name` ou a `description` do `SKILL.md`, rode `python -X utf8 ferramentas/sincronizar_atalhos.py`. Propostas recusadas ficam como `recusada`, com o motivo, para não voltarem.
