"use strict";

/* ---------- utilitários ---------- */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const api = () => window.pywebview.api;
const reduzir = matchMedia("(prefers-reduced-motion: reduce)").matches;
const comRato = matchMedia("(hover: hover)").matches;

const num1 = new Intl.NumberFormat("pt-PT", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const num0 = new Intl.NumberFormat("pt-PT", { maximumFractionDigits: 0 });

function fmt(n) {
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return (i === 0 ? num0.format(n) : num1.format(n)) + " " + u[i];
}

const corNivel = p => (p < 60 ? "var(--verde)" : p < 85 ? "var(--amarelo)" : "var(--vermelho)");

function h(tag, props = {}, ...filhos) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) if (f != null) el.append(f);
  return el;
}

function icone(nome) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("class", "ic");
  const use = document.createElementNS(ns, "use");
  use.setAttribute("href", "#i-" + nome);
  svg.append(use);
  return svg;
}

function definirBarra(el, pct, cor, ativa = false) {
  el.style.setProperty("--pct", Math.max(0, Math.min(100, pct)));
  if (cor) el.style.setProperty("--cor", cor);
  el.classList.toggle("ativa", ativa);
}

function contar(el, para, formatar, dur = 800) {
  const de = Number(el.dataset.valor ?? 0);
  el.dataset.valor = para;
  if (reduzir || de === para) { el.textContent = formatar(para); return; }
  const t0 = performance.now();
  const passo = t => {
    const f = Math.min(1, (t - t0) / dur);
    const e = 1 - Math.pow(1 - f, 4);
    el.textContent = formatar(de + (para - de) * e);
    if (f < 1 && el.dataset.valor == para) requestAnimationFrame(passo);
  };
  requestAnimationFrame(passo);
}

function carregar(botao, sim) {
  botao.classList.toggle("a-carregar", sim);
  botao.disabled = sim;
  botao.setAttribute("aria-busy", String(sim));
}

function vazio(ic, titulo, texto) {
  return h("div", { class: "vazio" },
    h("span", { class: "vazio-icone" }, icone(ic)),
    h("strong", { text: titulo }),
    texto ? h("span", { text: texto }) : null);
}

function erroInline(texto, tentar) {
  return h("div", { class: "erro-inline", role: "alert" }, icone("aviso"), h("span", { text: texto }),
    tentar ? h("button", { class: "botao secundario pequeno", text: "Tentar de novo", onclick: tentar }) : null);
}

/* eventos enviados pelo Python durante operações longas */
const ouvintes = {};
window.receber = (ev, dados) => (ouvintes[ev] || []).forEach(f => f(dados));
const ouvir = (ev, f) => (ouvintes[ev] ||= []).push(f);

/* ---------- microinterações ---------- */

// borda dos cartões que acende por baixo do cursor
function ativarSpotlight() {
  if (!comRato || reduzir) return;
  let pendente = null;
  document.addEventListener("pointermove", e => {
    if (pendente) return;
    pendente = requestAnimationFrame(() => {
      pendente = null;
      const c = e.target.closest?.("[data-spot]");
      if (!c) return;
      const r = c.getBoundingClientRect();
      c.style.setProperty("--x", `${e.clientX - r.left}px`);
      c.style.setProperty("--y", `${e.clientY - r.top}px`);
    });
  }, { passive: true });
}

// botões principais puxam ligeiramente para o cursor
function ativarMagnetico() {
  if (!comRato || reduzir) return;
  document.addEventListener("pointermove", e => {
    for (const b of $$(".magnetico")) {
      if (b.disabled || b.offsetParent === null) continue;
      const r = b.getBoundingClientRect();
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const dx = e.clientX - cx, dy = e.clientY - cy;
      const perto = Math.abs(dx) < r.width / 2 + 40 && Math.abs(dy) < r.height / 2 + 30;
      b.style.setProperty("--mx", perto ? `${(dx * 0.12).toFixed(1)}px` : "0px");
      b.style.setProperty("--my", perto ? `${(dy * 0.22).toFixed(1)}px` : "0px");
    }
  }, { passive: true });
}

/* ---------- modal e avisos ---------- */

function dialogo({ titulo, texto = "", itens = [], nota = "", ok = "Continuar", cancelar = "Cancelar", perigo = false, icone: ic = "aviso" }) {
  return new Promise(resolver => {
    const fundo = $("#modal");
    const bOk = $("#modal-ok"), bCancelar = $("#modal-cancelar");
    const anterior = document.activeElement;
    $("#modal-titulo").textContent = titulo;
    $("#modal-texto").textContent = texto;
    $("#modal-nota").textContent = nota;
    $("#modal-itens").replaceChildren(...itens.map(i => h("li", { text: i })));
    const caixa = $("#modal-icone");
    caixa.className = "modal-icone" + (perigo ? " perigo" : "");
    caixa.replaceChildren(icone(ic));
    bOk.textContent = ok;
    bOk.className = "botao" + (perigo ? " perigo" : "");
    bCancelar.hidden = !cancelar;
    bCancelar.textContent = cancelar || "";
    fundo.hidden = false;
    fundo.classList.remove("sair");
    (perigo && cancelar ? bCancelar : bOk).focus();

    const fechar = valor => {
      document.removeEventListener("keydown", tecla, true);
      bOk.onclick = bCancelar.onclick = fundo.onclick = null;
      fundo.classList.add("sair");
      setTimeout(() => { fundo.hidden = true; anterior?.focus?.(); }, reduzir ? 0 : 200);
      resolver(valor);
    };
    const tecla = e => {
      if (e.key === "Escape") { e.preventDefault(); fechar(false); }
      if (e.key === "Tab") { // manter o foco dentro do diálogo
        const foco = [bCancelar, bOk].filter(b => !b.hidden);
        const i = foco.indexOf(document.activeElement);
        e.preventDefault();
        foco[(i + (e.shiftKey ? -1 : 1) + foco.length) % foco.length].focus();
      }
    };
    document.addEventListener("keydown", tecla, true);
    bOk.onclick = () => fechar(true);
    bCancelar.onclick = () => fechar(false);
    fundo.onclick = e => { if (e.target === fundo) fechar(false); };
  });
}

const alerta = (titulo, texto, perigo = false) =>
  dialogo({ titulo, texto, ok: "OK", cancelar: null, perigo, icone: perigo ? "aviso" : "info" });

function avisar(texto, tipo = "info") {
  const ic = { ok: "ok", aviso: "aviso", erro: "aviso", info: "info" }[tipo];
  const t = h("div", { class: "toast " + tipo, role: "status" }, icone(ic), h("span", { text: texto }));
  $("#toasts").append(t);
  setTimeout(() => {
    if (reduzir) return t.remove();
    t.classList.add("sair");
    t.addEventListener("animationend", () => t.remove(), { once: true });
  }, 4500);
}

/* ---------- navegação ---------- */

const paginas = {};
let atual = null;

function mostrar(nome) {
  if (nome === atual) return;
  atual = nome;
  $$(".pagina").forEach(p => p.classList.toggle("ativa", p.id === "pagina-" + nome));
  $$(".item").forEach(b => {
    if (b.dataset.pagina === nome) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  moverIndicador();
  $("#conteudo").scrollTop = 0;
  paginas[nome]?.mostrar?.();
}

function moverIndicador() {
  const item = $(".item[aria-current]");
  const ind = $(".indicador");
  if (!item) return;
  ind.style.height = item.offsetHeight + "px";
  ind.style.transform = `translateY(${item.offsetTop}px)`;
  ind.style.opacity = 1;
}

/* ---------- Início ---------- */

paginas.inicio = {
  seguras: [],

  iniciar() {
    $("#ini-otimizar").addEventListener("click", () => this.otimizar());
    $$("[data-ir]").forEach(b => b.addEventListener("click", () => mostrar(b.dataset.ir)));
    $("#ini-resultados").replaceChildren(vazio("limpeza", "Ainda não otimizou nesta sessão.",
      "Carregue em Otimizar agora. O resultado de cada categoria aparece aqui."));
    ouvir("otimizar", ({ i, n, nome }) => {
      definirBarra($("#ini-barra"), 100 * i / n, "var(--acento)", true);
      this.estado(`A limpar: ${nome}`);
    });
  },

  mostrar() { this.resumo(); },

  estado(texto, tipo = "") {
    const el = $("#ini-estado");
    el.textContent = texto;
    el.className = "estado " + tipo;
  },

  async resumo() {
    let r;
    try {
      r = await api().resumo();
    } catch (e) {
      $("#ini-disco").replaceChildren(erroInline("Não foi possível ler o estado do PC.", () => this.resumo()));
      return;
    }
    const usado = r.total - r.livre;
    const cor = corNivel(r.pct);
    const disco = $("#ini-disco");
    disco.style.color = cor;
    if (!disco.querySelector(".v")) disco.replaceChildren(h("span", { class: "v" }), h("small", { text: "livres" }));
    contar($(".v", disco), r.livre, fmt);
    $("#ini-disco-sub").textContent = `${num0.format(100 - r.pct)}% de ${fmt(r.total)} disponível`;
    const barra = $("#ini-disco-barra");
    definirBarra(barra, r.pct, cor);
    barra.closest(".disco").style.setProperty("--cor", cor);
    $("#ini-disco-usado").textContent = fmt(usado);
    $("#ini-disco-livre").textContent = fmt(r.livre);
    const sist = r.discos.find(d => d.sistema);
    $("#ini-disco-letra").textContent = sist ? `(${sist.letra})` : "";
    $("#ini-outros").replaceChildren(...r.discos.filter(d => !d.sistema).map(d => {
      const barra = h("div", { class: "barra" }, h("i"));
      definirBarra(barra, d.pct, corNivel(d.pct));
      return h("div", { class: "disco-mini", title: `${d.letra} ${d.nome}` },
        h("span", { class: "letra", text: d.letra }),
        h("span", { class: "nome", text: d.nome }),
        h("span", { class: "livre", text: `${fmt(d.livre)} livres` }),
        barra);
    }));

    const arr = $("#ini-arranque");
    arr.style.color = r.arranque_ativos > 10 ? "var(--amarelo)" : "";
    if (!arr.querySelector(".v")) arr.replaceChildren(h("span", { class: "v" }), h("small"));
    contar($(".v", arr), r.arranque_ativos, v => `${Math.round(v)}`);
    $("small", arr).textContent = `de ${r.arranque_total} ativos`;
    $("#ini-arranque-sub").textContent = r.arranque_ativos > 10
      ? "São muitos. Veja quais pode desligar." : "Abrem sozinhos com o Windows.";

    $("#ini-energia").textContent = r.plano;
  },

  async otimizar() {
    const sim = await dialogo({
      titulo: "Otimizar tudo",
      texto: "Vão ser apagados os ficheiros de:",
      itens: this.seguras,
      nota: "Os ficheiros em uso são ignorados.",
      ok: "Otimizar agora",
      icone: "energia",
    });
    if (!sim) return;
    const botao = $("#ini-otimizar");
    carregar(botao, true);
    $(".hero").classList.add("a-trabalhar");
    definirBarra($("#ini-barra"), 0, "var(--acento)", true);
    this.estado("A preparar…");
    let r;
    try {
      r = await api().otimizar_tudo();
    } catch (e) {
      r = { erro: String(e) };
    }
    carregar(botao, false);
    $(".hero").classList.remove("a-trabalhar");
    if (r.erro) {
      definirBarra($("#ini-barra"), 0);
      this.estado(`Ocorreu um erro: ${r.erro}`, "erro");
    } else {
      this.mostrarResultado(r.resultados);
    }
    this.resumo();
  },

  mostrarResultado(res) {
    const total = res.reduce((s, x) => s + x.bytes, 0);
    definirBarra($("#ini-barra"), 100, "var(--verde)");
    this.estado(`Concluído: ${fmt(total)} libertados.`, "ok");
    avisar(`Otimização concluída: ${fmt(total)} libertados.`, "ok");
    $("#ini-resultados").replaceChildren(...res.map((x, i) => {
      const tipo = x.ignorado ? "ignorado" : x.bytes ? "ok" : "";
      const texto = x.ignorado || `${fmt(x.bytes)}` + (x.falhas ? ` · ${x.falhas} em uso` : "");
      return h("div", { class: "resultado " + tipo, style: `--i:${i}` },
        h("span", { class: "marca-estado" }, icone(x.ignorado ? "aviso" : "ok")),
        h("span", { class: "nome", text: x.nome, title: x.nome }),
        h("span", { class: "valor", text: texto, title: texto }));
    }));
  },
};

/* ---------- Limpeza ---------- */

paginas.limpeza = {
  itens: [], tamanhos: {}, ocupado: false, linhas: {},

  async iniciar() {
    $("#lim-analisar").addEventListener("click", () => this.analisar());
    $("#lim-limpar").addEventListener("click", () => this.limpar());
    ouvir("analise", ({ i, n, nome }) => this.progresso(i, n, `A analisar: ${nome}`));
    ouvir("limpeza", ({ i, n, nome }) => this.progresso(i, n, `A limpar: ${nome}`));
    ouvir("tamanho", ({ nome, bytes }) => this.mostrarTamanho(nome, bytes));

    const r = await api().limpeza_categorias();
    this.itens = r.categorias;
    paginas.inicio.seguras = r.seguras;
    $("#lim-lista").replaceChildren(...this.itens.map((c, i) => {
      const tog = h("button", { class: "toggle", role: "switch", "aria-checked": String(c.ligado), "aria-label": c.nome });
      tog.addEventListener("click", () => {
        tog.setAttribute("aria-checked", String(tog.getAttribute("aria-checked") !== "true"));
        this.atualizarTotal();
      });
      const valor = h("span", { class: "linha-valor", text: "—" });
      this.linhas[c.nome] = { tog, valor };
      return h("div", { class: "linha entrar", style: `--i:${i}` }, tog,
        h("div", { class: "linha-texto" },
          h("div", { class: "linha-nome", text: c.nome }),
          h("div", { class: "linha-desc", text: c.desc })),
        valor);
    }));
  },

  selecionados() {
    return this.itens.map(c => c.nome).filter(n => this.linhas[n].tog.getAttribute("aria-checked") === "true");
  },

  progresso(i, n, texto) {
    definirBarra($("#lim-barra"), 100 * i / n, "var(--acento)", true);
    const el = $("#lim-estado");
    el.textContent = texto;
    el.className = "estado";
  },

  definirOcupado(sim) {
    this.ocupado = sim;
    carregar($("#lim-analisar"), sim);
    this.atualizarTotal();
  },

  atualizarTotal() {
    const sel = this.selecionados();
    const temTamanhos = Object.keys(this.tamanhos).length > 0;
    $("#lim-limpar").disabled = !(temTamanhos && sel.length && !this.ocupado);
    if (this.ocupado || !temTamanhos) return;
    const total = sel.reduce((s, n) => s + (this.tamanhos[n] || 0), 0);
    contar($("#lim-total"), total, fmt, 600);
    const el = $("#lim-estado");
    el.textContent = `podem ser libertados (${sel.length} de ${this.itens.length} categorias selecionadas)`;
    el.className = "estado";
  },

  mostrarTamanho(nome, bytes) {
    this.tamanhos[nome] = bytes;
    const v = this.linhas[nome].valor;
    v.className = "linha-valor" + (bytes === 0 ? "" : bytes >= 500 * 1024 ** 2 ? " grande" : " cheio");
    v.textContent = fmt(bytes);
  },

  async analisar() {
    if (this.ocupado) return;
    this.tamanhos = {};
    for (const { valor } of Object.values(this.linhas)) {
      valor.className = "linha-valor";
      valor.replaceChildren(h("span", { class: "esqueleto curto" }));
    }
    const total = $("#lim-total");
    total.textContent = "A analisar…";
    total.dataset.valor = 0;
    this.definirOcupado(true);
    let r;
    try {
      r = await api().limpeza_analisar();
    } catch (e) {
      r = { erro: String(e) };
    }
    definirBarra($("#lim-barra"), 100, r.erro ? "var(--vermelho)" : "var(--verde)");
    this.definirOcupado(false);
    if (r.erro) {
      const el = $("#lim-estado");
      el.textContent = `A análise falhou: ${r.erro}`;
      el.className = "estado erro";
    }
  },

  async limpar() {
    const sel = this.selecionados();
    if (this.ocupado || !sel.length) return;
    const sim = await dialogo({
      titulo: "Confirmar limpeza",
      texto: "Vão ser apagados os ficheiros de:",
      itens: sel,
      nota: "Esta ação não pode ser desfeita.",
      ok: "Limpar",
      perigo: true,
      icone: "lixo",
    });
    if (!sim) return;
    $("#lim-total").textContent = "A limpar…";
    $("#lim-total").dataset.valor = 0;
    this.definirOcupado(true);
    carregar($("#lim-limpar"), true);
    let r;
    try {
      r = await api().limpeza_limpar(sel);
    } catch (e) {
      r = { erro: String(e), libertado: 0, falhas: 0 };
    }
    carregar($("#lim-limpar"), false);
    definirBarra($("#lim-barra"), 100, "var(--verde)");
    this.definirOcupado(false);
    if (r.erro) alerta("Erro", r.erro, true);
    const extra = r.falhas ? ` ${r.falhas} ficheiros estavam em uso e foram ignorados.` : "";
    avisar(`Limpeza concluída: foram libertados ${fmt(r.libertado)}.${extra}`, "ok");
    this.analisar();
  },
};

/* ---------- Monitorização ---------- */

const HISTORICO = 60; // 60 pontos x 2 s = 2 minutos
const MARGEM_EIXO = 44; // espaço à direita para os rótulos do gráfico

paginas.monitor = {
  hist: [], medidores: {}, aLer: false, selecionado: null, procs: [],

  iniciar() {
    for (const [chave, titulo, ic] of [["ram", "Memória RAM", "memoria"]]) {
      const ns = "http://www.w3.org/2000/svg";
      const svg = document.createElementNS(ns, "svg");
      svg.setAttribute("viewBox", "0 0 76 76");
      for (const cls of ["fundo-anel", "valor-anel"]) {
        const c = document.createElementNS(ns, "circle");
        c.setAttribute("cx", 38); c.setAttribute("cy", 38); c.setAttribute("r", 32);
        c.setAttribute("class", cls);
        svg.append(c);
      }
      const numero = h("span", { class: "anel-num", text: "—" });
      const anel = h("div", { class: "anel" }, svg, numero);
      const valor = h("div", { class: "medidor-valor" }, h("span", { class: "esqueleto", style: "width:110px" }));
      const sub = h("div", { class: "medidor-sub", text: " " });
      this.medidores[chave] = { anel, numero, valor, sub };
      $(`#mon-${chave}`).replaceChildren(anel,
        h("div", { class: "medidor-texto" }, h("span", { class: "rotulo" }, icone(ic), titulo), valor, sub));
    }
    $("#mon-corpo").replaceChildren(...Array.from({ length: 8 }, () =>
      h("div", { class: "tabela-linha" }, h("span", { class: "esqueleto", style: "width:45%" }),
        h("span", { class: "esqueleto", style: "width:60%;justify-self:end" }),
        h("span", { class: "esqueleto", style: "width:50%;justify-self:end" }))));
    this.prepararGrafico();
    this.prepararTabela();
    this.tick();
    setInterval(() => this.tick(), 2000);
  },

  mostrar() {
    this.desenhar();
    this.lerProcessos();
  },

  medidor(chave, pct, valor, sub) {
    const m = this.medidores[chave];
    m.anel.style.setProperty("--pct", pct);
    m.anel.style.setProperty("--cor", corNivel(pct));
    contar(m.numero, pct, v => `${Math.round(v)}%`, 700);
    m.valor.textContent = valor;
    m.sub.textContent = sub;
  },

  async tick() {
    let e;
    try {
      e = await api().estado();
    } catch {
      return;
    }
    this.hist.push(e.cpu);
    if (this.hist.length > HISTORICO) this.hist.shift();
    const cpu = $("#mon-cpu");
    cpu.style.color = corNivel(e.cpu);
    contar(cpu, e.cpu, v => `${num1.format(v)}%`, 700);
    const [ru, rt, rp] = e.ram;
    this.medidor("ram", rp, `${fmt(ru)} / ${fmt(rt)}`, `${fmt(rt - ru)} disponíveis`);
    this.discos(e.discos);
    if (atual === "monitor") {
      this.desenhar();
      this.lerProcessos();
    }
  },

  discos(lista) {
    const caixa = $("#mon-discos-lista");
    const linhas = caixa.querySelectorAll(".disco-linha");
    if (linhas.length !== lista.length) {
      caixa.replaceChildren(...lista.map(() => h("div", { class: "disco-linha" },
        h("span", { class: "nome" }, h("b"), h("span")), h("span", { class: "pct" }),
        h("div", { class: "barra" }, h("i")))));
    }
    lista.forEach((d, i) => {
      const l = caixa.children[i];
      l.title = `${d.letra} ${d.nome}: ${fmt(d.usado)} de ${fmt(d.total)} usados, ${fmt(d.livre)} livres`;
      $("b", l).textContent = d.letra;
      $(".nome > span", l).textContent = `${d.nome} · ${fmt(d.livre)} livres`;
      const pct = $(".pct", l);
      pct.textContent = `${Math.round(d.pct)}%`;
      pct.style.color = corNivel(d.pct);
      definirBarra($(".barra", l), d.pct, corNivel(d.pct));
    });
  },

  /* gráfico */

  prepararGrafico() {
    const g = $("#mon-grafico");
    g.addEventListener("mousemove", e => this.dica(e));
    g.addEventListener("mouseleave", () => g.classList.remove("sobre"));
    new ResizeObserver(() => this.desenhar()).observe(g);
  },

  pontos() {
    const g = $("#mon-grafico");
    const w = g.clientWidth - MARGEM_EIXO, alt = g.clientHeight;
    const passo = w / (HISTORICO - 1);
    const x0 = w - passo * (this.hist.length - 1);
    return this.hist.map((v, i) => [x0 + i * passo, alt - 2 - (alt - 4) * v / 100]);
  },

  desenhar() {
    const g = $("#mon-grafico");
    const W = g.clientWidth, H = g.clientHeight;
    if (!W) return;
    const svg = $("svg", g);
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    $$(".grelha-linhas line", g).forEach((l, i) => {
      const y = [0, H / 2, H][i];
      l.setAttribute("x1", 0); l.setAttribute("x2", W - MARGEM_EIXO);
      l.setAttribute("y1", y); l.setAttribute("y2", y);
    });
    if (this.hist.length < 2) return;
    const p = this.pontos();
    // curva suave (Catmull-Rom convertida em Bézier), limitada à área do gráfico
    const lim = y => Math.max(1, Math.min(H - 1, y));
    let d = `M${p[0][0]},${p[0][1]}`;
    for (let i = 0; i < p.length - 1; i++) {
      const [a, b, c, e] = [p[i - 1] || p[i], p[i], p[i + 1], p[i + 2] || p[i + 1]];
      const c1 = [b[0] + (c[0] - a[0]) / 6, lim(b[1] + (c[1] - a[1]) / 6)];
      const c2 = [c[0] - (e[0] - b[0]) / 6, lim(c[1] - (e[1] - b[1]) / 6)];
      d += ` C${c1},${c2},${c}`;
    }
    $(".linha-g", g).setAttribute("d", d);
    $(".area", g).setAttribute("d", `${d} L${p.at(-1)[0]},${H} L${p[0][0]},${H} Z`);
    const ponto = $(".ponto", g);
    ponto.style.transform = `translate(${p.at(-1)[0]}px, ${p.at(-1)[1]}px)`;
    ponto.style.opacity = 1;
  },

  dica(e) {
    const g = $("#mon-grafico");
    const p = this.pontos();
    if (p.length < 2) return;
    const x = e.clientX - g.getBoundingClientRect().left;
    let i = 0;
    p.forEach((q, j) => { if (Math.abs(q[0] - x) < Math.abs(p[i][0] - x)) i = j; });
    const segundos = (this.hist.length - 1 - i) * 2;
    const dica = $(".dica", g);
    dica.textContent = `${num1.format(this.hist[i])}% · ${segundos ? `há ${segundos} s` : "agora"}`;
    const larg = dica.offsetWidth;
    const px = Math.max(0, Math.min(g.clientWidth - larg, p[i][0] - larg / 2));
    dica.style.transform = `translate(${px}px, -100%)`;
    const cur = $(".cursor", g);
    cur.setAttribute("x1", p[i][0]); cur.setAttribute("x2", p[i][0]);
    cur.setAttribute("y1", 0); cur.setAttribute("y2", g.clientHeight);
    g.classList.add("sobre");
  },

  /* tabela de processos */

  prepararTabela() {
    $("#mon-terminar").addEventListener("click", () => this.terminar());
    $("#mon-corpo").addEventListener("click", e => {
      const linha = e.target.closest(".tabela-linha[data-pid]");
      if (linha) this.selecionar(Number(linha.dataset.pid));
    });
    $("#mon-tabela").addEventListener("keydown", e => {
      if (!["ArrowDown", "ArrowUp", "Delete"].includes(e.key) || !this.procs.length) return;
      e.preventDefault();
      if (e.key === "Delete") return this.selecionado && this.terminar();
      const i = this.procs.findIndex(p => p.pid === this.selecionado);
      const j = i < 0 ? 0 : Math.max(0, Math.min(this.procs.length - 1, i + (e.key === "ArrowDown" ? 1 : -1)));
      this.selecionar(this.procs[j].pid);
      $(`.tabela-linha[data-pid="${this.procs[j].pid}"]`)?.scrollIntoView({ block: "nearest" });
    });
  },

  selecionar(pid) {
    this.selecionado = pid;
    $$(".tabela-linha[data-pid]").forEach(l => l.setAttribute("aria-selected", String(Number(l.dataset.pid) === pid)));
    $("#mon-terminar").disabled = pid == null;
  },

  async lerProcessos() {
    if (this.aLer) return;
    this.aLer = true;
    try {
      this.procs = await api().processos();
      this.preencher();
    } catch (e) {
      $("#mon-corpo").replaceChildren(erroInline("Não foi possível ler a lista de processos.", () => this.lerProcessos()));
    } finally {
      this.aLer = false;
    }
  },

  preencher() {
    const corpo = $("#mon-corpo");
    if (!this.procs.length) {
      corpo.replaceChildren(vazio("monitor", "Sem processos para mostrar.", "A lista volta a ser lida dentro de 2 segundos."));
      return;
    }
    const max = Math.max(1, ...this.procs.map(p => p.mem));
    const topo = corpo.scrollTop;
    corpo.replaceChildren(...this.procs.map(p => h("div", {
      class: "tabela-linha", "data-pid": p.pid, "aria-selected": String(p.pid === this.selecionado),
    },
      h("span", { class: "nome", text: p.nome, title: p.nome }),
      h("span", { class: "num pid", text: p.pid }),
      h("span", { class: "num mem" },
        h("span", { class: "mem-barra" }, h("i", { style: `--pct:${(100 * p.mem / max).toFixed(1)}` })),
        h("span", { text: fmt(p.mem) })),
    )));
    corpo.scrollTop = topo;
    if (!this.procs.some(p => p.pid === this.selecionado)) this.selecionar(null);
  },

  async terminar() {
    const p = this.procs.find(x => x.pid === this.selecionado);
    if (!p) return;
    const sim = await dialogo({
      titulo: "Terminar processo",
      texto: `Terminar '${p.nome}' (PID ${p.pid})?`,
      nota: "Qualquer trabalho não guardado nesse programa perde-se.",
      ok: "Terminar", perigo: true, icone: "parar",
    });
    if (!sim) return;
    const botao = $("#mon-terminar");
    carregar(botao, true);
    let r = await api().terminar(p.pid, false);
    if (!r.ok) {
      carregar(botao, false);
      const forcar = await dialogo({
        titulo: "Não respondeu", texto: r.msg, nota: "Forçar o encerramento?",
        ok: "Forçar", perigo: true,
      });
      if (forcar) {
        carregar(botao, true);
        r = await api().terminar(p.pid, true);
      }
    }
    carregar(botao, false);
    if (r.ok) {
      avisar(`'${p.nome}' foi terminado.`, "ok");
      this.selecionar(null);
      this.lerProcessos();
    } else {
      alerta("Não foi possível", r.msg || "O processo não pôde ser terminado.", true);
      $("#mon-terminar").disabled = this.selecionado == null;
    }
  },
};

/* ---------- Analisador de espaço ---------- */

paginas.espaco = {
  discos: [], pilha: [], res: null, ocupado: false, discoSel: null,

  iniciar() {
    $("#esp-voltar").addEventListener("click", () => this.voltar());
    $("#esp-abrir").addEventListener("click", () => this.abrir(this.res?.pasta));
    $("#esp-denovo").addEventListener("click", () => this.res && this.ir(this.res.pasta, true, false));
    $("#esp-cancelar").addEventListener("click", () => api().espaco_cancelar());
    ouvir("espaco", ({ i, n, nome, ficheiros }) => {
      definirBarra($("#esp-barra"), n ? 100 * i / n : 0, "var(--acento)", true);
      $("#esp-estado").textContent = `A ler: ${nome} · ${num0.format(ficheiros)} ficheiros`;
    });
    $("#esp-lista").replaceChildren(vazio("espaco", "Escolha um disco para começar.",
      "A primeira análise de um disco grande pode demorar alguns minutos. Depois disso, entrar nas pastas é imediato."));
  },

  async mostrar() {
    try {
      this.discos = await api().espaco_discos();
    } catch {
      $("#esp-discos").replaceChildren(erroInline("Não foi possível ler os discos.", () => this.mostrar()));
      return;
    }
    this.desenharDiscos();
  },

  desenharDiscos() {
    $("#esp-discos").replaceChildren(...this.discos.map(d => {
      const barra = h("div", { class: "barra" }, h("i"));
      definirBarra(barra, d.pct, corNivel(d.pct));
      const b = h("button", { class: "disco-botao", "aria-pressed": String(d.letra === this.discoSel), title: `${d.letra} ${d.nome}` },
        h("span", { class: "letra", text: d.letra }),
        h("span", { class: "nome", text: d.nome }),
        h("span", { class: "info", text: `${fmt(d.livre)} livres de ${fmt(d.total)}` }),
        barra);
      b.addEventListener("click", () => {
        if (this.ocupado) return;
        this.discoSel = d.letra;
        this.pilha = [];
        this.res = null;
        this.desenharDiscos();
        this.ir(d.raiz);
      });
      return b;
    }));
  },

  botoes() {
    $("#esp-voltar").disabled = this.ocupado || !this.pilha.length;
    $("#esp-abrir").disabled = this.ocupado || !this.res;
    $("#esp-denovo").disabled = this.ocupado || !this.res;
  },

  async ir(pasta, deNovo = false, empilhar = true) {
    if (this.ocupado) return;
    this.ocupado = true;
    this.botoes();
    $("#esp-progresso").hidden = false;
    definirBarra($("#esp-barra"), 0, "var(--acento)", true);
    $("#esp-estado").textContent = "A preparar…";
    let r;
    try {
      r = await api().espaco_analisar(pasta, deNovo);
    } catch (e) {
      r = { erro: String(e) };
    }
    this.ocupado = false;
    $("#esp-progresso").hidden = true;
    if (r.cancelado) {
      avisar("Análise cancelada.", "info");
    } else if (r.erro) {
      $("#esp-lista").replaceChildren(erroInline(r.erro, () => this.ir(pasta, deNovo, empilhar)));
    } else {
      if (empilhar && this.res && this.res.pasta !== r.pasta) this.pilha.push(this.res.pasta);
      this.res = r;
      this.desenhar();
    }
    this.botoes();
  },

  voltar() {
    const p = this.pilha.pop();
    if (p) this.ir(p, false, false);
  },

  async abrir(pasta) {
    if (!pasta) return;
    const r = await api().abrir_pasta(pasta);
    if (!r.ok) avisar(r.erro, "aviso");
  },

  desenhar() {
    const r = this.res;
    // migalhas: C:\ > Users > Utilizador
    const partes = r.pasta.split("\\").filter(Boolean);
    const caminhos = partes.map((_, i) => i === 0 ? partes[0] + "\\" : partes.slice(0, i + 1).join("\\"));
    const mig = [];
    partes.forEach((p, i) => {
      if (i) mig.push(icone("chevron"));
      mig.push(h("button", { text: i === 0 ? p : p, title: caminhos[i],
        onclick: () => caminhos[i] !== r.pasta && this.ir(caminhos[i]) }));
    });
    $("#esp-caminho").replaceChildren(...mig);

    const pastas = r.itens.filter(x => x.pasta).length;
    $("#esp-resumo").replaceChildren(
      h("span", {}, "Total", h("b", { text: fmt(r.total) })),
      h("span", {}, "Ficheiros", h("b", { text: num0.format(r.ficheiros) })),
      h("span", {}, "Pastas", h("b", { text: num0.format(pastas) })));

    if (!r.itens.length) {
      $("#esp-lista").replaceChildren(vazio("pasta", "Esta pasta está vazia.", "Ou não tem permissão para ver o que está dentro."));
      return;
    }
    const maior = Math.max(1, r.itens[0].bytes);
    $("#esp-lista").replaceChildren(...r.itens.slice(0, 200).map((x, i) => {
      const barra = h("div", { class: "barra" }, h("i"));
      definirBarra(barra, 100 * x.bytes / maior, x.pasta ? "var(--acento)" : "var(--suave)");
      const abrir = h("button", { class: "icone-botao", title: "Abrir no Explorador", "aria-label": `Abrir ${x.nome} no Explorador` }, icone("externo"));
      abrir.addEventListener("click", e => { e.stopPropagation(); this.abrir(x.caminho); });
      const linha = h("div", {
        class: "item-espaco" + (x.pasta ? " pasta" : ""), style: `--i:${Math.min(i, 20)}`,
        title: `${x.nome}\n${fmt(x.bytes)} · ${num0.format(x.ficheiros)} ficheiros`,
        tabindex: x.pasta ? "0" : null, role: x.pasta ? "button" : null,
      },
        icone(x.pasta ? "pasta" : "ficheiro"),
        h("span", { class: "nome", text: x.nome }),
        barra,
        h("span", { class: "tam", text: fmt(x.bytes) }),
        h("span", { class: "pct", text: r.total ? `${num1.format(100 * x.bytes / r.total)}%` : "" }),
        abrir);
      if (x.pasta) {
        linha.addEventListener("click", () => this.ir(x.caminho));
        linha.addEventListener("keydown", e => { if (e.key === "Enter") this.ir(x.caminho); });
      }
      return linha;
    }));
  },
};

/* ---------- Sistema ---------- */

function duracao(seg) {
  const d = Math.floor(seg / 86400), hh = Math.floor(seg % 86400 / 3600), m = Math.floor(seg % 3600 / 60);
  return d ? `${d} d ${hh} h` : hh ? `${hh} h ${m} min` : `${m} min`;
}

function pilula(texto, tipo = "") {
  return h("span", { class: "estado-pilula " + tipo, text: texto });
}

paginas.sistema = {
  info: null,

  iniciar() {
    $("#sis-atualizar").addEventListener("click", () => this.carregar(true));
    const esq = n => Array.from({ length: n }, () => h("span", { class: "esqueleto", style: "display:block;width:100%;height:44px;margin-top:10px;border-radius:12px" }));
    $("#sis-dicas").replaceChildren(...esq(3));
    $("#sis-hw").replaceChildren(...esq(5));
    $("#sis-ram").replaceChildren(...esq(2));
    $("#sis-ecra").replaceChildren(...esq(3));
    $("#sis-discos").replaceChildren(...esq(2));
  },

  mostrar() { this.carregar(); },

  async carregar(atualizar = false) {
    const b = $("#sis-atualizar");
    carregar(b, true);
    let r;
    try {
      r = await api().sistema_info(atualizar);
    } catch (e) {
      r = { erro: String(e) };
    }
    carregar(b, false);
    if (r.erro) {
      $("#sis-dicas").replaceChildren(erroInline(r.erro, () => this.carregar(true)));
      return;
    }
    this.info = r;
    paginas.jogos.info = r;
    this.desenhar();
  },

  desenhar() {
    const r = this.info;
    $("#sis-dicas").replaceChildren(...(r.dicas.length ? r.dicas : [{ nivel: "ok", titulo: "Está tudo bem configurado", texto: "Não encontrei nada para melhorar." }])
      .map((d, i) => h("div", { class: "dica " + d.nivel, style: `--i:${i}` },
        h("span", { class: "marca-estado" }, icone(d.nivel === "ok" ? "ok" : d.nivel === "aviso" ? "aviso" : "info")),
        h("strong", { text: d.titulo }), h("span", { text: d.texto }))));

    const ram = r.ram;
    const linhas = [
      ["Processador", `${r.cpu.nome}${r.cpu.nucleos ? ` · ${r.cpu.nucleos} núcleos / ${r.cpu.threads} threads` : ""}`],
      ...r.gpus.map((g, i) => [r.gpus.length > 1 ? `Placa gráfica ${i + 1}` : "Placa gráfica",
        g.nome + (g.vram ? ` · ${fmt(g.vram)}` : "")]),
      ["Memória", ram ? `${fmt(ram.total)} ${ram.tipo || ""}`.trim() : "—"],
      ["Placa-mãe", r.placa || "—"],
      ["Windows", `${r.so}${r.build ? ` (build ${r.build})` : ""}`],
      ["Ligado há", duracao(r.ligado_segundos)],
    ];
    $("#sis-hw").replaceChildren(...linhas.flatMap(([k, v]) => [h("dt", { text: k }), h("dd", { text: v })]));

    // RAM: velocidade atual face à anunciada
    if (!ram) {
      $("#sis-ram").replaceChildren(vazio("memoria", "Não foi possível ler a memória."));
    } else {
      const ref = ram.nominal || ram.suportada || ram.velocidade;
      const abaixo = ram.nominal && ram.nominal > ram.velocidade + 150;
      const escala = h("div", { class: "barra" }, h("i"));
      definirBarra(escala, ref ? 100 * ram.velocidade / ref : 100, abaixo ? "var(--amarelo)" : "var(--verde)");
      $("#sis-ram").replaceChildren(
        h("div", { class: "ram-velocidade" },
          h("div", { class: "metrica", style: abaixo ? "color:var(--amarelo)" : "" },
            String(ram.velocidade || "—"), h("small", { text: "MT/s" }))),
        h("p", { class: "sub", text: abaixo ? `Os módulos são de ${ram.nominal} MT/s. Está a perder velocidade.`
          : `${ram.tipo || "RAM"} · ${ram.modulos.length} ${ram.modulos.length === 1 ? "módulo" : "módulos"}` }),
        h("div", { class: "ram-escala" }, escala),
        h("div", { class: "ram-escala-legenda" }, h("span", { text: "0" }), h("span", { text: ref ? `${ref} MT/s` : "" })),
        h("div", { class: "modulos" }, ...ram.modulos.map((m, i, todos) => h("div", { class: "modulo" },
          h("b", { text: fmt(m.capacidade) }),
          h("span", { text: [m.fabricante, m.codigo].filter(Boolean).join(" ") || "Módulo" }),
          // alguns PCs reportam a mesma ranhura em todos os módulos; aí mostra-se só a ordem
          h("span", { text: new Set(todos.map(x => x.ranhura)).size === todos.length && m.ranhura ? m.ranhura : `Módulo ${i + 1}` })))));
    }

    const e = r.ecra;
    const ecra = [
      ["Resolução", e ? `${e.largura} × ${e.altura}` : "—"],
      ["Taxa de atualização", e ? (e.hz_max > e.hz + 1 ? `${e.hz} Hz (aceita ${e.hz_max} Hz)` : `${e.hz} Hz`) : "—"],
      ["Modo de Jogo", pilula(r.modo_jogo ? "Ligado" : "Desligado", r.modo_jogo ? "ok" : "aviso")],
      ["Agendamento de GPU", pilula(r.agendamento_gpu === null ? "Não suportado" : r.agendamento_gpu ? "Ligado" : "Desligado",
        r.agendamento_gpu ? "ok" : "")],
    ];
    $("#sis-ecra").replaceChildren(...ecra.flatMap(([k, v]) => [h("dt", { text: k }), h("dd", {}, v)]));

    const discos = r.discos_fisicos;
    const semDados = discos.every(d => d.temp == null && d.desgaste == null);
    $("#sis-discos").replaceChildren(
      ...(discos.length ? discos.map(d => {
        const saude = d.saude === "Healthy" ? pilula("Saudável", "ok") : pilula(d.saude || "Desconhecido", d.saude ? "aviso" : "");
        return h("div", { class: "disco-fisico" },
          h("span", { class: "tile" }, icone("disco")),
          h("span", { class: "nome", text: d.nome }),
          h("span", { class: "detalhes" },
            h("span", { class: "distintivo", text: [d.tipo !== "Unspecified" ? d.tipo : "", d.bus].filter(Boolean).join(" · ") || "Disco" }),
            h("span", { class: "mono", text: fmt(d.tamanho) })),
          h("span", { class: "lado" },
            d.temp != null ? h("span", { class: "distintivo", text: `${d.temp} °C` }) : null,
            d.desgaste != null ? h("span", { class: "distintivo", text: `Desgaste ${d.desgaste}%` }) : null,
            saude));
      }) : [vazio("disco", "Nenhum disco físico encontrado.")]),
      semDados && !window.__admin ? h("p", { class: "nota", text: "A temperatura e o desgaste dos discos só aparecem com a app aberta como administrador." }) : null);
  },
};

/* ---------- Jogos ---------- */

function segmentos(grupo, valor, aoMudar) {
  const botoes = $$("button", grupo);
  const definir = v => {
    const k = Math.max(0, botoes.findIndex(b => b.dataset.v === v));
    botoes.forEach((b, i) => { b.setAttribute("aria-checked", String(i === k)); b.tabIndex = i === k ? 0 : -1; });
    grupo.style.setProperty("--n", botoes.length);
    grupo.style.setProperty("--k", k);
  };
  botoes.forEach((b, i) => {
    b.addEventListener("click", () => { definir(b.dataset.v); aoMudar(b.dataset.v); });
    b.addEventListener("keydown", e => {
      if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
      const j = (i + (e.key === "ArrowRight" ? 1 : -1) + botoes.length) % botoes.length;
      botoes[j].focus();
      botoes[j].click();
    });
  });
  definir(valor);
  return definir;
}

paginas.jogos = {
  info: null, res: null, qual: "alta", definirRes: null,

  iniciar() {
    this.definirRes = segmentos($("#jog-res"), "1080p", v => { this.res = v; this.calcular(); });
    segmentos($("#jog-qual"), this.qual, v => { this.qual = v; this.calcular(); });
    $("#jog-lista").replaceChildren(...Array.from({ length: 6 }, () => h("div", { class: "linha" },
      h("div", { class: "linha-texto" }, h("span", { class: "esqueleto", style: "width:40%" })),
      h("span", { class: "esqueleto", style: "width:30%" }))));
    $("#jog-hw").replaceChildren(h("span", { class: "esqueleto", style: "width:80%;height:60px" }));
  },

  async mostrar() {
    if (!this.res) {
      // começa na resolução do ecrã
      if (!this.info) {
        try { this.info = await api().sistema_info(); } catch { /* usa 1080p */ }
      }
      const alt = this.info?.ecra?.altura || 1080;
      this.res = alt >= 2000 ? "4k" : alt >= 1400 ? "1440p" : "1080p";
      this.definirRes(this.res);
    }
    this.calcular();
  },

  async calcular() {
    let r;
    try {
      r = await api().jogos_estimar(this.res, this.qual);
    } catch (e) {
      r = { erro: String(e) };
    }
    if (r.erro) {
      $("#jog-lista").replaceChildren(erroInline(r.erro, () => this.calcular()));
      return;
    }
    this.desenhar(r);
  },

  desenhar(r) {
    const peca = (rotulo, ic, nome, sub, pontos, aproximado) => {
      const barra = h("div", { class: "barra" }, h("i"));
      definirBarra(barra, pontos ? Math.min(100, pontos / 2.5) : 0, "var(--acento)");
      return h("div", { class: "peca" },
        h("span", { class: "rotulo" }, icone(ic), rotulo),
        h("div", { class: "nome", text: nome || "Não detetado" }),
        h("p", { class: "sub", text: sub }),
        h("div", { class: "pontos", title: "Desempenho relativo (RTX 3060 / Ryzen 5 5600 = 100)" }, barra,
          h("span", { text: pontos ? `${aproximado ? "~" : ""}${pontos}` : "?" })));
    };
    $("#jog-hw").replaceChildren(
      peca("Placa gráfica", "jogos", r.gpu.nome, `${r.gpu.nivel}${r.gpu.vram ? ` · ${fmt(r.gpu.vram)} VRAM` : ""}`, r.gpu.pontos),
      peca("Processador", "sistema", r.cpu.nome, r.cpu.exata ? "Desempenho em jogos" : "Modelo não está na tabela: valor aproximado",
        r.cpu.pontos, !r.cpu.exata));

    if (!r.gpu.pontos) {
      $("#jog-lista").replaceChildren(vazio("jogos", "Não reconheci a placa gráfica.",
        `"${r.gpu.nome || "desconhecida"}" não está na tabela de desempenho, por isso não consigo estimar os FPS.`));
      return;
    }
    const hz = r.hz || 60;
    const escala = Math.max(hz * 1.35, ...r.jogos.map(j => j.max)) * 1.05;
    $("#jog-lista").replaceChildren(...r.jogos.map((j, i) => {
      const meio = (j.min + j.max) / 2;
      const cor = meio >= hz ? "var(--verde)" : meio >= 60 ? "var(--acento)" : meio >= 30 ? "var(--amarelo)" : "var(--vermelho)";
      const faixa = h("span", { class: "faixa" }, h("i", { style: `--pct:${(100 * meio / escala).toFixed(1)};--cor:${cor}` }));
      const marca = h("span", { class: "hz", style: `left:${(100 * hz / escala).toFixed(1)}%`, title: `Taxa do ecrã: ${hz} Hz` },
        i === 0 ? h("span", { text: `${hz} Hz` }) : null);
      const nota = j.limite && j.max >= j.limite ? `limitado a ${j.limite} FPS pelo jogo`
        : j.falta_vram ? "pouca VRAM nesta qualidade" : meio >= hz ? `acima dos ${hz} Hz` : "";
      const garg = j.gargalo === "Gráfica" ? ["Limita: gráfica", "gpu"] : j.gargalo === "Processador" ? ["Limita: processador", "cpu"] : ["Equilibrado", ""];
      return h("div", { class: "linha jogo entrar", style: `--i:${i}` },
        h("div", { class: "linha-texto" }, h("div", { class: "linha-nome", text: j.nome }), h("div", { class: "linha-desc", text: j.genero })),
        h("div", { class: "fps-barra", "aria-hidden": "true" }, faixa, marca),
        h("div", { class: "fps-valor" }, h("b", { text: j.min === j.max ? `${j.max}` : `${j.min}–${j.max}` }), " FPS",
          h("small", { class: j.falta_vram ? "vram-aviso" : "", text: nota })),
        h("span", { class: "distintivo " + garg[1], text: garg[0] }));
    }));
  },
};

/* ---------- Arranque ---------- */

paginas.arranque = {
  progs: [], carregado: false,

  iniciar() {
    $("#arr-atualizar").addEventListener("click", () => this.carregar(true));
  },

  mostrar() { this.carregar(); },

  async carregar(botao = false) {
    const b = $("#arr-atualizar");
    const lista = $("#arr-lista");
    if (botao) carregar(b, true);
    if (!this.carregado) lista.replaceChildren(...Array.from({ length: 6 }, () => this.esqueleto()));
    try {
      this.progs = await api().arranque_listar();
      this.carregado = true;
    } catch (e) {
      lista.replaceChildren(erroInline("Não foi possível ler os programas de arranque.", () => this.carregar()));
      return;
    } finally {
      if (botao) carregar(b, false);
    }
    if (!this.progs.length) {
      lista.replaceChildren(vazio("arranque", "Nenhum programa de arranque encontrado.",
        "Os programas que abrem com o Windows aparecem aqui."));
    } else {
      lista.replaceChildren(...this.progs.map((p, i) => this.linha(p, i)));
    }
    this.resumo();
  },

  esqueleto() {
    return h("div", { class: "linha" },
      h("span", { class: "esqueleto", style: "width:42px;height:24px;border-radius:12px" }),
      h("div", { class: "linha-texto" },
        h("span", { class: "esqueleto", style: "width:28%" }), h("br"),
        h("span", { class: "esqueleto", style: "width:62%;height:.75em;margin-top:6px" })));
  },

  linha(p, i) {
    const tog = h("button", { class: "toggle", role: "switch", "aria-checked": String(p.ativo), "aria-label": p.nome });
    const linha = h("div", { class: "linha entrar" + (p.ativo ? "" : " desligada"), style: `--i:${Math.min(i, 14)}` }, tog,
      h("div", { class: "linha-texto" },
        h("div", { class: "linha-nome", text: p.nome }),
        h("div", { class: "linha-desc cmd", text: p.comando, title: p.comando })),
      h("span", { class: "distintivo", text: p.origem }));
    tog.addEventListener("click", async () => {
      const novo = !p.ativo;
      tog.setAttribute("aria-checked", String(novo));
      tog.disabled = true;
      const r = await api().arranque_definir(p.id, novo);
      tog.disabled = false;
      if (r.ok) {
        p.ativo = novo;
        linha.classList.toggle("desligada", !novo);
      } else {
        tog.setAttribute("aria-checked", String(p.ativo));
        alerta(r.admin ? "Precisa de administrador" : "Erro", r.erro, !r.admin);
      }
      this.resumo();
    });
    return linha;
  },

  resumo() {
    const ativos = this.progs.filter(p => p.ativo).length;
    contar($("#arr-ativos"), ativos, v => `${Math.round(v)} ativos`, 600);
    $("#arr-sub").textContent = `de ${this.progs.length} programas que podem abrir com o Windows`;
  },
};

/* ---------- Energia ---------- */

paginas.energia = {
  iniciar() {
    $("#ene-adicionar").addEventListener("click", () => this.adicionar());
  },

  mostrar() { this.carregar(); },

  async carregar() {
    const lista = $("#ene-lista");
    let r;
    try {
      r = await api().energia_planos();
    } catch (e) {
      lista.replaceChildren(erroInline("Não foi possível ler os planos de energia.", () => this.carregar()));
      return;
    }
    if (!r.planos.length) {
      lista.replaceChildren(vazio("energia", "Nenhum plano de energia encontrado.", "O Windows não devolveu nenhum plano."));
    } else {
      lista.replaceChildren(...r.planos.map((p, i) => {
        const direita = p.ativo
          ? h("span", { class: "distintivo ativo", text: "Ativo" })
          : h("button", { class: "botao secundario pequeno", text: "Ativar" });
        if (!p.ativo) direita.addEventListener("click", () => this.ativar(p, direita));
        return h("div", { class: "linha entrar", style: `--i:${i}` },
          h("span", { class: "ponto-estado" + (p.ativo ? " ativo" : "") }),
          h("div", { class: "linha-texto" },
            h("div", { class: "linha-nome", text: p.nome }),
            h("div", { class: "linha-desc", text: p.desc })),
          direita);
      }));
    }
    $("#ene-extra").hidden = r.tem_alto;
  },

  async ativar(p, botao) {
    carregar(botao, true);
    const r = await api().energia_ativar(p.guid);
    if (!r.ok) alerta("Erro", r.msg || "Não foi possível mudar o plano.", true);
    else avisar(`Plano ativado: ${p.nome}`, "ok");
    this.carregar();
  },

  async adicionar() {
    const sim = await dialogo({
      titulo: "Adicionar plano",
      texto: "Criar o plano 'Alto desempenho' a partir do modelo do Windows?",
      ok: "Criar plano", icone: "energia",
    });
    if (!sim) return;
    const b = $("#ene-adicionar");
    carregar(b, true);
    const r = await api().energia_adicionar_alto();
    carregar(b, false);
    if (!r.ok) alerta("Erro", r.msg, true);
    this.carregar();
  },
};

/* ---------- arranque da app ---------- */

async function iniciar() {
  $$(".item").forEach(b => b.addEventListener("click", () => mostrar(b.dataset.pagina)));
  addEventListener("resize", moverIndicador);
  ativarSpotlight();
  ativarMagnetico();

  const info = await api().info();
  window.__admin = info.admin;
  const admin = $("#admin");
  admin.textContent = info.admin ? "Administrador" : "Sem administrador";
  admin.className = "admin " + (info.admin ? "sim" : "nao");
  admin.title = info.admin ? "A correr como administrador" : "Algumas pastas e programas do Windows não vão poder ser alterados.";
  $("#admin-nota").hidden = info.admin;
  $("#versao").textContent = `v${info.versao}`;

  for (const p of Object.values(paginas)) await p.iniciar?.();
  mostrar("inicio");
}

if (window.pywebview?.api) iniciar();
else addEventListener("pywebviewready", iniciar, { once: true });
