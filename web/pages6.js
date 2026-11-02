// Telas-mãe com abas: reúne as telas que serviam pro mesmo fim (menu mais curto, tudo no lugar certo).

Pages.space = makeGroup("Espaço e limpeza", "Limpe o lixo e descubra o que está comendo o seu disco. Tudo com aviso de risco antes de apagar.", [
  ["clean", "🧹 Limpeza", Pages.clean],
  ["dirs", "📁 Pastas", SpaceTabs.dirs],
  ["files", "📄 Arquivos grandes", SpaceTabs.files],
  ["dups", "👯 Duplicados", SpaceTabs.dups],
  ["dl", "📥 Downloads antigos", SpaceTabs.dl],
]);

Pages.apps = makeGroup("Aplicativos", "Tire o que vem de fábrica no Windows e desinstale o que você não usa mais.", [
  ["bloat", "🧨 Bloatware", Pages.bloat],
  ["progs", "📦 Programas instalados", Pages.progs],
]);

Pages.speed = makeGroup("Velocidade", "Plano de energia, o que liga com o Windows e a sua conexão. Tudo dá pra desfazer.", [
  ["perf", "⚡ Desempenho", Pages.perf],
  ["start", "🚀 Inicialização", Pages.start],
].concat(Pages.net ? [["net", "🌐 Rede", Pages.net]] : []));

Pages.protect = makeGroup("Saúde e proteção", "Veja se o PC está bem, vigie a temperatura e ache quem está pesando.", [
  ["health", "🩺 Saúde", Pages.health],
  ["security", "🛡 Segurança", Pages.security],
  ["proc", "🧠 Processos", Pages.proc],
]);
