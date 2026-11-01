// Base da interface: ponte com o Python, eventos, rotas, tema, avisos e janela de confirmação.
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => n >= 1073741824 ? (n / 1073741824).toFixed(1) + " GB" : n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : n >= 1024 ? (n / 1024).toFixed(0) + " KB" : n + " B";

// ---- eventos que o Python manda (window.__emit)
const handlers = {};
window.__emit = (event, payload) => (handlers[event] || []).slice().forEach((fn) => fn(payload));
const on = (event, fn) => (handlers[event] = handlers[event] || []).push(fn);

// ---- chamadas ao Python
const ready = new Promise((res) => {
  if (window.pywebview && window.pywebview.api) res();
  else window.addEventListener("pywebviewready", () => res());
});
const api = new Proxy({}, { get: (_, name) => async (...a) => { await ready; return window.pywebview.api[name](...a); } });
on("error", (msg) => toast("⚠ " + msg));

// ---- avisos e confirmação
function toast(text) {
  const e = $("#toast");
  e.textContent = text;
  e.classList.add("on");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => e.classList.remove("on"), 2600);
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
function busy(delta) { busyCount = Math.max(0, busyCount + delta); $("#busy").classList.toggle("on", busyCount > 0); }

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
  ["home", "🏠", "Início"], ["bloat", "🧨", "Bloatware"], ["clean", "🧹", "Limpeza"], ["space", "📊", "Espaço"],
  ["progs", "📦", "Programas"], ["start", "🚀", "Inicialização"], ["health", "🩺", "Saúde"], ["perf", "⚡", "Desempenho"],
  ["proc", "🧠", "Processos"], ["security", "🛡", "Segurança"], ["settings", "🎨", "Ajustes"],
];
let current = null;
function go(id) {
  const prev = current && Pages[current];
  if (prev && prev.unmount) prev.unmount();
  const page = Pages[id] || Pages._soon(id);
  current = id;
  $$("nav button").forEach((b) => b.classList.toggle("on", b.dataset.id === id));
  const main = $("#main");
  main.innerHTML = '<section class="page"></section>';
  const el = $(".page", main);
  if (page.mount) page.mount(el);
  if (page.show) page.show(el);
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
    b.onclick = () => api.relaunch_admin();
  }
  if (Pages[current] && Pages[current].info) Pages[current].info(info);
}
