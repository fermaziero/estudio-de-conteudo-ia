# Rotina: publicar agendados e coletar métricas

A Meta não oferece agendamento de publicação pela API do Instagram que esta skill usa (veja `limites-instagram.md`). Então o agendamento acontece **no computador da pessoa**: uma tarefa programada roda `publicar.py agendados` a cada 15 minutos e publica o que já chegou na hora. Outra tarefa roda `metricas.py coletar` a cada 4 horas.

## O que a pessoa precisa saber (explique antes de instalar)

- **O computador precisa estar ligado e com a sua sessão aberta** na hora. A tarefa roda como o usuário atual, sem senha guardada, e não roda com a sessão fechada.
- **Janela de atraso de 2 horas.** Se o computador estava desligado no horário, o post ainda sai em até 2 horas depois. Passou disso, o post **não** é publicado: vai para `erro` com o motivo no `historico` e a pessoa precisa dar novo ok e escolher novo horário. O limite é ajustável com `--janela-horas`.
- A rotina só publica post **aprovado e agendado**, com a assinatura e o hash conferidos. Se alguém mudar o texto ou a arte depois do ok, ou se a aprovação não tiver a assinatura deste computador (chave de aprovação perdida, computador novo), ela recusa.
- O log fica em `marcas/<marca>/publicacao/logs/rotina-AAAA-MM.log` (um arquivo por mês). Quando não há post vencido, o `agendados` sai em silêncio e não escreve no log (a coleta de métricas escreve a cada rodada).
- A rotina também **renova o token** do Instagram sozinha quando faltam 10 dias ou menos, e avisa no log.

## Quem roda o quê

1. O agente roda `rotina.py mostrar --marca <marca>` (só mostra, não altera nada) e explica o resultado.
2. Com o ok da pessoa, **a pessoa** roda o `instalar` no terminal dela. O agente **não** roda `instalar` nem `remover`: criar uma tarefa permanente no sistema é decisão dela, e esse comando pode ser bloqueado para o agente.
3. Depois o agente roda `mostrar` de novo e confirma `JÁ INSTALADA`.

Comando para a pessoa (na raiz do projeto):

```
python -X utf8 skills/publicar-instagram/scripts/rotina.py instalar --marca <marca>
```

No macOS e no Linux, use `python3`. Para tirar a rotina: `rotina.py remover --marca <marca>`.

## O que é criado

| Sistema | Como | Nomes |
|---|---|---|
| Windows | Agendador de Tarefas, duas tarefas | `EstudioConteudo-<marca>-publicar-agendados` e `EstudioConteudo-<marca>-coletar-metricas` |
| macOS | agentes do `launchd` do usuário em `~/Library/LaunchAgents/` | `com.estudio-de-conteudo.<marca>.publicar-agendados` e `...coletar-metricas` |
| Linux | duas linhas no `crontab` do usuário, com o marcador `# estudio-de-conteudo:<marca>:<tarefa>` | (as linhas com o marcador) |

Os nomes **não têm acento** de propósito: um acento no nome da tarefa (como "métricas") quebrou a criação da rotina no Windows.

### Windows

- As tarefas usam o `pythonw.exe` (Python sem janela de console) do mesmo Python que roda o `rotina.py`. Se o `pythonw.exe` não existir, usam o `python.exe`.
- Configuração: executa só com o usuário conectado (logon interativo, nível limitado), sem senha guardada; `StartWhenAvailable` (se perdeu a hora, roda assim que possível); `MultipleInstances IgnoreNew` (não roda duas ao mesmo tempo); limite de 90 minutos por execução; funciona na bateria.
- O criador da tarefa é um script PowerShell enviado codificado ao `powershell`, para que caminhos com acento, espaço ou apóstrofo não quebrem. O PowerShell trata como aspa simples também os apóstrofos tipográficos (U+2018, U+2019, U+201A e U+201B); o script dobra todos eles. Se o PowerShell falhar, a mensagem de erro chega em português legível (o script roda com `-OutputFormat Text`, sem barra de progresso e em UTF-8), não em XML.
- Para ver o estado: `Get-ScheduledTask -TaskName "EstudioConteudo-*"` no PowerShell, ou `rotina.py mostrar`.

### macOS

- Cada tarefa é um arquivo `.plist` com `StartInterval` (900 s e 14400 s), carregado com `launchctl bootstrap gui/<seu id>`.
- **Cuidado:** se o projeto estiver em **Documentos** ou **Mesa**, o macOS pode bloquear a rotina por privacidade (erro "Operation not permitted" no log). Fóruns de desenvolvedores da Apple (não é documentação oficial) recomendam mover o projeto para fora dessas pastas ou liberar o Python em Ajustes do Sistema > Privacidade e Segurança. O resultado varia por versão do macOS.

### Linux

- **Sem o programa `crontab`** (Linux mínimo, contêiner ou WSL), `mostrar`, `instalar` e `remover` explicam o que fazer em vez de dar erro: instale o cron (em Debian e Ubuntu, `sudo apt install cron`) e deixe o serviço rodando. No WSL o cron só roda enquanto o WSL está ligado; para um computador Windows, prefira instalar a rotina no próprio Windows, com o Python do Windows.
- O `cron` roda com o ambiente mínimo; os comandos usam o caminho completo do Python e `cd` para a raiz do projeto.
- Os dois horários são `*/15 * * * *` e `7 */4 * * *`.

## Se a rotina "não faz nada"

1. `rotina.py mostrar --marca <marca>`: ela está instalada?
2. `publicar.py situacao --marca <marca>`: o post está mesmo `agendado`? O horário já chegou? O fuso está certo?
3. `publicar.py agendados --simular --marca <marca>`: mostra o que seria publicado agora, sem publicar.
4. Leia o log do mês. As causas mais comuns: computador desligado, sessão fechada, token vencido (`credenciais.py verificar`), hash que não confere (mudaram o post), aprovação sem assinatura válida (a chave de aprovação não está onde a tarefa procura: confira se a tarefa roda com o mesmo usuário e a mesma pasta de credenciais; depois, `aprovar` de novo), janela de atraso perdida.
5. Sem rede? `agendados` só usa a rede quando há post vencido; sem post a publicar ele sai sem tocar na internet.

## Fontes (consultadas em 2026-10-28)

- Microsoft Learn, `schtasks create` (sintaxe, `/xml`, intervalo em minutos) e Task Scheduler (`Principal.LogonType`: tarefas interativas só rodam com o usuário conectado; `StartWhenAvailable`; `MultipleInstances`): https://learn.microsoft.com/windows/win32/taskschd
- Apple Developer Forums, "Operation Not Permitted" em tarefas do `launchd` em pastas protegidas: developer.apple.com/forums/thread/653668
