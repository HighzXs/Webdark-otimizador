// Telas: Espaço (abas Pastas, Duplicados, Downloads antigos e o contêiner das abas) e Limpeza.

// ================================================================ ESPAÇO (contêiner)
Pages.space = (() => {
  let tab = "files";
  const TABS = [["dirs", "📁 Pastas"], ["files", "📄 Arquivos grandes"], ["dups", "👯 Duplicados"], ["dl", "📥 Downloads antigos"]];
  function open(t) {
    const prev = SpaceTabs[tab];
    if (prev && prev.unmount && $("#tabbody")) prev.unmount();
    tab = t;
    $$("[data-tab]").forEach((b) => b.classList.toggle("on", b.dataset.tab === t));
    const body = $("#tabbody");
    body.innerHTML = "";
    SpaceTabs[t].mount(body);
    if (SpaceTabs[t].show) SpaceTabs[t].show();
  }
  return {
    mount(el) {
      el.innerHTML = head("Quem está comendo meu espaço?", "Pastas pesadas, arquivos grandes com aviso de risco, duplicados e downloads velhos.") +
        `<div class="tabs">${TABS.map(([id, label]) => `<button class="chip" data-tab="${id}">${label}</button>`).join("")}</div><div id="tabbody" class="tabbody"></div>`;
      $$("[data-tab]").forEach((b) => (b.onclick = () => open(b.dataset.tab)));
      open(tab);
    },
    unmount() { const t = SpaceTabs[tab]; if (t && t.unmount) t.unmount(); },
    info(i) { if (SpaceTabs.files.info) SpaceTabs.files.info(i); },
  };
})();

const driveOptions = (sel) => ((window.INFO && window.INFO.drives) || ["C:\\"]).map((d) => `<option ${d === sel ? "selected" : ""}>${esc(d)}</option>`).join("");
const riskPill = (r) => `<span class="pill ${r.level}">${esc(r.label)}</span>`;

// ------------------------------------------------------------------- Pastas
SpaceTabs.dirs = (() => {
  const S = { path: null, items: [], loading: false };
  function paint() {
    const box = $("#dirl");
    if (!box) return;
    $("#dpath").textContent = S.path || "";
    $("#dup").disabled = !S.path || S.path.replace(/\\$/, "").length <= 2;
    if (S.loading) box.innerHTML = '<div class="empty">Medindo… (o disco inteiro pode levar 1–2 minutos)</div>';
    else if (!S.items.length) box.innerHTML = '<div class="empty">Vazio (ou sem permissão).</div>';
    else {
      const big = Math.max(...S.items.map((i) => i.size), 1);
      box.innerHTML = S.items.map((it, n) => `<div class="row slim" data-n="${n}" style="--cols:1fr 220px 100px 90px">
        <div class="name" style="${it.dir ? "cursor:pointer" : ""}" data-a="${it.dir ? "enter" : ""}">${it.dir ? "📁" : "📄"} ${esc(it.name)}</div>
        <div class="meter"><i style="width:${Math.max(2, (it.size / big) * 100)}%"></i></div>
        <div class="size">${fmt(it.size)}</div><div class="acts"><button class="mini" data-a="open">Abrir</button></div></div>`).join("");
    }
  }
  function scan(path) { if (!S.loading) busy(1); S.path = path; S.loading = true; paint(); api.dirs_scan(path); }
  on("dirs:list", (d) => { if (d.path !== S.path || !S.loading) return; S.items = d.items; S.loading = false; busy(-1); paint(); });
  return {
    mount(el) {
      el.innerHTML = `<div class="tools"><select id="droot">${driveOptions(S.path)}</select><button class="btn" id="dscan">🔍 Escanear</button>
        <button class="ghost" id="dup">⬆ Subir</button><span class="muted" id="dpath"></span></div>
        <div class="card" style="flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden"><div class="list" id="dirl"></div></div>`;
      $("#dscan").onclick = () => scan($("#droot").value);
      $("#dup").onclick = () => { let p = S.path.replace(/\\$/, ""); p = p.slice(0, p.lastIndexOf("\\")); if (p.length === 2) p += "\\"; if (p) scan(p); };
      $("#dirl").onclick = (e) => {
        const row = e.target.closest(".row"), a = e.target.dataset.a;
        if (!row) return;
        const it = S.items[+row.dataset.n];
        if (a === "enter") scan(it.path); else if (a === "open") api.reveal(it.path);
      };
      paint();
    },
    show() { if (!S.path && !S.loading) scan((window.INFO && window.INFO.drives[0]) || "C:\\"); },
  };
})();

// --------------------------------------------------------------- Duplicados
SpaceTabs.dups = (() => {
  const S = { groups: [], total: 0, marks: new Set(), scanning: false, done: false, progress: "" };
  const sizeOf = (p) => { for (const g of S.groups) if (g.files.some((f) => f.path === p)) return g.size; return 0; };
  function paint() {
    const box = $("#dupl");
    if (!box) return;
    if (S.scanning) box.innerHTML = `<div class="empty">${esc(S.progress || "Procurando… (pode levar alguns minutos)")}</div>`;
    else if (!S.groups.length) box.innerHTML = S.done ? '<div class="empty">Nenhum duplicado desse tamanho por aqui. 👍<br>Tente “maiores que 1 MB” ou outra pasta.</div>'
      : '<div class="empty">Escolha onde procurar e clique em “Procurar”.<br>A busca continua sozinha se você trocar de tela.</div>';
    else box.innerHTML = S.groups.map((g) => `<div class="grp" style="padding-top:16px">${g.files.length} cópias de ${fmt(g.size)} • desperdício de ${fmt(g.size * (g.files.length - 1))}</div>` +
      g.files.map((f) => `<div class="row slim" data-p="${esc(f.path)}" style="--cols:44px 1fr 100px">
        <div class="cb ${S.marks.has(f.path) ? "on" : ""}" data-a="check"></div>
        <div style="min-width:0"><div class="name">${esc(f.path.split("\\").pop())}</div><div class="why" title="${esc(f.path)}">${esc(f.path.slice(0, f.path.lastIndexOf("\\")))}</div></div>
        <div class="why">${f.date}</div></div>`).join("")).join("");
    const total = [...S.marks].reduce((a, p) => a + sizeOf(p), 0);
    const b = $("#dupdel");
    b.disabled = !S.marks.size || S.scanning;
    b.textContent = S.marks.size ? `🗑 Mandar ${S.marks.size} marcados pra lixeira (${fmt(total)})` : "🗑 Mandar marcados pra lixeira";
    $("#dupinfo").textContent = S.groups.length ? `${S.groups.length}${S.total > S.groups.length ? " de " + S.total : ""} grupo(s). Em cada grupo uma cópia fica sem marca (a que sugiro manter).` : "";
    $("#dupgo").disabled = S.scanning;
  }
  on("dups:progress", (t) => { S.progress = t; paint(); });
  on("dups:done", (d) => {
    S.groups = d.groups; S.total = d.total; S.scanning = false; S.done = true; busy(-1);
    S.marks = new Set(d.groups.flatMap((g) => g.files.slice(1).map((f) => f.path)));
    paint();
  });
  return {
    mount(el) {
      el.innerHTML = `<div class="tools"><select id="dupwhere"><option value="mine">Minhas pastas (Documentos, Downloads…)</option>${driveOptions("")}</select>
        <select id="dupmin"><option value="1">maiores que 1 MB</option><option value="10" selected>maiores que 10 MB</option><option value="100">maiores que 100 MB</option></select>
        <button class="btn" id="dupgo">🔍 Procurar</button><span class="muted" id="dupinfo"></span><span style="flex:1"></span>
        <button class="btn red" id="dupdel" disabled>🗑 Mandar marcados pra lixeira</button></div>
        <div class="card" style="flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden"><div class="list" id="dupl"></div></div>`;
      $("#dupgo").onclick = () => { if (S.scanning) return; S.scanning = true; S.done = false; S.groups = []; S.marks.clear(); S.progress = ""; busy(1); paint(); api.dups_scan($("#dupwhere").value, +$("#dupmin").value); };
      $("#dupl").onclick = (e) => {
        const row = e.target.closest(".row");
        if (!row || e.target.dataset.a !== "check") return;
        const p = row.dataset.p, g = S.groups.find((x) => x.files.some((f) => f.path === p));
        if (S.marks.has(p)) S.marks.delete(p);
        else { S.marks.add(p); if (g.files.every((f) => S.marks.has(f.path))) { S.marks.delete(p); toast("⚠ Deixe pelo menos uma cópia de cada arquivo sem marcar."); } }
        paint();
      };
      $("#dupdel").onclick = async () => {
        const paths = [...S.marks], total = paths.reduce((a, p) => a + sizeOf(p), 0);
        if (!await confirmBox({ title: `Mandar ${paths.length} cópia(s) para a lixeira?`, body: `Libera ${fmt(total)}. Dá pra recuperar da lixeira do Windows.`, ok: "Mandar para a lixeira", danger: true })) return;
        busy(1); const r = await api.dups_trash(paths); busy(-1);
        const gone = new Set(r.done);
        S.groups = S.groups.map((g) => ({ ...g, files: g.files.filter((f) => !gone.has(f.path)) })).filter((g) => g.files.length > 1);
        S.marks = new Set([...S.marks].filter((p) => !gone.has(p)));
        paint();
        toast(r.failed.length ? `⚠ ${r.done.length} ok, ${r.failed.length} falharam: ${r.failed[0].err}` : `✅ ${fmt(r.freed)} na lixeira`);
      };
      paint();
    },
  };
})();

// ---------------------------------------------------------- Downloads antigos
SpaceTabs.dl = (() => {
  const S = { rows: [], checked: new Set(), scanning: false, done: false };
  function paint() {
    const box = $("#dll");
    if (!box) return;
    if (S.scanning) box.innerHTML = '<div class="empty">Procurando…</div>';
    else if (!S.done) box.innerHTML = '<div class="empty">Clique em “Listar”. Só listo: nada é apagado sozinho, você escolhe arquivo por arquivo.</div>';
    else if (!S.rows.length) box.innerHTML = '<div class="empty">Nada velho por aqui. 👍</div>';
    else box.innerHTML = S.rows.map((r) => {
      const lock = r.level === "danger";
      return `<div class="row" data-id="${r.id}" style="--cols:44px 118px 1fr 100px 150px"><div class="cb ${S.checked.has(r.id) ? "on" : ""} ${lock ? "off" : ""}" data-a="check"></div><div>${riskPill(r)}</div>
        <div style="min-width:0"><div class="name">${esc(r.rel)}</div><div class="why">${esc(r.reason)}</div></div><div class="size">${fmt(r.size)}</div>
        <div class="acts"><button class="mini" data-a="show">Mostrar</button><button class="mini red" data-a="trash" ${lock ? "disabled" : ""}>${lock ? "🔒" : "🗑"}</button></div></div>`;
    }).join("");
    $("#dlgo").disabled = S.scanning;
    $("#dlinfo").textContent = S.done ? `${S.rows.length} arquivo(s) • ${fmt(S.rows.reduce((a, r) => a + r.size, 0))}` : "";
    const chosen = S.rows.filter((r) => S.checked.has(r.id)), safe = S.rows.filter((r) => r.level === "ok");
    const del = $("#dldel");
    del.hidden = !chosen.length;
    del.textContent = `🗑 Mandar ${chosen.length} marcado(s) pra lixeira (${fmt(chosen.reduce((a, r) => a + r.size, 0))})`;
    $("#dlsafe").hidden = !safe.length;
    $("#dlsafe").textContent = safe.every((r) => S.checked.has(r.id)) ? "Desmarcar todos" : `✔ Marcar os ${safe.length} seguros`;
  }
  on("dl:done", (rows) => { S.rows = rows; S.checked.clear(); S.scanning = false; S.done = true; busy(-1); paint(); });
  return {
    mount(el) {
      el.innerHTML = `<div class="tools"><span class="muted">Sem mexer há mais de</span><select id="dldays"><option value="30">30 dias</option><option value="60">60 dias</option>
        <option value="90" selected>90 dias</option><option value="180">180 dias</option><option value="365">1 ano</option></select>
        <button class="btn" id="dlgo">🔍 Listar</button><span class="muted" id="dlinfo"></span><span style="flex:1"></span>
        <button class="btn" id="dlsafe" hidden></button><button class="btn red" id="dldel" hidden></button></div>
        <div class="card" style="flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden"><div class="list" id="dll"></div></div>`;
      $("#dlgo").onclick = () => { if (S.scanning) return; S.scanning = true; busy(1); paint(); api.dl_scan(+$("#dldays").value); };
      $("#dlsafe").onclick = () => {
        const safe = S.rows.filter((r) => r.level === "ok");
        if (safe.every((r) => S.checked.has(r.id))) safe.forEach((r) => S.checked.delete(r.id));
        else safe.forEach((r) => S.checked.add(r.id));
        paint();
      };
      $("#dldel").onclick = async () => {
        const chosen = S.rows.filter((r) => S.checked.has(r.id) && r.level !== "danger"), total = chosen.reduce((a, r) => a + r.size, 0);
        const care = chosen.filter((r) => r.level === "care").length;
        if (!await confirmBox({ title: `Mandar ${chosen.length} arquivo(s) para a lixeira?`, body: `Libera ${fmt(total)}. Dá pra recuperar da lixeira do Windows.` + (care ? `\n\n⚠ ${care} deles estão como CUIDADO: confira antes.` : ""), ok: "Mandar para a lixeira", danger: care > 0 })) return;
        busy(1); const res = await api.trash(chosen.map((r) => r.path)); busy(-1);
        const gone = new Set(res.done);
        S.rows = S.rows.filter((r) => !gone.has(r.path)); S.checked = new Set([...S.checked].filter((id) => S.rows.some((r) => r.id === id)));
        paint();
        toast(res.failed.length ? `⚠ ${res.done.length} ok, ${res.failed.length} falharam: ${res.failed[0].err}` : `✅ ${fmt(res.freed)} na lixeira`);
      };
      $("#dll").onclick = async (e) => {
        const row = e.target.closest(".row");
        if (!row) return;
        const r = S.rows.find((x) => x.id === +row.dataset.id), a = e.target.dataset.a;
        if (a === "check") { if (r.level === "danger") return; S.checked.has(r.id) ? S.checked.delete(r.id) : S.checked.add(r.id); paint(); }
        else if (a === "show") api.reveal(r.path);
        else if (a === "trash") {
          if (!await confirmBox({ title: "Mandar para a lixeira?", body: `${r.label}: ${r.reason}\n\n${r.path}`, ok: "Mandar para a lixeira", danger: r.level === "care" })) return;
          const res = await api.trash([r.path]);
          if (res.done.length) { S.rows = S.rows.filter((x) => x.id !== r.id); paint(); toast(`✅ ${fmt(res.freed)} na lixeira`); } else toast("⚠ " + res.failed[0].err);
        }
      };
      paint();
    },
  };
})();

// ================================================================== LIMPEZA
Pages.clean = (() => {
  const S = { items: [], sizes: {}, checked: new Set(), sized: false, loading: false, running: false, log: "", pct: 0, extras: null };
  const isAdmin = () => !!(window.INFO && window.INFO.admin);

  function paint() {
    const box = $("#cl");
    if (!box) return;
    box.innerHTML = S.loading ? '<div class="empty">Carregando…</div>' : S.items.map((c) => {
      const locked = c.admin && !isAdmin(), size = S.sizes[c.key];
      return `<div class="card set" data-k="${c.key}" style="${locked ? "opacity:.55" : ""}"><div class="cb ${S.checked.has(c.key) ? "on" : ""}" data-a="check" ${locked ? 'title="Precisa de administrador"' : ""}></div>
        <div class="t"><b>${esc(c.name)}</b>${locked ? ' <span class="tag q">PRECISA DE ADMIN</span>' : ""}<div class="muted">${esc(c.desc)}</div></div>
        <b style="min-width:90px;text-align:right">${size === undefined ? "…" : fmt(size)}</b></div>`;
    }).join("");
    const tot = S.items.filter((c) => S.checked.has(c.key)).reduce((a, c) => a + (S.sizes[c.key] || 0), 0);
    $("#cltot").textContent = S.sized ? `Marcados: ${fmt(tot)} para liberar` : "Medindo…";
    $("#clrun").disabled = S.running || !S.checked.size;
    $("#clfill").style.width = S.pct + "%";
    $("#cllog").textContent = S.log;
    $("#cllog").scrollTop = 1e9;
    const ex = S.extras;
    if (ex) $("#hibtxt").textContent = ex.hiber ? `Arquivo de hibernação ocupa ${fmt(ex.hiber)}. Desligar também desativa a inicialização rápida.` : "Hibernação já está desligada.";
  }
  const load = () => { S.loading = true; S.sized = false; S.sizes = {}; busy(1); paint(); api.clean_list(); api.extras_info().then((x) => { S.extras = x; paint(); }); };
  on("cl:list", (items) => { S.items = items; S.loading = false; S.checked = new Set(items.filter((c) => c.default && (!c.admin || isAdmin())).map((c) => c.key)); paint(); });
  on("cl:size", (d) => { S.sizes[d.key] = d.size; paint(); });
  on("cl:sized", () => { S.sized = true; busy(-1); paint(); });
  on("cl:step", (d) => { S.pct = Math.round((d.i / d.n) * 100); paint(); });
  on("cl:log", (l) => { S.log += l + "\n"; paint(); });
  on("cl:done", (d) => { S.running = false; S.pct = 100; busy(-1); S.log += `✅ ${fmt(d.freed)} liberados.\n`; toast("✅ " + fmt(d.freed) + " liberados"); paint(); });
  on("cl:dism_done", () => { busy(-1); S.log += "✅ DISM terminou.\n"; paint(); });

  return {
    mount(el) {
      el.innerHTML = head("Limpeza", "Escolha o que limpar. Nada aqui apaga seus documentos, fotos ou senhas.") + `
        <div class="tools"><button class="ghost" id="clre">🔍 Analisar de novo</button><span class="muted" id="cltot"></span><span style="flex:1"></span><button class="btn" id="clrun">🧹 Limpar marcados</button></div>
        <div class="bar" style="margin:0"><i id="clfill"></i></div>
        <div class="scroll" id="clscroll"><div id="cl" style="display:flex;flex-direction:column;gap:10px"></div>
          <h2>🔧 Extras para liberar MUITO espaço <span class="muted">(precisam de administrador)</span></h2>
          <div class="card" style="padding:16px 18px;display:flex;flex-direction:column;gap:12px">
            <div style="display:flex;gap:14px;align-items:center"><button class="ghost" id="hib">Desligar hibernação</button><span class="muted" id="hibtxt"></span></div>
            <div style="display:flex;gap:14px;align-items:center"><button class="ghost" id="dism">Limpar componentes antigos do Windows (DISM)</button><span class="muted">Demora uns minutos e fica parado em 20%/40%… é normal. Não feche.</span></div>
            <div style="display:flex;gap:14px;align-items:center"><button class="ghost" id="cmgr">Abrir Limpeza de Disco do Windows</button><span class="muted">Apaga o Windows.old e instalações antigas.</span></div>
          </div><div class="logbox" id="cllog"></div></div>`;
      $("#clre").onclick = load;
      $("#cl").onclick = (e) => {
        const row = e.target.closest("[data-k]");
        if (!row || e.target.dataset.a !== "check") return;
        const c = S.items.find((x) => x.key === row.dataset.k);
        if (c.admin && !isAdmin()) return toast("Esse item precisa de administrador.");
        S.checked.has(c.key) ? S.checked.delete(c.key) : S.checked.add(c.key);
        paint();
      };
      $("#clrun").onclick = async () => {
        const chosen = S.items.filter((c) => S.checked.has(c.key)), warns = chosen.filter((c) => c.warn);
        if (warns.length && !await confirmBox({ title: "Atenção", body: warns.map((c) => `⚠ ${c.name}\n${c.warn}`).join("\n\n") + "\n\nQuer mesmo limpar isso?", ok: "Limpar mesmo assim", danger: true })) return;
        if (!await confirmBox({ title: `Limpar ${chosen.length} item(ns)?`, body: "Feche os navegadores antes para limpar mais.", ok: "Limpar" })) return;
        S.running = true; S.pct = 0; S.log = ""; busy(1); paint();
        api.clean_run(chosen.map((c) => c.key));
      };
      const needAdmin = () => { if (isAdmin()) return false; toast("Isso precisa de administrador. Use “Reabrir como administrador”."); return true; };
      $("#hib").onclick = async () => {
        if (needAdmin()) return;
        if (!await confirmBox({ title: "Desligar a hibernação?", body: "Libera o arquivo hiberfil.sys (vários GB), mas desativa hibernar e a inicialização rápida.\n\nPra desfazer: powercfg /h on (como administrador).", ok: "Desligar", danger: true })) return;
        const ok = await api.hibernate_off(); S.extras = await api.extras_info(); toast(ok ? "Hibernação desligada. ✅" : "Não consegui desligar. 😕"); paint();
      };
      $("#dism").onclick = async () => {
        if (needAdmin()) return;
        S.log += "Iniciando limpeza de componentes… pode levar 10+ minutos, não feche.\n"; busy(1); paint(); api.dism_cleanup();
      };
      $("#cmgr").onclick = () => api.open_cleanmgr();
      paint();
    },
    show() { if (!S.items.length && !S.loading) load(); },
  };
})();
