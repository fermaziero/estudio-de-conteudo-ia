"""Monta o HTML do painel: página única, gráficos em SVG inline, sem biblioteca externa."""
from __future__ import annotations

import html
import json
import math
from datetime import date, timedelta

from _analise import (
    DIAS_AVISO_DADOS,
    HORAS_MATURIDADE,
    INDICE_ABAIXO,
    INDICE_ACIMA,
    JANELA_KPI_DIAS,
    LIMITE_CONCENTRACAO,
    N_AMOSTRA_MINIMA,
    N_AMOSTRA_OK,
    N_MIN_RANKING,
    NOMES_ETAPA,
    NOMES_FORMATO,
    ROTULOS_EXTRAS,
    SEM_CLASSIFICACAO,
    SEMANAS_RITMO,
    serializar,
    valor_indicador_texto,
)
from _comum import (
    NAO_MEDIDO,
    fmt_data,
    fmt_data_curta,
    fmt_dec,
    fmt_dias,
    fmt_int,
    fmt_pct,
    fmt_sinal,
    plural,
)

TOKENS_CLARO = {
    "pagina": "#f9f9f7",
    "superficie": "#fcfcfb",
    "superficie-2": "#f3f2ee",
    "tinta": "#0b0b0b",
    "tinta-2": "#52514e",
    "tinta-3": "#6b6964",
    "linha": "#e1e0d9",
    "base": "#c3c2b7",
    "borda": "rgba(11,11,11,0.10)",
    "link": "#1c5cab",
    "serie-1": "#2a78d6",
    "serie-2": "#eb6834",
    "neutro": "#898781",
    "trilho-1": "#cde2fb",
    "trilho-aviso": "#fdeab8",
    "trilho-critico": "#f4cccc",
    "st-bom": "#0ca30c",
    "st-aviso": "#fab219",
    "st-critico": "#d03b3b",
    "texto-bom": "#006300",
    "texto-critico": "#a82a2a",
    "sombra": "0 6px 24px rgba(11,11,11,0.12)",
}
TOKENS_ESCURO = {
    "pagina": "#0d0d0d",
    "superficie": "#1a1a19",
    "superficie-2": "#222221",
    "tinta": "#f0efec",
    "tinta-2": "#c3c2b7",
    "tinta-3": "#a3a198",
    "linha": "#2c2c2a",
    "base": "#383835",
    "borda": "rgba(255,255,255,0.10)",
    "link": "#6da7ec",
    "serie-1": "#3987e5",
    "serie-2": "#d95926",
    "neutro": "#898781",
    "trilho-1": "#1f3556",
    "trilho-aviso": "#4a3a10",
    "trilho-critico": "#4d2020",
    "st-bom": "#0ca30c",
    "st-aviso": "#fab219",
    "st-critico": "#d03b3b",
    "texto-bom": "#3ccf3c",
    "texto-critico": "#ff8f8f",
    "sombra": "0 6px 24px rgba(0,0,0,0.5)",
}


def _bloco_tokens(t: dict) -> str:
    return "".join(f"--{k}:{v};" for k, v in t.items())


CSS = """
:root{__CLARO__color-scheme:light dark}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){__ESCURO__color-scheme:dark}}
:root[data-theme="dark"]{__ESCURO__color-scheme:dark}
:root[data-theme="light"]{color-scheme:light}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--pagina);color:var(--tinta);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
h1,h2,h3,h4,p,dl,dd,figure{margin:0}
a{color:var(--link)}
a:focus-visible,button:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--serie-1);outline-offset:2px;border-radius:4px}
.pular{position:absolute;left:-9999px;top:8px;background:var(--superficie);color:var(--tinta);padding:8px 12px;border-radius:8px;border:1px solid var(--borda);z-index:20}
.pular:focus{left:12px}
.env{max-width:1120px;margin:0 auto;padding:0 16px}
.topo{padding:20px 0 12px}
.topo-linha{display:flex;flex-wrap:wrap;gap:12px 16px;align-items:flex-start;justify-content:space-between}
.sobre{color:var(--tinta-2);font-size:13px;font-weight:600;letter-spacing:.04em;text-transform:uppercase}
h1{font-size:28px;line-height:1.2;font-weight:650;margin-top:2px;overflow-wrap:anywhere}
.arroba{color:var(--tinta-2);font-weight:450;font-size:.7em;margin-left:6px}
.objetivo{margin-top:6px;color:var(--tinta-2);max-width:72ch}
.gerado{margin-top:6px;color:var(--tinta-3);font-size:13px}
.selos{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.selo{display:inline-flex;align-items:center;gap:6px;padding:3px 9px;border-radius:999px;border:1px solid var(--borda);background:var(--superficie);font-size:12.5px;white-space:nowrap}
.selo.destaque{background:var(--superficie-2);font-weight:600}
button.selo{cursor:pointer;color:var(--tinta);font-family:inherit}
button.selo:hover{background:var(--superficie-2)}
.nav{position:sticky;top:0;z-index:10;background:var(--pagina);border-bottom:1px solid var(--linha)}
@supports (background:color-mix(in srgb,red,blue)){.nav{background:color-mix(in srgb,var(--pagina) 94%,transparent);backdrop-filter:blur(6px)}}
.nav .env{display:flex;gap:4px;overflow-x:auto;padding-top:6px;padding-bottom:6px;scrollbar-width:thin}
.nav a{white-space:nowrap;text-decoration:none;color:var(--tinta-2);padding:5px 10px;border-radius:999px;font-size:13.5px}
.nav a:hover{background:var(--superficie-2);color:var(--tinta)}
main{padding-bottom:40px}
.faixa{display:flex;gap:10px;align-items:flex-start;margin-top:16px;padding:10px 14px;border-radius:10px;border:1px solid var(--borda);background:var(--superficie)}
.faixa.aviso{border-color:var(--st-aviso);background:var(--superficie-2)}
.faixa .ic{margin-top:6px}
.sec{margin-top:32px;scroll-margin-top:56px}
.sec>h2{font-size:19px;font-weight:650}
.sec>.sub{color:var(--tinta-2);font-size:14px;margin:2px 0 12px;max-width:78ch}
.cartao{background:var(--superficie);border:1px solid var(--borda);border-radius:12px;padding:16px 18px;min-width:0}
.cartao h3{font-size:15px;font-weight:650}
.cartao .sub{color:var(--tinta-2);font-size:13px;margin-top:2px}
.nota{color:var(--tinta-2);font-size:13px;margin-top:10px;max-width:80ch}
.nm{color:var(--tinta-3);font-style:italic;font-weight:400}
.mut{color:var(--tinta-3)}
.ic{display:inline-block;width:10px;height:10px;flex:none;vertical-align:baseline}
.ic-bom{background:var(--st-bom);border-radius:50%}
.ic-aviso{background:var(--st-aviso);clip-path:polygon(50% 0,100% 100%,0 100%)}
.ic-critico{background:var(--st-critico);clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%)}
.ic-neutro{border:2px solid var(--tinta-3);border-radius:50%;width:10px;height:10px}
.ic-info{border:2px solid var(--serie-1);border-radius:50%;width:10px;height:10px}
.estado{display:inline-flex;align-items:center;gap:6px;padding:2px 9px;border-radius:999px;border:1px solid var(--borda);background:var(--superficie-2);font-size:12.5px;font-weight:600;white-space:nowrap}
.amostra{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:999px;border:1px dashed var(--base);color:var(--tinta-2);font-size:11.5px;white-space:nowrap}
.atencao-lista{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.atencao-lista li{display:flex;gap:10px;align-items:baseline;padding:8px 12px;border:1px solid var(--borda);border-radius:10px;background:var(--superficie)}
.atencao-lista .ic{align-self:center}
.atencao-lista .nivel{font-size:12px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;color:var(--tinta-2);min-width:62px}
.atencao-lista a{margin-left:auto;font-size:13px;white-space:nowrap}
.resumo{display:grid;gap:12px;grid-template-columns:repeat(4,minmax(0,1fr))}
.heroi{grid-column:span 2;grid-row:span 2;display:flex;flex-direction:column;justify-content:center;gap:4px;padding:20px 22px}
.rotulo{color:var(--tinta-2);font-size:13.5px;font-weight:600}
.heroi-num{font-size:56px;line-height:1.05;font-weight:650;letter-spacing:-.02em}
.heroi-sub{color:var(--tinta);font-size:14.5px}
.heroi-nota{color:var(--tinta-2);font-size:13px}
.tile{display:flex;flex-direction:column;gap:3px}
.tile-num{font-size:30px;line-height:1.15;font-weight:650;letter-spacing:-.01em}
.tile-sub{color:var(--tinta-2);font-size:13px}
.delta{font-size:13px;font-weight:600}
.delta.sobe{color:var(--texto-bom)}
.delta.desce{color:var(--texto-critico)}
.delta.igual{color:var(--tinta-2)}
.metas{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr))}
.meta-topo{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}
.fluxo{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline;margin:12px 0 8px}
.fluxo .atual{font-size:26px;font-weight:650;line-height:1.1}
.fluxo .seta{color:var(--tinta-3)}
.medidor{height:10px;border-radius:999px;background:var(--trilho-1);overflow:hidden}
.medidor>i{display:block;height:100%;border-radius:999px;background:var(--serie-1)}
.medidor.aviso{background:var(--trilho-aviso)}
.medidor.aviso>i{background:var(--st-aviso)}
.medidor.critico{background:var(--trilho-critico)}
.medidor.critico>i{background:var(--st-critico)}
.medidor.neutro{background:var(--superficie-2)}
.medidor.neutro>i{background:var(--neutro)}
.prog{font-size:13px;color:var(--tinta-2);margin-top:6px}
.lista-def{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin-top:10px;font-size:13.5px}
.lista-def dt{color:var(--tinta-2)}
.lista-def dd{text-align:right;font-variant-numeric:tabular-nums}
.movs{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.movs li{display:grid;grid-template-columns:1fr auto;gap:2px 14px;padding:9px 0;border-bottom:1px solid var(--linha)}
.movs li:last-child{border-bottom:0}
.movs .quando{text-align:right;font-variant-numeric:tabular-nums;color:var(--tinta-2);font-size:13px;white-space:nowrap}
.movs .ind{grid-column:1/-1;color:var(--tinta-2);font-size:13px}
.duas{display:grid;gap:12px;grid-template-columns:repeat(2,minmax(0,1fr))}
.tres{display:grid;gap:12px;grid-template-columns:repeat(3,minmax(0,1fr))}
.graf{display:block;width:100%;height:auto;max-width:720px}
.graf-cel{display:none}
.graf text{fill:var(--tinta-3);font-family:inherit}
.graf .valor{fill:var(--tinta);font-weight:600}
.graf .grade{stroke:var(--linha);stroke-width:1}
.graf .eixo{stroke:var(--base);stroke-width:1}
.graf .serie{fill:none;stroke:var(--serie-1);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.graf .nece{fill:none;stroke:var(--serie-2);stroke-width:2;stroke-dasharray:7 5;stroke-linecap:round}
.graf .proj{fill:none;stroke:var(--neutro);stroke-width:2;stroke-dasharray:2 5;stroke-linecap:round}
.graf .ponto{fill:var(--serie-1);stroke:var(--superficie);stroke-width:2}
.graf .ponto-nece{fill:var(--serie-2);stroke:var(--superficie);stroke-width:2}
.graf .ponto-proj{fill:var(--neutro);stroke:var(--superficie);stroke-width:2}
.graf .barra-1{fill:var(--serie-1)}
.graf .barra-2{fill:var(--neutro)}
.graf .meta-linha{stroke:var(--serie-2);stroke-width:2}
.graf .parcial{opacity:.5}
.graf .alvo{fill:transparent;cursor:default}
.graf .alvo:hover{fill:color-mix(in srgb,var(--serie-1) 10%,transparent)}
.legenda{display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:8px;font-size:13px;color:var(--tinta-2)}
.legenda span{display:inline-flex;align-items:center;gap:6px}
.chave{display:inline-block;width:18px;height:0;border-top:2px solid var(--serie-1)}
.chave.nece{border-top:2px dashed var(--serie-2)}
.chave.proj{border-top:2px dotted var(--neutro)}
.chave.cx1,.chave.cx2{width:10px;height:10px;border:0;border-radius:2px;background:var(--serie-1)}
.chave.cx2{background:var(--neutro)}
.chave.meta{border-top:2px solid var(--serie-2)}
details.alt{margin-top:10px;font-size:13.5px}
details.alt summary{cursor:pointer;color:var(--link);width:fit-content}
.rolagem{overflow-x:auto}
table.tab{width:100%;border-collapse:collapse;font-size:13.5px}
.tab th{font-weight:600;color:var(--tinta-2);text-align:right;padding:8px 8px;border-bottom:1px solid var(--base);vertical-align:bottom;font-size:12.5px}
.tab td{padding:9px 8px;border-bottom:1px solid var(--linha);text-align:right;vertical-align:top;font-variant-numeric:tabular-nums}
.tab th:first-child,.tab td:first-child{text-align:left}
.tab td:first-child{min-width:170px}
.tab td.nw,.tab .nw{white-space:nowrap}
.th-sub{display:block;font-weight:400;color:var(--tinta-3);font-size:11.5px}
.tab tr.conta td{font-weight:600;background:var(--superficie-2)}
.tab .sub-c{display:block;color:var(--tinta-3);font-size:12px;font-weight:400}
.tab .acima .idx{color:var(--texto-bom);font-weight:600}
.tab .abaixo .idx{color:var(--texto-critico);font-weight:600}
.cv{min-width:0}
.tab td.vazio-g{text-align:left}
.grupo-tit{font-size:14.5px;font-weight:650;margin:18px 0 2px}
.grupo-tit:first-child{margin-top:0}
.etapas{display:grid;gap:12px;grid-template-columns:repeat(3,minmax(0,1fr))}
.etapa.trava{border-color:var(--st-aviso);box-shadow:0 0 0 1px var(--st-aviso)}
.etapa .plano{font-size:13.5px;color:var(--tinta-2);margin:6px 0 10px}
.etapa .valor{font-size:24px;font-weight:650;line-height:1.15}
.indice-svg{display:block;margin:6px 0 2px}
.indice-svg .trilho{stroke:var(--base);stroke-width:2}
.indice-svg .centro{stroke:var(--tinta-3);stroke-width:2}
.indice-svg .bola{fill:var(--serie-1);stroke:var(--superficie);stroke-width:2}
.rank-par{display:grid;gap:12px;grid-template-columns:repeat(2,minmax(0,1fr))}
.rank h4{font-size:12.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--tinta-2);margin:12px 0 6px}
.rank h4:first-of-type{margin-top:8px}
.rank ol{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.rank li{display:grid;grid-template-columns:1fr auto;gap:2px 10px;padding:8px 10px;border:1px solid var(--linha);border-radius:10px;background:var(--superficie)}
.rank li .tit{font-weight:600;overflow-wrap:anywhere}
.rank li .v{font-weight:650;text-align:right}
.rank li .meta-l{grid-column:1/-1;color:var(--tinta-2);font-size:12.5px}
.chip{display:inline-block;padding:0 7px;border-radius:999px;background:var(--superficie-2);font-size:12px;color:var(--tinta-2)}
.barras-ref{display:grid;gap:6px;margin:6px 0 12px;font-size:13px}
.barras-ref .lin{display:grid;grid-template-columns:minmax(110px,190px) 1fr 70px;gap:10px;align-items:center}
.barras-ref .lin .nome{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.barras-ref .lin .num{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.barras-ref .lin.eu .nome{font-weight:650}
dl.glossario{display:grid;gap:10px;margin:8px 0 0}
dl.glossario dt{font-weight:650}
dl.glossario dd{color:var(--tinta-2);margin-left:0}
details.bloco{border:1px solid var(--borda);border-radius:12px;background:var(--superficie);padding:2px 18px}
details.bloco>summary{cursor:pointer;font-weight:650;padding:12px 0}
details.bloco[open]>summary{border-bottom:1px solid var(--linha);margin-bottom:12px}
details.bloco>div{padding-bottom:16px}
ul.avisos{margin:6px 0 0;padding-left:20px;color:var(--tinta-2);font-size:13.5px}
ul.avisos li{margin:3px 0}
.rodape{margin-top:36px;padding:16px 0 32px;border-top:1px solid var(--linha);color:var(--tinta-2);font-size:13px}
#dica{position:fixed;z-index:30;max-width:280px;pointer-events:none;background:var(--superficie);color:var(--tinta);border:1px solid var(--borda);border-radius:8px;box-shadow:var(--sombra);padding:8px 10px;font-size:13px;line-height:1.4}
#dica[hidden]{display:none}
#dica .dica-titulo{font-weight:650;margin-bottom:2px}
@media (max-width:900px){
  .resumo{grid-template-columns:repeat(2,minmax(0,1fr))}
  .heroi{grid-column:span 2;grid-row:auto}
  .duas,.tres,.etapas,.rank-par{grid-template-columns:minmax(0,1fr)}
}
@media (max-width:720px){
  .graf-desk{display:none}
  .graf-cel{display:block}
  h1{font-size:24px}
  .heroi-num{font-size:48px}
  table.empilhar,.empilhar tbody,.empilhar tr,.empilhar td{display:block;width:100%}
  .empilhar thead{position:absolute;left:-9999px}
  .empilhar tr{border:1px solid var(--linha);border-radius:10px;margin:0 0 10px;padding:8px 12px;background:var(--superficie)}
  .empilhar tr.conta{background:var(--superficie-2)}
  .empilhar td{display:flex;justify-content:space-between;gap:14px;border:0;padding:4px 0;text-align:right}
  .empilhar td::before{content:attr(data-rot);color:var(--tinta-2);text-align:left;font-weight:500;flex:none}
  .empilhar td:first-child{display:block;text-align:left;font-weight:650;padding-bottom:6px;min-width:0}
  .empilhar td:first-child::before{content:none}
  .empilhar .sub-c{text-align:right}
  .empilhar td:first-child .sub-c,.empilhar td:first-child .cv{text-align:left}
  .barras-ref .lin{grid-template-columns:minmax(80px,120px) 1fr 58px;gap:8px}
  .atencao-lista li{display:block}
  .atencao-lista .ic{margin-right:8px}
  .atencao-lista .nivel{display:inline-block;min-width:0;margin-right:8px}
  .atencao-lista li>span:not(.nivel){display:inline}
  .atencao-lista a{margin-left:8px}
}
@media (max-width:480px){
  .resumo{grid-template-columns:minmax(0,1fr)}
  .heroi{grid-column:auto}
}
@media print{
  .nav,#tema{display:none}
  body{background:#fff}
  .cartao,details.bloco{break-inside:avoid}
}
""".replace("__CLARO__", _bloco_tokens(TOKENS_CLARO)).replace("__ESCURO__", _bloco_tokens(TOKENS_ESCURO))

JS_CABECA = """(function(){try{var t=localStorage.getItem("painel-tema");if(t==="light"||t==="dark"){document.documentElement.setAttribute("data-theme",t)}}catch(e){}})();"""

JS = """
(function () {
  var raiz = document.documentElement;
  var botao = document.getElementById("tema");
  var chave = "painel-tema";
  var modos = [null, "light", "dark"];
  var nomes = ["automático", "claro", "escuro"];
  function ler() { try { return localStorage.getItem(chave); } catch (e) { return null; } }
  function gravar(v) { try { if (v) { localStorage.setItem(chave, v); } else { localStorage.removeItem(chave); } } catch (e) {} }
  var atual = ler();
  if (atual !== "light" && atual !== "dark") { atual = null; }
  function aplicar() {
    if (atual) { raiz.setAttribute("data-theme", atual); } else { raiz.removeAttribute("data-theme"); }
    if (botao) { botao.textContent = "Tema: " + nomes[modos.indexOf(atual)]; }
  }
  if (botao) {
    botao.addEventListener("click", function () {
      atual = modos[(modos.indexOf(atual) + 1) % 3];
      gravar(atual);
      aplicar();
    });
  }
  aplicar();

  var faixa = document.getElementById("idade-dados");
  if (faixa) {
    var ultima = faixa.getAttribute("data-ultima");
    var limite = parseInt(faixa.getAttribute("data-limite"), 10) || 7;
    if (ultima) {
      var p = ultima.split("-");
      var d0 = new Date(parseInt(p[0], 10), parseInt(p[1], 10) - 1, parseInt(p[2], 10));
      var agora = new Date();
      var h0 = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate());
      var n = Math.max(0, Math.round((h0 - d0) / 86400000));
      var quando = faixa.querySelector(".idade-quando");
      if (quando) { quando.textContent = n <= 0 ? "hoje" : (n === 1 ? "ontem" : "há " + n + " dias"); }
      var aviso = faixa.querySelector(".idade-aviso");
      var velho = n > limite;
      if (aviso) { aviso.hidden = !velho; }
      faixa.classList.toggle("aviso", velho);
      var ic = faixa.querySelector(".ic");
      if (ic) { ic.className = "ic " + (velho ? "ic-aviso" : "ic-info"); }
    }
  }

  var dica = document.getElementById("dica");
  if (!dica) { return; }
  var alvoAtual = null;
  function esconder() { dica.hidden = true; alvoAtual = null; }
  function posicionar(x, y) {
    var r = dica.getBoundingClientRect();
    var nx = x + 14, ny = y + 14;
    if (nx + r.width > window.innerWidth - 8) { nx = x - r.width - 14; }
    if (ny + r.height > window.innerHeight - 8) { ny = y - r.height - 14; }
    dica.style.left = Math.max(8, nx) + "px";
    dica.style.top = Math.max(8, ny) + "px";
  }
  function mostrar(alvo, x, y) {
    var texto = alvo.getAttribute("data-dica");
    if (!texto) { return; }
    while (dica.firstChild) { dica.removeChild(dica.firstChild); }
    texto.split("\\n").forEach(function (linha, i) {
      var d = document.createElement("div");
      if (i === 0) { d.className = "dica-titulo"; }
      d.textContent = linha;
      dica.appendChild(d);
    });
    dica.hidden = false;
    alvoAtual = alvo;
    posicionar(x, y);
  }
  function achar(e) { return e.target && e.target.closest ? e.target.closest("[data-dica]") : null; }
  function mover(e) {
    var t = achar(e);
    if (!t) { esconder(); return; }
    if (t !== alvoAtual) { mostrar(t, e.clientX, e.clientY); } else { posicionar(e.clientX, e.clientY); }
  }
  document.addEventListener("pointermove", mover);
  document.addEventListener("pointerdown", mover);
  document.addEventListener("focusin", function (e) {
    var t = achar(e);
    if (t) { var r = t.getBoundingClientRect(); mostrar(t, r.left + r.width / 2, r.top); }
  });
  document.addEventListener("focusout", esconder);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { esconder(); } });
  window.addEventListener("scroll", esconder, { passive: true });
})();
"""


def esc(t) -> str:
    return html.escape(str(t), quote=True)


def v_txt(txt: str) -> str:
    """Texto formatado para HTML; 'não medido' ganha o estilo discreto."""
    if txt == NAO_MEDIDO:
        return f'<span class="nm">{NAO_MEDIDO}</span>'
    return esc(txt)


def h_int(v) -> str:
    return v_txt(fmt_int(v))


def h_dec(v, casas: int = 1) -> str:
    return v_txt(fmt_dec(v, casas))


def h_pct(v, casas: int | None = None) -> str:
    return v_txt(fmt_pct(v, casas))


def dica(*linhas: str) -> str:
    return esc("\n".join(linhas))


def ic_status(nivel: str) -> str:
    mapa = {
        "bom": "ic-bom",
        "aviso": "ic-aviso",
        "critico": "ic-critico",
        "neutro": "ic-neutro",
        "info": "ic-info",
    }
    return f'<i class="ic {mapa.get(nivel, "ic-neutro")}" aria-hidden="true"></i>'


def selo_estado(nivel: str, rotulo: str) -> str:
    return f'<span class="estado">{ic_status(nivel)}{esc(rotulo)}</span>'


HORIZONTE_DIAS = 42

STATUS_META_VISUAL = {
    "atingida": "bom",
    "no_caminho": "bom",
    "atencao": "aviso",
    "critico": "critico",
    "prazo_vencido": "critico",
    "nao_medido": "neutro",
    "sem_ritmo": "neutro",
    "amostra_pequena": "neutro",
}
MEDIDOR_CLASSE = {"bom": "", "aviso": "aviso", "critico": "critico", "neutro": "neutro"}


def ticks_bonitos(minimo: float, maximo: float, alvo: int = 4) -> list[float]:
    if maximo <= minimo:
        maximo = minimo + 1
    bruto = (maximo - minimo) / alvo
    exp = math.floor(math.log10(bruto))
    passo = 10 ** exp
    for mult in (1, 2, 2.5, 5, 10):
        if mult * passo >= bruto:
            passo = mult * passo
            break
    inicio = math.floor(minimo / passo) * passo
    fim = math.ceil(maximo / passo) * passo
    n = int(round((fim - inicio) / passo))
    return [inicio + i * passo for i in range(n + 1)]


def rotulo_eixo(v: float) -> str:
    if abs(v) >= 10000:
        return fmt_dec(v / 1000, 0 if v % 1000 == 0 else 1) + " mil"
    return fmt_int(v)


def caminho_topo_arredondado(x: float, y: float, w: float, h: float, r: float = 4) -> str:
    r = min(r, w / 2, h)
    return (
        f"M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
        f"L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} L{x + w:.1f},{y + h:.1f} Z"
    )


def valor_meta(ind: str, v) -> str:
    return valor_indicador_texto(ind, v)


def sinal_meta(ind: str, v) -> str:
    return valor_indicador_texto(ind, v, sinal=True)


def svg_linha_seguidores(m: dict, variante: str) -> str:
    seg = m["seguidores"]
    serie = [(x["dia"], x["valor"]) for x in seg["serie"]]
    meta = next((x for x in m["metas"] if x["indicador"] == "seguidores"), None)
    ultimo_dia, ultimo_val = serie[-1]
    larg, alt, fs = (540, 270, 12) if variante == "desk" else (340, 250, 11)
    ml, mr, mt, mb = (46, 58, 14, 34) if variante == "desk" else (40, 50, 12, 32)

    fim_h = ultimo_dia
    nece = proj = None
    if meta and meta["status"] in ("no_caminho", "atencao", "critico", "sem_ritmo") and meta["prazo"] and meta["prazo"] > ultimo_dia:
        fim_h = min(meta["prazo"], ultimo_dia + timedelta(days=HORIZONTE_DIAS))
        semanas = (fim_h - ultimo_dia).days / 7
        if meta["ritmo_necessario"] is not None:
            nece = (fim_h, ultimo_val + meta["ritmo_necessario"] * semanas)
        if meta["ritmo_recente"] is not None:
            proj = (fim_h, max(0, ultimo_val + meta["ritmo_recente"] * semanas))
    inicio = serie[0][0]
    unico = len(serie) == 1 and fim_h == ultimo_dia
    if unico:
        inicio = ultimo_dia - timedelta(days=1)
    dias_total = max((fim_h - inicio).days, 1) if not unico else 2
    valores = [v for _, v in serie] + [p[1] for p in (nece, proj) if p]
    vmin, vmax = min(valores), max(valores)
    if vmax == vmin:
        vmin, vmax = vmin - 1, vmax + 1
    pad = (vmax - vmin) * 0.08
    ticks = ticks_bonitos(max(0, vmin - pad), vmax + pad, 4)
    y0, y1 = ticks[0], ticks[-1]
    largura_plot = larg - ml - mr
    altura_plot = alt - mt - mb

    def px(d: date) -> float:
        return ml + largura_plot * ((d - inicio).days / dias_total)

    def py(v: float) -> float:
        return mt + altura_plot * (1 - (v - y0) / (y1 - y0))

    partes = [f'<svg class="graf graf-{variante if variante == "desk" else "cel"}" viewBox="0 0 {larg} {alt}" role="img" aria-label="Linha com a evolução de seguidores de {fmt_data(inicio)} a {fmt_data(ultimo_dia)}: de {fmt_int(serie[0][1])} para {fmt_int(ultimo_val)}.">']
    for t in ticks:
        y = py(t)
        partes.append(f'<line class="grade" x1="{ml}" x2="{larg - mr}" y1="{y:.1f}" y2="{y:.1f}"/>')
        partes.append(f'<text x="{ml - 6}" y="{y + fs * 0.35:.1f}" text-anchor="end" font-size="{fs}">{esc(rotulo_eixo(t))}</text>')
    partes.append(f'<line class="eixo" x1="{ml}" x2="{larg - mr}" y1="{py(y0):.1f}" y2="{py(y0):.1f}"/>')
    n_x = 5 if variante == "desk" else 4
    if unico:
        rotulos_x = [(ultimo_dia, "middle")]
    else:
        rotulos_x = []
        for i in range(n_x):
            d = inicio + timedelta(days=round(dias_total * i / (n_x - 1)))
            rotulos_x.append((d, "start" if i == 0 else ("end" if i == n_x - 1 else "middle")))
    for d, ancora in rotulos_x:
        partes.append(f'<text x="{px(d):.1f}" y="{alt - 10}" text-anchor="{ancora}" font-size="{fs}">{esc(fmt_data_curta(d))}</text>')

    if proj:
        partes.append(f'<path class="proj" d="M{px(ultimo_dia):.1f},{py(ultimo_val):.1f} L{px(proj[0]):.1f},{py(proj[1]):.1f}"/>')
    if nece:
        partes.append(f'<path class="nece" d="M{px(ultimo_dia):.1f},{py(ultimo_val):.1f} L{px(nece[0]):.1f},{py(nece[1]):.1f}"/>')
    caminho = " ".join(("M" if i == 0 else "L") + f"{px(d):.1f},{py(v):.1f}" for i, (d, v) in enumerate(serie))
    partes.append(f'<path class="serie" d="{caminho}"/>')
    for i, (d, v) in enumerate(serie):
        anterior = serie[i - 1][1] if i else None
        linhas = [fmt_data(d), f"{fmt_int(v)} seguidores"]
        if anterior is not None:
            linhas.append(f"{fmt_sinal(v - anterior)} desde a coleta anterior")
        partes.append(f'<circle class="ponto" cx="{px(d):.1f}" cy="{py(v):.1f}" r="4"/>')
        partes.append(f'<circle class="alvo" cx="{px(d):.1f}" cy="{py(v):.1f}" r="12" tabindex="0" data-dica="{dica(*linhas)}"/>')
    xf, yf = px(ultimo_dia), py(ultimo_val)
    rotulo_ultimo_y = yf - 10
    partes.append(f'<text class="valor" x="{xf:.1f}" y="{rotulo_ultimo_y:.1f}" text-anchor="{"end" if nece or proj else "middle"}" font-size="{fs + 1}">{esc(fmt_int(ultimo_val))}</text>')
    fim_labels = []
    if nece:
        fim_labels.append(("nece", nece, "Ritmo necessário", f"Chegaria a {fmt_int(nece[1])} em {fmt_data(nece[0])}"))
    if proj:
        fim_labels.append(("proj", proj, "Se mantiver o ritmo recente (hipótese)", f"Chegaria a {fmt_int(proj[1])} em {fmt_data(proj[0])}"))
    ys_usados: list[float] = []
    for tipo, (d, v), titulo_dica, detalhe_dica in fim_labels:
        x, y = px(d), py(v)
        partes.append(f'<circle class="ponto-{tipo}" cx="{x:.1f}" cy="{y:.1f}" r="4"/>')
        partes.append(f'<circle class="alvo" cx="{x:.1f}" cy="{y:.1f}" r="12" tabindex="0" data-dica="{dica(titulo_dica, detalhe_dica)}"/>')
        if all(abs(y - u) > fs * 1.3 for u in ys_usados):
            partes.append(f'<text class="valor" x="{x + 8:.1f}" y="{y + fs * 0.35:.1f}" font-size="{fs}">{esc(fmt_int(v))}</text>')
            ys_usados.append(y)
    partes.append("</svg>")
    return "".join(partes)


def html_legenda_seguidores(m: dict) -> str:
    meta = next((x for x in m["metas"] if x["indicador"] == "seguidores"), None)
    itens = ['<span><i class="chave"></i>Seguidores medidos</span>']
    if meta and meta["status"] in ("no_caminho", "atencao", "critico", "sem_ritmo") and meta["ritmo_necessario"] is not None:
        itens.append(f'<span><i class="chave nece"></i>Ritmo necessário para o prazo de {esc(fmt_data(meta["prazo"]))}</span>')
    if meta and meta["ritmo_recente"] is not None and meta["status"] in ("no_caminho", "atencao", "critico", "sem_ritmo"):
        itens.append('<span><i class="chave proj"></i>Se mantiver o ritmo recente (hipótese)</span>')
    return '<div class="legenda">' + "".join(itens) + "</div>"


def tabela_html(cabecalhos: list[str], linhas: list[list[str]], classe: str = "") -> str:
    th = "".join(f"<th>{esc(c)}</th>" for c in cabecalhos)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in linha) + "</tr>" for linha in linhas)
    return f'<div class="rolagem"><table class="tab {classe}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def html_secao_seguidores(m: dict) -> str:
    seg = m["seguidores"]
    if not seg["disponivel"]:
        corpo = '<p class="nota">Sem coleta de seguidores ainda. Rode a coleta de métricas (ou preencha metricas/perfil.csv) para ver a evolução.</p>'
        return f'<article class="cartao"><h3>Evolução de seguidores</h3>{corpo}</article>'
    linhas = []
    anterior = None
    for x in seg["serie"]:
        linhas.append([esc(fmt_data(x["dia"])), h_int(x["valor"]), v_txt(fmt_sinal(x["valor"] - anterior)) if anterior is not None else "–"])
        anterior = x["valor"]
    if seg["n_coletas"] < 2:
        nota = '<p class="nota">Só uma coleta de perfil: com uma coleta só não dá para ver tendência. A linha aparece a partir da segunda coleta.</p>'
    else:
        nota = (
            '<p class="nota">Cada ponto é uma coleta do total de seguidores. A diferença entre dois pontos é o '
            "<strong>crescimento líquido</strong>: quem entrou menos quem saiu. Ela não separa as duas coisas.</p>"
        )
    graficos = svg_linha_seguidores(m, "desk") + svg_linha_seguidores(m, "cel")
    return (
        '<article class="cartao" id="seguidores"><h3>Evolução de seguidores</h3>'
        f'<p class="sub">{plural(seg["n_coletas"], "coleta")} entre {esc(fmt_data(seg["dia_inicial"]))} e {esc(fmt_data(seg["dia_atual"]))}</p>'
        f"{graficos}{html_legenda_seguidores(m)}{nota}"
        '<details class="alt"><summary>Ver os números em tabela</summary>'
        f'{tabela_html(["Coleta", "Seguidores", "Variação"], linhas)}</details></article>'
    )


def svg_barras_semanais(m: dict, variante: str) -> str:
    r = m["ritmo"]
    semanas = r["semanas"]
    meta = r.get("meta")
    larg, alt, fs = (540, 270, 12) if variante == "desk" else (340, 250, 11)
    ml, mr, mt, mb = (34, 50, 16, 46) if variante == "desk" else (30, 40, 16, 46)
    topo_max = max([s["total"] for s in semanas] + [meta or 0, 1])
    ticks = ticks_bonitos(0, topo_max + 0.4, 4)
    ticks = [t for t in ticks if float(t).is_integer()] or [0, 1]
    y1 = ticks[-1]
    largura_plot = larg - ml - mr
    altura_plot = alt - mt - mb
    slot = largura_plot / len(semanas)
    bw = min(24.0, slot * 0.6)

    def py(v: float) -> float:
        return mt + altura_plot * (1 - v / y1)

    partes = [f'<svg class="graf graf-{"desk" if variante == "desk" else "cel"}" viewBox="0 0 {larg} {alt}" role="img" aria-label="Colunas com o número de posts publicados por semana nas últimas {len(semanas)} semanas.">']
    for t in ticks:
        y = py(t)
        partes.append(f'<line class="{"eixo" if t == 0 else "grade"}" x1="{ml}" x2="{larg - mr}" y1="{y:.1f}" y2="{y:.1f}"/>')
        partes.append(f'<text x="{ml - 6}" y="{y + fs * 0.35:.1f}" text-anchor="end" font-size="{fs}">{int(t)}</text>')
    for i, s in enumerate(semanas):
        cx = ml + slot * (i + 0.5)
        x = cx - bw / 2
        base_y = py(0)
        parcial = " parcial" if (not s["completa"] or s.get("parcial_inicio")) else ""
        proj_h = altura_plot * s["n_projeto"] / y1
        fora_h = altura_plot * s["n_fora"] / y1
        gap = 2 if (s["n_projeto"] and s["n_fora"]) else 0
        if s["n_projeto"]:
            y_p = base_y - proj_h
            if s["n_fora"]:
                partes.append(f'<rect class="barra-1{parcial}" x="{x:.1f}" y="{y_p:.1f}" width="{bw:.1f}" height="{proj_h:.1f}"/>')
            else:
                partes.append(f'<path class="barra-1{parcial}" d="{caminho_topo_arredondado(x, y_p, bw, proj_h)}"/>')
        if s["n_fora"]:
            y_f = base_y - proj_h - fora_h
            h_f = fora_h - gap
            partes.append(f'<path class="barra-2{parcial}" d="{caminho_topo_arredondado(x, y_f, bw, h_f)}"/>')
        topo_y = base_y - proj_h - fora_h
        partes.append(f'<text class="valor" x="{cx:.1f}" y="{topo_y - 5:.1f}" text-anchor="middle" font-size="{fs}">{s["total"]}</text>')
        partes.append(f'<text x="{cx:.1f}" y="{alt - 26}" text-anchor="middle" font-size="{fs - 1 if variante != "desk" else fs}">{esc(fmt_data_curta(s["inicio"]))}</text>')
        if not s["completa"]:
            partes.append(f'<text x="{cx:.1f}" y="{alt - 12}" text-anchor="middle" font-size="{fs - 1}">em curso</text>')
        elif s.get("parcial_inicio"):
            partes.append(f'<text x="{cx:.1f}" y="{alt - 12}" text-anchor="middle" font-size="{fs - 1}">parcial</text>')
        formatos = [f"{NOMES_FORMATO[f]} {s['por_formato'][f]}" for f in NOMES_FORMATO if s["por_formato"][f]]
        rotulo_sem = " (em curso)" if not s["completa"] else (" (parcial: os dados começam no meio da semana)" if s.get("parcial_inicio") else "")
        linhas = [f"Semana de {fmt_data_curta(s['inicio'])}" + rotulo_sem, f"{plural(s['total'], 'post')}: {s['n_projeto']} do projeto, {s['n_fora']} de fora"]
        if formatos:
            linhas.append(" · ".join(formatos))
        partes.append(f'<rect class="alvo" x="{cx - slot / 2:.1f}" y="{mt}" width="{slot:.1f}" height="{altura_plot:.1f}" tabindex="0" data-dica="{dica(*linhas)}"/>')
    if meta:
        ym = py(meta)
        partes.append(f'<line class="meta-linha" x1="{ml}" x2="{larg - mr}" y1="{ym:.1f}" y2="{ym:.1f}"/>')
        partes.append(f'<text class="valor" x="{larg - mr + 6}" y="{ym + fs * 0.35:.1f}" font-size="{fs}">meta {esc(fmt_dec(meta, 0 if float(meta).is_integer() else 1))}</text>')
    partes.append("</svg>")
    return "".join(partes)


def html_secao_ritmo(m: dict) -> str:
    r = m["ritmo"]
    if not r.get("disponivel"):
        return '<article class="cartao"><h3>Ritmo de publicação</h3><p class="nota">Sem posts coletados ainda: o ritmo fica como não medido. Rode a coleta de métricas e gere o painel de novo.</p></article>'
    meta = r.get("meta")
    aviso_projeto = (
        ' <strong>Só conta posts publicados por este projeto</strong>: sem coleta de posts, não sei dos posts de fora.'
        if r.get("so_projeto")
        else ""
    )
    if r["media_recente"] is None:
        resumo = f'<p class="nota">Ainda não há 2 semanas completas de dados: sem elas, a média não é calculada.{aviso_projeto}</p>'
    else:
        base = f"Média das últimas {plural(r['n_semanas_media'], 'semana completa', 'semanas completas')}: <strong>{esc(fmt_dec(r['media_recente'], 1))} posts por semana</strong>"
        if meta:
            nivel = {"ok": "bom", "atencao": "aviso", "critico": "critico"}.get(r["status"], "neutro")
            rot = {"ok": "No ritmo", "atencao": "Abaixo da meta", "critico": "Bem abaixo da meta"}.get(r["status"], "")
            base += f" para uma meta de {esc(fmt_dec(meta, 0 if float(meta).is_integer() else 1))} ({esc(fmt_pct(r['razao'], 0))} da meta). {selo_estado(nivel, rot)}"
        resumo = f'<p class="nota">{base}{aviso_projeto}</p>'
    tem_fora = any(s["n_fora"] for s in r["semanas"])
    leg = ['<span><i class="chave cx1"></i>Posts do projeto</span>']
    if tem_fora:
        leg.append('<span><i class="chave cx2"></i>Posts de fora do projeto</span>')
    if meta:
        leg.append('<span><i class="chave meta"></i>Meta por semana</span>')
    linhas = [
        [esc(fmt_data(s["inicio"])) + (" (em curso)" if not s["completa"] else (" (parcial)" if s.get("parcial_inicio") else "")), str(s["n_projeto"]), str(s["n_fora"]), str(s["total"])]
        for s in r["semanas"]
    ]
    return (
        '<article class="cartao" id="ritmo"><h3>Ritmo de publicação</h3>'
        f'<p class="sub">Posts por semana (segunda a domingo). As semanas parciais (a primeira, se os dados começam no meio dela, e a em curso) aparecem mais claras e ficam fora da média.</p>'
        f'{svg_barras_semanais(m, "desk")}{svg_barras_semanais(m, "cel")}'
        f'<div class="legenda">{"".join(leg)}</div>{resumo}'
        '<details class="alt"><summary>Ver os números em tabela</summary>'
        f'{tabela_html(["Semana de", "Do projeto", "De fora", "Total"], linhas)}</details></article>'
    )


def html_faixa_idade(m: dict) -> str:
    d = m["dados"]
    ult = d["ultima_coleta"]
    if ult is None:
        return (
            '<div id="idade-dados" class="faixa aviso" role="status">'
            f"{ic_status('aviso')}<div><strong>Nenhuma coleta de métricas encontrada.</strong> "
            "O painel mostra só o plano. Colete as métricas (ou preencha os CSVs à mão, veja referencias/coleta-manual.md) e gere o painel de novo.</div></div>"
        )
    velho = d["desatualizado"]
    classe = "faixa aviso" if velho else "faixa"
    aviso = (
        f'<span class="idade-aviso"{"" if velho else " hidden"}> Passou de {DIAS_AVISO_DADOS} dias: colete de novo antes de decidir com estes números.</span>'
    )
    return (
        f'<div id="idade-dados" class="{classe}" data-ultima="{ult.isoformat()}" data-limite="{DIAS_AVISO_DADOS}" role="status">'
        f"{ic_status('aviso' if velho else 'info')}"
        f'<div class="idade-txt">Última coleta de métricas: <strong>{esc(fmt_data(ult))}</strong> '
        f'(<span class="idade-quando">{esc(fmt_dias(d["idade_dias"]))}</span>).{aviso}</div></div>'
    )


def html_atencao(m: dict) -> str:
    alertas = m["alertas"]
    if not alertas:
        return ""
    nomes = {"alta": ("critico", "Alta"), "media": ("aviso", "Média"), "baixa": ("neutro", "Baixa"), "info": ("info", "Aviso")}
    itens = []
    for a in alertas[:8]:
        nivel, rot = nomes[a["nivel"]]
        link = f'<a href="#{esc(a["ancora"])}">ver na seção</a>' if a["ancora"] else ""
        itens.append(f'<li>{ic_status(nivel)}<span class="nivel">{rot}</span><span>{esc(a["texto"])}</span>{link}</li>')
    extra = f'<p class="nota">Mais {len(alertas) - 8} pontos menores no JSON embutido do painel.</p>' if len(alertas) > 8 else ""
    return (
        '<section class="sec" id="atencao"><h2>Pontos de atenção</h2>'
        '<p class="sub">O que olhar primeiro, em ordem de prioridade. São observações dos números, não conclusões.</p>'
        f'<ul class="atencao-lista">{"".join(itens)}</ul>{extra}</section>'
    )


def delta_html(delta, n: int, n0: int) -> str:
    if delta is None:
        if n0 < N_AMOSTRA_MINIMA:
            return '<span class="delta igual">sem base para comparar com as 4 semanas anteriores</span>'
        return ""
    if abs(delta) < 0.03:
        return '<span class="delta igual">≈ estável vs 4 semanas antes</span>'
    seta = "▲" if delta > 0 else "▼"
    classe = "sobe" if delta > 0 else "desce"
    return f'<span class="delta {classe}">{seta} {esc(fmt_sinal(delta * 100, 0))}% vs 4 semanas antes</span>'


def tile_kpi(rotulo: str, valor_html: str, sub: str, delta: str = "", n: int | None = None) -> str:
    amostra = ""
    if n is not None and n < N_AMOSTRA_OK:
        amostra = ' <span class="amostra">amostra pequena</span>'
    return (
        f'<article class="cartao tile"><p class="rotulo">{esc(rotulo)}</p><p class="tile-num">{valor_html}</p>'
        f'{delta}<p class="tile-sub">{sub}{amostra}</p></article>'
    )


def html_resumo(m: dict) -> str:
    seg = m["seguidores"]
    if seg["disponivel"]:
        j = seg["janela"]
        if j["saldo"] is not None:
            linha = f"<strong>{esc(fmt_sinal(j['saldo']))}</strong> em {j['dias']} dias (cerca de {esc(fmt_sinal(j['ritmo_semana']))} por semana)"
        else:
            linha = "Poucas coletas para medir o ritmo: preciso de duas coletas com pelo menos 14 dias de diferença."
        heroi = (
            '<article class="cartao heroi"><p class="rotulo">Seguidores</p>'
            f'<p class="heroi-num">{h_int(seg["atual"])}</p><p class="heroi-sub">{linha}</p>'
            f'<p class="heroi-nota">Crescimento líquido: quem entrou menos quem saiu. Coleta de {esc(fmt_data(seg["dia_atual"]))}.</p></article>'
        )
    else:
        heroi = (
            '<article class="cartao heroi"><p class="rotulo">Seguidores</p>'
            f'<p class="heroi-num">{v_txt(NAO_MEDIDO)}</p><p class="heroi-sub">Ainda não há coleta do perfil.</p></article>'
        )
    k = m["kpis"]
    r = m["ritmo"]
    tiles = []
    if r.get("disponivel") and r["media_recente"] is not None:
        meta = r.get("meta")
        sub = f"média das últimas {r['n_semanas_media']} semanas completas"
        if meta:
            sub += f" · meta {esc(fmt_dec(meta, 0 if float(meta).is_integer() else 1))}"
        tiles.append(tile_kpi("Posts por semana", h_dec(r["media_recente"], 1), sub))
    else:
        tiles.append(tile_kpi("Posts por semana", v_txt(NAO_MEDIDO), "precisa de 2 semanas completas de posts coletados"))
    if k:
        a = k["alcance_medio"]
        tiles.append(
            tile_kpi(
                "Alcance médio por post",
                h_int(a["valor"]) if a["n"] else v_txt(NAO_MEDIDO),
                f"contas diferentes que viram, em posts dos últimos {JANELA_KPI_DIAS} dias · n={a['n']}",
                delta_html(a["delta"], a["n"], a["n_anterior"]) if a["n"] else "",
                a["n"],
            )
        )
        t = k["interacao_valor"]
        tiles.append(
            tile_kpi(
                "Interação de valor",
                h_pct(t["valor"]) if t["n"] else v_txt(NAO_MEDIDO),
                f"salvou, compartilhou ou comentou ÷ alcance · n={t['n']}",
                delta_html(t["delta"], t["n"], t["n_anterior"]) if t["n"] else "",
                t["n"],
            )
        )
        rl = k["alcance_rel"]
        tiles.append(
            tile_kpi(
                "Alcance ÷ seguidores",
                h_pct(rl["valor"], 0) if rl["n"] else v_txt(NAO_MEDIDO),
                f"mediana de quanto da base cada post alcança · n={rl['n']}",
                delta_html(rl["delta"], rl["n"], rl["n_anterior"]) if rl["n"] else "",
                rl["n"],
            )
        )
    else:
        for rot in ("Alcance médio por post", "Interação de valor", "Alcance ÷ seguidores"):
            tiles.append(tile_kpi(rot, v_txt(NAO_MEDIDO), "sem posts coletados"))
    return (
        '<section class="sec" id="resumo"><h2>Resumo</h2>'
        '<p class="sub">Os números que mais pesam, com a base de posts de cada um. Só entram posts maduros: coletados pelo menos '
        f"{HORAS_MATURIDADE} horas depois de publicados.</p>"
        f'<div class="resumo">{heroi}{"".join(tiles)}</div></section>'
    )


def texto_prazo(x: dict, hoje: date) -> str:
    prazo = x["prazo"]
    if prazo is None:
        return NAO_MEDIDO
    dias = (prazo - hoje).days
    if x["status"] == "prazo_vencido" or dias < 0:
        return f"{fmt_data(prazo)} · vencido"
    if dias == 0:
        return f"{fmt_data(prazo)} · hoje"
    if dias < 7:
        return f"{fmt_data(prazo)} · {plural(dias, 'dia')}"
    return f"{fmt_data(prazo)} · {plural(int(round(dias / 7)), 'semana')}"


def html_meta(x: dict, rascunho: bool, hoje: date) -> str:
    nivel = STATUS_META_VISUAL[x["status"]]
    ind = x["indicador"]
    prog = x["progresso"]
    largura = 0 if prog is None else max(0, min(prog, 1)) * 100
    if prog is None:
        txt_prog = "Sem medição para calcular o progresso."
    elif prog < 0:
        txt_prog = f"Abaixo da base de partida · faltam {sinal_meta(ind, x['falta'])}"
    elif prog >= 1:
        txt_prog = f"Alvo alcançado ({fmt_pct(prog, 0)} do caminho)"
    else:
        txt_prog = f"{fmt_pct(prog, 0)} do caminho da base até o alvo · faltam {sinal_meta(ind, x['falta'])}"
    linhas = [("Prazo", esc(texto_prazo(x, hoje)))]
    if ind == "posts_por_semana":
        linhas.append(("Como se mede", esc(f"média das últimas {SEMANAS_RITMO} semanas completas")))
    else:
        necessario, recente = x["ritmo_necessario"], x["ritmo_recente"]
        if necessario is not None:
            nec_html = esc(sinal_meta(ind, necessario) + " por semana")
        elif x["status"] in ("atingida", "prazo_vencido"):
            nec_html = '<span class="mut">–</span>'
        else:
            nec_html = v_txt(NAO_MEDIDO)
        linhas.append(("Ritmo necessário", nec_html))
        rec_html = esc(sinal_meta(ind, recente) + " por semana") if recente is not None else v_txt(NAO_MEDIDO)
        linhas.append(("Ritmo recente", rec_html))
    dl = "".join(f"<dt>{esc(a)}</dt><dd>{b}</dd>" for a, b in linhas)
    notas = []
    if x["nota"]:
        notas.append(esc(x["nota"]))
    if rascunho:
        notas.append("Meta em rascunho: é sugestão até a pessoa aprovar.")
    nota = f'<p class="nota">{" ".join(notas)}</p>' if notas else ""
    mostrar_unidade = ind == "alcance_medio" and "contas" not in x["descricao"].lower()
    unidade = f' <span class="mut">({esc(x["unidade"])})</span>' if mostrar_unidade else ""
    return (
        '<article class="cartao">'
        f'<div class="meta-topo"><h3>{esc(x["descricao"])}{unidade}</h3>{selo_estado(nivel, x["status_rotulo"])}</div>'
        f'<div class="fluxo"><span class="mut">base {esc(valor_meta(ind, x["base"]))}</span><span class="seta">→</span>'
        f'<span class="atual">{v_txt(valor_meta(ind, x["atual"]))}</span><span class="seta">→</span>'
        f'<span class="mut">alvo {esc(valor_meta(ind, x["alvo"]))}</span></div>'
        f'<div class="medidor {MEDIDOR_CLASSE[nivel]}" role="img" aria-label="Progresso: {esc(txt_prog)}"><i style="width:{largura:.1f}%"></i></div>'
        f'<p class="prog">{esc(txt_prog)}</p><dl class="lista-def">{dl}</dl>{nota}</article>'
    )


def html_movimentos(m: dict) -> str:
    movs = m["movimentos"]
    if not movs:
        return ""
    itens = []
    for mv in movs:
        if mv["dias"] is None:
            quando = ""
        elif mv["dias"] < 0:
            quando = f"até {fmt_data(mv['ate'])} · prazo vencido"
        elif mv["dias"] == 0:
            quando = f"até {fmt_data(mv['ate'])} · hoje"
        else:
            quando = f"até {fmt_data(mv['ate'])} · {plural(mv['dias'], 'dia')}"
        if mv["mede_sozinho"]:
            hoje_txt = v_txt(mv["atual_texto"]) if mv["atual_texto"] is not None else v_txt(NAO_MEDIDO)
            ind = f'Como saber se funcionou: {esc(mv["indicador_nome"])} · hoje {hoje_txt}'
        else:
            ind = f'Como saber se funcionou: {esc(mv["indicador_nome"])}' + (' <span class="mut">(o painel não mede: a pessoa informa)</span>' if mv["indicador"] else "")
        itens.append(f'<li><span><strong>{esc(mv["o_que"])}</strong></span><span class="quando">{esc(quando)}</span><span class="ind">{ind}</span></li>')
    return (
        '<article class="cartao" style="margin-top:12px"><h3>Movimentos do período</h3>'
        '<p class="sub">Ações combinadas na estratégia, cada uma com o indicador que mostra se funcionou.</p>'
        f'<ul class="movs">{"".join(itens)}</ul></article>'
    )


def html_metas(m: dict) -> str:
    rascunho = m["estrategia"]["status"] == "rascunho"
    if not m["metas"]:
        corpo = '<p class="nota">A estratégia não tem metas. Peça à skill configurar-marca para definir.</p>'
    else:
        corpo = '<div class="metas">' + "".join(html_meta(x, rascunho, m["hoje"]) for x in m["metas"]) + "</div>"
    sub = (
        "Base, onde está agora e o alvo. O ritmo necessário é o que falta dividido pelas semanas até o prazo; "
        "ele é comparado com o ritmo dos últimos 28 dias."
    )
    return f'<section class="sec" id="metas"><h2>Metas</h2><p class="sub">{sub}</p>{corpo}{html_movimentos(m)}</section>'


def texto_media(e: dict) -> str:
    if not e["n"] or e["media"] is None:
        return ""
    return fmt_dec(e["media"], 1) if e["media"] < 100 else fmt_int(e["media"])


def celula_metrica(s: dict, campo: str, chave_taxa: str, indice, n_maduros: int, comparavel: bool = True) -> tuple[str, str]:
    t = s[chave_taxa]
    e = s[campo]
    if t["valor"] is None and not e["n"]:
        return v_txt(NAO_MEDIDO), ""
    classe = ""
    seta = ""
    sub_idx = ""
    if indice is not None and comparavel and n_maduros >= N_AMOSTRA_MINIMA and t["valor"] is not None:
        if indice >= INDICE_ACIMA:
            classe, seta = "acima", "▲ "
        elif indice <= INDICE_ABAIXO:
            classe, seta = "abaixo", "▼ "
        sub_idx = f'<span class="sub-c idx nw">{seta}{esc(fmt_dec(indice, 1))}× a conta</span>'
    principal = esc(fmt_pct(t["valor"])) if t["valor"] is not None else v_txt(NAO_MEDIDO)
    media_txt = texto_media(e)
    sub_media = f'<span class="sub-c">média {esc(media_txt)} por post</span>' if media_txt else ""
    return principal + sub_media + sub_idx, classe


def linha_grupo(g: dict, tipo: str, rot_conta: bool = False, conta_n: int | None = None) -> str:
    s = g["stats"]
    n = s["n_maduros"]
    if rot_conta:
        nome = "Conta (todos os posts maduros)"
        extra_nome = ""
    else:
        nome = esc(g["nome"])
        extra_nome = ""
        desc = g.get("descricao") or g.get("plano") or ""
        if g["id"] == SEM_CLASSIFICACAO:
            desc = "Posts de fora do projeto, ou sem arquivo em conteudo/<lote>/posts/"
        if desc:
            extra_nome += f'<span class="sub-c">{esc(desc)}</span>'
        if s["amostra"]:
            extra_nome += f'<span class="amostra">{esc(s["amostra"])} · n={n}</span>'
    plano = '<span class="mut">–</span>'
    if not rot_conta:
        if tipo == "pilar":
            if g.get("peso") is not None and g.get("fatia_real") is not None:
                plano = f'{esc(fmt_dec(g["peso"], 0))}% → {esc(fmt_pct(g["fatia_real"], 0))}'
            elif g.get("peso") is not None and g["id"] != SEM_CLASSIFICACAO:
                plano = f'{esc(fmt_dec(g["peso"], 0))}% → <span class="nm">sem posts</span>'
            elif g.get("fatia_real") is not None:
                plano = f'– → {esc(fmt_pct(g["fatia_real"], 0))}'
        elif tipo == "formato":
            if g.get("plano_semana") is not None:
                real = g.get("real_semana")
                real_txt = esc(fmt_dec(real, 1)) if real is not None else '<span class="nm">não medido</span>'
                plano = f'{esc(fmt_dec(g["plano_semana"], 0))} → {real_txt}<span class="sub-c">posts por semana</span>'
        elif tipo == "etapa":
            if g.get("fatia_real") is not None:
                plano = f'{esc(fmt_pct(g["fatia_real"], 0))}<span class="sub-c">dos posts</span>'
    posts_txt = f'{s["n_posts"]}<span class="sub-c">{n} maduros</span>' if s["n_posts"] else "0"
    a = s["alcance"]
    alc_txt = h_int(a["media"]) if a["n"] else v_txt(NAO_MEDIDO)
    if a["n"] and a["mediana"] is not None:
        alc_txt += f'<span class="sub-c">mediana {esc(fmt_int(a["mediana"]))}</span>'
    ind = g["indices"] if not rot_conta else {}
    comparavel = g["id"] != SEM_CLASSIFICACAO and n < (conta_n or 10**9)
    cels = [
        (None, f"{nome}{extra_nome}", "", ""),
        ("Plano → real", plano, "", "nw"),
        ("Posts", posts_txt, "", ""),
        ("Alcance médio", alc_txt, "", ""),
    ]
    for rot, campo, chave in (
        ("Salvamentos", "salvamentos", "taxa_salvamentos"),
        ("Compartilhamentos", "compartilhamentos", "taxa_compartilhamentos"),
        ("Comentários", "comentarios", "taxa_comentarios"),
    ):
        txt, cl = celula_metrica(s, campo, chave, ind.get(chave), n, comparavel)
        cels.append((rot + " (% do alcance)", txt, cl, ""))
    tds = ""
    if n == 0 and not rot_conta:
        vazio = "Nenhum post neste grupo no período." if not s["n_posts"] else f"{plural(s['n_posts'], 'post')}, nenhum maduro ainda."
        tds = (
            f'<td><div class="cv">{nome}{extra_nome}</div></td>'
            f'<td data-rot="Plano → real" class="nw"><div class="cv">{plano}</div></td>'
            f'<td colspan="5" class="vazio-g"><div class="cv"><span class="nm">{esc(vazio)}</span></div></td>'
        )
        return f"<tr>{tds}</tr>"
    for rot, conteudo, cl, extra in cels:
        attr = f' data-rot="{esc(rot)}"' if rot else ""
        tds += f'<td{attr} class="{(cl + " " + extra).strip()}"><div class="cv">{conteudo}</div></td>'
    classe = ' class="conta"' if rot_conta else ""
    return f"<tr{classe}>{tds}</tr>"


def tabela_grupos(titulo: str, grupos: list[dict], conta: dict, tipo: str, ajuda: str, cab_plano: str, aviso: str = "") -> str:
    sub_taxa = '<span class="th-sub">% do alcance · média por post</span>'
    cab = [
        "Grupo",
        cab_plano,
        "Posts",
        'Alcance médio<span class="th-sub">por post</span>',
        "Salvamentos" + sub_taxa,
        "Compartilhamentos" + sub_taxa,
        "Comentários" + sub_taxa,
    ]
    th = "".join(f"<th>{c if '<span' in c else esc(c)}</th>" for c in cab)
    linhas = "".join(linha_grupo(g, tipo, conta_n=conta["n_maduros"]) for g in grupos)
    linhas += linha_grupo({"nome": "Conta", "id": "_conta", "stats": conta, "indices": {}}, tipo, rot_conta=True)
    aviso_html = f'<p class="nota" style="margin:4px 0 8px">{esc(aviso)}</p>' if aviso else ""
    return (
        f'<h3 class="grupo-tit">{esc(titulo)}</h3><p class="mut" style="font-size:13px;margin-bottom:6px">{esc(ajuda)}</p>{aviso_html}'
        f'<div class="rolagem"><table class="tab empilhar"><thead><tr>{th}</tr></thead><tbody>{linhas}</tbody></table></div>'
    )


def html_grupos(m: dict) -> str:
    g = m["grupos"]
    conta = g["conta"]
    if conta["n_posts"] == 0:
        corpo = '<p class="nota">Sem posts coletados nas últimas semanas. Rode a coleta de métricas e gere o painel de novo.</p>'
        return f'<section class="sec" id="grupos"><h2>Desempenho por pilar, formato e etapa</h2>{corpo}</section>'
    aviso_amostra = ""
    if conta["n_maduros"] < N_MIN_RANKING:
        aviso_amostra = (
            f'<p class="nota"><strong>Amostra pequena:</strong> só {plural(conta["n_maduros"], "post maduro", "posts maduros")}. '
            "Diferenças entre grupos são pista, não regra. Repita a comparação em pelo menos 3 ocasiões antes de mudar a estratégia.</p>"
        )
    sub = (
        f"Posts publicados nas últimas {m['janela_dias'] // 7} semanas. O número grande é a taxa sobre o alcance (comparação por proporção); "
        f"abaixo dele, a média por post. ▲ ou ▼ marcam grupos que fogem da taxa da conta em mais de 25% (só com {N_AMOSTRA_MINIMA} posts ou mais no grupo)."
    )
    na_janela = [p for p in m["posts"] if p["na_janela"]]
    aviso_pilar = "" if any(p["pilar"] for p in na_janela) else (
        "Nenhum post do período tem pilar. O pilar vem do post do projeto (conteudo/<lote>/posts/<id>.json); "
        "posts de fora do projeto não têm."
    )
    aviso_etapa = "" if any(p["etapa"] for p in na_janela) else (
        "Nenhum post do período tem etapa do funil. A etapa vem do post do projeto (campo etapa_funil); "
        "posts de fora do projeto não têm."
    )
    pilar = tabela_grupos("Por pilar", g["pilar"], conta, "pilar", "Peso → real: o peso planejado do pilar e a fatia dos posts classificados no período.", "Peso → real", aviso_pilar)
    formato = tabela_grupos("Por formato", g["formato"], conta, "formato", "Plano → real: posts por semana planejados e a média real das últimas semanas completas.", "Plano → real")
    etapa = tabela_grupos("Por etapa do funil", g["etapa"], conta, "etapa", "Cada etapa existe para mover uma métrica diferente; veja o bloco do funil abaixo.", "Fatia dos posts", aviso_etapa)
    return (
        f'<section class="sec" id="grupos"><h2>Desempenho por pilar, formato e etapa</h2><p class="sub">{sub}</p>'
        f'<div class="cartao">{pilar}{formato}{etapa}{aviso_amostra}</div></section>'
    )


def svg_indice(indice) -> str:
    if indice is None:
        return ""
    x = 8 + min(max(indice, 0), 2) / 2 * 184
    return (
        '<svg class="indice-svg" width="200" height="20" viewBox="0 0 200 20" aria-hidden="true">'
        '<line class="trilho" x1="8" x2="192" y1="10" y2="10"/>'
        '<line class="centro" x1="100" x2="100" y1="3" y2="17"/>'
        f'<circle class="bola" cx="{x:.1f}" cy="10" r="6"/></svg>'
    )


def html_funil(m: dict) -> str:
    f = m["funil"]
    conta = m["grupos"]["conta"]
    if conta["n_posts"] == 0:
        return ""
    cards = []
    for e in f["etapas"]:
        trava = f["gargalo"] == e["id"]
        if e["valor"] is None:
            corpo = f'<p class="valor">{v_txt(NAO_MEDIDO)}</p><p class="mut" style="font-size:13px">{"Nenhum post maduro desta etapa no período." if e["n_maduros"] == 0 else "Faltam dados de alcance ou da métrica."}</p>'
        else:
            comp = ""
            if e["indice"] is not None:
                base_conta = "mediana" if e["chave_stat"] == "alcance_rel" else "média"
                comp = f'{esc(fmt_dec(e["indice"], 2))}× a {base_conta} da conta ({esc(fmt_pct(e["conta"]))})'
            valor = h_pct(e["valor"]) if e["chave_stat"] != "alcance_rel" else h_pct(e["valor"], 0)
            corpo = f'<p class="valor">{valor}</p>{svg_indice(e["indice"])}<p class="mut" style="font-size:13px">{comp}</p>'
        tag = '<span class="estado">' + ic_status("aviso") + "Hipótese: trava aqui</span>" if trava else ""
        amostra = f'<span class="amostra">{esc(e["amostra"])} · n={e["n_maduros"]}</span>' if e["amostra"] else f'<span class="mut" style="font-size:12.5px"> n={e["n_maduros"]}</span>'
        cards.append(
            f'<article class="cartao etapa{" trava" if trava else ""}"><div class="meta-topo"><h3>{esc(e["nome"])}{amostra}</h3>{tag}</div>'
            f'<p class="plano">{esc(e["plano"])}</p><p class="rotulo">{esc(e["metrica"])}</p>{corpo}</article>'
        )
    sem_etapas = not any(p["etapa"] for p in m["posts"] if p["na_janela"])
    aviso_funil = (
        '<p class="nota"><strong>Nenhum post do período tem etapa do funil</strong>, então nada é medido por etapa. '
        "A etapa vem do post do projeto (campo etapa_funil em conteudo/&lt;lote&gt;/posts/&lt;id&gt;.json).</p>"
        if sem_etapas
        else ""
    )
    nota = (
        "Cada etapa deveria puxar acima da média da conta a métrica que ela existe para mover. "
        f"A bolinha mostra onde a etapa está em relação à média (centro = 1×). Abaixo de {fmt_dec(INDICE_ABAIXO, 2)}× com {N_AMOSTRA_MINIMA} posts ou mais vira "
        "<strong>hipótese</strong> de gargalo, não conclusão. Cliques no link, conversas no direct e vendas não são medidos pelo projeto: pergunte à pessoa no check-in."
    )
    return (
        '<section class="sec" id="funil"><h2>Funil: onde o conteúdo trava</h2>'
        '<p class="sub">Atração traz gente nova, relacionamento faz a pessoa guardar e voltar, conversão pede uma ação.</p>'
        f'{aviso_funil}<div class="etapas">{"".join(cards)}</div><p class="nota">{nota}</p></section>'
    )


def item_post(p: dict, campo: str) -> str:
    titulo = esc(p["titulo"])
    if p["permalink"].startswith(("http://", "https://")):
        titulo = f'<a href="{esc(p["permalink"])}" target="_blank" rel="noopener noreferrer">{titulo}</a>'
    chips = []
    if p["formato"]:
        chips.append(NOMES_FORMATO.get(p["formato"], p["formato"]))
    chips.append(p["pilar"] if p["pilar"] else ("do projeto, sem pilar" if p["do_projeto"] else "fora do projeto"))
    if p["etapa"]:
        chips.append(NOMES_ETAPA.get(p["etapa"], p["etapa"]))
    chips_html = " ".join(f'<span class="chip">{esc(c)}</span>' for c in chips)
    if campo == "alcance_rel":
        principal = fmt_pct(p["alcance_rel"], 0)
        aprox = " (aprox.)" if p.get("seguidores_aprox") else ""
        detalhe = f"alcance {fmt_int(p['alcance'])} · {fmt_int(p['seguidores_na_data'])} seguidores na data{aprox}"
    else:
        principal = fmt_pct(p["interacao_valor"])
        total = (p["salvamentos"] or 0) + (p["compartilhamentos"] or 0) + (p["comentarios"] or 0)
        detalhe = f"{total} (salv. {p['salvamentos']}, compart. {p['compartilhamentos']}, coment. {p['comentarios']}) em {fmt_int(p['alcance'])} de alcance"
    return (
        f'<li><span class="tit">{titulo}</span><span class="v">{esc(principal)}</span>'
        f'<span class="meta-l">{esc(fmt_data_curta(p["pub_dia"]))} · {chips_html}<br>{esc(detalhe)}</span></li>'
    )


def html_ranking(m: dict) -> str:
    por_chave = {p["chave"]: p for p in m["posts"]}
    blocos = []
    for campo, titulo, ajuda in (
        ("alcance_rel", "Quem chegou a mais gente", "Alcance ÷ seguidores na data da publicação."),
        ("interacao_valor", "Quem mais fez agir", "(Salvamentos + compartilhamentos + comentários) ÷ alcance."),
    ):
        r = m["ranking"][campo]
        if not r["disponivel"]:
            corpo = f'<p class="nota">Preciso de pelo menos {N_MIN_RANKING} posts maduros com este dado para ranquear (hoje há {r["n"]}). Com menos que isso, o melhor e o pior são acaso.</p>'
        else:
            melhores = "".join(item_post(por_chave[c], campo) for c in r["melhores"])
            piores = "".join(item_post(por_chave[c], campo) for c in r["piores"])
            corpo = f'<h4>Melhores 3</h4><ol>{melhores}</ol><h4>Piores 3</h4><ol>{piores}</ol>'
        blocos.append(f'<article class="cartao rank"><h3>{esc(titulo)}</h3><p class="sub">{esc(ajuda)}</p>{corpo}</article>')
    imaturos = [p for p in m["posts"] if p["estado"] == "imaturo" and p["na_janela"]]
    nota = ""
    if imaturos:
        nota = f'<p class="nota">{plural(len(imaturos), "post recente", "posts recentes")} ({", ".join(esc(p["titulo"]) for p in imaturos[:3])}{"…" if len(imaturos) > 3 else ""}) tem menos de {HORAS_MATURIDADE} horas na última coleta e ainda não entra no ranking.</p>'
    return (
        '<section class="sec" id="posts"><h2>Melhores e piores posts</h2>'
        '<p class="sub">Dois olhares: alcance (chegar a gente) e interação de valor (levar a pessoa a agir). O ranking compara posts da mesma conta por proporção, não por número bruto.</p>'
        f'<div class="rank-par">{"".join(blocos)}</div>{nota}</section>'
    )


def html_referencias(m: dict) -> str:
    refs = m["referencias"]
    if not refs["itens"]:
        corpo = '<p class="nota">Sem perfis em referencias/referencias.csv. Use a skill pesquisar-referencias para trazer exemplos de perfis parecidos; aqui eles viram comparação por proporção.</p>'
        return f'<section class="sec" id="referencias"><h2>Comparação com referências</h2>{corpo}</section>'
    linhas_barra = []
    todas = [(r["rotulo"], r["views_por_seguidor"], True) for r in refs["proprios"][:1]] + [(i["perfil"], i["views_por_seguidor"], False) for i in refs["itens"]]
    maximo = max([x[1] for x in todas if x[1] is not None] + [0.0001])
    for nome, val, eu in todas:
        barra = ""
        if val is not None:
            w = max(1.5, val / maximo * 100)
            barra = (
                f'<svg width="100%" height="10" viewBox="0 0 100 10" preserveAspectRatio="none" role="img" aria-label="{esc(nome)}: {esc(fmt_dec(val, 2))} visualizações por seguidor">'
                f'<rect x="0" y="0" width="{w:.1f}" height="10" rx="2" fill="{"var(--serie-1)" if eu else "var(--neutro)"}"/></svg>'
            )
        else:
            barra = '<span class="nm">não medido</span>'
        num = esc(fmt_dec(val, 2)) + "×" if val is not None else ""
        linhas_barra.append(f'<div class="lin{" eu" if eu else ""}"><span class="nome" title="{esc(nome)}">{esc(nome)}</span><span>{barra}</span><span class="num">{num}</span></div>')
    cab = ["Perfil", "Nicho", "Seguidores", "Posts por semana", "Views típicas", "Views ÷ seguidores", "% com chamada", "Alavanca", "Analisado em"]
    th = "".join(f"<th>{esc(c)}</th>" for c in cab)
    trs = []
    for p in refs["proprios"]:
        sub_v = f'<span class="sub-c">mediana de {p["n_views"]} posts</span>' if p["n_views"] else ""
        sub_c = f'<span class="sub-c">de {p["n_cta"]} posts com roteiro do projeto</span>' if p["pct_cta"] is not None else ""
        trs.append(
            f'<tr class="conta"><td data-rot="Perfil">{esc(p["rotulo"])}</td><td data-rot="Nicho">–</td>'
            f'<td data-rot="Seguidores">{h_int(p["seguidores"])}</td><td data-rot="Posts por semana">{h_dec(p["posts_semana"], 1)}</td>'
            f'<td data-rot="Views típicas">{h_int(p["mediana_views"])}{sub_v}</td><td data-rot="Views ÷ seguidores">{h_dec(p["views_por_seguidor"], 2) if p["views_por_seguidor"] is not None else v_txt(NAO_MEDIDO)}</td>'
            f'<td data-rot="% com chamada">{(esc(fmt_dec(p["pct_cta"], 0)) + "%" + sub_c) if p["pct_cta"] is not None else v_txt(NAO_MEDIDO)}</td>'
            f'<td data-rot="Alavanca">–</td><td data-rot="Analisado em">–</td></tr>'
        )
    for i in refs["itens"]:
        antiga = ' <span class="amostra">dado antigo</span>' if i["antiga"] else ""
        trs.append(
            f'<tr><td data-rot="Perfil">{esc(i["perfil"])}<span class="sub-c">{esc(i["tipo"])}</span></td><td data-rot="Nicho">{esc(i["nicho"]) or "–"}</td>'
            f'<td data-rot="Seguidores">{h_int(i["seguidores"])}</td><td data-rot="Posts por semana">{h_dec(i["posts_semana"], 1)}</td>'
            f'<td data-rot="Views típicas">{h_int(i["mediana_views"])}</td><td data-rot="Views ÷ seguidores">{h_dec(i["views_por_seguidor"], 2) if i["views_por_seguidor"] is not None else v_txt(NAO_MEDIDO)}</td>'
            f'<td data-rot="% com chamada">{(esc(fmt_dec(i["pct_cta"], 0)) + "%") if i["pct_cta"] is not None else v_txt(NAO_MEDIDO)}</td>'
            f'<td data-rot="Alavanca">{esc(i["alavanca"]) or "–"}</td><td data-rot="Analisado em">{esc(fmt_data(i["data"]))}{antiga}</td></tr>'
        )
    return (
        '<section class="sec" id="referencias"><h2>Comparação com referências</h2>'
        '<p class="sub">Perfis parecidos servem de régua, não de meta. Compare por proporção (views típicas ÷ seguidores), porque o tamanho da base muda tudo.</p>'
        '<div class="cartao"><h3>Views típicas ÷ seguidores</h3>'
        '<p class="sub">Quantas visualizações um post típico faz para cada seguidor. Você em azul, referências em cinza.</p>'
        f'<div class="barras-ref">{"".join(linhas_barra)}</div>'
        f'<div class="rolagem"><table class="tab empilhar"><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
        '<p class="nota">Visualizações públicas não provam seguidores ganhos, e perfis maiores têm outra distribuição. '
        'Use a tabela para achar o que a referência faz de diferente (coluna alavanca), não para copiar números. '
        'A mediana de views das referências vem da análise feita pela skill pesquisar-referencias; a sua vem dos posts maduros das últimas semanas.</p></div></section>'
    )


def html_dados(m: dict) -> str:
    d = m["dados"]
    linhas = []
    for f in d["fontes"]:
        if f["existe"]:
            estado = "lido" if f["linhas"] or f["id"] == "estrategia" else "vazio"
        else:
            estado = "não existe"
        linhas.append(
            [
                esc(f["arquivo"]),
                esc(estado),
                esc(str(f["linhas"])) if f["linhas"] is not None else "–",
                (esc(fmt_data(f["ultima"])) + f' <span class="mut">({esc(f["rotulo_data"])})</span>') if f["ultima"] else v_txt(NAO_MEDIDO),
                esc(fmt_dias(f["idade_dias"])) if f["idade_dias"] is not None else "–",
            ]
        )
    fontes = tabela_html(["Arquivo", "Situação", "Linhas", "Data mais recente", "Idade"], linhas)
    avisos = m["qualidade"]["avisos"]
    if avisos:
        lista = "<ul class=\"avisos\">" + "".join(f"<li>{esc(a)}</li>" for a in avisos[:40]) + "</ul>"
        if len(avisos) > 40:
            lista += f'<p class="nota">Mais {len(avisos) - 40} avisos omitidos.</p>'
    else:
        lista = '<p class="nota">Nenhum problema encontrado nos arquivos lidos.</p>'
    seg = m["seguidores"]
    bloco_extras = ""
    if seg["disponivel"]:
        itens = []
        for chave, rot in ROTULOS_EXTRAS.items():
            e = seg["extras"].get(chave)
            if e:
                itens.append(f"<dt>{esc(rot)}</dt><dd>{h_int(e['valor'])} <span class=\"mut\">(coleta de {esc(fmt_data_curta(e['dia']))})</span></dd>")
            else:
                itens.append(f"<dt>{esc(rot)}</dt><dd>{v_txt(NAO_MEDIDO)}</dd>")
        bloco_extras = (
            '<h3 class="grupo-tit">Insights da conta (colunas extras de perfil.csv)</h3>'
            '<p class="mut" style="font-size:13px">Valor da última coleta. A janela (7 ou 30 dias) é a que a coleta registrou; não somo coletas diferentes.</p>'
            f'<dl class="lista-def">{"".join(itens)}</dl>'
        )
    glossario = f"""
<dl class="glossario">
<div><dt>Visualizações</dt><dd>Quantas vezes o conteúdo foi visto. A mesma pessoa pode contar mais de uma vez.</dd></div>
<div><dt>Alcance</dt><dd>Quantas contas diferentes viram o conteúdo. É o número mais próximo de "quantas pessoas".</dd></div>
<div><dt>Seguidores ganhos</dt><dd>Quem passou a seguir no período. Só aparece se a coleta trouxer esse dado; por post, o projeto não mede.</dd></div>
<div><dt>Crescimento líquido</dt><dd>Seguidores que entraram menos os que saíram: a diferença entre dois totais. Não separa quem entrou de quem saiu.</dd></div>
<div><dt>Interação de valor</dt><dd>Salvamentos + compartilhamentos + comentários, divididos pelo alcance. Curtida fica de fora porque é o gesto mais fraco. Definição deste painel.</dd></div>
<div><dt>Post maduro</dt><dd>Post cuja última coleta foi feita pelo menos {HORAS_MATURIDADE} horas depois de publicado. Antes disso os números ainda estão subindo e distorcem a média.</dd></div>
<div><dt>Amostra pequena</dt><dd>Menos de {N_AMOSTRA_OK} posts maduros no grupo (menos de {N_AMOSTRA_MINIMA} é só uma pista). Um post fora da curva muda a média; por isso o painel avisa quando um post concentra mais de {int(LIMITE_CONCENTRACAO * 100)}% do alcance do grupo.</dd></div>
<div><dt>Proporção</dt><dd>Taxas sobre o alcance e views ÷ seguidores permitem comparar posts, formatos e perfis de tamanhos diferentes. Números brutos favorecem quem é maior ou mais antigo.</dd></div>
<div><dt>Não medido</dt><dd>O dado não veio na coleta. Nunca é tratado como zero e fica fora das médias.</dd></div>
</dl>"""
    return (
        '<section class="sec" id="dados"><h2>Dados e como ler</h2>'
        '<details class="bloco"><summary>De onde vêm os números e o que significam</summary><div>'
        f'<h3 class="grupo-tit">Arquivos lidos</h3>{fontes}{bloco_extras}'
        f'<h3 class="grupo-tit">Avisos sobre os dados</h3>{lista}'
        f'<h3 class="grupo-tit">Glossário</h3>{glossario}</div></details></section>'
    )


def html_topo(m: dict) -> str:
    marca = m["marca"]
    arroba = f'<span class="arroba">{esc(marca["arroba"])}</span>' if marca["arroba"] and marca["arroba"] != marca["nome"] else ""
    selos = []
    if marca["exemplo"]:
        selos.append('<span class="selo destaque">Marca de exemplo · dados fictícios</span>')
    est = m["estrategia"]
    selos.append(f'<span class="selo">Estratégia {esc(est["status"])} · {esc(fmt_data(date.fromisoformat(est["atualizado_em"])))}</span>')
    selos.append('<button class="selo" id="tema" type="button" aria-label="Alternar tema">Tema: automático</button>')
    leitura = m["dados"]["ultima_leitura"]
    extra = ""
    if leitura:
        extra = f' · Última leitura escrita: <a href="{esc(leitura["arquivo"])}">{esc(fmt_data(leitura["data"]))}</a>'
    return (
        '<header class="topo env"><div class="topo-linha"><div>'
        '<p class="sobre">Painel de resultados</p>'
        f'<h1>{esc(marca["nome"])}{arroba}</h1>'
        f'<p class="objetivo"><strong>Objetivo:</strong> {esc(est["objetivo"])}</p>'
        f'<p class="gerado">Gerado em {esc(m["gerado_em"])}{extra}</p></div>'
        f'<div class="selos">{"".join(selos)}</div></div></header>'
    )


def html_nav(presentes: str) -> str:
    itens = [("atencao", "Atenção"), ("resumo", "Resumo"), ("metas", "Metas"), ("evolucao", "Evolução"), ("grupos", "Desempenho"), ("funil", "Funil"), ("posts", "Posts"), ("referencias", "Referências"), ("dados", "Dados")]
    links = "".join(f'<a href="#{i}">{esc(r)}</a>' for i, r in itens if f'id="{i}"' in presentes)
    return f'<nav class="nav" aria-label="Seções do painel"><div class="env">{links}</div></nav>'


def embutir_json(modelo: dict) -> str:
    texto = json.dumps(serializar(modelo), ensure_ascii=False, separators=(",", ":"))
    return texto.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def renderizar(m: dict, versao: str) -> str:
    conteudo = [
        html_faixa_idade(m),
        html_atencao(m),
        html_resumo(m),
        html_metas(m),
        '<section class="sec" id="evolucao"><h2>Evolução</h2>'
        '<p class="sub">Seguidores ao longo das coletas e posts publicados por semana, lado a lado.</p>'
        f'<div class="duas">{html_secao_seguidores(m)}{html_secao_ritmo(m)}</div></section>',
        html_grupos(m),
        html_funil(m),
        html_ranking(m),
        html_referencias(m),
        html_dados(m),
    ]
    corpo = "".join(conteudo)
    rodape = (
        f'<footer class="rodape env">Painel gerado pela skill acompanhar-resultados (versão {esc(versao)}) em {esc(m["gerado_em"])}. '
        f'Os números vêm dos arquivos de marcas/{esc(m["marca"]["slug"])}/ e nada foi estimado ou inventado: o que falta aparece como "não medido". '
        "Para atualizar, colete as métricas e rode de novo o montar_painel.py.</footer>"
    )
    titulo = f'Painel de resultados · {m["marca"]["nome"]}'
    return (
        "<!doctype html>\n"
        '<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="color-scheme" content="light dark">\n'
        f"<title>{esc(titulo)}</title>\n"
        f"<script>{JS_CABECA}</script>\n"
        f"<style>{CSS}</style>\n</head>\n<body>\n"
        '<a class="pular" href="#principal">Pular para o conteúdo</a>\n'
        f"{html_topo(m)}\n{html_nav(corpo)}\n"
        f'<main id="principal" class="env">{corpo}</main>\n'
        f"{rodape}\n"
        '<div id="dica" role="tooltip" hidden></div>\n'
        f'<script type="application/json" id="dados-do-painel">{embutir_json(m)}</script>\n'
        f"<script>{JS}</script>\n</body>\n</html>\n"
    )
