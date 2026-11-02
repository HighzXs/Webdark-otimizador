// Telas: Bloatware, Programas, Inicialização, Processos.

const LEVEL_TITLE = { lixo: "🗑 Lixo — recomendo remover", opcional: "🤔 Opcionais — você decide", outro: "⚠ Outros apps — só remova se souber o que é" };
const head = (title, sub) => (INTAB ? `<div class="muted tabsub">${sub}</div>` : `<div><h1>${title}</h1><div class="muted">${sub}</div></div>`);

// ================================================================= BLOATWARE
Pages.bloat = (() => {
  const S = { items: [], checked: new Set(), loaded: false, loading: false, removing: false, log: "" };

  function paint() {
    const box = $("#list");
    if (!box) return;
    if (S.loading) box.innerHTML = '<div class="empty">Procurando apps instalados… (pode levar uns segundos)</div>';
    else if (!S.items.length) box.innerHTML = '<div class="empty">Nenhum bloatware encontrado. 🎉</div>';
    else {
      let html = "", last = null;
      for (const it of S.items) {
        if (it.level !== last) {
          last = it.level;
          const kids = S.items.filter((x) => x.level === it.level), all = kids.every((x) => S.checked.has(x.id));
          html += `<div class="grp" data-g="${it.level}"><div class="cb ${all ? "on" : ""}" data-a="group"></div>${LEVEL_TITLE[it.level]} <span class="muted">(${kids.length})</span></div>`;
        }
        html += `<div class="row slim" data-id="${esc(it.id)}" style="--cols:44px 1fr 1fr"><div class="cb ${S.checked.has(it.id) ? "on" : ""}" data-a="check"></div>
          <div class="name" style="${it.level === "outro" ? "color:#fbbf24" : ""}">${esc(it.friendly)}</div><div class="why">${esc(it.desc)}</div></div>`;
      }
      box.innerHTML = html;
    }
    $("#n").textContent = `${S.checked.size} marcado(s)`;
    $("#rm").disabled = !S.checked.size || S.removing;
    $("#log").textContent = S.log;
    $("#log").scrollTop = 1e9;
  }
  const load = () => { S.loading = true; S.checked.clear(); busy(1); paint(); api.bloat_scan(); };

  on("bloat:list", (items) => {
    S.items = items; S.loading = false; S.loaded = true; busy(-1);
    S.checked = new Set(items.filter((i) => i.level === "lixo").map((i) => i.id));
    paint();
  });
  on("bloat:log", (l) => { S.log += l + "\n"; paint(); });
  on("bloat:done", (n) => { S.removing = false; busy(-1); S.log += `\n✅ ${n} app(s) removidos.\n`; toast(`✅ ${n} app(s) removidos`); load(); });

  return {
    mount(el) {
      el.innerHTML = head("Bloatware", "Apps que vêm com o Windows e quase ninguém usa. Dá pra reinstalar depois pela Microsoft Store.") + `
        <div class="tools"><button class="chip" id="rec">Marcar recomendados</button><button class="chip" id="none">Desmarcar tudo</button>
          <span class="muted" id="n"></span><span style="flex:1"></span><button class="btn red" id="rm">🔥 Remover marcados</button></div>
        <div class="card" style="flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden"><div class="list" id="list"></div></div>
        <div class="logbox" id="log"></div>`;
      $("#rec").onclick = () => { S.checked = new Set(S.items.filter((i) => i.level === "lixo").map((i) => i.id)); paint(); };
      $("#none").onclick = () => { S.checked.clear(); paint(); };
      $("#list").onclick = (e) => {
        const a = e.target.dataset.a, row = e.target.closest(".row"), grp = e.target.closest(".grp");
        if (a === "check" && row) { const id = row.dataset.id; S.checked.has(id) ? S.checked.delete(id) : S.checked.add(id); paint(); }
        else if (a === "group" && grp) {
          const kids = S.items.filter((x) => x.level === grp.dataset.g), all = kids.every((x) => S.checked.has(x.id));
          kids.forEach((k) => (all ? S.checked.delete(k.id) : S.checked.add(k.id)));
          paint();
        } else if (row && !a) { const id = row.dataset.id; S.checked.has(id) ? S.checked.delete(id) : S.checked.add(id); paint(); }
      };
      $("#rm").onclick = async () => {
        const chosen = S.items.filter((i) => S.checked.has(i.id));
        const names = chosen.slice(0, 15).map((c) => "• " + c.friendly).join("\n") + (chosen.length > 15 ? "\n…" : "");
        if (!await confirmBox({ title: `Remover ${chosen.length} app(s)?`, body: names + "\n\nDá pra reinstalar depois pela Microsoft Store.", ok: "Remover", danger: true })) return;
        S.removing = true; S.log = ""; busy(1); paint();
        api.bloat_remove(chosen.map((c) => c.id));
      };
      paint();
    },
    show() { if (!S.loaded && !S.loading) load(); },
  };
})();

// ================================================================ PROGRAMAS
Pages.progs = (() => {
  const S = { items: [], loaded: false, loading: false, query: "", sort: "default", checked: new Set(), q: null };
  const COLS = "44px 1fr 200px 100px 130px";
  const view = () => {
    const q = S.query.toLowerCase();
    const rows = S.items.filter((p) => !q || p.name.toLowerCase().includes(q) || (p.publisher || "").toLowerCase().includes(q));
    if (S.sort === "size") rows.sort((a, b) => b.size - a.size);
    if (S.sort === "name") rows.sort((a, b) => a.name.localeCompare(b.name));
    return rows;
  };
  const chosen = () => S.items.filter((p) => S.checked.has(p.id));
  function bar() {
    const n = S.checked.size, b = $("#unmany");
    if (!b) return;
    b.hidden = !n;
    b.disabled = !!S.q;
    b.textContent = `🗑 Desinstalar ${n} marcado(s)`;
    const sus = S.items.filter((p) => p.suspect);
    $("#marksus").hidden = !sus.length;
    $("#marksus").textContent = sus.every((p) => S.checked.has(p.id)) ? "Desmarcar suspeitos" : `⚠ Marcar os ${sus.length} suspeitos`;
    $("#cnt").textContent = `${view().length} programa(s)` + (n ? ` • ${n} marcado(s)` : "");
  }
  function paintQueue() {
    const box = $("#uq");
    if (!box) return;
    box.hidden = !S.q;
    if (!S.q) return;
    const q = S.q;
    box.innerHTML = `<div style="flex:1;min-width:0"><b>🗑 Desinstalando ${q.i + 1} de ${q.n}: ${esc(q.name)}</b>
      <div class="muted">${q.wait ? "Confirme na janela do desinstalador. Quando ele terminar, abro o próximo sozinho." : "Abrindo o desinstalador… confirme na janela dele."}</div>
      <div class="bar" style="margin:8px 0 0"><i style="width:${Math.round((q.i / q.n) * 100)}%"></i></div></div>
      ${q.wait ? '<button class="ghost" id="uqskip">⏭ Pular este</button>' : ""}<button class="ghost" id="uqstop">⏹ Parar a fila</button>`;
    if (q.wait) $("#uqskip").onclick = () => api.progs_queue_skip();
    $("#uqstop").onclick = () => api.progs_queue_stop();
  }
  function paint() {
    const box = $("#list");
    if (!box) return;
    const rows = view();
    box.innerHTML = S.loading ? '<div class="empty">Lendo programas…</div>' : !rows.length ? '<div class="empty">Nada aqui.</div>' :
      rows.map((p) => `<div class="row slim" data-id="${esc(p.id)}" style="--cols:${COLS}">
        <div class="cb ${S.checked.has(p.id) ? "on" : ""}" data-a="check" title="Marcar para desinstalar vários de uma vez"></div>
        <div style="min-width:0"><div class="name" style="${p.suspect ? "color:#fbbf24" : ""}">${p.suspect ? "⚠ " : ""}${esc(p.name)}</div></div>
        <div class="why">${esc(p.publisher || "—")}</div><div class="size">${p.size ? fmt(p.size) : "—"}</div>
        <div class="acts"><button class="mini red" data-a="un">Desinstalar</button></div></div>`).join("");
    bar();
  }
  const load = () => { S.loading = true; S.checked.clear(); busy(1); paint(); api.progs_scan(); };
  on("progs:list", (items) => { S.items = items; S.loading = false; S.loaded = true; busy(-1); paint(); });
  on("progs:q", (q) => { S.q = q; paintQueue(); bar(); });
  on("progs:qdone", (r) => {
    S.q = null; busy(-1);
    const parts = [];
    if (r.removed) parts.push(`${r.removed} removido(s)`);
    if (r.opened) parts.push(`${r.opened} aberto(s) (confirme nas janelas deles)`);
    if (r.kept) parts.push(`${r.kept} continua(m) instalado(s)`);
    if (r.skipped) parts.push(`${r.skipped} pulado(s)`);
    if (r.failed) parts.push(`${r.failed} não abriu`);
    toast("🗑 " + (parts.join(" • ") || "Fila parada") + (r.opened ? ". Depois clique em Atualizar." : ""));
    paintQueue();
    if (!r.opened) load(); else bar();
  });

  async function removeMany() {
    const list = chosen();
    if (!list.length || S.q) return;
    const names = list.slice(0, 8).map((p) => "• " + p.name).join("\n") + (list.length > 8 ? `\n… e mais ${list.length - 8}` : "");
    const mode = await choiceBox({ title: `Desinstalar ${list.length} programas?`,
      body: `${names}\n\nCada desinstalador abre a própria janela e pede a sua confirmação. Nada é removido sem você aceitar nela.`,
      options: [
        { id: "auto", primary: true, label: "Automático (recomendado)", hint: "Abre juntos os que aceitam e coloca em fila os que não aceitam dois ao mesmo tempo (instaladores MSI)." },
        { id: "queue", label: "Um de cada vez", hint: "O próximo só abre quando o anterior terminar. Mais lento, mais seguro." },
        { id: "together", label: "Todos de uma vez", hint: "Abre tudo junto. Alguns desinstaladores podem dar erro de “outra instalação em andamento”." },
      ] });
    if (!mode) return;
    busy(1);
    if (!await api.progs_uninstall_many(list.map((p) => p.id), mode)) { busy(-1); toast("⚠ Já tem uma desinstalação em andamento."); }
  }

  return {
    mount(el) {
      el.innerHTML = head("Programas instalados", "Os suspeitos (testes de antivírus, barras de ferramentas) aparecem primeiro com ⚠. Marque vários pra desinstalar de uma vez.") + `
        <div class="card bar2">
          <div class="fld grow"><label for="q">Buscar</label><input class="search" id="q" placeholder="Programa ou editora…" value="${esc(S.query)}"></div>
          <div class="fld"><label for="sort">Ordem</label><select id="sort"><option value="default">Suspeitos e maiores primeiro</option><option value="size">Maiores primeiro</option><option value="name">Nome (A–Z)</option></select></div>
          <button class="ghost" id="re">🔄 Atualizar</button>
          <button class="ghost" id="marksus" hidden></button>
          <button class="btn red" id="unmany" hidden></button>
        </div>
        <div class="card queue" id="uq" hidden></div>
        <div class="card" style="flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden">
          <div class="head" style="--cols:${COLS}"><span></span><span>PROGRAMA</span><span>EDITORA</span><span style="text-align:right">TAMANHO</span><span></span></div>
          <div class="list" id="list"></div></div><div class="muted" id="cnt"></div>`;
      $("#sort").value = S.sort;
      $("#q").oninput = (e) => { S.query = e.target.value; paint(); };
      $("#sort").onchange = (e) => { S.sort = e.target.value; paint(); };
      $("#re").onclick = load;
      $("#unmany").onclick = removeMany;
      $("#marksus").onclick = () => {
        const sus = S.items.filter((p) => p.suspect), all = sus.every((p) => S.checked.has(p.id));
        sus.forEach((p) => (all ? S.checked.delete(p.id) : S.checked.add(p.id)));
        paint();
      };
      $("#list").onclick = async (e) => {
        const row = e.target.closest(".row"), a = e.target.dataset.a;
        if (!row || !a) return;
        const id = row.dataset.id;
        if (a === "check") {
          S.checked.has(id) ? S.checked.delete(id) : S.checked.add(id);
          e.target.classList.toggle("on", S.checked.has(id));
          bar();
        } else if (a === "un") {
          const p = S.items.find((x) => x.id === id);
          if (await confirmBox({ title: "Desinstalar?", body: `Abrir o desinstalador de:\n\n${p.name}`, ok: "Abrir desinstalador", danger: true })) {
            const ok = await api.prog_uninstall(p.id);
            toast(ok ? "Desinstalador aberto. Depois clique em Atualizar." : "⚠ Não consegui abrir o desinstalador desse programa.");
          }
        }
      };
      paint();
      paintQueue();
    },
    show() { if (!S.loaded && !S.loading) load(); },
  };
})();
// ============================================================== INICIALIZAÇÃO
Pages.start = (() => {
  const S = { items: [], loaded: false, loading: false, busyIds: new Set(), sel: null };
  const SEC = { run: "📋 Programas que abrem com o Windows (o Gerenciador de Tarefas também mostra)", task: "🕵 Tarefas agendadas — o Gerenciador de Tarefas NÃO mostra",
    service: "⚙ Serviços — o Gerenciador de Tarefas NÃO mostra (só na aba Serviços)" };
  const sec = (k) => (k === "folder" ? "run" : k);
  const BADGE = { off: ["off", "PODE DESLIGAR"], keep: ["keep", "MANTENHA"], "?": ["q", "DEPENDE"] };

  function paint() {
    const box = $("#list");
    if (!box) return;
    if (S.loading) box.innerHTML = '<div class="empty">Procurando… (leva alguns segundos)</div>';
    else {
      let html = "", last = null;
      for (const it of S.items) {
        if (sec(it.kind) !== last) { last = sec(it.kind); html += `<div class="grp">${SEC[last]}</div>`; }
        const [cls, label] = BADGE[it.advice];
        html += `<div class="row slim ${S.sel === it.id ? "sel" : ""}" data-id="${esc(it.id)}" style="--cols:60px 1fr 130px">
          <div class="sw ${it.enabled ? "on" : ""} small" data-a="sw" title="${it.enabled ? "Ligado" : "Desligado"}"></div>
          <div style="min-width:0"><div class="name">${esc(it.name)}</div><div class="why">${esc(it.note)}</div></div><div><span class="tag ${cls}">${label}</span></div></div>`;
      }
      box.innerHTML = html || '<div class="empty">Nada encontrado.</div>';
    }
    const on = S.items.filter((i) => i.enabled).length;
    $("#cnt").textContent = `${on} ligados de ${S.items.length}`;
    const it = S.items.find((i) => i.id === S.sel);
    $("#detail").innerHTML = it ? `<b>${esc(it.name)}</b><br>${esc(it.note)}<br><span class="muted">Onde: ${esc(it.where)}</span><br><span class="muted">Comando: ${esc(it.command)}</span>` : '<span class="muted">Clique numa linha para ver os detalhes.</span>';
  }
  const load = () => { S.loading = true; busy(1); paint(); api.start_scan(); };
  on("start:list", (items) => { S.items = items; S.loading = false; S.loaded = true; busy(-1); paint(); });
  on("start:bulk", (d) => { busy(-1); toast(d.failed.length ? `⚠ Não consegui desligar: ${d.failed.slice(0, 3).join(", ")}` : `✅ ${d.done} item(ns) desligados`); load(); });

  async function toggle(it) {
    if (S.busyIds.has(it.id)) return;
    if (it.admin && !(window.INFO && window.INFO.admin)) { toast("Esse item precisa de administrador. Use “Reabrir como administrador”."); return; }
    const want = !it.enabled;
    if (!want && it.advice === "keep" && !await confirmBox({ title: `“${it.name}” parece importante`, body: it.note + "\n\nDesligar mesmo assim?", ok: "Desligar", danger: true })) return;
    S.busyIds.add(it.id); it.enabled = want; paint();
    const r = await api.start_set(it.id, want);
    S.busyIds.delete(it.id);
    if (!r.ok) { it.enabled = !want; toast("⚠ Não consegui mudar: " + r.msg); }
    paint();
  }
  return {
    mount(el) {
      el.innerHTML = head("Inicialização", "Tudo que liga junto com o Windows, inclusive o que o Gerenciador de Tarefas esconde. Menos coisa ligando = PC liga mais rápido.") + `
        <div class="tools"><button class="ghost" id="re">🔄 Atualizar</button><span class="muted" id="cnt"></span><span style="flex:1"></span>
          <button class="btn" id="rec">Desligar os recomendados</button></div>
        ${window.INFO && !window.INFO.admin ? '<div class="muted" style="color:#fbbf24">⚠ Sem administrador, só dá pra mexer nos itens do seu usuário. Tarefas e serviços precisam de admin.</div>' : ""}
        <div class="card" style="flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden"><div class="list" id="list"></div></div>
        <div class="card" style="padding:12px 16px;min-height:86px;user-select:text" id="detail"></div>`;
      $("#re").onclick = load;
      $("#rec").onclick = async () => {
        const t = S.items.filter((i) => i.advice === "off" && i.enabled && (window.INFO.admin || !i.admin));
        if (!t.length) return toast("Nada recomendado para desligar agora.");
        const names = t.slice(0, 12).map((x) => "• " + x.name).join("\n") + (t.length > 12 ? "\n…" : "");
        if (await confirmBox({ title: `Desligar ${t.length} item(ns)?`, body: names + "\n\nDá pra religar depois pelo interruptor.", ok: "Desligar" })) { busy(1); api.start_disable_recommended(); }
      };
      $("#list").onclick = (e) => {
        const row = e.target.closest(".row");
        if (!row) return;
        const it = S.items.find((x) => x.id === row.dataset.id);
        if (e.target.dataset.a === "sw") toggle(it); else { S.sel = it.id; paint(); }
      };
      paint();
    },
    show() { if (!S.loaded && !S.loading) load(); },
  };
})();

// ================================================================== PROCESSOS
Pages.proc = (() => {
  const S = { rows: [], sort: "ram", auto: true, timer: null, busy: false, sel: null, vm: null, ready: false };
  const els = new Map();                      // key -> elemento da linha (atualiza no lugar, sem piscar)

  function rowEl(r) {
    const d = document.createElement("div");
    d.className = "row slim"; d.dataset.key = r.key; d.style.setProperty("--cols", "1fr 110px 80px 120px 110px");
    d.innerHTML = '<div class="name"></div><div class="size"></div><div class="size"></div><div class="why"></div><div class="acts"><button class="mini red" data-a="close">Fechar</button></div>';
    return d;
  }
  function paint() {
    const list = $("#list");
    if (!list) return;
    const key = S.sort === "cpu" ? (r) => r.cpu : (r) => r.ram;
    const top = [...S.rows].sort((a, b) => key(b) - key(a)).slice(0, 40);
    const keep = new Set(top.map((r) => r.key));
    for (const [k, el] of els) if (!keep.has(k)) { el.remove(); els.delete(k); }
    if (!S.ready) { if (!list.firstChild) list.innerHTML = '<div class="empty">Lendo processos…</div>'; return; }
    if (list.querySelector(".empty")) list.innerHTML = "";
    top.forEach((r, i) => {
      let el = els.get(r.key);
      if (!el) { el = rowEl(r); els.set(r.key, el); }
      const c = el.children;
      c[0].textContent = r.name + (r.count > 1 ? `  ×${r.count}` : "");
      c[1].textContent = fmt(r.ram); c[2].textContent = r.cpu.toFixed(1) + "%";
      c[3].textContent = r.protected ? "🔒 Windows" : "";
      const b = c[4].firstChild; b.disabled = r.protected; b.textContent = r.protected ? "🔒" : "Fechar";
      el.classList.toggle("sel", S.sel === r.key);
      if (list.children[i] !== el) list.insertBefore(el, list.children[i] || null);   // só mexe se mudou de lugar
    });
    if (S.vm) $("#sum").textContent = `RAM: ${fmt(S.vm.ram_used)} de ${fmt(S.vm.ram_total)} (${Math.round(S.vm.ram_pct)}%)   •   CPU: ${Math.round(S.vm.cpu_total)}%   •   ${S.rows.reduce((a, r) => a + r.count, 0)} processos`;
  }
  async function refresh() {
    if (S.busy || document.hidden) return;
    S.busy = true;
    try { const d = await api.proc_list(); S.rows = d.rows; S.vm = d; S.ready = true; paint(); } finally { S.busy = false; }
  }
  return {
    mount(el) {
      el.innerHTML = head("Processos", "Quem está pesando agora. Fechar um programa perde o que não foi salvo nele. Os do Windows ficam trancados.") + `
        <div class="tools"><span class="muted">Ordenar por:</span><button class="chip on" data-s="ram">RAM</button><button class="chip" data-s="cpu">CPU</button>
          <button class="ghost" id="re">🔄 Atualizar</button><span class="muted">Atualizar sozinho</span><div class="sw on" id="auto"></div></div>
        <div class="muted" id="sum"></div>
        <div class="card" style="flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden">
          <div class="head" style="--cols:1fr 110px 80px 120px 110px"><span>PROGRAMA</span><span style="text-align:right">RAM</span><span style="text-align:right">CPU</span><span>ESTADO</span><span></span></div>
          <div class="list" id="list"></div></div>`;
      els.clear(); S.ready = false;
      $$("[data-s]").forEach((b) => b.onclick = () => { S.sort = b.dataset.s; $$("[data-s]").forEach((x) => x.classList.toggle("on", x === b)); paint(); });
      $("#re").onclick = refresh;
      $("#auto").onclick = (e) => { S.auto = !S.auto; e.target.classList.toggle("on", S.auto); };
      $("#list").onclick = async (e) => {
        const row = e.target.closest(".row");
        if (!row) return;
        const r = S.rows.find((x) => x.key === row.dataset.key);
        if (e.target.dataset.a === "close" && !r.protected) {
          if (!await confirmBox({ title: `Fechar ${r.name}?`, body: `${r.count} processo(s).\n\n⚠ Tudo que não foi salvo nele será perdido.`, ok: "Fechar", danger: true })) return;
          const res = await api.proc_close(r.key);
          toast(res.errors.length ? "⚠ " + res.errors.slice(0, 2).join(" • ") : `✅ ${r.name} fechado`);
          refresh();
        } else { S.sel = r.key; paint(); }
      };
      paint();
    },
    show() {
      api.proc_list().then(() => setTimeout(refresh, 1200));          // a 1ª leitura só prepara o cálculo de CPU
      S.timer = setInterval(() => S.auto && refresh(), 4000);
    },
    unmount() { clearInterval(S.timer); },
  };
})();
