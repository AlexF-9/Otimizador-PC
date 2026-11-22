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
    for (const [chave, titulo, ic] of [["ram", "Memória RAM", "memoria"], ["disco", "Disco C:", "disco"]]) {
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
    const [du, dt, dp] = e.disco;
    this.medidor("disco", dp, `${fmt(du)} / ${fmt(dt)}`, `${fmt(dt - du)} livres`);
    if (atual === "monitor") {
      this.desenhar();
      this.lerProcessos();
    }
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
