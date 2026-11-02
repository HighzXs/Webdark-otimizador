// Telas: Início, Espaço > Arquivos grandes, Ajustes. As outras ficam em pages2.js e pages3.js.
const SpaceTabs = {};

Pages._soon = (id) => ({
  mount(el) {
    const [, icon, label] = NAV.find((n) => n[0] === id);
    el.innerHTML = `<div class="soon-card card"><div style="font-size:44px">${icon}</div><h1 style="margin:8px 0">${label}</h1>
      <p class="muted">Essa aba ainda está no app antigo (Faxina Várzea) e vem para o WebDark nas próximas etapas.</p></div>`;
  },
});

// ================================================================== INÍCIO
Pages.home = (() => {
  const st = { sum: null, pct: 0, text: "Pronto para começar.", cleaning: false, loadedAt: 0, loading: false };

  function paint() {
    if (!$("#t-free")) return;
    const s = st.sum || {};
    const low = s.free !== undefined && s.free / s.total < 0.10;
    $("#t-free").textContent = s.free !== undefined ? fmt(s.free) : "…";
    $("#t-free-sub").textContent = s.free !== undefined ? "de " + fmt(s.total) + (low ? "  ⚠ quase cheio" : "") : " ";
    $("#tile-free").classList.toggle("warn", low);
    $("#t-junk").textContent = s.junk !== undefined ? fmt(s.junk) : "…";
    $("#t-start").textContent = s.startup !== undefined ? s.startup : "…";
    $("#t-start-sub").textContent = s.startup !== undefined ? "programas ligados" + (s.startup > 12 ? "  (muitos!)" : "") : " ";
    $("#t-ram").textContent = s.ram_pct !== undefined ? Math.round(s.ram_pct) + "%" : "…";
    $("#t-ram-sub").textContent = s.ram_total ? fmt(s.ram_used) + " de " + fmt(s.ram_total) : " ";
    $("#fill").style.width = st.pct + "%";
    $("#ptxt").textContent = st.text;
    $("#go").disabled = st.cleaning;
  }

  function load() {
    if (st.loading) return;
    st.loading = true;
    busy(1);
    api.summary();
  }

  on("summary", (d) => {
    st.sum = { ...(st.sum || {}), ...d };
    if (d.done) { st.loading = false; st.loadedAt = Date.now(); busy(-1); }
    paint();
  });
  on("clean:step", (d) => { st.pct = Math.round((d.i / d.n) * 100); st.text = `→ ${d.name}…  ${st.pct}%`; paint(); });
  on("clean:done", (d) => {
    st.cleaning = false; st.pct = 100; busy(-1);
    st.text = `✅ Pronto! ${fmt(d.freed)} liberados.  Espaço livre no C: ${fmt(d.before)} → ${fmt(d.after)}`;
    toast("✅ " + fmt(d.freed) + " liberados");
    st.loadedAt = 0;
    paint();
    load();
    api.info().then((i) => { window.INFO = i; const h = $("#hist"); if (h) h.textContent = histText(i); });
  });

  const adminNote = () => { const n = $("#adminnote"); if (n) n.hidden = !!(window.INFO && window.INFO.admin) || !window.INFO; };
  const upText = (s) => { const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60); return (d ? d + "d " : "") + h + "h " + m + "min"; };

  async function pullLive() {
    const d = await api.live();
    if (!$("#l-cpu")) return;
    $("#l-cpu").textContent = Math.round(d.cpu) + "%";
    $("#l-cpu-b").style.width = d.cpu + "%";
    $("#l-ram").textContent = Math.round(d.ram_pct) + "%";
    $("#l-ram-s").textContent = fmt(d.ram_used) + " de " + fmt(d.ram_total);
    $("#l-ram-b").style.width = d.ram_pct + "%";
    $("#l-up").textContent = upText(d.uptime);
    $("#l-up-s").textContent = d.uptime > 7 * 86400 ? "⚠ Faz tempo sem reiniciar. Reiniciar ajuda." : "Reiniciar de vez em quando ajuda";
    $("#drives").innerHTML = d.drives.map((x) => {
      const pct = (x.used / x.total) * 100;
      return `<div class="drv"><span class="n">💽 ${esc(x.root)}</span><div class="meter"><i class="${pct > 90 ? "hot" : ""}" style="width:${pct.toFixed(1)}%"></i></div>
        <span class="u">${fmt(x.free)} livres de ${fmt(x.total)}</span></div>`;
    }).join("");
  }
  function paintSpecs() {
    const box = $("#specs");
    if (!box || !st.specs) return;
    box.innerHTML = st.specs.cards.length ? st.specs.cards.map((c) => `<div class="card spec"><i>${c.icon}</i><div style="min-width:0"><div class="k">${esc(c.k)}</div>
      <div class="v" title="${esc(c.v)}">${esc(c.v)}</div>${c.s ? `<div class="s">${esc(c.s)}</div>` : ""}</div></div>`).join("") : '<div class="muted">Não consegui ler as especificações.</div>';
  }
  on("specs", (d) => { st.specs = d; paintSpecs(); });

  const histText = (i) => i.history_total ? `📈 Total liberado até hoje: ${fmt(i.history_total)}` : "📈 Ainda não liberei nada por aqui. Bora fazer a primeira faxina!";

  return {
    mount(el) {
      el.innerHTML = `
        <div><h1>Início</h1><div class="muted">Resumo do seu PC e uma faxina segura com um clique.</div></div>
        <div class="scroll">
        <div class="card adminnote" id="adminnote" hidden><div class="t"><b>🛡 Você está sem permissão de administrador</b>
          <div class="muted">Algumas faxinas, reparos e ajustes do Windows ficam travados. Reabra como administrador pra liberar tudo.</div></div>
          <button class="btn" id="adminnow">Reabrir como administrador</button></div>
        <div class="tiles">
          <div class="card tile" id="tile-free"><span class="muted">💽 Espaço livre (C:)</span><b id="t-free">…</b><span class="muted" id="t-free-sub"> </span></div>
          <div class="card tile"><span class="muted">🧹 Dá pra limpar</span><b id="t-junk">…</b><span class="muted">lixo seguro</span></div>
          <div class="card tile"><span class="muted">🚀 Abrem com o Windows</span><b id="t-start">…</b><span class="muted" id="t-start-sub"> </span></div>
          <div class="card tile"><span class="muted">🧠 Memória em uso</span><b id="t-ram">…</b><span class="muted" id="t-ram-sub"> </span></div>
        </div>
        <div class="homegrid">
          <div class="card faxina">
            <b>⚡ Faxina rápida</b>
            <div class="muted">Limpa só o que é seguro: temporários, cache, lixeira e restos do Windows. Seus arquivos não são tocados.</div>
            <div class="bar"><i id="fill"></i></div>
            <div class="faxina-row"><span class="muted" id="ptxt"></span><button class="btn" id="go">Limpar agora</button></div>
          </div>
          <div class="card now">
            <b>🖥 Seu PC agora</b>
            <div class="metric"><span class="muted">⚙ Processador</span><div class="meter"><i id="l-cpu-b" style="width:0"></i></div><span><b id="l-cpu">…</b></span></div>
            <div class="metric"><span class="muted">🧠 Memória</span><div class="meter"><i id="l-ram-b" style="width:0"></i></div><span><b id="l-ram">…</b> <span class="muted" id="l-ram-s"></span></span></div>
            <div class="metric up"><span class="muted">⏱ Ligado há</span><span><b id="l-up">…</b></span><span class="muted" id="l-up-s"></span></div>
          </div>
        </div>
        <div class="card" style="padding:6px 18px" id="drives"><div class="muted" style="padding:8px 0">Lendo os discos…</div></div>
        <h2>🧾 Ficha técnica</h2>
        <div class="specs" id="specs"><div class="muted">Lendo as especificações… (leva alguns segundos)</div></div>
        <div class="histrow"><div class="muted" id="hist"></div>
          <button class="ghost" id="restore">🛟 Criar ponto de restauração</button></div>
        </div>`;
      $("#adminnow").onclick = () => $("#adminBtn").click();
      adminNote();
      pullLive(); st.timer = setInterval(pullLive, 3000);
      if (st.specs) paintSpecs(); else api.specs();
      $("#restore").onclick = async () => {
        if (!(window.INFO && window.INFO.admin)) return toast("Precisa de administrador. Use “Reabrir como administrador”.");
        busy(1); const r = await api.restore_point(); busy(-1); toast((r.ok ? "🛟 " : "😕 ") + r.msg);
      };
      $("#go").onclick = async () => {
        const ok = await confirmBox({ title: "Faxina rápida", ok: "Limpar agora",
          body: "Vou limpar arquivos temporários, cache dos navegadores, lixeira e restos de atualização.\n\nFeche os navegadores antes para limpar mais. Seus documentos, fotos e senhas não são tocados." });
        if (!ok) return;
        st.cleaning = true; st.pct = 0; st.text = "Começando…"; busy(1); paint();
        api.quick_clean();
      };
      paint();
      if (window.INFO) $("#hist").textContent = histText(window.INFO);
    },
    show() { if (Date.now() - st.loadedAt > 60000) load(); },
    unmount() { clearInterval(st.timer); },
    info(i) { const h = $("#hist"); if (h) h.textContent = histText(i); adminNote(); },
  };
})();

// ============================================================ ESPAÇO / ARQUIVOS GRANDES
SpaceTabs.files = (() => {
  const F = { rows: [], level: "", query: "", checked: new Set(), scanning: false, progress: "", min: 100, root: "C:\\", sel: -1 };
  const TABS = [["dirs", "📁 Pastas"], ["files", "📄 Arquivos grandes"], ["dups", "👯 Duplicados"], ["dl", "📥 Downloads antigos"]];

  const visible = () => {
    const q = F.query.toLowerCase();
    return F.rows.filter((r) => (!F.level || r.level === F.level) && (!q || r.path.toLowerCase().includes(q)));
  };
  const safeRows = () => F.rows.filter((r) => r.level === "ok");

  function renderList() {
    const box = $("#list");
    if (!box) return;
    const rows = visible();
    if (F.scanning) box.innerHTML = `<div class="empty">${esc(F.progress || "Procurando…")}</div>`;
    else if (!F.rows.length) box.innerHTML = '<div class="empty">Escolha o disco e o tamanho mínimo e clique em “Procurar”.</div>';
    else if (!rows.length) box.innerHTML = '<div class="empty">Nada aqui. 👍</div>';
    else box.innerHTML = rows.map((r) => {
      const name = r.path.split("\\").pop(), folder = r.path.slice(0, r.path.lastIndexOf("\\"));
      const lock = r.level === "danger";
      return `<div class="row ${F.sel === r.id ? "sel" : ""}" data-id="${r.id}">
        <div class="cb ${F.checked.has(r.id) ? "on" : ""}" data-a="check" title="Marcar"></div>
        <div><span class="pill ${r.level}">${esc(r.label)}</span></div>
        <div style="min-width:0"><div class="name">${esc(name)}</div><div class="why" title="${esc(r.path)}">${esc(folder)} • ${esc(r.reason)}</div></div>
        <div class="size">${fmt(r.size)}</div>
        <div class="acts"><button class="mini" data-a="show">Mostrar</button>
          <button class="mini red" data-a="trash" ${lock ? 'disabled title="Protegido: pode quebrar o Windows ou um programa"' : 'title="Mandar para a lixeira"'}>${lock ? "🔒" : "🗑"}</button></div></div>`;
    }).join("");
    const safe = safeRows(), total = safe.reduce((a, r) => a + r.size, 0);
    const sb = $("#delsafe");
    sb.disabled = !safe.length || F.scanning;
    sb.textContent = safe.length ? `🧹 Apagar todos os seguros (${fmt(total)})` : "🧹 Apagar todos os seguros";
    const chk = [...F.checked].map((id) => F.rows.find((r) => r.id === id)).filter(Boolean);
    const cb = $("#delchk");
    cb.hidden = !chk.length;
    cb.textContent = `🗑 Lixeira nos ${chk.length} marcados (${fmt(chk.reduce((a, r) => a + r.size, 0))})`;
    $("#count").textContent = F.scanning ? "" : `${rows.length} de ${F.rows.length} arquivos • ${chk.length} marcados`;
    $("#scan").disabled = F.scanning;
    $("#scan").textContent = F.scanning ? "Procurando…" : "🔍 Procurar";
  }

  async function trash(rows, what) {
    const locked = rows.filter((r) => r.level === "danger");
    if (locked.length) { toast("🔒 Tem arquivo protegido na seleção. Tire da seleção."); return; }
    const total = rows.reduce((a, r) => a + r.size, 0);
    const detail = rows.length === 1 ? `${rows[0].label}: ${rows[0].reason}\n\n${rows[0].path}` : `${rows.length} arquivos (${fmt(total)}).`;
    const ok = await confirmBox({ title: what, ok: "Mandar para a lixeira", danger: rows.some((r) => r.level === "care"),
      body: detail + "\n\nDá pra recuperar da lixeira do Windows." });
    if (!ok) return;
    busy(1);
    const res = await api.trash(rows.map((r) => r.path));
    busy(-1);
    const gone = new Set(res.done);
    F.rows = F.rows.filter((r) => !gone.has(r.path));
    F.checked = new Set([...F.checked].filter((id) => F.rows.some((r) => r.id === id)));
    renderList();
    toast(res.failed.length ? `⚠ ${res.done.length} ok, ${res.failed.length} falharam: ${res.failed[0].err}` : `✅ ${fmt(res.freed)} na lixeira`);
    api.info().then((i) => (window.INFO = i));
  }

  on("scan:progress", (d) => { F.progress = d.n < 0 ? "Avaliando o risco de cada arquivo…" : `Procurando… ${d.n.toLocaleString("pt-BR")} arquivos verificados`; renderList(); });
  on("scan:done", (rows) => { F.rows = rows; F.checked.clear(); F.scanning = false; F.sel = -1; busy(-1); renderList(); });

  return {
    mount(el) {
      el.innerHTML = `
        <div class="card bar2">
          <div class="fld"><label for="root">Onde procurar</label>
            <select id="root">${((window.INFO && window.INFO.drives) || ["C:\\"]).map((d) => `<option ${d === F.root ? "selected" : ""}>${esc(d)}</option>`).join("")}</select></div>
          <div class="fld"><label for="min">Tamanho mínimo</label>
            <select id="min">${[50, 100, 500, 1024].map((m) => `<option value="${m}" ${m === F.min ? "selected" : ""}>maiores que ${m >= 1024 ? "1 GB" : m + " MB"}</option>`).join("")}</select></div>
          <button class="btn" id="scan">🔍 Procurar</button>
          <div class="fld grow"><label for="q">Filtrar resultados</label>
            <input class="search" id="q" placeholder="Nome ou pasta…" value="${esc(F.query)}"></div>
        </div>
        <div class="filters">
          ${[["", "Todos"], ["ok", "Seguros"], ["care", "Cuidado"], ["danger", "Perigo"]].map(([l, t]) => `<button class="chip ${F.level === l ? "on" : ""}" data-l="${l}">${t}</button>`).join("")}
          <span style="flex:1"></span>
          <button class="btn red" id="delchk" hidden></button>
          <button class="btn" id="delsafe" disabled>🧹 Apagar todos os seguros</button>
        </div>
        <div class="muted legend">SEGURO = o programa recria • CUIDADO = só você sabe • NÃO APAGUE = pode quebrar o Windows</div>
        <div class="card" style="flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden">
          <div class="head"><span></span><span>RISCO</span><span>ARQUIVO</span><span style="text-align:right">TAMANHO</span><span></span></div>
          <div class="list" id="list"></div>
        </div>
        <div class="muted" id="count"></div>`;
      $("#scan").onclick = () => {
        F.scanning = true; F.progress = "Procurando…"; F.rows = []; F.checked.clear();
        F.root = $("#root").value; F.min = +$("#min").value;
        busy(1); renderList();
        api.scan_files(F.root, F.min);
      };
      $("#q").oninput = (e) => { F.query = e.target.value; renderList(); };
      $$("[data-l]", el).forEach((c) => c.onclick = () => { F.level = c.dataset.l; $$("[data-l]", el).forEach((x) => x.classList.toggle("on", x === c)); renderList(); });
      $("#delsafe").onclick = () => trash(safeRows(), "Apagar todos os seguros");
      $("#delchk").onclick = () => trash([...F.checked].map((id) => F.rows.find((r) => r.id === id)).filter(Boolean), "Mandar marcados para a lixeira");
      $("#list").onclick = (e) => {
        const row = e.target.closest(".row");
        if (!row) return;
        const r = F.rows.find((x) => x.id === +row.dataset.id), a = e.target.dataset.a;
        if (a === "check") { F.checked.has(r.id) ? F.checked.delete(r.id) : F.checked.add(r.id); renderList(); }
        else if (a === "show") api.reveal(r.path);
        else if (a === "trash") trash([r], "Mandar para a lixeira");
        else { F.sel = r.id; $$(".row").forEach((x) => x.classList.toggle("sel", +x.dataset.id === r.id)); }
      };
      renderList();
    },
    info() { const s = $("#root"); if (s && window.INFO) s.innerHTML = window.INFO.drives.map((d) => `<option ${d === F.root ? "selected" : ""}>${esc(d)}</option>`).join(""); },
  };
})();

// ============================================================================ AJUSTES
Pages.settings = {
  mount(el) {
    const accents = ["#8b5cf6", "#4fd1e6", "#b043d1", "#22c55e", "#f59e0b", "#ef4444", "#ec4899", "#3b82f6"];
    el.innerHTML = `
      <div><h1>Ajustes</h1><div class="muted">Deixe o WebDark com a sua cara. Tudo muda na hora e fica salvo.</div></div>
      <div class="scroll">
        <h2>🆕 Atualizações</h2>
        <div class="card" style="padding:16px 18px"><div class="set" style="padding:0"><div class="t"><b>Você está na v${esc((window.INFO || {}).version || "")}</b>
          <div class="muted">O WebDark confere sozinho a cada 6 horas. Quando tem versão nova, aparece uma faixa no topo e um botão na lateral.</div></div>
          <button class="ghost" id="updcheck">🔄 Procurar agora</button></div></div>
        <h2>🎨 Aparência</h2>
        <div class="card" style="padding:16px 18px;display:flex;flex-direction:column;gap:16px">
          <div>Cor de destaque
            <div class="swatches" style="margin-top:10px" id="sw">${accents.map((c) => `<i style="background:${c}" data-c="${c}"></i>`).join("")}
              <input type="color" id="custom" title="Outra cor"></div></div>
          <div class="set" style="padding:0"><div class="t"><b>Blur (vidro fosco)</b><div class="muted">Desfoca o fundo atrás dos cartões e do menu.</div></div><div class="sw" id="s-blur"></div></div>
          <div class="set" style="padding:0"><div class="t"><b>Intensidade do blur</b></div><input type="range" id="r-blur" min="0" max="50"></div>
          <div class="set" style="padding:0"><div class="t"><b>Brilho colorido no fundo</b></div><div class="sw" id="s-glow"></div></div>
          <div class="set" style="padding:0"><div class="t"><b>Fonte</b></div>
            <select id="font"><option>Segoe UI</option><option>Georgia</option><option>Consolas</option><option>Arial</option></select></div>
          <div><button class="ghost" id="reset">↩ Voltar ao padrão</button></div>
        </div>
      </div>`;
    const sync = () => {
      $$("#sw i").forEach((i) => i.classList.toggle("on", i.dataset.c.toLowerCase() === theme.accent.toLowerCase()));
      $("#custom").value = theme.accent;
      $("#s-blur").classList.toggle("on", theme.blur);
      $("#s-glow").classList.toggle("on", theme.glow);
      $("#r-blur").value = theme.blurpx;
      $("#font").value = theme.font;
    };
    const change = (patch) => { applyTheme({ ...theme, ...patch }); saveTheme(); sync(); };
    $("#sw").onclick = (e) => { if (e.target.dataset.c) change({ accent: e.target.dataset.c }); };
    $("#custom").oninput = (e) => change({ accent: e.target.value });
    $("#s-blur").onclick = () => change({ blur: !theme.blur });
    $("#s-glow").onclick = () => change({ glow: !theme.glow });
    $("#r-blur").oninput = (e) => change({ blurpx: +e.target.value });
    $("#font").onchange = (e) => change({ font: e.target.value });
    $("#reset").onclick = () => change({ ...THEME_DEFAULT });
    $("#updcheck").onclick = async () => {
      const b = $("#updcheck"); b.disabled = true; b.textContent = "Procurando…";
      const r = await api.update_check_now();
      b.disabled = false; b.textContent = "🔄 Procurar agora";
      toast(r.found ? `🆕 Versão ${r.version} disponível! Veja a faixa no topo.` : "✅ Você já está na versão mais nova.");
      if (r.found) UPD_HIDDEN = false, updBanner();
    };
    sync();
  },
};
