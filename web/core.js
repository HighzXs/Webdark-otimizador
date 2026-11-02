// Base da interface: ponte com o Python, eventos, rotas, tema, avisos e janela de confirmação.
let muted = false;                           // true enquanto um evento chega pra uma tela que não está aberta
const $ = (s, el = document) => (muted && el === document ? null : el.querySelector(s));
const $$ = (s, el = document) => (muted && el === document ? [] : [...el.querySelectorAll(s)]);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => n >= 1073741824 ? (n / 1073741824).toFixed(1) + " GB" : n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : n >= 1024 ? (n / 1024).toFixed(0) + " KB" : n + " B";

// ---- eventos que o Python manda (window.__emit)
const handlers = {};
window.__emit = (event, payload) => (handlers[event] || []).slice().forEach((fn) => fn(payload));
// Cada evento pertence a uma tela. Se a resposta chega depois de você trocar de aba, o handler só guarda o estado:
// sem isso, "#list" (nome repetido nas telas) pegava a lista da tela errada e desenhava por cima.
// "current" é a tela (ou aba) aberta agora.
const OWNER = { bloat: "bloat", progs: "progs", start: "start", proc: "proc", scan: "files", dirs: "dirs", dups: "dups", dl: "dl",
  cl: "clean", clean: "home", summary: "home", health: "health", sys: "perf", perf: "perf", sec: "security", net: "net" };
let current = null, curPage = null, INTAB = false;
const on = (event, fn) => {
  const owner = OWNER[event.split(":")[0]] || (event === "summary" ? "home" : null);
  (handlers[event] = handlers[event] || []).push(!owner ? fn : (p) => {
    if (owner === current) return fn(p);
    muted = true;
    try { fn(p); } catch (e) { /* sem tela pra desenhar: o estado já foi guardado */ } finally { muted = false; }
  });
};

// ---- chamadas ao Python
const ready = new Promise((res) => {
  if (window.pywebview && window.pywebview.api) res();
  else window.addEventListener("pywebviewready", () => res());
});
const api = new Proxy({}, { get: (_, name) => async (...a) => { await ready; return window.pywebview.api[name](...a); } });
on("error", (msg) => toast("⚠ " + msg));

// ---- avisos e confirmação
function toast(text) {
  // aviso de "precisa de administrador" vira uma pergunta com o botão pra reabrir, em vez de um recado que some
  if (/precisa de administrador/i.test(text) && !(window.INFO && window.INFO.admin)) return adminPrompt(text.replace(/^⚠\s*/, ""));
  const e = $("#toast");
  e.textContent = text;
  e.classList.add("on");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => e.classList.remove("on"), 2600);
}
async function adminPrompt(text) {
  if (adminPrompt.open) return;
  adminPrompt.open = true;
  const yes = await confirmBox({ title: "Precisa de administrador", body: text + "\n\nO WebDark fecha e abre de novo como administrador. Quer fazer isso agora?", ok: "Reabrir como administrador" });
  adminPrompt.open = false;
  if (yes) document.getElementById("adminBtn").click();
}
function confirmBox({ title, body = "", ok = "Confirmar", cancel = "Cancelar", danger = false }) {
  return new Promise((resolve) => {
    const m = $("#modal");
    m.innerHTML = `<div class="dialog"><h3>${esc(title)}</h3><div class="body">${esc(body)}</div>
      <div class="btns"><button class="ghost" data-r="0">${esc(cancel)}</button><button class="btn ${danger ? "red" : ""}" data-r="1">${esc(ok)}</button></div></div>`;
    m.hidden = false;
    const done = (v) => { m.hidden = true; m.onclick = null; document.removeEventListener("keydown", key); resolve(v); };
    const key = (e) => { if (e.key === "Escape") done(false); };
    document.addEventListener("keydown", key);
    m.onclick = (e) => { const r = e.target.dataset && e.target.dataset.r; if (r !== undefined) done(r === "1"); else if (e.target === m) done(false); };
    $(".btn", m).focus();
  });
}

// caixa com várias opções grandes. Devolve o id da escolhida, ou null se cancelar.
function choiceBox({ title, body = "", options, cancel = "Cancelar" }) {
  return new Promise((resolve) => {
    const m = $("#modal");
    m.innerHTML = `<div class="dialog"><h3>${esc(title)}</h3><div class="body">${esc(body)}</div>
      <div class="choices">${options.map((o) => `<button class="choice ${o.primary ? "primary" : ""}" data-c="${esc(o.id)}"><b>${esc(o.label)}</b><small>${esc(o.hint || "")}</small></button>`).join("")}</div>
      <div class="btns"><button class="ghost" data-r="0">${esc(cancel)}</button></div></div>`;
    m.hidden = false;
    const done = (v) => { m.hidden = true; m.onclick = null; document.removeEventListener("keydown", key); resolve(v); };
    const key = (e) => { if (e.key === "Escape") done(null); };
    document.addEventListener("keydown", key);
    m.onclick = (e) => {
      const c = e.target.closest("[data-c]");
      if (c) return done(c.dataset.c);
      if ((e.target.dataset && e.target.dataset.r !== undefined) || e.target === m) done(null);
    };
  });
}

// caixa com texto editável (colar/copiar perfil). Devolve o texto, ou null se cancelar.
function inputBox({ title, body = "", value = "", readonly = false, ok = "OK" }) {
  return new Promise((resolve) => {
    const m = $("#modal");
    m.innerHTML = `<div class="dialog"><h3>${esc(title)}</h3><div class="body">${esc(body)}</div>
      <textarea id="ibox" ${readonly ? "readonly" : ""} style="width:100%;height:110px;margin-top:12px;background:#0c0c14;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:10px;font:12px Consolas,monospace;user-select:text">${esc(value)}</textarea>
      <div class="btns"><button class="ghost" data-r="0">Cancelar</button><button class="btn" data-r="1">${esc(ok)}</button></div></div>`;
    m.hidden = false;
    const t = $("#ibox"); t.focus(); if (readonly) t.select();
    m.onclick = (e) => { const r = e.target.dataset && e.target.dataset.r; if (r === undefined) return; const v = t.value; m.hidden = true; m.onclick = null; resolve(r === "1" ? v : null); };
  });
}

// ---- barra de atividade da lateral
let busyCount = 0;
function busy(delta) { busyCount = Math.max(0, busyCount + delta); document.getElementById("busy").classList.toggle("on", busyCount > 0); }

// ---- tema
const THEME_DEFAULT = { accent: "#8b5cf6", blur: true, blurpx: 22, font: "Segoe UI", glow: true };
let theme = { ...THEME_DEFAULT };
function applyTheme(t) {
  theme = { ...THEME_DEFAULT, ...t };
  const r = document.documentElement.style;
  r.setProperty("--accent", theme.accent);
  r.setProperty("--blurpx", (theme.blur ? theme.blurpx : 0) + "px");
  r.setProperty("--glass", theme.blur ? "rgba(18,18,30,.55)" : "#10101a");
  r.setProperty("--glow", theme.glow ? 1 : 0);
  r.setProperty("--font", `'${theme.font}', system-ui, sans-serif`);
}
let saveTimer;
function saveTheme() { clearTimeout(saveTimer); saveTimer = setTimeout(() => api.set_theme(theme), 300); }

// ---- páginas e rotas
const Pages = {};
const NAV = [
  ["home", "🏠", "Início"], ["space", "🧹", "Espaço e limpeza"], ["apps", "📦", "Aplicativos"], ["speed", "⚡", "Velocidade"],
  ["protect", "🩺", "Saúde e proteção"], ["help", "💡", "Ajuda"], ["settings", "🎨", "Ajustes"],
];
function go(id, tab) {
  const prev = curPage && Pages[curPage];
  if (prev && prev.unmount) prev.unmount();
  const page = Pages[id] || Pages._soon(id);
  curPage = current = id;
  $$("nav button").forEach((b) => b.classList.toggle("on", b.dataset.id === id));
  const main = $("#main");
  main.innerHTML = '<section class="page"></section>';
  const el = $(".page", main);
  if (page.mount) page.mount(el, tab);
  if (page.show && !page.tabs) page.show(el);
  if (typeof helpRefresh === "function") helpRefresh();
}

// Tela com abas: junta telas que servem pro mesmo fim. Cada aba é uma tela com mount/show/unmount próprios.
// Os textos de cabeçalho (head) viram só a legenda da aba, porque o título fica na tela-mãe.
function makeGroup(title, sub, tabs) {
  const impl = (k) => (tabs.find((t) => t[0] === k) || tabs[0])[2];
  let tab = tabs[0][0];
  function open(k) {
    const prev = impl(tab);
    if (prev.unmount && $("#tabbody")) prev.unmount();
    tab = k; current = k;
    $$("[data-tab]").forEach((b) => b.classList.toggle("on", b.dataset.tab === k));
    const body = $("#tabbody");
    body.innerHTML = "";
    const t = impl(k);
    INTAB = true;
    try { if (t.mount) t.mount(body); } finally { INTAB = false; }
    if (t.show) t.show(body);
    if (typeof helpRefresh === "function") helpRefresh();
  }
  return {
    tabs,
    mount(el, want) {
      if (want && tabs.some((t) => t[0] === want)) tab = want;
      el.innerHTML = `<div><h1>${title}</h1><div class="muted">${sub}</div></div>
        <div class="tabs">${tabs.map(([id, label]) => `<button class="chip" data-tab="${id}">${label}</button>`).join("")}</div><div id="tabbody" class="tabbody"></div>`;
      $$("[data-tab]").forEach((b) => (b.onclick = () => open(b.dataset.tab)));
      open(tab);
    },
    unmount() { const t = impl(tab); if (t.unmount) t.unmount(); },
    info(i) { const t = impl(tab); if (t.info) t.info(i); },
  };
}

async function boot() {
  $("#nav").innerHTML = NAV.map(([id, icon, label]) =>
    `<button data-id="${id}">${icon} ${label}${Pages[id] ? "" : '<span class="soon">em breve</span>'}</button>`).join("");
  $("#nav").onclick = (e) => { const b = e.target.closest("button"); if (b) go(b.dataset.id); };
  go("home");
  const info = await api.info();
  window.INFO = info;
  applyTheme(info.theme || {});
  $("#ver").textContent = "v" + info.version;
  if (!info.admin) {
    const b = $("#adminBtn");
    b.hidden = false;
    b.onclick = async () => {
      b.disabled = true;
      toast("Confirme o aviso do Windows… esta janela fecha sozinha e abre de novo como administrador.");
      const ok = await api.relaunch_admin();
      if (!ok) { b.disabled = false; toast("⚠ Você recusou o pedido do Windows. Sem administrador, parte das funções fica travada."); }
    };
  }
  if (Pages[curPage] && Pages[curPage].info) Pages[curPage].info(info);
}
