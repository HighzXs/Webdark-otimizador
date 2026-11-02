// Tela Rede (aba de Velocidade): Wi-Fi e adaptadores, melhor DNS, Otimização de Entrega, limite por programa, drivers e reparos.
Pages.net = (() => {
  const S = { scan: null, loading: false, loadAt: 0, dns: null, dnsBusy: false, dnsProg: "", apps: null, drivers: null, drvUpd: null, drvBusy: false, log: "", repairing: false };
  const alive = () => current === "net";
  const isAdmin = () => !!(window.INFO && window.INFO.admin);
  const ok = (r) => { if (r && r.ok === false) { toast("⚠ " + r.msg); return false; } return true; };
  const adminTag = () => (isAdmin() ? "" : ' <span class="tag q">PRECISA DE ADMIN</span>');
  const card = (id, title, sub, body = "") => `<h2>${title}${sub ? ` <span class="muted" style="font-weight:400">${sub}</span>` : ""}</h2><div class="card" id="${id}" style="padding:14px 18px">${body}</div>`;

  // ------------------------------------------------------------ Wi-Fi e adaptadores
  function signalVerdict(s) {
    if (s >= 70) return ["Excelente", "#4ade80"];
    if (s >= 45) return ["Bom", "#a3e635"];
    if (s >= 25) return ["Fraco: chegue mais perto do roteador ou use a rede de 5 GHz", "#fbbf24"];
    return ["Muito fraco: a conexão vai cair e travar", "#f87171"];
  }
  function paintWifi() {
    const box = $("#n-wifi");
    if (!box) return;
    const d = S.scan;
    if (!d) { box.innerHTML = '<div class="muted">Lendo os adaptadores…</div>'; return; }
    let html = d.adapters.map((a) => `<div class="drv"><span style="flex:1;min-width:0"><b>${a.PhysicalMediaType === "802.3" ? "🔌" : "📶"} ${esc(a.Name)}</b>
      <span class="muted">${esc(a.InterfaceDescription)}</span></span><span class="muted">${esc(a.LinkSpeed)}</span>
      <span class="pill ${a.Status === "Up" ? "ok" : "care"}">${a.Status === "Up" ? "LIGADO" : "DESCONECTADO"}</span></div>`).join("") || '<div class="muted">Nenhum adaptador de rede encontrado.</div>';
    const w = d.wifi;
    if (w && w.status === "ok") {
      const [txt, col] = signalVerdict(w.signal);
      html += `<div style="margin-top:10px"><b>Sinal do Wi-Fi “${esc(w.ssid)}”: ${w.signal}%</b> <span style="color:${col}">${esc(txt)}</span>
        <div class="meter" style="margin:8px 0"><i style="width:${w.signal}%;background:${col}"></i></div>
        <div class="muted">Velocidade de conexão: ${w.rx} Mbps recebendo • ${w.tx} Mbps enviando${w.radio ? " • " + esc(w.radio) : ""}</div></div>`;
    } else if (w && w.status === "blocked") {
      // sem Localização o Windows não entrega a % do sinal (nem como administrador); a velocidade do adaptador, acima, continua valendo
      html += `<div class="set" style="margin-top:10px;padding:8px 0"><div class="t muted">O Windows não mostra a % do sinal do Wi-Fi sem a Localização ligada (o app não usa a sua localização). Sem ela, use a velocidade de conexão de cada adaptador, na lista acima: quanto mais perto do máximo do seu Wi-Fi, melhor o sinal.</div>
        <button class="ghost" id="n-loc">Abrir Localização</button></div>`;
    }
    if (d.txpower.length) {
      html += '<div style="margin-top:12px"><b>Potência de transmissão do Wi-Fi</b>' + d.txpower.map((t, i) => `<div class="set" style="padding:8px 0">
        <div class="t"><b>${esc(t.DisplayName)}</b> <span class="muted">(${esc(t.Name)}) • agora: ${esc(t.DisplayValue)}</span>
        ${/ibss/i.test(t.RegistryKeyword) ? '<div class="muted">Em adaptadores Intel essa opção costuma valer só pro modo “ad hoc” (Wi-Fi direto entre dois aparelhos). No Wi-Fi comum o driver já ajusta a potência sozinho.</div>' : ""}</div>
        <select data-tx="${i}">${t.valid.map((v) => `<option ${v === t.DisplayValue ? "selected" : ""}>${esc(v)}</option>`).join("")}</select>
        <button class="ghost" data-txgo="${i}">Aplicar${adminTag()}</button></div>`).join("") + "</div>";
    } else if (d.adapters.some((a) => a.PhysicalMediaType !== "802.3")) {
      html += '<div class="muted" style="margin-top:10px">O driver do seu Wi-Fi não deixa mudar a potência de transmissão (isso é normal).</div>';
    }
    box.innerHTML = html;
    const loc = $("#n-loc");
    if (loc) loc.onclick = () => api.net_open("location");
    $$("[data-txgo]", box).forEach((b) => (b.onclick = async () => {
      const t = d.txpower[+b.dataset.txgo], v = $(`[data-tx="${b.dataset.txgo}"]`).value;
      if (!await confirmBox({ title: "Mudar a potência do Wi-Fi?", body: `${t.DisplayName}: ${t.DisplayValue} → ${v}\n\nO Wi-Fi pode piscar por um instante. Potência mais alta gasta mais bateria e esquenta o adaptador um pouco.`, ok: "Aplicar" })) return;
      busy(1); const r = await api.net_tx_set(t.Name, t.RegistryKeyword, v); busy(-1);
      if (ok(r)) { toast("✅ " + r.msg); load(); }
    }));
  }

  // ------------------------------------------------------------------- DNS
  function paintDns() {
    const box = $("#n-dns");
    if (!box) return;
    const now = S.scan && S.scan.dns_now && S.scan.dns_now.length ? S.scan.dns_now.map((c) => `${esc(c.name)}: ${esc([].concat((c.servers && c.servers.value) || c.servers || []).join(", ") || "automático")}`).join(" • ") : "…";
    let html = `<div class="muted">DNS é a “agenda telefônica” da internet: quanto mais rápido ele responde, mais rápido os sites começam a abrir. Seu DNS agora: ${now}</div>
      <div class="tools" style="margin-top:12px"><button class="btn" id="n-dnstest" ${S.dnsBusy ? "disabled" : ""}>${S.dnsBusy ? esc(S.dnsProg || "Testando…") : "⚡ Testar e achar o melhor"}</button>
        <button class="ghost" id="n-dnsreset">↩ Voltar ao automático${adminTag()}</button></div>`;
    if (S.dns) {
      const res = S.dns.results, worst = Math.max(...res.map((r) => r.ms || 0), 1), best = res.find((r) => r.ms !== null);
      if (!best) html += '<div class="muted" style="margin-top:12px">Nenhum servidor respondeu. Sem internet ou a rede bloqueia consulta de DNS.</div>';
      else {
        const used = res.find((r) => r.in_use && r.ms !== null);
        html += `<div style="margin-top:12px"><b>🏆 Mais rápido: ${esc(best.name)} (${best.ms} ms)</b>${used && used !== best && used.ms > best.ms * 1.15 ? ` <span class="muted">• o seu responde em ${used.ms} ms: dá pra ganhar uns ${Math.round(used.ms - best.ms)} ms por consulta</span>` : ""}</div>
        <div style="margin-top:6px">${res.map((r, i) => `<div class="row slim" style="--cols:1fr 200px 80px 130px" data-i="${i}"><div style="min-width:0"><div class="name">${i === 0 && r.ms !== null ? "🏆 " : ""}${esc(r.name)}${r.in_use ? ' <span class="tag keep">EM USO</span>' : ""}</div><div class="why">${esc(r.note)} • ${esc(r.primary)}</div></div>
          <div class="meter"><i style="width:${r.ms === null ? 0 : Math.max(4, (r.ms / worst) * 100)}%"></i></div><div class="size">${r.ms === null ? "falhou" : r.ms + " ms"}</div>
          <div class="acts" style="opacity:1">${r.kind === "list" && r.ms !== null ? `<button class="mini" data-use="${i}">Usar este</button>` : ""}</div></div>`).join("")}</div>`;
        if (best.kind === "list") html += `<div class="tools" style="margin-top:8px"><button class="btn" id="n-dnsbest">✔ Usar o mais rápido (${esc(best.name)})${adminTag()}</button></div>`;
      }
    }
    box.innerHTML = html;
    $("#n-dnstest").onclick = () => { S.dnsBusy = true; S.dnsProg = "Testando…"; busy(1); paintDns(); api.net_dns_test(); };
    $("#n-dnsreset").onclick = async () => {
      if (!await confirmBox({ title: "Voltar o DNS ao automático?", body: "O seu PC volta a usar o DNS que o roteador/provedor manda. A conexão pode cair por 1 ou 2 segundos.", ok: "Voltar ao automático" })) return;
      busy(1); const r = await api.net_dns_reset(); busy(-1);
      if (ok(r)) { toast("✅ " + r.msg); load(); }
    };
    const useDns = async (r) => {
      if (!await confirmBox({ title: `Usar o DNS ${r.name}?`, body: `Vou trocar o DNS dos adaptadores ligados para ${r.primary}${r.secondary ? " e " + r.secondary : ""}.\n\nA conexão pode cair por 1 ou 2 segundos. Dá pra voltar ao automático quando quiser. Redes de empresa e alguns provedores dependem do DNS deles: se algum site parar de abrir, volte ao automático.`, ok: "Trocar o DNS" })) return;
      busy(1); const res = await api.net_dns_set(r.primary, r.secondary); busy(-1);
      if (ok(res)) { toast("✅ " + res.msg); load(); }
    };
    $$("[data-use]", box).forEach((b) => (b.onclick = () => useDns(S.dns.results[+b.dataset.use])));
    const bb = $("#n-dnsbest");
    if (bb) bb.onclick = () => useDns(S.dns.results.find((r) => r.ms !== null));
  }
  on("net:dns_progress", (d) => { S.dnsProg = `Testando… ${d.n}/${d.total}`; const b = $("#n-dnstest"); if (b) b.textContent = S.dnsProg; });
  on("net:dns", (d) => { S.dns = d; S.dnsBusy = false; busy(-1); paintDns(); });

  // ----------------------------------------------- Otimização de Entrega do Windows
  function paintDelivery() {
    const box = $("#n-do");
    if (!box || !S.scan) return;
    const d = S.scan.delivery || { p2p_off: false, cap: 0 };
    box.innerHTML = `<div class="set" style="padding:0"><div class="t"><b>Não repassar atualizações para outros PCs</b>${adminTag()}
        <div class="muted">Por padrão o Windows pode usar a sua internet pra mandar pedaços de atualização pra outros computadores. Desligar economiza sua banda de upload. As atualizações continuam chegando normalmente da Microsoft.</div></div>
        <div class="sw ${d.p2p_off ? "on" : ""}" id="n-p2p"></div></div>
      <div class="set" style="padding:12px 0 0"><div class="t"><b>Limitar o download de atualizações em segundo plano</b>${adminTag()}
        <div class="muted">Windows Update e Microsoft Store passam a usar no máximo essa parte da sua internet quando baixam sozinhos. Vale no próximo download.</div></div>
        <select id="n-cap">${[[0, "Sem limite"], [10, "10%"], [25, "25%"], [50, "50%"], [75, "75%"]].map(([v, t]) => `<option value="${v}" ${v === d.cap ? "selected" : ""}>${t}</option>`).join("")}</select></div>`;
    const apply = async (patch) => {
      busy(1); const r = await api.net_delivery_set(patch.p2p_off === undefined ? null : patch.p2p_off, patch.cap === undefined ? null : patch.cap); busy(-1);
      if (!alive()) return;
      if (ok(r)) { S.scan.delivery = { p2p_off: r.p2p_off, cap: r.cap }; toast("✅ " + r.msg); }
      paintDelivery();
    };
    $("#n-p2p").onclick = () => apply({ p2p_off: !d.p2p_off });
    $("#n-cap").onchange = (e) => apply({ cap: +e.target.value });
  }

  // --------------------------------------------------- limite de programas (QoS)
  function paintLimits() {
    const box = $("#n-lim");
    if (!box) return;
    const lim = S.scan ? S.scan.limits : [];
    let html = `<div class="card adminnote" style="border-color:rgba(248,113,113,.6);background:rgba(220,38,38,.1)"><div class="t"><b>⚠ Cuidado: isso pode causar instabilidade</b>
      <div class="muted">O limite segura o que o programa ENVIA (upload) e marca o tráfego dele como de baixa prioridade. O Windows não limita o que ele baixa. Se limitar demais, o programa fica lento, chamadas de vídeo e jogos online podem travar ou cair. Não limite navegador de trabalho, jogos nem o que você está usando agora. O limite vale até reiniciar o PC ou até você remover aqui.</div></div></div>
      <div class="tools" style="margin-top:10px"><button class="ghost" id="n-apps">🔄 Ver quem está usando a internet agora</button></div>`;
    if (S.apps) {
      html += S.apps.length ? `<div style="margin-top:6px">${S.apps.map((a, i) => `<div class="row slim" style="--cols:1fr 170px 130px 110px"><div style="min-width:0"><div class="name">${esc(a.name)}</div><div class="why">${a.conns} ${a.conns === 1 ? "conexão" : "conexões"} • ${a.hosts} ${a.hosts === 1 ? "servidor" : "servidores"} • ${fmt(a.mem)} de memória</div></div>
        <select data-lim="${i}">${[[64, "64 KB/s (bem lento)"], [128, "128 KB/s"], [256, "256 KB/s"], [512, "512 KB/s"], [1024, "1 MB/s"], [2048, "2 MB/s"]].map(([v, t]) => `<option value="${v}" ${v === 256 ? "selected" : ""}>${t}</option>`).join("")}</select>
        <div></div><div class="acts" style="opacity:1"><button class="mini red" data-limgo="${i}">Limitar</button></div></div>`).join("")}</div>` : '<div class="muted" style="margin-top:10px">Nenhum programa com conexão aberta agora.</div>';
    }
    if (lim.length) {
      html += `<h2 style="margin-top:14px">Limites ativos</h2>${lim.map((l) => `<div class="drv"><span style="flex:1"><b>${esc(l.AppPathNameMatchCondition)}</b>
        <span class="muted">• envio até ${Math.round(l.ThrottleRateActionBitsPerSecond / 8 / 1024)} KB/s</span></span><button class="mini" data-unlim="${esc(l.Name)}">Remover limite</button></div>`).join("")}`;
    }
    box.innerHTML = html;
    $("#n-apps").onclick = async () => {
      busy(1); const a = await api.net_apps(); busy(-1);
      if (!alive()) return;
      S.apps = a; paintLimits();
    };
    $$("[data-limgo]", box).forEach((b) => (b.onclick = async () => {
      const a = S.apps[+b.dataset.limgo], kb = +$(`[data-lim="${b.dataset.limgo}"]`).value;
      if (!await confirmBox({ title: `Limitar ${a.name}?`, body: `O envio dele fica limitado a ${kb} KB/s e o tráfego vira de baixa prioridade.\n\nPode deixar o programa lento ou instável. Vale até reiniciar o PC. Você remove o limite na mesma tela.`, ok: "Limitar", danger: true })) return;
      busy(1); const r = await api.net_limit(a.name, kb); busy(-1);
      if (!alive()) return;
      if (ok(r)) { S.scan.limits = r.limits; toast("✅ " + r.msg); paintLimits(); }
    }));
    $$("[data-unlim]", box).forEach((b) => (b.onclick = async () => {
      busy(1); const r = await api.net_unlimit(b.dataset.unlim); busy(-1);
      if (!alive()) return;
      if (ok(r)) { S.scan.limits = r.limits; toast("✅ " + r.msg); paintLimits(); }
    }));
  }

  // --------------------------------------------------------------- drivers
  function paintDrivers() {
    const box = $("#n-drv");
    if (!box) return;
    let html = S.drivers === null ? '<div class="muted">Lendo os drivers de rede…</div>' : S.drivers.length ? S.drivers.map((d, i) => `<div class="row slim" style="--cols:1fr 100px 170px 140px" data-d="${i}"><div style="min-width:0"><div class="name">${esc(d.DeviceName)}</div>
        <div class="why">${esc(d.Manufacturer)} • versão ${esc(d.DriverVersion)}</div></div><div class="why">${esc(d.date)}</div>
        <div><span class="pill ${d.age > 3 ? "care" : "ok"}">${d.age > 3 ? "ANTIGO • " : ""}${d.age.toFixed(1).replace(".", ",")} anos</span></div>
        <div class="acts" style="opacity:1"><button class="mini" data-find="${i}">Procurar no site</button></div></div>`).join("") : '<div class="muted">Nenhum driver de rede de fabricante encontrado.</div>';
    html += `<div class="tools" style="margin-top:10px"><button class="ghost" id="n-drvupd" ${S.drvBusy ? "disabled" : ""}>${S.drvBusy ? "Procurando… (até 1 min)" : "🔎 Procurar drivers no Windows Update"}</button>
      <button class="btn" id="n-drvwu">⬇ Baixar drivers pelo Windows Update</button><button class="ghost" id="n-devmgr">🛠 Gerenciador de Dispositivos</button></div>`;
    if (S.drvUpd) {
      html += S.drvUpd.error ? `<div class="muted" style="margin-top:10px">Não consegui consultar o Windows Update: ${esc(S.drvUpd.error)}</div>`
        : S.drvUpd.updates.length ? `<div style="margin-top:10px"><b>O Windows Update tem ${S.drvUpd.updates.length} item(ns) de driver/rede esperando:</b>${S.drvUpd.updates.map((u) => `<div class="why" style="white-space:normal">• ${esc(u.Title)} (${fmt(u.Size)})</div>`).join("")}
          <div class="muted">Clique em “Baixar drivers pelo Windows Update” pra instalar.</div></div>`
        : `<div class="muted" style="margin-top:10px">✅ O Windows Update não tem driver de rede novo pra você (de ${S.drvUpd.total} atualização(ões) pendente(s) no total).</div>`;
    }
    box.innerHTML = html;
    $$("[data-find]", box).forEach((b) => (b.onclick = () => api.net_driver_search(S.drivers[+b.dataset.find].DeviceName)));
    $("#n-drvupd").onclick = () => { S.drvBusy = true; busy(1); paintDrivers(); api.net_driver_updates(); };
    $("#n-drvwu").onclick = () => { api.net_open("wu"); toast("Abrindo o Windows Update. Os drivers ficam em “Atualizações opcionais”."); };
    $("#n-devmgr").onclick = () => api.net_open("devmgr");
  }
  on("net:drivers", (d) => { S.drivers = d; paintDrivers(); });
  on("net:drvupd", (d) => { S.drvUpd = d; S.drvBusy = false; busy(-1); paintDrivers(); });

  // ---------------------------------------------------------------- reparos
  function paintRepair() {
    const box = $("#n-fix");
    if (!box) return;
    box.innerHTML = `<div class="muted">Internet lenta, caindo ou “sem acesso”? Estes comandos do próprio Windows resolvem a maioria dos casos. Cada um mostra o que está fazendo no quadro abaixo.</div>
      <div class="tools" style="margin-top:12px">
        <button class="btn" data-fix="renew" ${S.repairing ? "disabled" : ""}>🔄 Renovar conexão e limpar DNS</button>
        <button class="ghost" data-fix="reset" ${S.repairing ? "disabled" : ""}>🧰 Resetar a pilha de rede${adminTag()}</button>
        <button class="ghost" data-fix="all" ${S.repairing ? "disabled" : ""}>🛠 Reparo completo${adminTag()}</button></div>
      <div class="muted" style="margin-top:8px"><code>ipconfig /release</code> • <code>ipconfig /renew</code> • <code>ipconfig /flushdns</code> • <code>netsh int ip reset</code> • <code>netsh winsock reset</code></div>
      <div class="logbox" id="n-log" style="margin-top:10px"></div>`;
    $("#n-log").textContent = S.log;
    $$("[data-fix]", box).forEach((b) => (b.onclick = async () => {
      const kind = b.dataset.fix;
      const text = {
        renew: ["Renovar a conexão?", "Vou soltar o IP, pedir um novo e limpar o cache de DNS. A internet cai por alguns segundos. Salve downloads e pare chamadas de vídeo ou jogos online antes."],
        reset: ["Resetar a pilha de rede?", "Roda netsh int ip reset e netsh winsock reset. Isso apaga IP fixo e ajustes de rede (inclusive de alguns VPNs e proxies) e você PRECISA reiniciar o PC depois. Só vale a pena se a internet está com problema e os outros reparos não resolveram."],
        all: ["Fazer o reparo completo?", "Renova a conexão e depois reseta a pilha de rede (os 5 comandos). A internet cai e você PRECISA reiniciar o PC no fim. Use quando nada mais resolveu."],
      }[kind];
      if (!await confirmBox({ title: text[0], body: text[1], ok: "Executar", danger: kind !== "renew" })) return;
      if (kind !== "renew" && !isAdmin()) return toast("Precisa de administrador. Use “Reabrir como administrador”.");
      S.repairing = true; S.log = ""; busy(1); paintRepair();
      if (!await api.net_repair(kind)) { S.repairing = false; busy(-1); paintRepair(); toast("⚠ Não consegui começar."); }
    }));
  }
  on("net:log", (l) => { S.log += l + "\n"; const b = $("#n-log"); if (b) { b.textContent = S.log; b.scrollTop = 1e9; } });
  on("net:repair_done", () => { S.repairing = false; busy(-1); S.log += "\n✅ Terminou.\n"; paintRepair(); });

  // ----------------------------------------------------------------- tela
  // cada seção isolada: uma falha não pode derrubar as outras
  const paintAll = () => {
    for (const paint of [paintWifi, paintDns, paintDelivery, paintLimits, paintDrivers, paintRepair]) {
      try { paint(); } catch (e) { console.error(paint.name, e); }
    }
  };
  async function load() {
    if (S.loading && Date.now() - S.loadAt < 45000) return;      // 45 s sem resposta: a leitura anterior travou, tenta de novo
    if (!S.loading) busy(1);
    S.loading = true; S.loadAt = Date.now();
    try {
      S.scan = await api.net_scan();                              // o cache (S.scan) só é trocado se a leitura der certo
    } catch (e) {
      console.error("net_scan", e);
    } finally {
      S.loading = false; busy(-1);
    }
    if (alive()) paintAll();
  }
  // Ao voltar de minimizado o WebView pode ter pausado: repinta do cache na hora e confere se está atualizado
  document.addEventListener("visibilitychange", () => {
    if (document.hidden || !alive() || !$("#n-wifi")) return;
    paintAll();
    if (!S.scan || Date.now() - (S.loadAt || 0) > 30000) load();
  });

  return {
    mount(el) {
      el.innerHTML = head("Rede", "Deixe a internet mais rápida e estável. Mexe só em ajustes do Windows e dá pra desfazer tudo.") + `<div class="scroll">
        ${card("n-wifi", "📶 Wi-Fi e adaptadores", "")}
        ${card("n-dns", "🌍 Melhor DNS", "")}
        ${card("n-do", "📦 Otimização de Entrega do Windows", "")}
        ${card("n-lim", "🐢 Limitar programas em segundo plano", "")}
        ${card("n-drv", "🧩 Drivers de rede", "")}
        ${card("n-fix", "🔧 Reparar a rede", "")}</div>`;
      paintAll();
    },
    show() {
      load();
      if (S.drivers === null) api.net_drivers();
    },
  };
})();
