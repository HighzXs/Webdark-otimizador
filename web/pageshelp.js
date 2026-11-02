// Central de ajuda: explica cada tela e cada botão, sem travar nada. Tem o botão 💡 flutuante (dicas da tela atual,
// com "mostrar onde fica" que acende o botão) e a tela "Ajuda" com um plano de otimização no seu ritmo.

// ---- dicas por tela (a chave é a aba aberta; sel = o botão que acende)
const TIPS = {
  home: ["Início", "Um resumo do seu PC e a faxina segura de um clique.", [
    ["Faxina rápida", "Apaga só o que é seguro: temporários, cache dos navegadores, lixeira e restos de atualização. Documentos, fotos e senhas não são tocados.", "#go"],
    ["Ponto de restauração", "Tira uma “foto” do Windows pra você voltar atrás se um ajuste der problema. Precisa de administrador.", "#restore"],
    ["Seu PC agora", "Uso de processador, memória e discos em tempo real. Disco acima de 90% cheio fica vermelho.", ".live"],
    ["Ficha técnica", "Modelo, processador, placa de vídeo, memória e discos do seu PC.", "#specs"]]],
  clean: ["Limpeza", "Escolha o que limpar. Nada aqui apaga documentos, fotos ou senhas.", [
    ["Analisar de novo", "Mede de novo quanto cada item ocupa.", "#clre"],
    ["Limpar marcados", "Limpa os itens marcados. Feche os navegadores antes pra liberar mais.", "#clrun"],
    ["Desligar hibernação", "Apaga o arquivo hiberfil.sys (vários GB). Você perde o “Iniciar Rápido” e a hibernação; suspender e desligar continuam normais.", "#hib"],
    ["DISM (componentes antigos)", "Remove restos de atualizações antigas do Windows. Demora uns minutos e fica parado em 20% ou 40%: é normal.", "#dism"],
    ["Limpeza de Disco do Windows", "Abre a ferramenta do próprio Windows, que apaga o Windows.old e instalações antigas.", "#cmgr"]]],
  dirs: ["Pastas", "Mostra quais pastas ocupam mais espaço, em ordem.", [
    ["Escanear", "Mede o disco escolhido. O disco inteiro pode levar 1 ou 2 minutos.", "#dscan"],
    ["Subir uma pasta", "Volta uma pasta acima. Clique no nome de uma pasta pra entrar nela.", "#dup"]]],
  files: ["Arquivos grandes", "Acha os arquivos que mais pesam e avisa o risco de apagar cada um.", [
    ["Procurar", "Varre o disco atrás de arquivos maiores que o tamanho escolhido. Continua em segundo plano se você sair da tela.", "#scan"],
    ["Risco: Seguro, Cuidado, Perigo", "SEGURO: o programa recria sozinho. CUIDADO: só você sabe se precisa. NÃO APAGUE: pode quebrar o Windows (fica trancado).", ".legend"],
    ["Apagar todos os seguros", "Manda pra lixeira só o que está marcado como seguro. Dá pra recuperar da lixeira do Windows.", "#delsafe"]]],
  dups: ["Duplicados", "Acha arquivos idênticos espalhados e deixa uma cópia de cada.", [
    ["Procurar", "Compara o conteúdo dos arquivos, não só o nome. Pode levar alguns minutos.", "#dupgo"],
    ["Mandar marcados pra lixeira", "Em cada grupo, uma cópia sempre fica sem marca. O app nunca deixa apagar todas as cópias.", "#dupdel"]]],
  dl: ["Downloads antigos", "Lista o que está parado na pasta Downloads há muito tempo.", [
    ["Listar", "Só lista. Nada é apagado sozinho.", "#dlgo"],
    ["Marcar os seguros", "Marca de uma vez os instaladores e arquivos que o app considera seguros.", "#dlsafe"],
    ["Mandar marcados pra lixeira", "Manda os marcados pra lixeira, com confirmação.", "#dldel"]]],
  bloat: ["Bloatware", "Apps que vêm com o Windows e quase ninguém usa. Dá pra reinstalar pela Microsoft Store.", [
    ["Marcar recomendados", "Marca o que é lixo de verdade: jogos de fábrica, propaganda, apps de teste.", "#rec"],
    ["Remover marcados", "Remove os apps marcados. Se for administrador, cria um ponto de restauração antes.", "#rm"]]],
  progs: ["Programas instalados", "Os programas do seu PC, dos maiores pros menores. Os suspeitos vêm primeiro.", [
    ["Marcar suspeitos", "Marca antivírus de teste, barras de ferramentas e “otimizadores” duvidosos.", "#marksus"],
    ["Desinstalar marcados", "Desinstala vários de uma vez. Você escolhe: automático, um de cada vez ou todos juntos. Cada desinstalador pede sua confirmação.", "#unmany"],
    ["Fila de desinstalação", "Quando o desinstalador não aceita dois ao mesmo tempo, o próximo só abre quando o anterior termina. Dá pra pular ou parar.", "#uq"]]],
  perf: ["Desempenho", "Plano de energia, clock da CPU e ajustes do Windows.", [
    ["Plano de energia", "Em PC de mesa, “Alto desempenho” deixa tudo mais ágil e não gasta bateria. Em notebook gasta mais bateria.", "#plans"],
    ["Tela e suspensão", "Define depois de quanto tempo parado a tela desliga e o PC dorme.", "#tapply"],
    ["Ajustes do Windows", "Interruptores: ligado = ajuste aplicado, desligue pra voltar ao padrão. Alguns precisam de administrador.", "#sy"],
    ["Otimizar o disco (TRIM)", "Em SSD, avisa o disco o que sobrou livre. Mantém a velocidade com o tempo.", "#opt"]]],
  start: ["Inicialização", "Tudo que liga junto com o Windows, inclusive o que o Gerenciador de Tarefas esconde.", [
    ["Desligar os recomendados", "Desliga o que quase ninguém precisa abrindo sozinho. O Windows liga mais rápido. Dá pra religar depois.", "#rec"],
    ["Detalhes", "Clique num item da lista pra ler o que ele é e se vale desligar.", "#detail"]]],
  net: ["Rede", "Internet mais rápida e estável.", [
    ["Wi-Fi e adaptadores", "Mostra a velocidade de cada placa de rede e o sinal do Wi-Fi.", "#n-wifi"],
    ["Melhor DNS", "Testa vários servidores de DNS de verdade e mostra qual responde mais rápido. Trocar não é obrigatório e dá pra voltar ao automático.", "#n-dnstest"],
    ["Otimização de Entrega", "Impede o Windows de usar sua internet pra repassar atualizações a outros PCs.", "#n-do"],
    ["Limitar programas", "Limita o que um programa envia. Pode causar instabilidade: use com cuidado.", "#n-lim"],
    ["Drivers de rede", "Mostra a idade do driver do Wi-Fi e do cabo e leva você ao Windows Update pra baixar drivers.", "#n-drv"],
    ["Reparar a rede", "Os comandos clássicos de reparo (ipconfig e netsh). Os mais fortes pedem reiniciar o PC.", "#n-fix"]]],
  mem: ["Memória", "Libere RAM e ajuste como o Windows usa a memória.", [
    ["Lista de espera", "Cache de arquivos na RAM. A limpeza suave é segura até com jogo aberto; a completa pode engasgar por uns segundos.", "#m-sb-soft"],
    ["Liberar RAM de todos", "Devolve a RAM que navegadores, Discord e Spotify guardam sem usar. O programa que você está usando não é tocado.", "#m-trimall"],
    ["Congelar", "Para um programa de vez enquanto você joga (a RAM volta na hora). Descongela sozinho no prazo ou ao fechar o WebDark.", "#m-apps"],
    ["Congelar sozinho ao jogar", "Detecta jogo em tela cheia e congela só os programas que você marcou, menos quem está em chamada. Descongela quando o jogo sai.", "#m-auto"],
    ["Serviços que dá pra desligar", "Lista com o risco e o que quebra em cada um. Dá pra religar com o mesmo interruptor.", "#m-svcs"],
    ["Arquivo de paginação", "Mostra uma sugestão pela sua RAM. Precisa reiniciar. Dá pra voltar ao automático.", "#m-pfgo"],
    ["Agrupar serviços", "Junta serviços em menos processos svchost e economiza RAM. Precisa reiniciar.", "#m-svcgo"],
    ["SysMain", "Pré-carrega programas na RAM. Em SSD pode desligar; em HD deixe ligado.", "#m-sysmain"]]],
  health: ["Saúde", "Veja se o disco está bom e conserte problemas do Windows.", [
    ["Saúde do disco", "Mostra se o disco avisa que vai falhar. Se aparecer alerta, faça backup antes de qualquer coisa.", "#hd"],
    ["Diagnóstico geral", "Confere sinais de problema no Windows.", "#rd"],
    ["Atualizações e drivers", "Só avisa o que está pendente. Não instala nada sozinho.", "#updbtn"]]],
  security: ["Segurança (temperatura)", "Vigia o calor do PC e baixa o clock sozinho se esquentar demais. Tudo começa desligado.", [
    ["Interruptor do vigia", "Liga ou desliga o vigia. Desligado, o app não mexe em nada.", "#sw-on"],
    ["Curva de temperatura", "Arraste os pontos: em cada temperatura, quanto do clock o PC pode usar.", "#curve"],
    ["Sugerir pra mim", "Monta uma curva sob medida pro seu processador.", "#sug"]]],
  proc: ["Processos", "Quem está pesando agora.", [
    ["Atualizar sozinho", "Mantém a lista viva. Desligue se quiser olhar com calma.", "#auto"],
    ["Fechar um programa", "Você perde o que não foi salvo nele. Os do Windows ficam trancados.", "#list"]]],
  settings: ["Ajustes", "Cor, blur, fonte, modo segundo plano e atualizações.", [
    ["Procurar atualização", "Confere agora se tem versão nova do WebDark.", "#updcheck"],
    ["Modo segundo plano", "Fecha na bandeja e confere o PC de tempos em tempos com prioridade mínima.", "#s-bg"]]],
};

// ---- plano de otimização (a ordem sugerida pra quem não sabe por onde começar)
const PLAN = [
  { k: "quick", icon: "🧹", t: "Faça a faxina rápida", where: ["home"], sel: "#go", level: "Seguro", time: "1 min",
    d: "Limpa temporários, cache e lixeira.", why: "É o jeito mais rápido de liberar espaço sem risco.", care: "Feche os navegadores antes pra limpar mais." },
  { k: "bloat", icon: "🧨", t: "Tire o bloatware", where: ["apps", "bloat"], sel: "#rec", level: "Seguro", time: "3 min",
    d: "Remove apps de fábrica que ninguém usa.", why: "Libera espaço e tira coisa rodando à toa.", care: "Dá pra reinstalar pela Microsoft Store." },
  { k: "progs", icon: "📦", t: "Desinstale o que você não usa", where: ["apps", "progs"], sel: "#marksus", level: "Cuidado", time: "5 min",
    d: "Marque vários programas e desinstale em lote.", why: "Programas parados ocupam GBs.", care: "Só marque o que você reconhece. Cada desinstalador pede sua confirmação." },
  { k: "start", icon: "🚀", t: "Limpe a inicialização", where: ["speed", "start"], sel: "#rec", level: "Seguro", time: "2 min",
    d: "Desliga o que abre junto com o Windows sem precisar.", why: "O PC liga mais rápido e sobra memória.", care: "Dá pra religar qualquer item depois." },
  { k: "space", icon: "📄", t: "Ache o que está comendo espaço", where: ["space", "files"], sel: "#scan", level: "Cuidado", time: "5 min",
    d: "Arquivos grandes, duplicados e downloads velhos, com aviso de risco.", why: "Costuma ser onde estão dezenas de GB.", care: "Tudo vai pra lixeira do Windows: dá pra recuperar." },
  { k: "power", icon: "⚡", t: "Ajuste o plano de energia", where: ["speed", "perf"], sel: "#plans", level: "Seguro", time: "1 min",
    d: "Escolha entre economia e desempenho máximo.", why: "Em PC de mesa, Alto desempenho deixa tudo mais ágil.", care: "Em notebook, gasta mais bateria." },
  { k: "health", icon: "🩺", t: "Confira a saúde do PC", where: ["protect", "health"], sel: "#rd", level: "Seguro", time: "2 min",
    d: "Saúde do disco e diagnóstico do Windows.", why: "Descobre problema antes de virar perda de dados.", care: "Se o disco der alerta, faça backup antes de tudo." },
  { k: "net", icon: "🌐", t: "Melhore a internet", where: ["speed", "net"], sel: "#n-dnstest", level: "Seguro", time: "3 min",
    d: "Teste o melhor DNS e confira o Wi-Fi e os drivers.", why: "Sites começam a abrir mais rápido.", care: "Trocar DNS é opcional e dá pra voltar ao automático." },
  { k: "sec", icon: "🛡", t: "Ligue o vigia de temperatura (opcional)", where: ["protect", "security"], sel: "#sw-on", level: "Opcional", time: "2 min",
    d: "Baixa o clock sozinho se o PC esquentar demais.", why: "Protege notebooks e PCs que esquentam.", care: "Vem desligado: só funciona se você ligar." },
];

// ---- otimização guiada (professor): o que a ferramenta faz em uma frase + o que clicar. A chave é a mesma do PLAN.
const TUTOR = {
  quick: ["Apaga temporários, cache dos navegadores e lixeira. Seus arquivos pessoais não são tocados.", "Clique em Faxina rápida."],
  bloat: ["São apps que vêm no Windows e quase ninguém usa. Tirar libera espaço e deixa o PC mais leve.", "Clique em Marcar recomendados e depois em Remover marcados."],
  progs: ["Lista seus programas, os maiores primeiro. O que você não usa só ocupa espaço.", "Marque só o que você reconhece e desinstale."],
  start: ["São os programas que ligam junto com o Windows. Menos coisas ligando = PC que liga mais rápido.", "Clique em Desligar os recomendados."],
  space: ["Acha os arquivos que mais pesam, com aviso de risco. Tudo vai pra lixeira, então dá pra voltar atrás.", "Clique em Procurar e apague os marcados como seguros."],
  power: ["O plano de energia decide se o PC economiza ou rende o máximo.", "Em PC de mesa, escolha Alto desempenho."],
  health: ["Confere se o disco está bom e se o Windows tem algum problema.", "Rode o diagnóstico e leia o resultado."],
  net: ["O DNS é a agenda da internet. Um mais rápido faz os sites abrirem antes.", "Clique em Testar DNS e veja qual responde melhor."],
  sec: ["Vigia a temperatura e baixa o clock sozinho se o PC esquentar demais. É opcional.", "Ligue o interruptor se o seu PC esquenta."],
};

// ---- professor: cartão flutuante que leva a cada tela, acende o botão e explica. O usuário clica no botão de verdade.
const Tutor = (() => {
  let i = 0, on = false, el = null;
  const total = PLAN.length;
  const doneCount = () => PLAN.filter((s) => HELP.done.includes(s.k)).length;
  function mark(k) { if (!HELP.done.includes(k)) { HELP.done = [...HELP.done, k]; helpSave(); } }
  function paint() {
    if (!el) return;
    if (i >= total) {
      el.innerHTML = `<div class="tt-head"><b>🎉 Pronto!</b></div><div class="tt-text">Você passou por todas as etapas e fez ${doneCount()} de ${total}. ${doneCount() < total ? "As puladas ficam no plano da Ajuda, pra fazer quando quiser." : "Seu PC está mais leve."}</div>
        <div class="tt-acts"><button class="btn" id="tt-end">Concluir</button></div>`;
      $("#tt-end").onclick = stop;
      return;
    }
    const s = PLAN[i], t = TUTOR[s.k] || [s.d, ""];
    el.innerHTML = `<div class="tt-head"><b>🎓 Passo ${i + 1} de ${total}</b><button class="mini" id="tt-x" title="Sair">✕</button></div>
      <div class="bar" style="margin:0 0 10px"><i style="width:${(i / total) * 100}%"></i></div>
      <div class="tt-title">${s.icon} ${esc(s.t)} <span class="pill ${s.level === "Seguro" ? "ok" : "care"}">${esc(s.level.toUpperCase())}</span></div>
      <div class="tt-text">${esc(t[0])}</div>${t[1] ? `<div class="tt-do">👉 ${esc(t[1])}</div>` : ""}
      <div class="tt-acts"><button class="mini" id="tt-pt">📍 Mostrar</button><span style="flex:1"></span>
        <button class="mini" id="tt-bk" ${i === 0 ? "disabled" : ""}>◀ Voltar</button><button class="mini" id="tt-sk">Pular</button>
        <button class="btn" id="tt-ok">Feito, próximo ▶</button></div>`;
    $("#tt-x").onclick = stop;
    $("#tt-pt").onclick = () => goAndPoint(s.where, s.sel);
    $("#tt-bk").onclick = () => { i--; enter(); };
    $("#tt-sk").onclick = () => { i++; enter(); };
    $("#tt-ok").onclick = () => { mark(s.k); i++; enter(); };
  }
  function enter() {
    paint();
    if (i < total) goAndPoint(PLAN[i].where, PLAN[i].sel);
  }
  function start() {
    const first = PLAN.findIndex((s) => !HELP.done.includes(s.k));
    i = first < 0 ? 0 : first;
    on = true;
    helpToggle(false);
    if (!el) { el = document.createElement("div"); el.id = "tutor"; document.querySelector(".stage").append(el); }
    el.hidden = false;
    enter();
  }
  function stop() {
    on = false;
    if (el) el.hidden = true;
    if (current === "help") Pages.help.mount($(".page"));
  }
  return { start, stop, get on() { return on; } };
})();

const TOPICS = [
  ["O que é bloatware?", "São programas que já vêm instalados no Windows ou no PC novo (jogos de fábrica, propagandas, testes de antivírus) e quase ninguém usa. Ocupam espaço e às vezes rodam em segundo plano."],
  ["O que é DNS?", "É a “agenda telefônica” da internet: transforma o nome do site (google.com) no endereço dele. Se o DNS é lento, todo site demora um pouco mais pra começar a abrir."],
  ["Por que o app pede administrador?", "Mexer em serviços, no registro e em pastas do Windows exige permissão especial. O WebDark funciona sem administrador, mas algumas limpezas, reparos e ajustes ficam travados e aparecem com a etiqueta PRECISA DE ADMIN."],
  ["Posso desfazer o que o WebDark faz?", "Quase tudo. Apps removidos reinstalam pela Microsoft Store. Arquivos apagados vão pra lixeira do Windows. Ajustes do sistema têm interruptor pra voltar ao padrão, e o app cria um ponto de restauração antes de mexer no sistema (como administrador)."],
  ["O que é o ponto de restauração?", "Uma “foto” das configurações do Windows num momento. Se algo der errado, você volta pra essa foto pela Restauração do Sistema do Windows."],
  ["Posso desligar a hibernação?", "Pode. O arquivo dela ocupa vários GB. Você perde o Iniciar Rápido e a hibernação, mas desligar e suspender continuam normais."],
  ["O que é TRIM?", "Um aviso que o Windows manda pro SSD dizendo quais partes estão livres. Com ele ligado o SSD mantém a velocidade com o tempo."],
  ["Meu PC está esquentando. E agora?", "Limpe a poeira, deixe as saídas de ar livres e use a aba Segurança: ela baixa o clock sozinho quando passa da temperatura que você definir (vem desligada)."],
  ["A Faxina rápida é segura?", "Sim. Ela só apaga temporários, cache, lixeira e restos de atualização. Nunca toca em documentos, fotos, senhas ou programas instalados."],
  ["Uma pasta ou arquivo está como “NÃO APAGUE”. Por quê?", "O app reconheceu que ele é parte do Windows ou de um programa em uso. Apagar pode quebrar o sistema, por isso fica trancado."],
];

// ---- mostrar onde fica o botão (acende e rola até ele)
function pointTo(sel) {
  const el = sel && document.querySelector(sel);
  if (!el) { toast("Esse item só aparece depois de usar a tela (ou ainda está carregando)."); return false; }
  el.scrollIntoView({ block: "center", behavior: "smooth" });
  el.classList.remove("hint-ring");
  void el.offsetWidth;
  el.classList.add("hint-ring");
  setTimeout(() => el.classList.remove("hint-ring"), 3600);
  return true;
}
function goAndPoint(where, sel) {
  go(where[0], where[1]);
  if (sel) setTimeout(() => pointTo(sel), 900);
}

// ---- painel flutuante (dicas da tela atual)
let HELP = { done: [], open: false };
const helpSave = () => api.help_save({ done: HELP.done });

function helpRefresh() {
  const panel = document.getElementById("helppanel");
  if (!panel) return;
  const tip = TIPS[current];
  const body = tip ? `<div class="hp-intro">${esc(tip[1])}</div>${tip[2].map(([t, d, sel], i) => `<div class="hp-item"><b>${esc(t)}</b><div>${esc(d)}</div>
      ${sel ? `<button class="mini" data-pt="${esc(sel)}">📍 Mostrar onde fica</button>` : ""}</div>`).join("")}`
    : '<div class="hp-intro">Escolha uma tela no menu e eu explico o que cada botão faz.</div>';
  panel.innerHTML = `<div class="hp-head"><b>💡 ${esc(tip ? tip[0] : "Ajuda")}</b><button class="mini" id="hp-x" title="Fechar">✕</button></div>
    <div class="hp-body">${body}</div><div class="hp-foot"><button class="ghost" id="hp-all">Abrir a Central de ajuda</button></div>`;
  $("#hp-x").onclick = () => helpToggle(false);
  $("#hp-all").onclick = () => { helpToggle(false); go("help"); };
  $$("[data-pt]", panel).forEach((b) => (b.onclick = () => pointTo(b.dataset.pt)));
}
function helpToggle(open) {
  HELP.open = open === undefined ? !HELP.open : open;
  document.getElementById("helppanel").hidden = !HELP.open;
  document.getElementById("helpfab").classList.toggle("on", HELP.open);
  if (HELP.open) helpRefresh();
}
(() => {
  const stage = document.querySelector(".stage");
  const fab = document.createElement("button");
  fab.id = "helpfab"; fab.title = "Dicas sobre esta tela"; fab.textContent = "💡";
  fab.onclick = () => helpToggle();
  const panel = document.createElement("div");
  panel.id = "helppanel"; panel.hidden = true;
  stage.append(fab, panel);
})();

// ---- tela Ajuda: plano + perguntas
Pages.help = (() => {
  const progress = () => `${PLAN.filter((s) => HELP.done.includes(s.k)).length} de ${PLAN.length} feitos`;
  function paint() {
    const box = $("#planbox");
    if (!box) return;
    $("#planprog").textContent = progress();
    $("#planbar").style.width = (PLAN.filter((s) => HELP.done.includes(s.k)).length / PLAN.length) * 100 + "%";
    box.innerHTML = PLAN.map((s, i) => `<div class="card step ${HELP.done.includes(s.k) ? "done" : ""}" data-k="${s.k}">
      <div class="num">${HELP.done.includes(s.k) ? "✓" : i + 1}</div>
      <div style="flex:1;min-width:0"><b>${s.icon} ${esc(s.t)}</b> <span class="pill ${s.level === "Seguro" ? "ok" : "care"}">${esc(s.level.toUpperCase())}</span> <span class="muted">• ${esc(s.time)}</span>
        <div>${esc(s.d)}</div><div class="muted">Pra quê: ${esc(s.why)} • Cuidado: ${esc(s.care)}</div></div>
      <div class="acts" style="opacity:1;flex-direction:column;align-items:stretch"><button class="btn" data-go="${s.k}">Ir pra lá</button>
        <button class="mini" data-done="${s.k}">${HELP.done.includes(s.k) ? "Desmarcar" : "Marcar como feito"}</button></div></div>`).join("");
  }
  function paintTopics() {
    const q = ($("#hq").value || "").toLowerCase(), box = $("#topics");
    const list = TOPICS.filter(([t, d]) => !q || (t + " " + d).toLowerCase().includes(q));
    box.innerHTML = list.length ? list.map(([t, d]) => `<details class="card topic"><summary>${esc(t)}</summary><div class="muted" style="margin-top:8px;font-size:13.5px">${esc(d)}</div></details>`).join("")
      : '<div class="muted">Nada com essa palavra. Tente outra.</div>';
  }
  return {
    mount(el) {
      el.innerHTML = `<div><h1>Ajuda e dicas</h1><div class="muted">Sem pressa e sem obrigação. Use o plano abaixo no seu ritmo, ou clique no 💡 de qualquer tela pra entender cada botão dela.</div></div>
        <div class="scroll">
          <div class="card tutorcta"><div style="flex:1"><b>🎓 Otimização guiada</b><div class="muted">Eu levo você a cada ferramenta, explico em uma frase o que ela faz e você otimiza o PC enquanto aprende.</div></div>
            <button class="btn" id="tutgo">Me guie</button></div>
          <h2>🗺 Plano de otimização <span class="muted" id="planprog" style="font-weight:400"></span></h2>
          <div class="bar" style="margin:0"><i id="planbar"></i></div>
          <div id="planbox" style="display:flex;flex-direction:column;gap:10px"></div>
          <h2>❓ Perguntas comuns</h2>
          <div class="fld"><input class="search" id="hq" placeholder="Buscar: DNS, bloatware, administrador…" style="flex:none"></div>
          <div id="topics" style="display:flex;flex-direction:column;gap:8px"></div>
        </div>`;
      $("#hq").oninput = paintTopics;
      $("#tutgo").onclick = () => Tutor.start();
      $("#planbox").onclick = (e) => {
        const g = e.target.dataset.go, d = e.target.dataset.done;
        if (g) { const s = PLAN.find((x) => x.k === g); goAndPoint(s.where, s.sel); }
        if (d) { HELP.done = HELP.done.includes(d) ? HELP.done.filter((x) => x !== d) : [...HELP.done, d]; helpSave(); paint(); }
      };
      paint(); paintTopics();
    },
  };
})();

// o progresso do plano vem do arquivo de preferências
(async () => { try { const s = await api.help_state(); HELP.done = Array.isArray(s.done) ? s.done : []; if (current === "help") Pages.help.mount($(".page")); } catch (e) { /* sem ponte ainda */ } })();
