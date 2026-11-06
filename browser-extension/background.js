// Junta o que cada aba do Discord vê e decide quando avisar. Uma fila por sala.
// Estado em storage.session: sobrevive ao service worker dormir, some ao fechar o Chrome.
//   tabs:    { [tabId]: { rooms: { [sala]: { label, visible, names } }, myChannel } }
//   known:   { [sala]: nomes já vistos } (sala ausente = ainda sem leitura, não avisa quem já estava)
//   since:   { [sala]: { [nome]: timestamp de quando apareceu } }
//   labels:  { [sala]: nome da sala }
//   history: últimas entradas [{ name, room, at }]

const SETTINGS_DEFAULTS = { notify: true, sound: true };
const STATE_KEYS = ["tabs", "known", "since", "labels", "history"];

let chain = Promise.resolve();
const serial = (fn) => (chain = chain.then(fn).catch(console.error));

async function loadState() {
  const s = await chrome.storage.session.get(STATE_KEYS);
  return {
    tabs: s.tabs ?? {},
    known: s.known ?? {},
    since: s.since ?? {},
    labels: s.labels ?? {},
    history: s.history ?? [],
  };
}

async function alertJoined(names, room, label, tabId, beep = true) {
  const settings = await chrome.storage.local.get(SETTINGS_DEFAULTS);
  if (settings.notify) {
    const id = `tab-${tabId ?? 0}-${Date.now()}-${room}`;
    chrome.notifications.create(id, {
      type: "basic",
      iconUrl: "icon.png",
      title: label,
      message: `${names.join(", ")} entrou na fila`,
      priority: 2,
      requireInteraction: true,
      buttons: [{ title: "Ir para o Discord" }],
    });
    await chrome.storage.session.set({ [`n:${id}`]: { name: names[0], room } });
  }
  if (beep && settings.sound && tabId) {
    chrome.tabs.sendMessage(tabId, { type: "beep" }).catch(() => {});
  }
}

// Nenhuma sala vista: "!". Alguma fora da tela: número em laranja. Todas vistas: verde.
function updateBadge(watched, total, count) {
  if (!watched) {
    chrome.action.setBadgeText({ text: "!" });
    chrome.action.setBadgeBackgroundColor({ color: "#e8a33d" });
  } else {
    chrome.action.setBadgeText({ text: count ? String(count) : "" });
    chrome.action.setBadgeBackgroundColor({ color: watched < total ? "#e8a33d" : "#3ba55d" });
  }
}

async function recompute(s, reporterTabId) {
  const tabs = Object.values(s.tabs);
  const rooms = new Set(tabs.flatMap((t) => Object.keys(t.rooms ?? {})));
  let watchedCount = 0;
  let count = 0; // só das salas vistas agora, igual ao painel
  let beeped = false; // várias entradas na mesma leitura: um bipe só
  for (const room of rooms) {
    const seen = tabs.map((t) => t.rooms?.[room]).filter((r) => r?.visible);
    // Sala sem nenhuma aba vendo: a fila dela fica como estava, e quem entrar
    // nesse meio-tempo é avisado assim que ela voltar para a tela.
    if (!seen.length) continue;
    watchedCount++;
    const label = (s.labels[room] = seen[0].label);
    const current = new Set(seen.flatMap((r) => r.names));
    const known = s.known[room];
    if (known) {
      const joined = [...current].filter((n) => !known.includes(n));
      if (joined.length) {
        await alertJoined(joined, room, label, reporterTabId, !beeped);
        beeped = true;
        const now = Date.now();
        s.history = [...joined.map((name) => ({ name, room, at: now })), ...s.history].slice(0, 20);
      }
    }
    const since = (s.since[room] ??= {});
    for (const n of current) since[n] ??= Date.now();
    for (const n of Object.keys(since)) if (!current.has(n)) delete since[n];
    s.known[room] = [...current];
    count += current.size;
  }
  await chrome.storage.session.set(s);
  updateBadge(watchedCount, rooms.size, count);
}

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === "report" && sender.tab) {
    serial(async () => {
      const s = await loadState();
      s.tabs[sender.tab.id] = { rooms: msg.rooms, myChannel: msg.myChannel };
      await recompute(s, sender.tab.id);
    });
  } else if (msg.type === "test") {
    serial(async () => {
      const { tabs } = await loadState();
      await alertJoined(["Teste"], "suporte", "Aguardando Suporte", Number(Object.keys(tabs)[0]) || null);
    });
  }
});

const forgetTab = (tabId) =>
  serial(async () => {
    const s = await loadState();
    if (!(tabId in s.tabs)) return;
    delete s.tabs[tabId];
    await recompute(s, null);
  });

chrome.tabs.onRemoved.addListener(forgetTab);
// Aba recarregando, indo para outro site ou descartada pelo Chrome: esquece até
// o content script (se ainda estiver no Discord) reportar de novo.
chrome.tabs.onUpdated.addListener((tabId, info) => {
  if (info.status === "loading" || info.discarded) forgetTab(tabId);
});

// Clique na notificação ou no botão: traz a aba e destaca o jogador com o menu pronto.
async function goTo(id) {
  const key = `n:${id}`;
  const { [key]: target } = await chrome.storage.session.get(key);
  chrome.notifications.clear(id);
  chrome.storage.session.remove(key);
  const tabId = Number(id.split("-")[1]);
  if (!tabId) return;
  const tab = await chrome.tabs.update(tabId, { active: true }).catch(() => null);
  if (!tab) return;
  const win = await chrome.windows.get(tab.windowId);
  await chrome.windows.update(win.id, win.state === "minimized" ? { state: "normal", focused: true } : { focused: true });
  chrome.tabs.sendMessage(tabId, { type: "focusUser", name: target?.name, room: target?.room }).catch(() => {});
}

chrome.notifications.onClicked.addListener(goTo);
chrome.notifications.onButtonClicked.addListener(goTo);
chrome.notifications.onClosed.addListener((id) => chrome.storage.session.remove(`n:${id}`));

chrome.runtime.onStartup.addListener(() => updateBadge(0, 0, 0));
chrome.runtime.onInstalled.addListener(() => updateBadge(0, 0, 0));
