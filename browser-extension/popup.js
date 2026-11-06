const SETTINGS_DEFAULTS = { notify: true, sound: true };
const $ = (id) => document.getElementById(id);

function ago(ts) {
  const min = Math.floor((Date.now() - ts) / 60000);
  if (min < 1) return "agora";
  if (min < 60) return `há ${min} min`;
  return `há ${Math.floor(min / 60)}h${String(min % 60).padStart(2, "0")}`;
}

function fillList(ul, items, emptyText) {
  ul.replaceChildren();
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = emptyText;
    ul.append(li);
    return;
  }
  for (const [name, ts] of items) {
    const li = document.createElement("li");
    const n = document.createElement("span");
    const t = document.createElement("span");
    n.textContent = name; // textContent: nome vem do Discord, nunca vira HTML
    t.textContent = ago(ts);
    li.append(n, t);
    ul.append(li);
  }
}

async function render() {
  const s = await chrome.storage.session.get(["tabs", "known", "since", "history"]);
  const tabs = Object.values(s.tabs ?? {});
  const watching = tabs.some((t) => t.visible);

  const box = $("status");
  if (watching) {
    box.className = "status ok";
    $("statusText").textContent = "Vigiando Aguardando Suporte";
    $("statusHint").textContent = "Pode minimizar ou trocar de aba.";
  } else {
    box.className = "status warn";
    $("statusText").textContent = tabs.length
      ? "Sala fora da tela — sem vigia"
      : "Nenhuma aba do Discord aberta";
    $("statusHint").textContent =
      "Deixe uma aba do Discord no servidor, com a lista rolada até Aguardando Suporte.";
  }

  const mine = tabs.map((t) => t.myChannel).find(Boolean);
  $("myChannel").className = mine ? "on" : "empty";
  $("myChannel").textContent = mine
    ? `Você está em: ${mine}`
    : "Não encontrei você em nenhuma canaleta de atendimento.";

  const since = s.since ?? {};
  const queue = (s.known ?? []).map((n) => [n, since[n] ?? Date.now()]).sort((a, b) => a[1] - b[1]);
  $("count").textContent = queue.length;
  fillList($("queue"), queue, "Ninguém aguardando");
  fillList($("history"), (s.history ?? []).slice(0, 8).map((h) => [h.name, h.at]), "Nenhuma entrada ainda");
}

async function init() {
  const settings = await chrome.storage.local.get(SETTINGS_DEFAULTS);
  for (const key of Object.keys(SETTINGS_DEFAULTS)) {
    $(key).checked = settings[key];
    $(key).addEventListener("change", (e) => chrome.storage.local.set({ [key]: e.target.checked }));
  }
  const { myName = "" } = await chrome.storage.local.get("myName");
  $("myName").value = myName;
  $("myName").addEventListener("change", (e) => chrome.storage.local.set({ myName: e.target.value.trim() }));
  $("test").addEventListener("click", () => chrome.runtime.sendMessage({ type: "test" }));
  chrome.storage.onChanged.addListener((_, area) => area === "session" && render());
  setInterval(render, 30000); // atualiza o "há X min"
  render();
}

init();
