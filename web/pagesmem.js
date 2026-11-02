// Tela Memória (aba de Velocidade): RAM agora e lista de espera, programas em segundo plano (liberar, baixar prioridade, congelar),
// arquivo de paginação, agrupamento de serviços (SvcHost) e SysMain.
Pages.mem = (() => {
  const S = { ram: null, groups: [], svc: null, deep: null, auto: null, svcs: null, loading: false, freezeMin: 30, timer: null };
  const alive = () => current === "mem";
  const isAdmin = () => !!(window.INFO && window.INFO.admin);
  const ok = (r) => { if (r && r.ok === false) { toast("⚠ " + r.msg); return false; } return true; };
  const adminTag = () => (isAdmin() ? "" : ' <span class="tag q">PRECISA DE ADMIN</span>');
  const card = (id, title, sub, body = "") => `<h2>${title}${sub ? ` <span class="muted" style="font-weight:400">${sub}</span>` : ""}</h2><div class="card" id="${id}" style="padding:14px 18px">${body}</div>`;
  const mb = (n) => (n >= 1024 ? (n / 1024).toFixed(n % 1024 ? 1 : 0) + " GB" : n + " MB");
  const mins = (s) => Math.max(1, Math.ceil(s / 60)) + " min";
  const TRIM_WARN = "Isso tira da RAM o que o programa não está usando agora. O Chrome (e os outros navegadores) podem ficar lentos, recarregar abas ou, em casos raros, travar uma aba na próxima vez que você usar. Salve o que estiver fazendo antes.";
  const act = async (fn) => { busy(1); try { return await fn(); } finally { busy(-1); } };

  // --------------------------------------------------------------------- RAM agora
  function paintRam() {
    const box = $("#m-ram");
    if (!box) return;
    const r = S.ram;
    if (!r) { box.innerHTML = '<div class="muted">Lendo a memória…</div>'; return; }
    const col = r.percent >= 90 ? "#f87171" : r.percent >= 75 ? "#fbbf24" : "#4ade80";
    box.innerHTML = `<b>${fmt(r.total - r.avail)} em uso de ${fmt(r.total)}</b> <span class="muted">• ${fmt(r.avail)} disponíveis • ${r.percent}%</span>
      <div class="meter" style="margin:8px 0"><i style="width:${r.percent}%;background:${col}"></i></div>
      <div class="muted">Lista de espera (standby): ${r.standby == null ? "precisa de administrador para ler" : fmt(r.standby)}. É cache de arquivos que o Windows guarda na RAM e devolve sozinho quando um programa precisa. Esvaziar não deixa o PC mais rápido na maioria dos casos: faz o Windows reler os arquivos do disco. Só vale a pena se a RAM “disponível” estiver sempre baixa.</div>
      <div class="tools" style="margin-top:10px"><button class="btn" id="m-sb-soft">🧹 Limpar a lista de espera (suave)${adminTag()}</button>
        <button class="ghost" id="m-sb-full">Limpeza completa${adminTag()}</button></div>
      <div class="muted" style="margin-top:6px">Suave: só solta o cache de prioridade baixa, não atrapalha jogo aberto. Completa: esvazia tudo e pode causar engasgos por alguns segundos.</div>`;
    const run = (full) => async () => {
      if (full && !await confirmBox({ title: "Esvaziar toda a lista de espera?", body: "O Windows vai reler do disco o que precisar de novo. Se tiver um jogo aberto, pode engasgar por alguns segundos. Prefira a limpeza suave.", ok: "Esvaziar" })) return;
      const res = await act(() => api.mem_standby(full));
      if (ok(res)) { toast("✅ " + res.msg); if (res.ram) S.ram = res.ram; paintRam(); }
    };
    $("#m-sb-soft").onclick = run(false);
    $("#m-sb-full").onclick = run(true);
  }

  // ------------------------------------------------------------- programas em segundo plano
  function paintApps() {
    const box = $("#m-apps");
    if (!box) return;
    const g = S.groups;
    const anyFrozen = g.some((x) => x.frozen);
    let html = `<div class="muted">Navegadores e launchers (Chrome, Edge, Opera, Discord, Spotify, Steam) costumam guardar GBs na RAM mesmo parados. Aqui você devolve essa memória, baixa a prioridade deles ou os congela de vez enquanto joga. O que você está usando agora nunca é tocado.</div>
      <div class="tools" style="margin-top:10px"><button class="btn" id="m-trimall">⚡ Liberar RAM de todos</button>
        <label class="muted">Congelar por <select id="m-fmin">${[15, 30, 60, 120].map((m) => `<option value="${m}" ${m === S.freezeMin ? "selected" : ""}>${m} min</option>`).join("")}</select></label>
        ${anyFrozen ? '<button class="mini red" id="m-unfreezeall">▶ Descongelar tudo</button>' : ""}
        <button class="ghost" id="m-regroups">🔄 Atualizar</button></div>`;
    html += autoBlock();
    if (!g.length) html += '<div class="muted" style="margin-top:10px">Nenhum desses programas está aberto agora.</div>';
    html += g.map((x) => `<div class="row slim" style="--cols:1fr 120px auto"><div style="min-width:0"><div class="name">${esc(x.label)} <span class="muted">• ${esc(x.kind)} • ${x.count} ${x.count === 1 ? "processo" : "processos"}</span></div>
        <div class="why">${x.frozen ? `❄ Congelado, volta sozinho em ${mins(x.frozen.left)}.` : x.foreground ? "Você está usando agora: não mexo." : "Em segundo plano."}</div></div>
        <div>${fmt(x.rss)}</div>
        <div class="acts" style="opacity:1">${x.frozen ? `<button class="mini" data-un="${x.id}">▶ Descongelar</button>` : `
          <button class="mini" data-trim="${x.id}" ${x.foreground ? "disabled" : ""}>Liberar RAM</button>
          <button class="mini" data-low="${x.id}" ${x.foreground ? "disabled" : ""} title="Memória e processador com prioridade baixa">Baixar prioridade</button>
          ${x.can_freeze ? `<button class="mini red" data-fr="${x.id}" ${x.foreground ? "disabled" : ""}>❄ Congelar</button>` : ""}`}</div></div>`).join("");
    box.innerHTML = html;
    wireAuto(box);
    $("#m-fmin").onchange = (e) => (S.freezeMin = +e.target.value);
    $("#m-regroups").onclick = refreshGroups;
    $("#m-trimall").onclick = async () => {
      if (!await confirmBox({ title: "Liberar a RAM dos programas?", body: TRIM_WARN, ok: "Liberar", danger: true })) return;
      const r = await act(() => api.mem_trim_all()); if (ok(r)) toast("✅ " + r.msg); refreshGroups(); };
    const un = $("#m-unfreezeall");
    if (un) un.onclick = async () => { const r = await act(() => api.mem_unfreeze()); ok(r); refreshGroups(); };
    $$("[data-trim]", box).forEach((b) => (b.onclick = async () => {
      const x = g.find((y) => y.id === b.dataset.trim);
      if (!await confirmBox({ title: `Liberar a RAM do ${x.label}?`, body: TRIM_WARN, ok: "Liberar", danger: x.kind === "Navegador" })) return;
      const r = await act(() => api.mem_trim(b.dataset.trim)); if (ok(r)) toast("✅ " + r.msg); refreshGroups(); }));
    $$("[data-low]", box).forEach((b) => (b.onclick = async () => { const r = await act(() => api.mem_lower(b.dataset.low, true)); if (ok(r)) toast("✅ " + r.msg); }));
    $$("[data-un]", box).forEach((b) => (b.onclick = async () => { const r = await act(() => api.mem_unfreeze(b.dataset.un)); if (ok(r)) toast("✅ " + r.msg); refreshGroups(); }));
    $$("[data-fr]", box).forEach((b) => (b.onclick = async () => {
      const x = g.find((y) => y.id === b.dataset.fr);
      if (!await confirmBox({ title: `Congelar o ${x.label}?`, danger: true, ok: "Congelar",
        body: `O programa fica parado até você descongelar ou até passar ${S.freezeMin} min: ${x.freeze_warn}.\n\nA RAM dele é devolvida na hora. Se você fechar o WebDark, tudo é descongelado sozinho. Use só enquanto joga e lembre de descongelar depois.` })) return;
      const r = await act(() => api.mem_freeze(x.id, S.freezeMin));
      if (ok(r)) toast("❄ " + r.msg);
      refreshGroups();
    }));
  }
  // congelar sozinho enquanto joga
  function autoBlock() {
    const a = S.auto;
    if (!a) return "";
    const skipped = Object.entries(a.skipped || {}).map(([id, why]) => `${esc((a.options.find((o) => o.id === id) || {}).label || id)}: ${esc(why)}`);
    return `<div class="card adminnote" style="margin:12px 0"><div class="t"><b>🎮 Congelar sozinho quando eu jogar</b>
        <div class="muted">Quando um jogo estiver em tela cheia, o WebDark congela os programas marcados abaixo (a RAM volta na hora) e descongela sozinho quando o jogo sai da frente. Quem estiver usando microfone ou câmera (chamada de voz ou vídeo) nunca é congelado, e se você voltar pra um programa congelado ele acorda na hora.</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:8px">${a.options.map((o) => `<label class="muted" title="${esc("Ao congelar: " + o.warn)}"><input type="checkbox" data-aug="${o.id}" ${a.groups.includes(o.id) ? "checked" : ""}> ${esc(o.label)}</label>`).join("")}</div>
        <div class="muted" style="margin-top:6px">⚠ Marque só o que você não usa no jogo. Discord congelado = sem chat de voz; Spotify = sem música; navegador = sem música/vídeo de abas.${a.on ? `<br><b>${a.game ? "🎮 Jogo detectado: " + esc(a.game) : "Vigiando… nenhum jogo em tela cheia agora."}</b>${skipped.length ? " • Pulei: " + skipped.join("; ") : ""}` : ""}</div></div>
        <div class="sw ${a.on ? "on" : ""}" id="m-auto"></div></div>`;
  }
  function wireAuto(box) {
    const sw = $("#m-auto", box);
    if (!sw) return;
    const picked = () => $$("[data-aug]", box).filter((c) => c.checked).map((c) => c.dataset.aug);
    const save = async (on) => { S.auto = await api.mem_auto_set(on, picked()); paintApps(); };
    sw.onclick = async () => {
      const on = !S.auto.on;
      if (on) {
        if (!picked().length) return toast("Marque pelo menos um programa para congelar.");
        if (!await confirmBox({ title: "Ligar o congelamento automático?", danger: true, ok: "Ligar",
          body: "Quando você abrir um jogo em tela cheia, os programas marcados ficam parados até o jogo sair da frente. Pode dar problema se você marcar algo que precisa durante o jogo (por exemplo, o Discord numa chamada). Se o WebDark fechar, tudo é descongelado." })) return;
      }
      save(on);
    };
    $$("[data-aug]", box).forEach((c) => (c.onchange = () => { if (S.auto.on) save(true); else S.auto.groups = picked(); }));
  }
  on("mem:auto", (d) => { toast("🎮 " + d.msg); refreshGroups(); });

  async function refreshGroups() {
    try {
      const d = await api.mem_groups();
      if (!alive()) return;
      S.ram = d.ram; S.groups = d.groups; S.auto = d.auto; paintRam(); paintApps();
    } catch (e) { console.error(e); }
  }

  // ------------------------------------------------------------------ arquivo de paginação
  function paintPf() {
    const box = $("#m-pf");
    if (!box) return;
    const d = S.deep && S.deep.pagefile;
    if (!d) { box.innerHTML = '<div class="muted">Lendo o arquivo de paginação…</div>'; return; }
    const use = d.use[0], cur = d.set[0];
    box.innerHTML = `<div class="muted">É um “pedaço de disco” que o Windows usa como RAM extra. Seu PC tem ${d.ram_gb} GB de RAM e ${mb(d.free_mb)} livres em ${esc(d.drive)}.</div>
      <div style="margin-top:8px"><b>Agora:</b> ${d.auto ? "o Windows escolhe sozinho" : cur ? `fixo em ${mb(cur.InitialSize)} a ${mb(cur.MaximumSize)}` : "sem arquivo definido"}${use ? ` <span class="muted">• ocupa ${mb(use.AllocatedBaseSize)}, em uso ${mb(use.CurrentUsage)}, pico ${mb(use.PeakUsage)}</span>` : ""}</div>
      <div class="tools" style="margin-top:10px"><label class="muted">Inicial <input type="number" id="m-pfi" min="1024" step="512" value="${d.suggest.initial}" style="width:90px"> MB</label>
        <label class="muted">Máximo <input type="number" id="m-pfm" min="1024" step="512" value="${d.suggest.maximum}" style="width:90px"> MB</label>
        <button class="btn" id="m-pfgo">Aplicar sugestão${adminTag()}</button>
        <button class="ghost" id="m-pfauto" ${d.auto ? "disabled" : ""}>↩ Deixar o Windows escolher${adminTag()}</button></div>
      <div class="muted" style="margin-top:6px">Sugestão calculada pela sua RAM (${d.ram_gb} GB) e pelo espaço do disco. Precisa reiniciar o PC. Não desligue o arquivo de paginação: vários jogos e programas travam sem ele.</div>`;
    $("#m-pfgo").onclick = async () => {
      const i = +$("#m-pfi").value, m = +$("#m-pfm").value;
      if (!await confirmBox({ title: "Mudar o arquivo de paginação?", body: `Tamanho fixo de ${mb(i)} a ${mb(m)} em ${d.drive}. O app cria um ponto de restauração antes. Você precisa reiniciar o PC. Dá pra voltar ao automático aqui mesmo.`, ok: "Aplicar" })) return;
      const r = await act(() => api.mem_pagefile_apply(i, m));
      if (ok(r)) { toast("✅ " + r.msg); api.mem_deep(); }
    };
    $("#m-pfauto").onclick = async () => { const r = await act(() => api.mem_pagefile_auto()); if (ok(r)) { toast("✅ " + r.msg); api.mem_deep(); } };
  }

  // ------------------------------------------------------------------ agrupar serviços (SvcHost)
  function paintSvc() {
    const box = $("#m-svc");
    if (!box) return;
    const v = S.svc;
    if (!v) { box.innerHTML = '<div class="muted">Lendo…</div>'; return; }
    const isRec = v.value != null && v.current === v.value;
    box.innerHTML = `<div class="muted">O Windows abre um processo svchost para cada serviço quando tem RAM sobrando. Subir esse limite junta os serviços em menos processos e economiza memória. Seu PC tem ${v.ram_gb} GB.</div>
      <div style="margin-top:8px"><b>Valor agora:</b> ${v.current_hex ? `<code>${esc(v.current_hex)}</code>` : "padrão do Windows (0x380000)"}
        <span class="muted">• recomendado para você: ${v.hex ? `<code>${esc(v.hex)}</code> (faixa de ${v.tier_gb} GB)` : "nenhum (pouca RAM)"}</span></div>
      <div class="tools" style="margin-top:10px"><button class="btn" id="m-svcgo" ${v.value == null || isRec ? "disabled" : ""}>${isRec ? "✔ Já aplicado" : "Aplicar o recomendado"}${adminTag()}</button>
        <button class="ghost" id="m-svcdef" ${v.current == null || v.current === 0x380000 ? "disabled" : ""}>↩ Voltar ao padrão${adminTag()}</button></div>
      <details style="margin-top:8px"><summary class="muted">Tabela de valores (KB, hexadecimal)</summary><div class="muted" style="margin-top:6px">Padrão: 0x380000 • ${v.table.map((t) => `${t.gb} GB: ${t.hex}`).join(" • ")}</div></details>
      <div class="muted" style="margin-top:6px">Vale depois de reiniciar o PC. Funciona no Windows 10 (1703) e no 11.</div>`;
    const set = (mode) => async () => {
      const r = await act(() => api.mem_svchost_set(mode));
      if (ok(r)) { toast("✅ " + r.msg); S.svc = await api.mem_scan().then((d) => d.svc); paintSvc(); }
    };
    $("#m-svcgo").onclick = set("auto");
    $("#m-svcdef").onclick = set("default");
  }

  // ------------------------------------------------------------------------- SysMain
  function paintSys() {
    const box = $("#m-sys");
    if (!box) return;
    const d = S.deep && S.deep.sysmain;
    if (!d) { box.innerHTML = '<div class="muted">Lendo…</div>'; return; }
    if (!d.available) { box.innerHTML = '<div class="muted">O SysMain não existe neste Windows.</div>'; return; }
    box.innerHTML = `<div class="set" style="padding:0"><div class="t"><b>Desligar o SysMain (Superfetch)</b>${adminTag()}
        <div class="muted">O SysMain pré-carrega programas na RAM. Em SSD ele gasta disco e memória à toa; em HD ele ajuda e desligar deixa o PC mais lento. Seu disco: <b>${esc(d.kind || "não identifiquei")}</b>.</div></div>
        <div class="sw ${d.off ? "on" : ""}" id="m-sysmain"></div></div>`;
    $("#m-sysmain").onclick = async () => {
      const want = !d.off;
      if (!isAdmin()) return toast("Precisa de administrador. Use “Reabrir como administrador”.");
      if (want && !await confirmBox({ title: "Desligar o SysMain?", body: d.warning, ok: "Desligar", danger: d.kind === "HDD" })) return;
      const r = await act(() => api.mem_sysmain_set(want));
      if (ok(r)) { d.off = want; toast("✅ " + r.msg); }
      paintSys();
    };
  }

  // ------------------------------------------------------------- serviços que dá pra desligar
  const RISK = { low: ["BAIXO", "ok"], mid: ["MÉDIO", "care"], high: ["ALTO", "care"] };
  function paintSvcs() {
    const box = $("#m-svcs");
    if (!box) return;
    const rows = S.svcs;
    if (!rows) { box.innerHTML = '<div class="muted">Lendo os serviços…</div>'; return; }
    box.innerHTML = `<div class="card adminnote" style="border-color:rgba(248,113,113,.6);background:rgba(220,38,38,.1)"><div class="t"><b>⚠ Cuidado: desligar serviço pode dar problema</b>
        <div class="muted">Cada serviço desligado libera um pouco de RAM e CPU, mas pode tirar um recurso do Windows (impressão, VPN, Xbox, certificado digital…). Leia o que quebra antes de desligar. Dá pra religar com o mesmo interruptor, e o app cria um ponto de restauração antes.</div></div></div>
      <div class="tools" style="margin:10px 0"><button class="btn" id="m-svclow">Desligar todos de risco baixo${adminTag()}</button>
        <button class="ghost" id="m-svcrest">↩ Voltar tudo ao que era${adminTag()}</button></div>
      ${rows.map((r, i) => `<div class="set" style="padding:8px 0"><div class="t"><b>${esc(r.title)}</b> <span class="muted">(${esc(r.name)})</span>
          <span class="pill ${RISK[r.risk][1]}">RISCO ${RISK[r.risk][0]}</span>${r.sug ? ' <span class="tag keep">SUGERIDO</span>' : ""}
          <div class="muted">${esc(r.desc)} <b>Se desligar:</b> ${esc(r.breaks)}</div>
          <div class="muted">Agora: ${esc(r.start_label)}${r.running ? " • rodando" : ""}${r.was ? ` • antes: ${esc(r.was)}` : ""}${!r.can_restore ? " • já vinha desligado do Windows" : ""}</div></div>
        <div class="sw ${r.off ? "on" : ""}" data-svc="${i}" ${!r.off || r.can_restore ? "" : 'style="opacity:.4;pointer-events:none"'}></div></div>`).join("")}`;
    const reload = async () => { S.svcs = await api.svc_list(); paintSvcs(); };
    $$("[data-svc]", box).forEach((b) => (b.onclick = async () => {
      const r = rows[+b.dataset.svc], want = !r.off;
      if (!isAdmin()) return toast("Precisa de administrador. Use “Reabrir como administrador”.");
      if (want && !await confirmBox({ title: `Desligar ${r.title}?`, danger: r.risk !== "low", ok: "Desligar",
        body: `${r.desc}\n\n⚠ SE DESLIGAR: ${r.breaks}\n\nRisco ${RISK[r.risk][0].toLowerCase()}. Dá pra religar aqui mesmo.` })) return;
      const res = await act(() => api.svc_set(r.name, want));
      if (ok(res)) toast("✅ " + res.msg);
      reload();
    }));
    $("#m-svclow").onclick = async () => {
      if (!await confirmBox({ title: "Desligar os serviços de risco baixo?", ok: "Desligar", body: "Desliga todos os marcados com RISCO BAIXO que estão ligados (telemetria, fax, relatório de erros, registro remoto…). Leia a lista abaixo antes. Dá pra voltar tudo com “Voltar tudo ao que era”." })) return;
      const res = await act(() => api.svc_bulk("low")); if (ok(res)) toast("✅ " + res.msg); reload();
    };
    $("#m-svcrest").onclick = async () => { const res = await act(() => api.svc_bulk("restore")); if (ok(res)) toast("✅ " + res.msg); reload(); };
  }

  on("mem:deep", (d) => { S.deep = d; paintPf(); paintSys(); });

  // ----------------------------------------------------------------------------- tela
  async function load() {
    if (S.loading) return;
    S.loading = true; busy(1);
    try {
      const d = await api.mem_scan();
      S.ram = d.ram; S.groups = d.groups; S.svc = d.svc; S.auto = d.auto;
    } finally { S.loading = false; busy(-1); }
    if (!alive()) return;
    for (const paint of [paintRam, paintApps, paintSvc]) {
      try { paint(); } catch (e) { console.error(paint.name, e); }
    }
    api.mem_deep();
    S.svcs = await api.svc_list();
    if (alive()) paintSvcs();
  }

  return {
    mount(el) {
      el.innerHTML = head("Memória", "Libere RAM, ajuste o arquivo de paginação e o agrupamento de serviços. Tudo dá pra desfazer.") + `<div class="scroll">
        ${card("m-ram", "🧠 Memória agora", "")}
        ${card("m-apps", "🌐 Programas em segundo plano", "")}
        ${card("m-pf", "💾 Arquivo de paginação", "")}
        ${card("m-svc", "🧩 Agrupar serviços (SvcHost)", "")}
        ${card("m-sys", "🚦 SysMain (Superfetch)", "")}
        ${card("m-svcs", "🔌 Serviços que você pode desligar", "")}</div>`;
      paintRam(); paintApps(); paintPf(); paintSvc(); paintSys(); paintSvcs();
    },
    show() {
      load();
      clearInterval(S.timer);
      S.timer = setInterval(() => { if (alive()) refreshGroups(); else { clearInterval(S.timer); S.timer = null; } }, 10000);   // contagem do congelamento e RAM ao vivo
    },
    unmount() { clearInterval(S.timer); S.timer = null; },
  };
})();
