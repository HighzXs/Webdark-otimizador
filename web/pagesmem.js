// Tela Memória (aba de Velocidade): RAM agora, programas em segundo plano (baixar prioridade, congelar, congelar sozinho
// ao jogar), arquivo de paginação e o desfazer do que versões antigas mudavam (SvcHost e serviços).
Pages.mem = (() => {
  const S = { ram: null, groups: [], deep: null, auto: null, loading: false, freezeMin: 30, timer: null };
  const alive = () => current === "mem";
  const isAdmin = () => !!(window.INFO && window.INFO.admin);
  const ok = (r) => { if (r && r.ok === false) { toast("" + r.msg); return false; } return true; };
  const adminTag = () => (isAdmin() ? "" : ' <span class="tag q">PRECISA DE ADMIN</span>');
  const card = (id, title, sub, body = "") => `<h2>${title}${sub ? ` <span class="muted" style="font-weight:400">${sub}</span>` : ""}</h2><div class="card" id="${id}" style="padding:14px 18px">${body}</div>`;
  const mins = (s) => Math.max(1, Math.ceil(s / 60)) + " min";
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
      <div class="muted">Pouca RAM disponível o tempo todo? Feche abas e programas, ou congele os que ficam abertos enquanto você joga (abaixo). “Limpar a RAM” não deixa o PC mais rápido: o Windows já usa a memória livre como cache e devolve na hora quando um programa precisa.</div>`;
  }

  // ------------------------------------------------------------- programas em segundo plano
  function paintApps() {
    const box = $("#m-apps");
    if (!box) return;
    const g = S.groups;
    const anyFrozen = g.some((x) => x.frozen);
    let html = `<div class="muted">Navegadores e launchers (Chrome, Edge, Opera, Discord, Spotify, Steam) costumam guardar GBs na RAM mesmo parados. Aqui você baixa a prioridade deles ou os congela enquanto joga. O que você está usando agora nunca é tocado.</div>
      <div class="tools" style="margin-top:10px"><label class="muted">Congelar por <select id="m-fmin">${[15, 30, 60, 120].map((m) => `<option value="${m}" ${m === S.freezeMin ? "selected" : ""}>${m} min</option>`).join("")}</select></label>
        ${anyFrozen ? '<button class="mini red" id="m-unfreezeall">Descongelar tudo</button>' : ""}
        <button class="ghost" id="m-regroups">${ICON("refresh")}Atualizar</button></div>`;
    html += autoBlock();
    if (!g.length) html += '<div class="muted" style="margin-top:10px">Nenhum desses programas está aberto agora.</div>';
    html += g.map((x) => `<div class="row slim" style="--cols:1fr 120px auto"><div style="min-width:0"><div class="name">${esc(x.label)} <span class="muted">• ${esc(x.kind)} • ${x.count} ${x.count === 1 ? "processo" : "processos"}</span></div>
        <div class="why">${x.frozen ? `Congelado, volta sozinho em ${mins(x.frozen.left)}.` : x.foreground ? "Você está usando agora: não mexo." : "Em segundo plano."}</div></div>
        <div>${fmt(x.rss)}</div>
        <div class="acts" style="opacity:1">${x.frozen ? `<button class="mini" data-un="${x.id}">Descongelar</button>` : `
          <button class="mini" data-low="${x.id}" ${x.foreground ? "disabled" : ""} title="Memória e processador com prioridade baixa">Baixar prioridade</button>
          ${x.can_freeze ? `<button class="mini red" data-fr="${x.id}" ${x.foreground ? "disabled" : ""}>Congelar</button>` : ""}`}</div></div>`).join("");
    box.innerHTML = html;
    wireAuto(box);
    $("#m-fmin").onchange = (e) => (S.freezeMin = +e.target.value);
    $("#m-regroups").onclick = refreshGroups;
    const un = $("#m-unfreezeall");
    if (un) un.onclick = async () => { const r = await act(() => api.mem_unfreeze()); ok(r); refreshGroups(); };
    $$("[data-low]", box).forEach((b) => (b.onclick = async () => { const r = await act(() => api.mem_lower(b.dataset.low, true)); if (ok(r)) toast("" + r.msg); }));
    $$("[data-un]", box).forEach((b) => (b.onclick = async () => { const r = await act(() => api.mem_unfreeze(b.dataset.un)); if (ok(r)) toast("" + r.msg); refreshGroups(); }));
    $$("[data-fr]", box).forEach((b) => (b.onclick = async () => {
      const x = g.find((y) => y.id === b.dataset.fr);
      if (!await confirmBox({ title: `Congelar o ${x.label}?`, danger: true, ok: "Congelar",
        body: `O programa fica parado até você descongelar ou até passar ${S.freezeMin} min: ${x.freeze_warn}.\n\nEle para de usar o processador, e o Windows reaproveita a RAM dele se precisar. Se você fechar o WebDark, tudo é descongelado sozinho. Use só enquanto joga e lembre de descongelar depois.` })) return;
      const r = await act(() => api.mem_freeze(x.id, S.freezeMin));
      if (ok(r)) toast("" + r.msg);
      refreshGroups();
    }));
  }
  // congelar sozinho enquanto joga
  function autoBlock() {
    const a = S.auto;
    if (!a) return "";
    const skipped = Object.entries(a.skipped || {}).map(([id, why]) => `${esc((a.options.find((o) => o.id === id) || {}).label || id)}: ${esc(why)}`);
    return `<div class="card autonote" style="margin:12px 0"><div class="t"><b>Congelar sozinho quando eu jogar</b>
        <div class="muted">Quando um jogo estiver em tela cheia, o WebDark congela os programas marcados abaixo e descongela sozinho quando o jogo sai da frente. Quem estiver usando microfone ou câmera (chamada de voz ou vídeo) nunca é congelado, e se você voltar pra um programa congelado ele acorda na hora.</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:8px">${a.options.map((o) => `<label class="muted" title="${esc("Ao congelar: " + o.warn)}"><input type="checkbox" data-aug="${o.id}" ${a.groups.includes(o.id) ? "checked" : ""}> ${esc(o.label)}</label>`).join("")}</div>
        <div class="muted" style="margin-top:6px">Marque só o que você não usa no jogo. Discord congelado = sem chat de voz; Spotify = sem música; navegador = sem música/vídeo de abas.${a.on ? `<br><b>${a.game ? "Jogo detectado: " + esc(a.game) : "Vigiando… nenhum jogo em tela cheia agora."}</b>${skipped.length ? " • Pulei: " + skipped.join("; ") : ""}` : ""}</div></div>
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
  on("mem:auto", (d) => { toast("" + d.msg); refreshGroups(); });

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
    box.innerHTML = `<div class="muted">É um “pedaço de disco” que o Windows usa como RAM extra. Seu PC tem ${d.ram_gb} GB de RAM.</div>
      <div style="margin-top:8px"><b>Agora:</b> ${d.auto ? "o Windows escolhe sozinho" : cur ? `fixo em ${cur.InitialSize} a ${cur.MaximumSize} MB` : "sem arquivo definido"}${use ? ` <span class="muted">• em uso ${use.CurrentUsage} MB, pico ${use.PeakUsage} MB</span>` : ""}</div>
      ${d.auto ? "" : `<div class="tools" style="margin-top:10px"><button class="btn" id="m-pfauto">Deixar o Windows escolher${adminTag()}</button></div>`}
      <div class="muted" style="margin-top:6px">${d.auto ? "Está no automático, que é o melhor na maioria dos PCs." : "Tamanho fixo raramente ajuda e, se ficar pequeno, jogos e programas podem fechar sozinhos. Recomendo voltar ao automático (precisa reiniciar)."} Não desligue o arquivo de paginação.</div>`;
    const pa = $("#m-pfauto");
    if (pa) pa.onclick = async () => { const r = await act(() => api.mem_pagefile_auto()); if (ok(r)) { toast("" + r.msg); api.mem_deep(); } };
  }

  // ------------------------------------------------- desfazer o que versões antigas mudavam
  // SvcHost e "serviços que dá pra desligar" saíram do app (não davam desempenho). Quem usou volta ao padrão aqui.
  function paintLegacy() {
    const box = $("#m-legacy"), lg = S.deep && S.deep.legacy;
    if (!box) return;
    const items = !lg ? [] : [].concat(lg.svchost ? ["Agrupamento de serviços (SvcHost) fora do padrão"] : [],
      lg.services.map((s) => `Serviço desligado: ${esc(s.title)} (era ${esc(s.was)})`));
    box.hidden = !items.length;
    if (!items.length) return;
    box.innerHTML = `<h2>Desfazer ajustes antigos</h2><div class="card" style="padding:14px 18px">
      <div class="muted">Versões antigas do WebDark mudavam isto. Esses ajustes saíram porque não deixam o PC mais rápido e podem tirar recursos do Windows. Recomendo voltar ao padrão.</div>
      <ul class="muted" style="margin:8px 0 0 18px">${items.map((t) => `<li>${t}</li>`).join("")}</ul>
      <div class="tools" style="margin-top:10px"><button class="btn" id="m-undo">Voltar ao padrão${adminTag()}</button></div></div>`;
    $("#m-undo").onclick = async () => { const r = await act(() => api.mem_legacy_undo()); if (ok(r)) { toast("" + r.msg); api.mem_deep(); } };
  }

  on("mem:deep", (d) => { S.deep = d; paintPf(); paintLegacy(); });

  // ----------------------------------------------------------------------------- tela
  async function load() {
    if (S.loading) return;
    S.loading = true; busy(1);
    try {
      const d = await api.mem_scan();
      S.ram = d.ram; S.groups = d.groups; S.auto = d.auto;
    } finally { S.loading = false; busy(-1); }
    if (!alive()) return;
    for (const paint of [paintRam, paintApps]) {
      try { paint(); } catch (e) { console.error(paint.name, e); }
    }
    api.mem_deep();
  }

  return {
    mount(el) {
      el.innerHTML = head("Memória", "Veja o uso da RAM e congele o que pesa enquanto você joga. Tudo dá pra desfazer.") + `<div class="scroll">
        ${card("m-ram", "Memória agora", "")}
        ${card("m-apps", "Programas em segundo plano", "")}
        ${card("m-pf", "Arquivo de paginação", "")}
        <div id="m-legacy" hidden></div></div>`;
      paintRam(); paintApps(); paintPf(); paintLegacy();
    },
    show() {
      load();
      clearInterval(S.timer);
      S.timer = setInterval(() => { if (alive()) refreshGroups(); else { clearInterval(S.timer); S.timer = null; } }, 10000);   // contagem do congelamento e RAM ao vivo
    },
    unmount() { clearInterval(S.timer); S.timer = null; },
  };
})();
