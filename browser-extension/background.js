// Junta o que cada aba do Discord vê e decide quando avisar.
// Estado em storage.session: sobrevive ao service worker dormir, some ao fechar o Chrome.
//   tabs:    { [tabId]: { visible, names } }
//   known:   nomes já vistos na sala (null = ainda sem leitura, não avisa quem já estava)
//   since:   { [nome]: timestamp de quando apareceu }
//   history: últimas entradas [{ name, at }]

const SETTINGS_DEFAULTS = { notify: true, sound: true };

let chain = Promise.resolve();
const serial = (fn) => (chain = chain.then(fn).catch(console.error));

async function loadState() {
  const s = await chrome.storage.session.get(["tabs", "known", "since", "history"]);
  return { tabs: s.tabs ?? {}, known: s.known ?? null, since: s.since ?? {}, history: s.history ?? [] };
}

async function alertJoined(names, tabId) {
  const settings = await chrome.storage.local.get(SETTINGS_DEFAULTS);
  if (settings.notify) {
    chrome.notifications.create(`tab-${tabId ?? 0}-${Date.now()}`, {
      type: "basic",
      iconUrl: "icon.png",
      title: "Aguardando Suporte",
      message: `${names.join(", ")} entrou na fila`,
      priority: 2,
      requireInteraction: true,
    });
  }
  if (settings.sound && tabId) {
    chrome.tabs.sendMessage(tabId, { type: "beep" }).catch(() => {});
  }
}

function updateBadge(watching, count) {
  if (!watching) {
    chrome.action.setBadgeText({ text: "!" });
    chrome.action.setBadgeBackgroundColor({ color: "#e8a33d" });
  } else {
    chrome.action.setBadgeText({ text: count ? String(count) : "" });
    chrome.action.setBadgeBackgroundColor({ color: "#3ba55d" });
  }
}

async function recompute(s, reporterTabId) {
  const watching = Object.values(s.tabs).filter((t) => t.visible);
  if (watching.length) {
    const current = new Set(watching.flatMap((t) => t.names));
    if (s.known) {
      const joined = [...current].filter((n) => !s.known.includes(n));
      if (joined.length) {
        await alertJoined(joined, reporterTabId);
        const now = Date.now();
        s.history = [...joined.map((name) => ({ name, at: now })), ...s.history].slice(0, 20);
      }
    }
    for (const n of current) s.since[n] ??= Date.now();
    for (const n of Object.keys(s.since)) if (!current.has(n)) delete s.since[n];
    s.known = [...current];
  }
  // Sem nenhuma aba vendo a sala, "known" fica como estava: quem entrar
  // nesse meio-tempo é avisado assim que a sala voltar para a tela.
  await chrome.storage.session.set(s);
  updateBadge(watching.length > 0, s.known?.length ?? 0);
}

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === "report" && sender.tab) {
    serial(async () => {
      const s = await loadState();
      s.tabs[sender.tab.id] = { visible: msg.visible, names: msg.names };
      await recompute(s, sender.tab.id);
    });
  } else if (msg.type === "test") {
    serial(async () => {
      const { tabs } = await loadState();
      await alertJoined(["Teste"], Number(Object.keys(tabs)[0]) || null);
    });
  }
});

chrome.tabs.onRemoved.addListener((tabId) =>
  serial(async () => {
    const s = await loadState();
    if (!(tabId in s.tabs)) return;
    delete s.tabs[tabId];
    await recompute(s, null);
  })
);

chrome.notifications.onClicked.addListener((id) => {
  const tabId = Number(id.split("-")[1]);
  chrome.notifications.clear(id);
  if (!tabId) return;
  chrome.tabs.update(tabId, { active: true }, (tab) => {
    if (tab) chrome.windows.update(tab.windowId, { focused: true });
  });
});

chrome.runtime.onStartup.addListener(() => updateBadge(false, 0));
chrome.runtime.onInstalled.addListener(() => updateBadge(false, 0));
