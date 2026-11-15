// Tela Jogos (aba de Velocidade): verificação do que tem efeito comprovado no FPS e costuma estar errado sem a pessoa saber.
// Placa certa no notebook, driver de vídeo, taxa do monitor, XMP da RAM, integridade de memória, HAGS e Modo de Jogo.
Pages.game = (() => {
  const S = { d: null, loading: false };
  const alive = () => current === "game";
  const isAdmin = () => !!(window.INFO && window.INFO.admin);
  const ok = (r) => { if (r && r.ok === false) { toast("⚠ " + r.msg); return false; } return true; };
  const adminTag = () => (isAdmin() ? "" : ' <span class="tag q">PRECISA DE ADMIN</span>');
  const act = async (fn) => { busy(1); try { return await fn(); } finally { busy(-1); } };
  // nível de cada item: a cor só aparece no pontinho de status (vermelho = tira FPS, amarelo = vale ver)
  const LV = { bad: ["#f87171", "Tira FPS"], care: ["#fbbf24", "Vale ver"], ok: ["#4ade80", "Certo"], info: ["#8d8da8", "Informação"] };
  const item = (lv, title, body, tools = "") => ({ lv, html: `<div class="gc-row"><i class="gc-dot" style="background:${LV[lv][0]}" title="${LV[lv][1]}"></i>
      <div class="gc-txt"><b>${title}</b><div class="muted">${body}</div></div>${tools ? `<div class="gc-acts">${tools}</div>` : ""}</div>` });
  const ago = (days) => (days >= 365 ? `${Math.floor(days / 365)} ano${days >= 730 ? "s" : ""}` : `${Math.max(1, Math.round(days / 30))} meses`);

  function itemsHtml(d) {
    const out = [];
    // placa certa (notebook com duas placas)
    if (d.hybrid) {
      const p = d.gpu_pref, dedicated = d.gpus.find((g) => !g.integrated);
      const names = d.game_names.length ? d.game_names.slice(0, 8).map(esc).join(", ") + (d.game_names.length > 8 ? "…" : "") : "nenhum jogo do Steam ou da Epic";
      const none = !p.exes, all = !none && p.set >= p.exes;
      out.push(item(none ? "info" : all ? "ok" : "care", "Jogos na placa de vídeo certa",
        `Seu PC tem duas placas: a integrada e a ${esc(dedicated.name)}. Às vezes o Windows abre o jogo na integrada e o FPS despenca.
         Achei: ${names}. ${none ? "" : all ? "Todos já estão marcados para a placa dedicada." : `${p.set} de ${p.exes} executáveis marcados.`}
         <br>Jogo de fora do Steam/Epic (Riot, Xbox, emulador)? Adicione o .exe à mão.`,
        `${none || all ? "" : '<button class="btn" id="g-gpu">Usar a placa dedicada nos jogos</button>'}
         <button class="ghost" id="g-gpuadd">Adicionar jogo (.exe)</button>
         ${d.gpu_pref_written ? '<button class="ghost" id="g-gpuundo">↩ Desfazer</button>' : ""}
         <button class="ghost" data-open="graphics">Abrir no Windows</button>`));
    }
    // driver de vídeo
    for (const g of d.gpus) {
      if (g.days == null) continue;
      const lv = g.days > 365 ? "bad" : g.days > 180 ? "care" : "ok";
      out.push(item(lv, `Driver de vídeo: ${esc(g.name)}`,
        `Versão ${esc(g.version)}, de ${ago(g.days)} atrás. ${lv === "ok" ? "Está em dia." : "Driver novo costuma trazer FPS a mais e correção de travamento nos jogos recentes."}${g.integrated && d.hybrid ? " Em notebook a imagem passa pela integrada, então vale atualizar ela também." : ""}`,
        lv !== "ok" && g.url ? `<button class="btn" data-open="${esc(g.url)}">Baixar no site da ${esc(g.vendor)}</button>` : ""));
    }
    // monitor
    for (const m of d.displays) {
      const low = m.hz < m.max_hz;
      out.push(item(low ? "bad" : "ok", `Monitor${d.displays.length > 1 ? (m.primary ? " principal" : " secundário") : ""}: ${m.hz} Hz`,
        low ? `Ele aceita até <b>${m.max_hz} Hz</b> em ${m.width}×${m.height}, mas está em ${m.hz} Hz. O Windows costuma deixar em 60 Hz e muita gente nunca percebe: o jogo pode até rodar a mais FPS, mas a tela só mostra ${m.hz}.`
            : `${m.width}×${m.height}, já na taxa máxima que o Windows enxerga.${m.max_hz <= 60 ? " Se o seu monitor for de 144 Hz ou mais e não aparece aqui, o problema costuma ser o cabo (use DisplayPort ou HDMI 2.0+)." : ""}`,
        low ? `<button class="btn" data-hz="${esc(m.device)}|${m.max_hz}|${m.hz}">Usar ${m.max_hz} Hz</button><button class="ghost" data-open="display">Abrir no Windows</button>` : ""));
    }
    // RAM
    const r = d.ram;
    if (r && r.desktop) {
      out.push(item(r.suspect ? "care" : "ok", `Memória RAM: ${esc(r.kind)} a ${r.speed} MHz`,
        r.suspect ? `Essa é a velocidade “de segurança” que a placa-mãe usa quando o perfil XMP (Intel) ou EXPO (AMD) está desligado. Se o seu pente é de velocidade maior (veja na caixa ou na etiqueta), ligue o XMP/EXPO na BIOS: é o ganho mais fácil de FPS em PC de mesa. O app não consegue ligar isso por você.`
          : "Parece estar na velocidade certa. Confira na etiqueta do pente se bate."));
    }
    // integridade de memória
    out.push(item(d.hvci ? "info" : "ok", `Integridade de memória (Isolamento de núcleo): ${d.hvci ? "ligada" : "desligada"}`,
      d.hvci ? "É uma proteção do Windows contra vírus que mexem no sistema. Em alguns jogos custa de 0 a uns 8% de FPS. Desligar deixa o PC menos protegido, por isso o WebDark não faz isso por você: se quiser, desligue na tela do Windows e reinicie."
        : "Desligada. O PC fica um pouco menos protegido contra vírus que mexem no sistema. Se não foi você que desligou, vale ligar de novo.",
      '<button class="ghost" data-open="coreisolation">Abrir Isolamento de núcleo</button>'));
    // HAGS e Modo de Jogo
    out.push(item(d.hags ? "ok" : "info", `Agendamento de GPU acelerado por hardware (HAGS): ${d.hags == null ? "padrão do Windows" : d.hags ? "ligado" : "desligado"}`,
      "Deixa a placa de vídeo organizar a própria fila de trabalho. Precisa para o Frame Generation do DLSS 3. O ganho de FPS varia: teste com e sem. Só funciona em placas recentes (NVIDIA GTX 10 ou mais nova, AMD RX 5000 ou mais nova). Precisa reiniciar o PC.",
      `<button class="${d.hags ? "ghost" : "btn"}" id="g-hags">${d.hags ? "Desligar" : "Ligar"}${adminTag()}</button>`));
    out.push(item(d.game_mode ? "ok" : "care", `Modo de Jogo do Windows: ${d.game_mode ? "ligado" : "desligado"}`,
      d.game_mode ? "Ligado: o Windows segura atualizações e tarefas em segundo plano enquanto você joga." : "Desligado. Ele segura atualizações e tarefas em segundo plano durante o jogo. Recomendo ligar.",
      d.game_mode ? "" : '<button class="btn" id="g-gm">Ligar</button>'));
    const need = out.filter((x) => x.lv === "bad" || x.lv === "care"), rest = out.filter((x) => !need.includes(x));
    const bad = need.filter((x) => x.lv === "bad").length;
    const lead = !need.length ? "Nada tirando FPS: está tudo no lugar."
      : `${need.length} ${need.length === 1 ? "coisa pode" : "coisas podem"} estar tirando FPS${bad ? `, ${bad} com certeza` : ""}. Comece por cima.`;
    const group = (title, list) => (list.length ? `<h2>${title}</h2><div class="card gc-list">${list.map((x) => x.html).join("")}</div>` : "");
    return `<p class="gc-lead">${lead}</p>${group("Precisa de atenção", need)}${group(need.length ? "O resto" : "Verificado", rest)}`;
  }

  function paint() {
    const box = $("#g-list");
    if (!box) return;
    if (!S.d) { box.innerHTML = '<div class="muted">Verificando placa de vídeo, monitor, memória e jogos instalados…</div>'; return; }
    box.innerHTML = itemsHtml(S.d);
    const run = (fn) => async () => { const r = await act(fn); if (ok(r)) toast("✅ " + r.msg); load(); };
    const on1 = (id, fn) => { const b = $(id, box); if (b) b.onclick = fn; };
    on1("#g-gpu", run(() => api.game_gpu_apply()));
    on1("#g-gpuadd", run(() => api.game_gpu_add()));
    on1("#g-gpuundo", run(() => api.game_gpu_undo()));
    on1("#g-gm", run(() => api.game_mode_enable()));
    on1("#g-hags", async () => {
      const want = !S.d.hags;
      if (!await confirmBox({ title: `${want ? "Ligar" : "Desligar"} o HAGS?`, ok: want ? "Ligar" : "Desligar",
        body: "Vale depois de reiniciar o PC. Se algum jogo ficar pior, é só voltar aqui e trocar de novo." })) return;
      run(() => api.game_hags_set(want))();
    });
    $$("[data-open]", box).forEach((b) => (b.onclick = () => api.game_open(b.dataset.open)));
    $$("[data-hz]", box).forEach((b) => (b.onclick = async () => {
      const [dev, hz, was] = b.dataset.hz.split("|");
      if (!await confirmBox({ title: `Usar ${hz} Hz?`, ok: "Usar",
        body: "A tela pode piscar por um segundo. Se ficar preta, espere 15 segundos sem mexer: o WebDark volta ao que estava." })) return;
      const r = await act(() => api.game_refresh_set(dev, +hz));
      if (!ok(r)) return;
      // como o “Manter alterações?” do Windows: sem resposta em 15 s, volta (a tela pode ter ficado preta)
      const keep = await Promise.race([
        confirmBox({ title: `Manter ${hz} Hz?`, body: "Se a imagem está normal, clique em Manter. Sem resposta em 15 segundos, volta sozinho.", ok: "Manter", cancel: "Voltar" }),
        new Promise((res) => setTimeout(() => res(false), 15000)),
      ]);
      if (!keep) {
        const m = $("#modal");
        m.hidden = true; m.onclick = null;
        await act(() => api.game_refresh_set(dev, +was));
        toast(`Voltei para ${was} Hz.`);
      } else toast("✅ " + r.msg);
      load();
    }));
  }

  on("game:scan", (d) => { S.d = d; S.loading = false; busy(-1); paint(); });

  function load() {
    if (S.loading) return;
    S.loading = true; busy(1);
    api.game_scan();
  }

  return {
    mount(el) {
      el.innerHTML = `<div class="gc-head">${head("Jogos", "Placa de vídeo, monitor, driver e memória: o que costuma estar errado sem você saber.")}
        <button class="ghost" id="g-again">${ICON("refresh")}Verificar de novo</button></div>
        <div class="scroll"><div id="g-list" style="display:flex;flex-direction:column;gap:10px"></div></div>`;
      $("#g-again").onclick = load;
      paint();
    },
    show() { if (!S.d) load(); },
  };
})();
