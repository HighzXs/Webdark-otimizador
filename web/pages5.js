// Telas: Segurança (temperatura + curva editável), modo segundo plano nos Ajustes e aviso de atualização no Início.

// ================================================================ SEGURANÇA
Pages.security = (() => {
  const S = { cfg: null, tick: null, events: null, procs: null, drag: null, timers: [], tip: "" };
  const STATE = { ok: ["Tudo tranquilo", "#4ade80"], warn: ["Esquentando — fique de olho", "#fbbf24"], hot: ["QUENTE! Reduzindo o clock pra esfriar", "#f87171"],
    crit: ["PERIGO! Clock no mínimo de segurança", "#fca5a5"], nosensor: ["Sem leitura de temperatura", "#8d8da8"] };
  const OVL = { hot: "Só quando esquentar", always: "Sempre", never: "Nunca" };
  const KIND = { ok: "✔", warn: "⚠", hot: "🔥", crit: "🚨", clock: "⏬", info: "•" };
  const TIPS = "• Notebook: use em superfície dura e plana, nunca em cama ou sofá.\n• Limpe a poeira das saídas de ar a cada 6 meses.\n• Limite o FPS do jogo (ex.: 60). Menos FPS = menos calor.\n• Plano de energia Equilibrado + clock máximo em 90% já tira vários graus (aba Desempenho).\n• Fechar navegador e apps pesados enquanto joga ajuda bastante.";
  const T_MIN = 50, T_MAX = 105, P_MIN = 20, P_MAX = 100, PL = 50, PR = 20, PT = 22, PB = 34, HIT = 13, MAXP = 8;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const tcolor = (t) => t == null ? "#8d8da8" : t >= S.cfg.limit ? "#f87171" : t >= S.cfg.warn ? "#fbbf24" : "#4ade80";

  // ---------- gráfico da curva (arraste os pontos; duplo clique cria; botão direito apaga)
  const cv = () => $("#curve");
  const geo = () => { const c = cv(); return { w: c.clientWidth, h: c.clientHeight }; };
  const X = (t) => PL + (t - T_MIN) / (T_MAX - T_MIN) * (geo().w - PL - PR);
  const Y = (p) => PT + (P_MAX - p) / (P_MAX - P_MIN) * (geo().h - PT - PB);
  const toT = (x) => T_MIN + (x - PL) / (geo().w - PL - PR) * (T_MAX - T_MIN);
  const toP = (y) => P_MAX - (y - PT) / (geo().h - PT - PB) * (P_MAX - P_MIN);
  const hit = (x, y) => S.cfg.curve.findIndex(([t, p]) => (x - X(t)) ** 2 + (y - Y(p)) ** 2 <= HIT ** 2);

  function drawCurve() {
    const c = cv();
    if (!c || !S.cfg) return;
    const dpr = window.devicePixelRatio || 1, { w, h } = geo();
    c.width = w * dpr; c.height = h * dpr;
    const g = c.getContext("2d"); g.scale(dpr, dpr);
    const top = PT, bot = h - PB, warn = S.cfg.warn, limit = S.cfg.limit;
    g.fillStyle = "rgba(34,197,94,.14)"; g.fillRect(X(T_MIN), top, X(warn) - X(T_MIN), bot - top);
    g.fillStyle = "rgba(234,179,8,.17)"; g.fillRect(X(warn), top, X(limit) - X(warn), bot - top);
    g.fillStyle = "rgba(239,68,68,.2)"; g.fillRect(X(limit), top, X(T_MAX) - X(limit), bot - top);
    g.font = "bold 10px Segoe UI"; g.fillStyle = "#9a9ab5"; g.textAlign = "center";
    [["LIVRE", T_MIN, warn], ["AVISO", warn, limit], ["LIMITANDO", limit, T_MAX]].forEach(([n, a, b]) => { if (X(b) - X(a) > 50) g.fillText(n, (X(a) + X(b)) / 2, top - 8); });
    g.font = "10px Segoe UI"; g.strokeStyle = "rgba(255,255,255,.1)"; g.lineWidth = 1;
    for (let t = 60; t < T_MAX; t += 10) { g.beginPath(); g.moveTo(X(t), top); g.lineTo(X(t), bot); g.stroke(); g.fillText(t + "°C", X(t), bot + 14); }
    g.textAlign = "right";
    [20, 40, 60, 80, 100].forEach((p) => { g.beginPath(); g.moveTo(X(T_MIN), Y(p)); g.lineTo(X(T_MAX), Y(p)); g.stroke(); g.fillText(p + "%", PL - 6, Y(p) + 3); });
    const pts = [...S.cfg.curve].sort((a, b) => a[0] - b[0]);
    g.strokeStyle = "#4fd1e6"; g.lineWidth = 3; g.lineJoin = "round"; g.beginPath();
    g.moveTo(X(T_MIN), Y(pts[0][1])); pts.forEach(([t, p]) => g.lineTo(X(t), Y(p))); g.lineTo(X(T_MAX), Y(pts[pts.length - 1][1])); g.stroke();
    const tk = S.tick;
    if (tk && tk.cpu != null) {
      const xt = X(clamp(tk.cpu, T_MIN, T_MAX)), cap = tk.cur_max || 100;
      g.setLineDash([4, 3]); g.strokeStyle = "#e5e7eb"; g.lineWidth = 1; g.beginPath(); g.moveTo(xt, top); g.lineTo(xt, bot); g.stroke(); g.setLineDash([]);
      g.fillStyle = "#22c55e"; g.beginPath(); g.arc(xt, Y(cap), 5, 0, 7); g.fill();
      g.fillStyle = "#e5e7eb"; g.font = "bold 11px Segoe UI"; g.textAlign = "right"; g.fillText(`agora: ${Math.round(tk.cpu)}°C  •  clock ${cap}%`, w - PR, top + 12);
    }
    S.cfg.curve.forEach(([t, p], i) => { g.fillStyle = i === S.drag ? "#fff" : "#facc15"; g.strokeStyle = "#1f2937"; g.lineWidth = 2; g.beginPath(); g.arc(X(t), Y(p), 7, 0, 7); g.fill(); g.stroke(); });
    if (S.tip) { g.fillStyle = "#e5e7eb"; g.font = "bold 12px Segoe UI"; g.textAlign = "left"; g.fillText(S.tip, PL + 8, bot - 10); }
  }
  function curveEvents() {
    const c = cv(), pos = (e) => { const r = c.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    const commit = async () => { const r = await api.sec_save({ curve: S.cfg.curve }); S.cfg = { ...S.cfg, ...r }; info(); drawCurve(); if (!r.ok) toast("⚠ Curva inválida: voltei à anterior."); };
    c.onmousedown = (e) => { const [x, y] = pos(e); const i = hit(x, y); S.drag = i >= 0 ? i : null; if (S.drag !== null) c.onmousemove(e); };
    c.onmousemove = (e) => {
      const [x, y] = pos(e), pts = S.cfg.curve, i = S.drag;
      if (i === null) { c.style.cursor = hit(x, y) >= 0 ? "grab" : "default"; return; }
      const t = Math.round(toT(x)), p = Math.round(toP(y) / 5) * 5;
      const loT = i > 0 ? pts[i - 1][0] + 1 : T_MIN, hiT = i < pts.length - 1 ? pts[i + 1][0] - 1 : T_MAX;
      const loP = i < pts.length - 1 ? Math.max(P_MIN, pts[i + 1][1]) : P_MIN, hiP = i > 0 ? Math.min(P_MAX, pts[i - 1][1]) : P_MAX;
      pts[i] = [clamp(t, loT, hiT), clamp(p, loP, hiP)];
      S.tip = `${pts[i][0]}°C  →  clock máximo ${pts[i][1]}%`; drawCurve();
    };
    window.addEventListener("mouseup", () => { if (S.drag !== null) { S.drag = null; S.tip = ""; drawCurve(); commit(); } });
    c.ondblclick = (e) => {
      const [x, y] = pos(e), pts = S.cfg.curve;
      if (hit(x, y) >= 0 || pts.length >= MAXP) return;
      const t = clamp(Math.round(toT(x)), T_MIN + 1, T_MAX - 1);
      if (pts.some((q) => q[0] === t)) return;
      const idx = pts.filter((q) => q[0] < t).length, hi = idx > 0 ? pts[idx - 1][1] : P_MAX, lo = idx < pts.length ? pts[idx][1] : P_MIN;
      pts.splice(idx, 0, [t, clamp(Math.round(toP(y) / 5) * 5, lo, hi)]); drawCurve(); commit();
    };
    c.oncontextmenu = (e) => { e.preventDefault(); const [x, y] = pos(e), i = hit(x, y); if (i >= 0 && S.cfg.curve.length > 2) { S.cfg.curve.splice(i, 1); drawCurve(); commit(); } };
  }

  // ---------- histórico de temperatura
  function drawHist() {
    const c = $("#hist");
    if (!c || !S.tick) return;
    const dpr = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
    c.width = w * dpr; c.height = h * dpr;
    const g = c.getContext("2d"); g.scale(dpr, dpr);
    const lo = 30, hi = 105, y = (t) => h - 14 - (clamp(t, lo, hi) - lo) / (hi - lo) * (h - 24);
    [[S.cfg.warn, "#fbbf24"], [S.cfg.limit, "#f87171"]].forEach(([t, col]) => { g.setLineDash([4, 3]); g.strokeStyle = col; g.beginPath(); g.moveTo(0, y(t)); g.lineTo(w, y(t)); g.stroke(); g.setLineDash([]);
      g.fillStyle = col; g.font = "10px Segoe UI"; g.textAlign = "right"; g.fillText(t + "°C", w - 4, y(t) - 4); });
    const hist = S.tick.history || [];
    if (hist.length < 2) { g.fillStyle = "#8d8da8"; g.textAlign = "center"; g.fillText("Coletando dados…", w / 2, h / 2); return; }
    const step = (w - 10) / 149, x0 = w - 5 - (hist.length - 1) * step;
    [[0, "#4fd1e6", 2], [1, "#a78bfa", 1.5]].forEach(([idx, col, lw]) => { g.strokeStyle = col; g.lineWidth = lw; g.beginPath(); let open = false;
      hist.forEach((s, i) => { if (s[idx] == null) return; const px = x0 + i * step; open ? g.lineTo(px, y(s[idx])) : (g.moveTo(px, y(s[idx])), open = true); }); g.stroke(); });
  }

  function info() {
    const c = S.cfg;
    if (!c || !$("#sw-on")) return;
    $("#sw-on").classList.toggle("on", c.enabled); $("#sw-snd").classList.toggle("on", c.sound);
    $("#ovl").value = c.overlay; $("#warn").value = c.warn;
    $("#warnl").textContent = `Avisar (amarelo e apito) a partir de ${c.warn}°C`;
    $("#pc").textContent = `Seu PC: ${c.cpu_name || "seu PC"}  •  limite estimado do chip: ${c.tj}°C (a curva inicial é calculada pra cada PC)`;
    $("#curvel").textContent = `Clock livre até ${c.limit}°C.   ${[...c.curve].sort((a, b) => a[0] - b[0]).map(([t, p]) => `${t}°C → ${p}%`).join("   •   ")}.   Perigo a partir de ${c.crit}°C.`;
  }
  function live() {
    const tk = S.tick;
    if (!tk || !$("#cpuBig")) return;
    $("#cpuBig").textContent = tk.cpu != null ? `CPU ${Math.round(tk.cpu)}°C` : "CPU —"; $("#cpuBig").style.color = tcolor(tk.cpu);
    $("#gpuBig").textContent = tk.gpu != null ? `GPU ${Math.round(tk.gpu)}°C` : "GPU —"; $("#gpuBig").style.color = tcolor(tk.gpu);
    $("#clk").textContent = tk.mhz != null && tk.util != null ? `Clock ${(tk.mhz / 1000).toFixed(2)} GHz • Uso ${Math.round(tk.util)}%` : "";
    const [txt, col] = STATE[tk.state] || STATE.nosensor;
    $("#stt").textContent = txt + (tk.throttled && tk.cur_max ? `  (clock em ${tk.cur_max}%)` : "") + (tk.enabled ? "" : "  — proteção DESLIGADA"); $("#stt").style.color = col;
    drawHist(); drawCurve();
  }
  function paintExtra() {
    if (!$("#evl")) return;
    const ev = S.events;
    $("#evl").textContent = ev && ev.events.length ? ev.events.map(([t, k, x]) => `${t.slice(5, 16)}  ${KIND[k] || "•"} ${x}`).join("\n") : "Nada ainda. Quando o PC esquentar, aparece aqui.";
    $("#evtip").textContent = ev && ev.hot7 >= 3 ? `⚠ O PC passou do limite ${ev.hot7} vezes nos últimos 7 dias. Limpe a poeira dos coolers, use o notebook em superfície dura e, se for antigo, troque a pasta térmica.` : "";
    $("#prc").textContent = S.procs ? (S.procs.map((p) => `${p.name.slice(0, 34).padEnd(36)}${p.cpu.toFixed(1).padStart(5)}% da CPU`).join("\n") || "Nada pesado agora. 👍") : "Lendo…";
  }
  const patch = async (p) => { const r = await api.sec_save(p); S.cfg = { ...S.cfg, ...r }; info(); drawCurve(); };
  on("sec:tick", (t) => { S.tick = t; live(); });
  on("sec:cfg", (c) => { S.cfg = { ...S.cfg, ...c }; info(); drawCurve(); toast("✨ Curva montada pro seu PC"); });

  return {
    async mount(el) {
      S.cfg = await api.sec_state();
      el.innerHTML = head("Segurança", "Vigia a temperatura do PC. Se chegar perto do perigo, avisa num cantinho da tela e baixa o clock sozinho até esfriar. Tudo começa desligado.") + `<div class="scroll">
        <h2>🌡 Temperatura agora</h2><div class="card" style="padding:14px 18px">
          <div style="display:flex;align-items:baseline;gap:30px"><span style="font-size:34px;font-weight:800" id="cpuBig">CPU —</span><span style="font-size:34px;font-weight:800" id="gpuBig">GPU —</span><span style="flex:1"></span><span class="muted" id="clk"></span></div>
          <div style="font-weight:700;margin:2px 0 8px" id="stt"></div><canvas id="hist" style="width:100%;height:150px"></canvas></div>
        <h2>🛡 Proteção térmica</h2><div class="card" style="padding:16px 18px;display:flex;flex-direction:column;gap:14px">
          <div class="set" style="padding:0"><div class="sw" id="sw-on"></div><div class="t"><b>Ligada: segue a curva abaixo e baixa o clock sozinha</b><div class="muted" id="pc"></div></div></div>
          <div class="tools"><button class="ghost" data-m="gamer">🎮 Gamer</button><button class="ghost" data-m="careful">🛡 Cuidadoso</button><button class="ghost" data-m="very">🧯 Bem cuidadoso</button><button class="ghost" id="sug">✨ Sugerir pro meu PC</button></div>
          <canvas id="curve" style="width:100%;height:300px;touch-action:none"></canvas>
          <div class="muted" id="curvel"></div>
          <div class="muted">Como usar: arraste os pontos amarelos. Duplo clique cria um ponto, botão direito apaga. Cada ponto diz: “se a CPU chegar nessa temperatura, o clock máximo vai para essa %”. Abaixo do primeiro ponto o clock fica livre; esfriou, ele volta sozinho.</div>
          <div class="set" style="padding:0"><span id="warnl" style="width:330px"></span><input type="range" id="warn" min="50" max="95" style="flex:1;width:auto"></div>
          <div class="set" style="padding:0"><span>Cantinho de aviso:</span><select id="ovl">${Object.entries(OVL).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select>
            <div class="sw" id="sw-snd"></div><span>Apitar ao esquentar</span></div>
          <div class="tools"><button class="ghost" id="exp">📋 Copiar meu perfil</button><button class="ghost" id="imp">📥 Colar perfil de um amigo</button></div>
          <div class="muted">O cantinho aparece por cima de jogos em janela ou tela cheia sem bordas. Em tela cheia exclusiva (alguns jogos) o Windows esconde — nesse caso o PC apita.</div></div>
        <h2>📜 O que aconteceu</h2><div class="muted" style="color:#fbbf24" id="evtip"></div><div class="logbox" id="evl" style="max-height:140px"></div>
        <h2>🔎 Quem está pesando agora</h2><div class="logbox" id="prc" style="max-height:none"></div>
        <h2>💡 Como esfriar o PC</h2><div class="muted" style="white-space:pre-line">${esc(TIPS)}</div></div>`;
      info(); drawCurve(); curveEvents(); paintExtra();
      $("#sw-on").onclick = () => patch({ enabled: !S.cfg.enabled });
      $("#sw-snd").onclick = () => patch({ sound: !S.cfg.sound });
      $("#ovl").onchange = (e) => patch({ overlay: e.target.value });
      $("#warn").oninput = (e) => { S.cfg.warn = +e.target.value; info(); drawCurve(); clearTimeout(S.wt); S.wt = setTimeout(() => patch({ warn: S.cfg.warn }), 300); };
      $$("[data-m]").forEach((b) => (b.onclick = async () => { S.cfg = { ...S.cfg, ...(await api.sec_preset(b.dataset.m)) }; info(); drawCurve(); }));
      $("#sug").onclick = () => { busy(1); api.sec_suggest(); setTimeout(() => busy(-1), 4000); };
      $("#exp").onclick = async () => {
        const text = JSON.stringify({ v: 1, warn: S.cfg.warn, curve: S.cfg.curve });
        try { await navigator.clipboard.writeText(text); toast("📋 Perfil copiado! Cole numa mensagem pro seu amigo."); }
        catch { await inputBox({ title: "Seu perfil", body: "Copie o texto abaixo (Ctrl+C) e mande pro seu amigo. Cada PC esquenta de um jeito: peça pra ele ajustar a curva no PC dele.", value: text, readonly: true, ok: "Fechar" }); }
      };
      $("#imp").onclick = async () => {
        const text = await inputBox({ title: "Colar perfil", body: "Cole aqui o perfil que seu amigo mandou:", ok: "Aplicar" });
        if (!text) return;
        const r = await api.sec_import(text);
        if (!r.ok) return toast("Esse perfil não parece válido.");
        S.cfg = { ...S.cfg, ...r }; info(); drawCurve(); toast("✅ Perfil aplicado");
      };
      window.onresize = () => { drawCurve(); drawHist(); };
    },
    show() {
      api.sec_open(true);
      const pull = async () => { S.events = await api.sec_events(); paintExtra(); };
      const pullP = async () => { S.procs = await api.sec_procs(); paintExtra(); };
      pull(); pullP();
      S.timers = [setInterval(pull, 10000), setInterval(pullP, 6000)];
    },
    unmount() { api.sec_open(false); S.timers.forEach(clearInterval); window.onresize = null; },
  };
})();

on("confirm_close", async () => {
  if (await confirmBox({ title: "Fechar mesmo?", body: "O PC ainda está quente e estou limitando o clock.\nSe fechar, o clock volta ao normal e ele pode esquentar de novo.", ok: "Fechar", danger: true })) api.quit();
});

// ============================================== AJUSTES: modo segundo plano
(() => {
  const orig = Pages.settings.mount;
  Pages.settings.mount = async function (el) {
    orig.call(this, el);
    const bg = await api.bg_get();
    const box = document.createElement("div");
    box.innerHTML = `<h2>🌙 Modo segundo plano</h2><div class="card" style="padding:16px 18px;display:flex;flex-direction:column;gap:14px">
      <div class="set" style="padding:0"><div class="t"><b>Fechar na bandeja e vigiar em silêncio</b><div class="muted">Ao fechar a janela, o programa vai pra bandeja (perto do relógio). De tempos em tempos confere o PC com prioridade mínima e só avisa se achar algo importante. O vigia de temperatura continua funcionando. Para sair de vez: botão direito no ícone > “Sair de vez”.</div></div><div class="sw ${bg.on ? "on" : ""}" id="s-bg"></div></div>
      <div class="set" style="padding:0"><div class="t"><b>Conferir a cada</b></div><select id="bgmin">${[[30, "30 min"], [60, "1 hora"], [180, "3 horas"]].map(([v, t]) => `<option value="${v}" ${v === bg.minutes ? "selected" : ""}>${t}</option>`).join("")}</select></div></div>`;
    $(".scroll", el).appendChild(box);
    const save = async () => {
      const on = $("#s-bg").classList.contains("on"), r = await api.bg_set(on, +$("#bgmin").value);
      if (!r.ok) { $("#s-bg").classList.remove("on"); toast("😕 Não consegui criar o ícone da bandeja."); }
    };
    $("#s-bg").onclick = () => { $("#s-bg").classList.toggle("on"); save(); };
    $("#bgmin").onchange = save;
  };
})();

// =============================================== INÍCIO: aviso de atualização
let UPDATE = null;
function updBanner() {
  const page = $(".page");
  if (!page || current !== "home") return;
  let b = $("#updbar");
  if (!UPDATE) { if (b) b.remove(); return; }
  if (!b) { b = document.createElement("div"); b.id = "updbar"; b.className = "card"; b.style.cssText = "padding:12px 18px;display:flex;gap:14px;align-items:center;border-color:var(--accent)"; page.insertBefore(b, page.children[1]); }
  b.innerHTML = `<b style="flex:1">🆕 Versão ${esc(UPDATE.version)} disponível (você está na ${esc((window.INFO || {}).version || "")})</b>
    <span class="muted" id="updtxt"></span><button class="ghost" id="updlater">Depois</button><button class="btn" id="updgo">${UPDATE.can_self ? "⬇ Atualizar agora" : "⬇ Abrir página de download"}</button>`;
  $("#updlater").onclick = () => { UPDATE = null; updBanner(); };
  $("#updgo").onclick = async () => {
    if (UPDATE.can_self && !await confirmBox({ title: `Atualizar para a versão ${UPDATE.version}?`, body: `Vou baixar ${fmt(UPDATE.size)} e reiniciar o programa.\n\n${UPDATE.notes}`, ok: "Atualizar" })) return;
    $("#updgo").disabled = true; busy(1); api.update_apply();
  };
}
on("update:available", (d) => { UPDATE = d; updBanner(); });
on("update:progress", (d) => { const t = $("#updtxt"); if (t) t.textContent = d.restart ? "Reiniciando…" : `Baixando… ${Math.round(d.frac * 100)}%`; });
(() => { const orig = Pages.home.mount; Pages.home.mount = function (el) { orig.call(this, el); updBanner(); }; })();
