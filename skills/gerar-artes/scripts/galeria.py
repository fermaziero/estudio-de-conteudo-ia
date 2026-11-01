#!/usr/bin/env python3
"""Cria a galeria.html do lote: as artes de cada post com legenda, chamada, pendências e status.

A página é um arquivo só, sem internet: abre com duplo clique, em modo claro ou escuro.
As imagens são lidas da pasta artes/ ao lado dela (não mova a galeria para outro lugar).

Uso (a partir da raiz do projeto):
    python -X utf8 skills/gerar-artes/scripts/galeria.py --marca minha-marca --lote 2026-11-03-semana-1 [--abrir]
"""
from __future__ import annotations

import html
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from string import Template

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _comum import ErroUsuario, ParserPT, adicionar_args_comuns, contexto_padrao, executar, ler_json, listar_posts, verificar_artes  # noqa: E402

STATUS_ROTULO = {
    "rascunho": "Rascunho", "em_revisao": "Em revisão", "texto_aprovado": "Texto aprovado", "arte_pronta": "Arte pronta",
    "aprovado": "Aprovado", "agendado": "Agendado", "publicado": "Publicado", "erro": "Erro",
}
ETAPA_ROTULO = {"atracao": "Atração", "relacionamento": "Relacionamento", "conversao": "Conversão"}

CSS = """
:root{--fundo:#f5f4f0;--cartao:#ffffff;--texto:#18212b;--suave:#5b6674;--linha:#e2dfd7;--destaque:#0f7b6c;--sobre-destaque:#ffffff;
--alerta-fundo:#fff3cf;--alerta-borda:#e8c25a;--alerta-texto:#5e4300;--erro-fundo:#fde4e1;--erro-borda:#e4877d;--erro-texto:#7a1d14;
--ok-fundo:#dff3e6;--ok-texto:#14532d;--info-fundo:#e6ecff;--info-texto:#1d3a9e;--sombra:0 1px 2px rgba(20,30,40,.08),0 6px 20px rgba(20,30,40,.06)}
@media (prefers-color-scheme:dark){:root:not([data-tema="claro"]){--fundo:#0e1318;--cartao:#171e26;--texto:#e9eef4;--suave:#9aa6b4;--linha:#27313c;--destaque:#7fa0ff;--sobre-destaque:#0e1318;
--alerta-fundo:#3a2f0b;--alerta-borda:#8a6d1c;--alerta-texto:#f5dc92;--erro-fundo:#3b1815;--erro-borda:#8f3b33;--erro-texto:#ffc9c3;
--ok-fundo:#12301f;--ok-texto:#a6e6bf;--info-fundo:#17244d;--info-texto:#b8c9ff;--sombra:none}}
:root[data-tema="escuro"]{--fundo:#0e1318;--cartao:#171e26;--texto:#e9eef4;--suave:#9aa6b4;--linha:#27313c;--destaque:#7fa0ff;--sobre-destaque:#0e1318;
--alerta-fundo:#3a2f0b;--alerta-borda:#8a6d1c;--alerta-texto:#f5dc92;--erro-fundo:#3b1815;--erro-borda:#8f3b33;--erro-texto:#ffc9c3;
--ok-fundo:#12301f;--ok-texto:#a6e6bf;--info-fundo:#17244d;--info-texto:#b8c9ff;--sombra:none}
*{box-sizing:border-box}
body{margin:0;background:var(--fundo);color:var(--texto);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.pagina{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
.topo{display:flex;gap:16px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap}
h1{font-size:1.6rem;line-height:1.2;margin:0 0 4px}
.sub{color:var(--suave);margin:0;font-size:.95rem}
button{font:inherit;color:inherit;cursor:pointer}
.botao{background:var(--cartao);border:1px solid var(--linha);border-radius:999px;padding:6px 14px;font-size:.9rem}
.botao:hover{border-color:var(--destaque)}
.botao:focus-visible,.slide:focus-visible,summary:focus-visible{outline:3px solid var(--destaque);outline-offset:2px}
.como{background:var(--info-fundo);color:var(--info-texto);border-radius:14px;padding:14px 18px;margin:20px 0 8px;font-size:.95rem}
.como strong{display:block;margin-bottom:2px}
.post{background:var(--cartao);border:1px solid var(--linha);border-radius:18px;padding:20px;margin:24px 0;box-shadow:var(--sombra)}
.post h2{font-size:1.25rem;margin:0 0 6px;line-height:1.25}
.id{font:.8rem ui-monospace,SFMono-Regular,Consolas,monospace;color:var(--suave);margin:6px 0 0;word-break:break-all}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:.78rem;border:1px solid var(--linha);border-radius:999px;padding:2px 10px;color:var(--suave);background:transparent}
.chip.status{font-weight:600;border-color:transparent}
.s-texto_aprovado,.s-em_revisao,.s-rascunho{background:var(--info-fundo);color:var(--info-texto)}
.s-arte_pronta,.s-aprovado,.s-agendado{background:var(--ok-fundo);color:var(--ok-texto)}
.s-publicado{background:var(--linha);color:var(--texto)}
.s-erro{background:var(--erro-fundo);color:var(--erro-texto)}
.tira{display:flex;gap:12px;overflow-x:auto;padding:16px 2px 10px;scroll-snap-type:x proximity}
.slide{position:relative;flex:0 0 auto;width:236px;border:1px solid var(--linha);border-radius:12px;padding:0;background:var(--fundo);overflow:hidden;scroll-snap-align:start;line-height:0}
.slide img{width:100%;height:auto;display:block}
.slide .n{position:absolute;left:8px;top:8px;background:rgba(0,0,0,.62);color:#fff;font:600 .72rem/1 system-ui,sans-serif;padding:4px 7px;border-radius:999px}
.slide .velha{position:absolute;right:8px;top:8px;background:var(--erro-fundo);color:var(--erro-texto);font:600 .68rem/1 system-ui,sans-serif;padding:4px 7px;border-radius:999px}
.vazio{border:1px dashed var(--linha);border-radius:12px;padding:20px;color:var(--suave);margin:14px 0}
.colunas{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:24px;margin-top:8px}
@media (max-width:820px){.colunas{grid-template-columns:1fr}.slide{width:200px}}
h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;color:var(--suave);margin:18px 0 6px}
.chamada{font-weight:600;margin:0}
pre.legenda{white-space:pre-wrap;word-wrap:break-word;font:inherit;background:var(--fundo);border:1px solid var(--linha);border-radius:12px;padding:12px 14px;margin:6px 0 0;max-height:360px;overflow:auto}
.linha-titulo{display:flex;align-items:center;justify-content:space-between;gap:8px}
.alerta,.erro{border-radius:12px;padding:10px 14px;margin:10px 0;font-size:.93rem}
.alerta{background:var(--alerta-fundo);border:1px solid var(--alerta-borda);color:var(--alerta-texto)}
.erro{background:var(--erro-fundo);border:1px solid var(--erro-borda);color:var(--erro-texto)}
.alerta strong,.erro strong{display:block}
.alerta ul,.erro ul,.lista ul{margin:6px 0 0;padding-left:20px}
details{margin-top:12px;border-top:1px solid var(--linha);padding-top:8px}
summary{cursor:pointer;font-weight:600;font-size:.93rem}
.lista{font-size:.92rem;color:var(--suave)}
.lista a{color:var(--destaque)}
dialog{border:0;padding:0;background:transparent;max-width:100vw;max-height:100vh;width:100vw;height:100vh}
dialog::backdrop{background:rgba(5,8,12,.88)}
.visor{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;gap:10px;padding:12px}
.visor img{max-width:min(96vw,720px);max-height:82vh;width:auto;height:auto;border-radius:10px;background:#fff}
.visor .barra{display:flex;gap:8px;align-items:center;color:#fff;font-size:.9rem}
.visor .botao{background:rgba(255,255,255,.12);color:#fff;border-color:rgba(255,255,255,.3)}
.rodape{color:var(--suave);font-size:.85rem;margin-top:32px}
"""

JS = """
(function(){
  var raiz=document.documentElement,rotulo=document.getElementById('tema');
  function aplicar(t){if(t==='auto'){raiz.removeAttribute('data-tema')}else{raiz.setAttribute('data-tema',t)}rotulo.textContent='Tema: '+({auto:'automático',claro:'claro',escuro:'escuro'}[t])}
  var atual='auto';try{atual=localStorage.getItem('galeria-tema')||'auto'}catch(e){}
  aplicar(atual);
  rotulo.addEventListener('click',function(){var ordem=['auto','claro','escuro'];atual=ordem[(ordem.indexOf(atual)+1)%3];aplicar(atual);try{localStorage.setItem('galeria-tema',atual)}catch(e){}});
  document.addEventListener('click',function(ev){
    var c=ev.target.closest('[data-copiar]');
    if(c){var alvo=document.getElementById(c.getAttribute('data-copiar'));var texto=alvo?alvo.textContent:'';
      var ok=function(){var t=c.textContent;c.textContent='Copiado!';setTimeout(function(){c.textContent=t},1500)};
      var plano=function(){var a=document.createElement('textarea');a.value=texto;a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.select();try{document.execCommand('copy');ok()}catch(e){}document.body.removeChild(a)};
      if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(texto).then(ok,plano)}else{plano()}return}
    var s=ev.target.closest('.slide');if(s){abrir(s)}
  });
  var janela=document.getElementById('visor'),img=janela.querySelector('img'),contagem=janela.querySelector('.contagem'),grupo=[],pos=0;
  function mostrar(){var b=grupo[pos];img.src=b.getAttribute('data-grande');img.alt=b.getAttribute('data-alt')||'';contagem.textContent=(pos+1)+' de '+grupo.length}
  function abrir(b){grupo=Array.prototype.slice.call(b.parentNode.querySelectorAll('.slide'));pos=grupo.indexOf(b);mostrar();if(janela.showModal){janela.showModal()}else{janela.setAttribute('open','')}}
  function passo(d){pos=(pos+d+grupo.length)%grupo.length;mostrar()}
  janela.querySelector('[data-acao=ant]').addEventListener('click',function(){passo(-1)});
  janela.querySelector('[data-acao=prox]').addEventListener('click',function(){passo(1)});
  janela.querySelector('[data-acao=fechar]').addEventListener('click',function(){janela.close()});
  janela.addEventListener('click',function(ev){if(ev.target===janela||ev.target.classList.contains('visor')){janela.close()}});
  document.addEventListener('keydown',function(ev){if(!janela.open){return}if(ev.key==='ArrowLeft'){passo(-1)}else if(ev.key==='ArrowRight'){passo(1)}});
})();
"""

PAGINA = Template("""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Artes do lote $lote</title>
<style>$css</style>
</head>
<body>
<main class="pagina">
<div class="topo">
<div><h1>Artes do lote $lote</h1><p class="sub">Marca: $marca. $resumo</p></div>
<button class="botao" id="tema" type="button">Tema: automático</button>
</div>
<div class="como"><strong>Como aprovar</strong>Esta página só mostra as artes: ela não aprova nem publica nada. Gostou? Volte ao chat e diga "pode publicar $exemplo". O agente confere tudo e abre uma janela no seu computador para você confirmar com um clique: só então a aprovação vale. Para pedir mudanças, descreva o que ajustar. Clique numa arte para ampliar.</div>
$posts
<p class="rodape">Gerada em $quando pela skill gerar-artes. Se as imagens não aparecerem, mantenha este arquivo dentro da pasta do lote, ao lado da pasta artes/.</p>
</main>
<dialog id="visor"><div class="visor"><img alt=""><div class="barra"><button class="botao" type="button" data-acao="ant">Anterior</button><span class="contagem"></span><button class="botao" type="button" data-acao="prox">Próxima</button><button class="botao" type="button" data-acao="fechar">Fechar</button></div></div></dialog>
<script>$js</script>
</body>
</html>
""")


def _e(valor) -> str:
    return html.escape(str(valor if valor is not None else ""), quote=True)


def _url_segura(url) -> bool:
    return str(url).lower().startswith(("http://", "https://"))


def _lista(itens: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{_e(i)}</li>" for i in itens) + "</ul>"


def _limpar(texto) -> str:
    return str(texto or "").replace("**", "")


def _bloco_post(pid: str, post: dict, manifesto: dict | None, pngs: list[Path], verificacao: dict) -> str:
    status = post.get("status", "rascunho")
    slides = {s.get("n"): s for s in post.get("slides") or [] if isinstance(s, dict)}
    versoes = {}
    if manifesto:
        for item in manifesto.get("slides", []):
            versoes[item.get("arquivo")] = str(item.get("sha256", ""))[:8]
    tira = ""
    for png in pngs:
        n = int(png.stem)
        alt = _limpar((slides.get(n) or {}).get("texto_alternativo") or (slides.get(n) or {}).get("titulo") or f"Slide {n}")
        caminho = f"artes/{pid}/{png.name}?v={versoes.get(png.name, '')}"
        velha = '<span class="velha">desatualizada</span>' if n in verificacao["slides"] else ""
        tira += (f'<button class="slide" type="button" data-grande="{_e(caminho)}" data-alt="{_e(alt)}">'
                 f'<img src="{_e(caminho)}" alt="{_e(alt)}" loading="lazy"><span class="n">{n}</span>{velha}</button>')
    if tira:
        tira = f'<div class="tira">{tira}</div>'
    else:
        tira = '<div class="vazio">Este post ainda não tem artes geradas.</div>'

    avisos = [a.get("mensagem", "") for a in verificacao["atencao"]]
    confirmar = [c for c in post.get("confirmar") or [] if str(c).strip()]
    caixas = ""
    if pngs and (verificacao["gerais"] or verificacao["slides"]):
        itens = list(verificacao["gerais"]) + [f"slide {n}: {txt}" for n, lista in sorted(verificacao["slides"].items()) for txt in lista]
        caixas += ('<div class="erro"><strong>As artes não batem com o texto atual do post: gere de novo antes de aprovar</strong>'
                   + _lista(itens) + "</div>")
    if confirmar:
        caixas += ('<div class="erro"><strong>Pendências: o post não pode ser publicado até resolver</strong>'
                   + _lista(confirmar) + "</div>")
    if avisos:
        caixas += '<div class="alerta"><strong>Atenção nas artes</strong>' + _lista(avisos) + "</div>"
    revisao = post.get("revisao")
    if isinstance(revisao, dict):
        pontos = [str(p) for p in revisao.get("pontos") or []]
        caixas += (f'<details><summary>Revisão independente: {_e(revisao.get("veredito", "sem veredito"))} ({_e(revisao.get("data", ""))})</summary>'
                   + (f'<div class="lista">{_lista(pontos)}</div>' if pontos else '<p class="lista">Sem pontos registrados.</p>') + "</details>")
    else:
        caixas += '<p class="lista">Sem revisão registrada.</p>'

    legenda = str(post.get("legenda") or "")
    hashtags = " ".join(str(h) if str(h).startswith("#") else f"#{h}" for h in post.get("hashtags") or [])
    texto_copia = legenda + (("\n\n" + hashtags) if hashtags else "")
    fontes = ""
    for f in post.get("fontes") or []:
        if not isinstance(f, dict):
            continue
        nome, url = _e(f.get("nome", "")), f.get("url", "")
        link = f'<a href="{_e(url)}" rel="noopener noreferrer" target="_blank">{_e(url)}</a>' if _url_segura(url) else _e(url)
        fontes += f"<li>{nome} ({_e(f.get('data', ''))}) {link}</li>"
    origem = ""
    for rotulo, chave in (("Objetivo", "objetivo"), ("De onde vem a pauta", "de_onde_vem")):
        if post.get(chave):
            origem += f"<p><strong>{rotulo}:</strong> {_e(post[chave])}</p>"
    detalhes_fontes = (f'<details><summary>Origem e fontes (uso interno, não vão para a arte nem para a legenda)</summary>'
                       f'<div class="lista">{origem}{"<ul>" + fontes + "</ul>" if fontes else "<p>Sem fontes registradas.</p>"}</div></details>')
    alternativos = "".join(f"<li>Slide {n}: {_e(_limpar(s.get('texto_alternativo')) or 'sem texto alternativo')}</li>" for n, s in sorted(slides.items(), key=lambda kv: kv[0] or 0))
    detalhes_alt = f'<details><summary>Texto alternativo de cada slide</summary><div class="lista"><ul>{alternativos}</ul></div></details>' if alternativos else ""

    chips = (f'<span class="chip status s-{_e(status)}">{_e(STATUS_ROTULO.get(status, status))}</span>'
             f'<span class="chip">{_e(post.get("formato", ""))}</span><span class="chip">{_e(post.get("proporcao", ""))}</span>'
             f'<span class="chip">pilar: {_e(post.get("pilar", ""))}</span>'
             f'<span class="chip">{_e(ETAPA_ROTULO.get(post.get("etapa_funil", ""), post.get("etapa_funil", "")))}</span>')
    return f"""<article class="post" id="post-{_e(pid)}">
<h2>{_e(post.get("titulo_interno") or pid)}</h2>
<div class="chips">{chips}</div>
<p class="id">{_e(pid)}</p>
{tira}
<div class="colunas">
<section>
<h3>Chamada</h3><p class="chamada">{_e(post.get("chamada") or "sem chamada")}</p>
<div class="linha-titulo"><h3>Legenda</h3><button class="botao" type="button" data-copiar="leg-{_e(pid)}">Copiar legenda</button></div>
<pre class="legenda" id="leg-{_e(pid)}">{_e(texto_copia)}</pre>
</section>
<section>
{caixas}
{detalhes_fontes}
{detalhes_alt}
</section>
</div>
</article>"""


def gerar(pasta_marca: Path, nome_marca: str, nome_lote: str, pasta_lote: Path) -> Path:
    posts = listar_posts(pasta_lote)
    blocos, contagem = [], {}
    for pid, (_, post) in posts.items():
        pasta_artes = pasta_lote / "artes" / pid
        manifesto = None
        if (pasta_artes / "manifesto.json").is_file():
            try:
                manifesto = ler_json(pasta_artes / "manifesto.json")
            except ErroUsuario:
                manifesto = None
        pngs = sorted(p for p in pasta_artes.glob("[0-9][0-9].png")) if pasta_artes.is_dir() else []
        blocos.append(_bloco_post(pid, post, manifesto, pngs, verificar_artes(pasta_marca, pasta_lote, pid, post)))
        status = post.get("status", "rascunho")
        contagem[status] = contagem.get(status, 0) + 1
    resumo = f"{len(posts)} post(s)"
    if contagem:
        resumo += ": " + ", ".join(f"{n} {STATUS_ROTULO.get(s, s).lower()}" for s, n in contagem.items())
    pagina = PAGINA.substitute(
        lote=_e(nome_lote), marca=_e(nome_marca), resumo=_e(resumo), css=CSS, js=JS,
        exemplo=_e(next((pid for pid, (_, p) in posts.items() if p.get("status") == "arte_pronta"),
                        next(iter(posts), "id-do-post"))), posts="\n".join(blocos) or '<div class="vazio">Este lote não tem posts.</div>',
        quando=_e(datetime.now().strftime("%d/%m/%Y às %H:%M")),
    )
    destino = pasta_lote / "galeria.html"
    destino.write_text(pagina, encoding="utf-8")
    return destino


def principal() -> int:
    parser = ParserPT(description="Cria a galeria.html do lote (artes, legenda, pendências e status).")
    adicionar_args_comuns(parser)
    parser.add_argument("--abrir", action="store_true", help="abre a galeria no navegador ao terminar")
    args = parser.parse_args()
    _, slug_marca, pasta_marca, nome_lote, pasta_lote = contexto_padrao(args)
    destino = gerar(pasta_marca, slug_marca, nome_lote, pasta_lote)
    print(f"Galeria criada: {destino}")
    if args.abrir:
        webbrowser.open(destino.as_uri())
    return 0


if __name__ == "__main__":
    executar(principal)
