// Telas: Saúde e Desempenho.
const isAdminNow = () => !!(window.INFO && window.INFO.admin);
const needAdmin = () => { if (isAdminNow()) return false; toast("Isso precisa de administrador. Use “Reabrir como administrador”."); return true; };
const LV = { ok: ["✔", "#4ade80"], care: ["⚠", "#fbbf24"], bad: ["✖", "#f87171"] };
const LV_TEXT = { ok: "SAUDÁVEL", care: "ATENÇÃO", bad: "RUIM" };
const PILL = { ok: "ok", care: "care", bad: "danger" };

// ===================================================================== SAÚDE
Pages.health = (() => {
  const S = { disks: null, diag: null, upd: null, updBusy: false, log: "", repairing: false, started: false };
  const REPAIRS = [["sfc", "🛠 Verificar arquivos do sistema (SFC)", "Procura arquivos do Windows corrompidos e conserta. Leva de 5 a 15 minutos.", true],
    ["dism", "🧰 Reparar a imagem do Windows (DISM)", "Baixa peças boas do Windows Update. Precisa de internet. Rode antes do SFC se ele falhar.", true],
    ["chkdsk", "💽 Verificar o disco (CHKDSK)", "Procura erros no sistema de arquivos sem precisar reiniciar.", true],
    ["dns", "🌐 Limpar cache de DNS", "Ajuda quando sites não abrem mesmo com a internet funcionando.", false]];

  function paint() {
    if (!$("#hd")) return;
    $("#hd").innerHTML = S.disks === null ? '<div class="muted">Lendo o disco…</div>' : !S.disks.length ? '<div class="muted">Não consegui ler os discos. Tente reabrir como administrador.</div>' :
      S.disks.map((d) => `<div class="card set"><span class="pill ${PILL[d.level]}">${LV_TEXT[d.level]}</span><div class="t"><b>${esc(d.name)}</b><div>${esc(d.headline)}</div>
        <div class="muted">${d.details.map(esc).join("  •  ")}</div></div></div>`).join("");
    $("#dg").innerHTML = S.diag === null ? '<div class="muted">Verificando… (uns segundos)</div>' :
      S.diag.map(([lv, t]) => `<div style="color:${LV[lv][1]};padding:2px 6px">${LV[lv][0]}  ${esc(t)}</div>`).join("");
    $("#upd").innerHTML = S.updBusy ? '<div class="muted">Procurando atualizações e drivers… (até 1 min)</div>' : !S.upd ? "" : (() => {
      const u = S.upd, rows = [];
      if (u.error) rows.push(["care", "Não consegui consultar o Windows Update: " + u.error]);
      else if (!u.updates.length) rows.push(["ok", "Nenhuma atualização pendente."]);
      else { rows.push(["care", `${u.updates.length} atualização(ões) pendente(s). Instale pelo Windows Update:`]);
        u.updates.forEach((x) => rows.push(["care", `   ${x.Title}  (${x.Driver ? "driver" : "Windows"}, ${fmt(x.Size || 0)}${x.Reboot ? " • pede reinicialização" : ""})`])); }
      if (u.drivers.length) { rows.push(["care", `${u.drivers.length} driver(s) com mais de 3 anos (estimativa pela data; procure no site do fabricante):`]);
        u.drivers.forEach((d) => rows.push(["care", `   ${d.DeviceName} — ${d.Manufacturer}, versão ${d.DriverVersion}, de ${d.Date}`])); }
      else rows.push(["ok", "Nenhum driver de vídeo, rede, áudio ou bluetooth com mais de 3 anos."]);
      return rows.map(([lv, t]) => `<div style="color:${LV[lv][1]};padding:2px 6px;white-space:pre-wrap">${LV[lv][0]}  ${esc(t)}</div>`).join("");
    })();
    $("#updbtn").disabled = S.updBusy;
    $("#hlog").textContent = S.log;
    $("#hlog").scrollTop = 1e9;
    $$("[data-r]").forEach((b) => (b.disabled = S.repairing));
  }
  on("health:disks", (d) => { S.disks = d; paint(); });
  on("health:diag", (d) => { S.diag = d; busy(-1); paint(); });
  on("health:upd", (u) => { S.upd = u; S.updBusy = false; busy(-1); paint(); });
  on("health:log", (l) => { S.log += l + "\n"; paint(); });
  on("health:repair_done", () => { S.repairing = false; busy(-1); S.log += "✅ Terminou.\n\n"; paint(); });

  return {
    mount(el) {
      el.innerHTML = head("Saúde", "Veja se o disco está bom, ache problemas no Windows e conserte.") + `<div class="scroll">
        <h2>💽 Saúde do disco</h2><div id="hd" style="display:flex;flex-direction:column;gap:10px"></div>
        <h2>🩺 Diagnóstico geral <button class="ghost" id="rd" style="margin-left:10px;padding:5px 12px">Rodar de novo</button></h2><div class="card" style="padding:12px 16px" id="dg"></div>
        <h2>🔄 Atualizações e drivers <span class="muted">(só avisa, não instala nada)</span></h2>
        <div><button class="ghost" id="updbtn">Verificar agora</button></div><div class="card" style="padding:10px 14px" id="upd" hidden></div>
        <h2>🔧 Consertar o Windows <span class="muted">(a maioria precisa de administrador)</span></h2>
        ${REPAIRS.map(([k, t, d]) => `<div class="card set"><button class="ghost" data-r="${k}" style="min-width:300px;text-align:left">${t}</button><span class="muted">${d}</span></div>`).join("")}
        <div class="logbox" id="hlog"></div></div>`;
      $("#rd").onclick = () => { S.diag = null; busy(1); paint(); api.health_scan(); };
      $("#updbtn").onclick = () => { S.updBusy = true; $("#upd").hidden = false; busy(1); paint(); api.updates_check(); };
      $$("[data-r]").forEach((b) => (b.onclick = async () => {
        const [k, title, , adm] = REPAIRS.find((r) => r[0] === b.dataset.r);
        if (adm && needAdmin()) return;
        S.repairing = true; S.log += `▶ ${title}… não feche o programa.\n`; busy(1); paint(); api.repair(k);
      }));
      $("#upd").hidden = !S.upd && !S.updBusy;
      paint();
    },
    show() { if (!S.started) { S.started = true; busy(1); api.health_scan(); } },
  };
})();

// ================================================================ DESEMPENHO
Pages.perf = (() => {
  const S = { plans: null, battery: false, tweaks: null, sys: null, clock: null, live: null, timer: null, log: "", opt: false };
  const QUICK = [["ultimate", "🚀 Desempenho máximo"], ["high", "⚡ Alto desempenho"], ["balanced", "⚖ Equilibrado"], ["saver", "🔋 Economia"]];
  const MIN = { "5 min": 5, "10 min": 10, "15 min": 15, "30 min": 30, "1 hora": 60, Nunca: 0 };
  const sw = (on, attr) => `<div class="sw ${on ? "on" : ""}" ${attr}></div>`;

  function paintPower() {
    const box = $("#plans");
    if (!box) return;
    box.innerHTML = !S.plans ? "" : S.plans.map((p) => `<div class="card set" style="padding:10px 16px"><b class="t">${esc(p.name)}</b>
      ${p.active ? '<span class="pill ok">ATIVO</span>' : `<button class="mini" data-guid="${esc(p.guid)}">Ativar</button>`}</div>`).join("");
    $("#phint").textContent = S.battery ? "Notebook: use Equilibrado na bateria. Alto desempenho gasta bateria rápido." : "PC de mesa: Alto desempenho não gasta bateria e deixa o PC mais ágil.";
  }
  function paintTweaks() {
    const box = $("#tw");
    if (box && S.tweaks) box.innerHTML = S.tweaks.map((t) => `<div class="card set" data-k="${t.key}"><div class="t"><b>${esc(t.name)}</b><div class="muted">${esc(t.desc)}</div></div>${sw(t.on, 'data-a="tw"')}</div>`).join("");
  }
  function paintSys() {
    const box = $("#sy");
    if (!box) return;
    if (!S.sys) { box.innerHTML = '<div class="muted">Lendo…</div>'; return; }
    box.innerHTML = S.sys.items.map((t) => `<div class="card set" data-k="${t.key}" style="${t.available ? "" : "opacity:.5"}"><div class="t"><b>${esc(t.name)}</b> <span class="tag q">CUIDADO</span><div class="muted">${esc(t.desc)}</div></div>
      ${t.available ? sw(t.on, 'data-a="sys"') : '<span class="muted">não existe neste Windows</span>'}</div>`).join("");
    const k = { SSD: "SSD", HDD: "HD" }[S.sys.kind] || "tipo de disco desconhecido";
    $("#trim").textContent = S.sys.trim === null ? `Disco do sistema: ${k}. Não consegui ler o estado do TRIM.` :
      S.sys.trim ? `Disco do sistema: ${k}. TRIM está ATIVO ✔` : `Disco do sistema: ${k}. TRIM está DESLIGADO. Em SSD isso deixa o disco mais lento com o tempo.`;
    $("#trimon").hidden = S.sys.trim !== false;
    $("#opt").disabled = S.opt;
    $("#plog").textContent = S.log;
  }
  function paintClock() {
    const c = S.clock;
    if (!$("#clk")) return;
    $("#clk").hidden = !c;
    if (!c) return;
    $("#cpuname").textContent = `${c.name}  •  clock base ${c.base} MHz  •  ${c.threads} threads`;
    $("#livetxt").textContent = S.live ? `⏱ ${(S.live.mhz / 1000).toFixed(2)} GHz   •   CPU em uso ${Math.round(S.live.util)}%` : "⏱ —";
    $("#mxl").textContent = `Clock máximo: ${$("#mx").value}%`;
    $("#mnl").textContent = `Clock mínimo: ${$("#mn").value}%`;
  }
  const loadAll = () => {
    api.power_info().then((r) => { S.plans = r.plans; S.battery = r.battery; paintPower(); });
    api.tweaks_list().then((t) => { S.tweaks = t; paintTweaks(); });
    api.systweaks_scan(); api.clock_info();
  };
  on("sys:state", (d) => { S.sys = d; paintSys(); });
  on("sys:applied", (d) => {
    const it = S.sys.items.find((x) => x.key === d.key);
    if (d.ok) { it.on = d.on; S.log += `✔ ${it.name}: ${d.on ? "aplicado" : "desfeito"}.${d.note ? "  🛟 " + d.note : ""}\n`; }
    else { toast("⚠ Não consegui mudar: " + d.msg); }
    paintSys();
  });
  on("perf:log", (l) => { S.log += l + "\n"; paintSys(); });
  on("perf:opt_done", () => { S.opt = false; busy(-1); S.log += "✅ Terminou.\n"; paintSys(); });
  on("perf:clock", (c) => {
    S.clock = c; paintClock();
    const s = c.snap;
    if (s.max !== null) { $("#mx").value = Math.max(20, s.max); $("#mn").value = s.min !== null ? s.min : 5; }
    $("#bst").innerHTML = Object.keys(c.boost_modes).map((k) => `<option>${esc(k)}</option>`).join("");
    const inv = Object.entries(c.boost_modes).find(([, v]) => v === s.boost);
    $("#bst").value = inv ? inv[0] : "Normal";
    $("#bstrow").hidden = s.boost === null;
    $("#frq").value = !s.freq ? "0" : String(s.freq);
    if (s.freq && ![...$("#frq").options].some((o) => o.value === String(s.freq))) $("#frq").add(new Option(s.freq + " MHz", String(s.freq)), null), $("#frq").value = String(s.freq);
    $("#frqrow").hidden = s.freq === null;
    paintClock();
  });

  function clockApply(mn, mx, boost, mhz) {
    const c = S.clock, snap = c.snap;
    api.clock_apply(mn, mx, snap.boost === null ? null : boost, snap.freq === null ? null : mhz);
    toast("✅ Clock aplicado no plano ativo");
  }

  return {
    mount(el) {
      el.innerHTML = head("Desempenho", "Plano de energia, clock da CPU e ajustes do Windows. Tudo dá pra desfazer.") + `<div class="scroll">
        <h2>🔋 Plano de energia</h2><div class="muted" id="phint"></div>
        <div class="tools">${QUICK.map(([k, t]) => `<button class="ghost" data-q="${k}">${t}</button>`).join("")}</div>
        <div id="plans" style="display:flex;flex-direction:column;gap:6px"></div>
        <div class="card set"><span>Tela desliga após</span><select id="tmon">${Object.keys(MIN).map((k) => `<option ${k === "10 min" ? "selected" : ""}>${k}</option>`).join("")}</select>
          <span>PC dorme após</span><select id="tslp">${Object.keys(MIN).map((k) => `<option ${k === "30 min" ? "selected" : ""}>${k}</option>`).join("")}</select>
          <span style="flex:1"></span><button class="btn" id="tapply">Aplicar</button></div>

        <div id="clk" hidden><h2>🧠 Controle de clock da CPU</h2><div class="muted" id="cpuname"></div>
          <div style="font-size:22px;font-weight:700;margin:4px 0" id="livetxt">⏱ —</div>
          <div class="tools" id="presets"></div>
          <div class="card" style="padding:14px 18px;display:flex;flex-direction:column;gap:12px">
            <div class="set" style="padding:0"><span id="mxl" style="width:200px"></span><input type="range" id="mx" min="20" max="100" value="100" style="flex:1;width:auto"></div>
            <div class="set" style="padding:0"><span id="mnl" style="width:200px"></span><input type="range" id="mn" min="0" max="100" value="5" style="flex:1;width:auto"></div>
            <div class="set" style="padding:0" id="bstrow"><span style="width:200px">Turbo</span><select id="bst"></select></div>
            <div class="set" style="padding:0" id="frqrow"><span style="width:200px">Limite de frequência</span><select id="frq"><option value="0">Sem limite</option>
              ${[1500, 2000, 2500, 3000, 3500, 4000].map((m) => `<option value="${m}">${m} MHz</option>`).join("")}</select></div>
            <div><button class="btn" id="capply">Aplicar no plano ativo</button> <button class="ghost" id="creset">Voltar ao padrão</button></div>
          </div>
          <div class="muted">Máximo abaixo de 100% desliga o turbo: a CPU fica mais fria e silenciosa, mas mais lenta. Vale pro plano ativo. Alguns notebooks ignoram.</div></div>

        <h2>🛠 Ajustes do Windows</h2><div class="muted">Ligado = ajuste aplicado. Desligue o interruptor para voltar ao padrão do Windows.</div>
        <div id="tw" style="display:flex;flex-direction:column;gap:10px"></div>

        <h2>🔧 Ajustes de sistema <span class="muted">(mexem no Windows, com aviso e precisam de administrador)</span></h2>
        <div class="muted">Antes de aplicar, mostro o que muda, o que pode dar errado e como desfazer. Crio um ponto de restauração antes do primeiro ajuste.</div>
        <div id="sy" style="display:flex;flex-direction:column;gap:10px"></div>
        <div class="card" style="padding:14px 18px;display:flex;flex-direction:column;gap:10px"><b>💽 Otimizar unidades (TRIM)</b><span class="muted" id="trim"></span>
          <div><button class="ghost" id="trimon" hidden>Ativar TRIM</button> <button class="ghost" id="opt">Otimizar o C: agora</button></div></div>
        <div class="logbox" id="plog"></div></div>`;

      $$("[data-q]").forEach((b) => (b.onclick = async () => { busy(1); const ok = await api.power_quick(b.dataset.q); busy(-1);
        if (!ok) toast("Seu PC não aceita esse plano de energia."); api.power_info().then((r) => { S.plans = r.plans; paintPower(); }); }));
      $("#plans").onclick = async (e) => { const g = e.target.dataset.guid; if (!g) return; await api.power_set(g); api.power_info().then((r) => { S.plans = r.plans; paintPower(); }); };
      $("#tapply").onclick = async () => { await api.power_timeouts(MIN[$("#tmon").value], MIN[$("#tslp").value]); toast("Tempos aplicados no plano ativo."); };

      $("#tw").onclick = async (e) => {
        if (e.target.dataset.a !== "tw") return;
        const t = S.tweaks.find((x) => x.key === e.target.closest("[data-k]").dataset.k), want = !t.on;
        const ok = await api.tweak_set(t.key, want);
        if (ok) t.on = want; else toast("⚠ Não consegui aplicar.");
        paintTweaks();
      };
      $("#sy").onclick = async (e) => {
        if (e.target.dataset.a !== "sys") return;
        const t = S.sys.items.find((x) => x.key === e.target.closest("[data-k]").dataset.k), want = !t.on;
        if (needAdmin()) return;
        if (want && !await confirmBox({ title: "Mexer no sistema", body: t.warning, ok: "Aplicar", danger: true })) return;
        busy(1); await api.systweak_set(t.key, want); busy(-1);
      };
      $("#trimon").onclick = async () => {
        if (needAdmin()) return;
        if (!await confirmBox({ title: "Ativar o TRIM?", body: "O TRIM avisa o SSD quais blocos não são mais usados. Só faz sentido em SSD e normalmente já vem ligado.\n\nPra desligar de novo: fsutil behavior set DisableDeleteNotify 1", ok: "Ativar" })) return;
        toast((await api.trim_enable()) ? "✔ TRIM ativado." : "✖ Não consegui ativar o TRIM."); api.systweaks_scan();
      };
      $("#opt").onclick = async () => {
        if (needAdmin()) return;
        const kind = S.sys && S.sys.kind;
        const body = kind === "SSD" ? "Vou rodar o TRIM no SSD (C:). É rápido e seguro." :
          kind === "HDD" ? "Seu disco é um HD, então vou DESFRAGMENTAR o C:.\n\n⚠ Demora de minutos a horas, o PC fica lento nesse tempo e você NÃO deve desligar nem fechar o programa até terminar." :
          "Não sei se é SSD ou HD, então só vou ANALISAR o C: (não muda nada).";
        if (!await confirmBox({ title: "Otimizar o C:", body, ok: "Continuar", danger: kind === "HDD" })) return;
        S.opt = true; S.log += "▶ Otimizando o C:… não feche o programa.\n"; busy(1); paintSys(); api.optimize_disk();
      };

      // clock
      const sync = (src) => { const mx = $("#mx"), mn = $("#mn"); if (+mn.value > +mx.value) { if (src === "mx") mn.value = mx.value; else mx.value = mn.value; } paintClock(); };
      $("#mx").oninput = () => sync("mx"); $("#mn").oninput = () => sync("mn");
      const apply = () => clockApply(+$("#mn").value, +$("#mx").value, S.clock.boost_modes[$("#bst").value], +$("#frq").value);
      $("#capply").onclick = apply;
      const preset = (name) => { const [mn, mx, boost, mhz] = S.clock.presets[name]; $("#mn").value = mn; $("#mx").value = mx;
        $("#bst").value = Object.entries(S.clock.boost_modes).find(([, v]) => v === boost)[0]; $("#frq").value = String(mhz); paintClock(); clockApply(mn, mx, boost, mhz); };
      $("#creset").onclick = () => S.clock && preset("⚖ Normal");
      $("#clk").addEventListener("click", (e) => { if (e.target.dataset.p) preset(e.target.dataset.p); });
      paintPower(); paintTweaks(); paintSys();
      if (S.clock) { $("#clk").hidden = false; $("#presets").innerHTML = Object.keys(S.clock.presets).map((n) => `<button class="ghost" data-p="${esc(n)}">${esc(n)}</button>`).join(""); paintClock(); }
    },
    show() {
      loadAll();
      const tickLive = () => { if (S.clock) api.clock_live().then((r) => { S.live = r; paintClock(); }); };
      S.timer = setInterval(tickLive, 3000);
      const waitPresets = setInterval(() => { if (S.clock && $("#presets") && !$("#presets").children.length) {
        $("#presets").innerHTML = Object.keys(S.clock.presets).map((n) => `<button class="ghost" data-p="${esc(n)}">${esc(n)}</button>`).join(""); clearInterval(waitPresets); } }, 500);
      setTimeout(() => clearInterval(waitPresets), 20000);
    },
    unmount() { clearInterval(S.timer); },
  };
})();
