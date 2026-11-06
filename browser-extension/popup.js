const SETTINGS_DEFAULTS = { notify: true, sound: true };
const LATE_MIN = 5; // a partir daqui a espera fica laranja
const $ = (id) => document.getElementById(id);
let myName = "";

const minutes = (ts) => Math.floor((Date.now() - ts) / 60000);
const clock = (ts) => new Date(ts).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
function waitLabel(min) {
  if (min < 1) return "agora";
  if (min < 60) return `${min} min`;
  return `${Math.floor(min / 60)}h${String(min % 60).padStart(2, "0")}`;
}

// Monta elementos com textContent: nomes vêm do Discord e nunca viram HTML.
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function initial(name) {
  const letter = name.replace(/^[^\p{L}]*/u, "")[0] ?? name[0] ?? "?";
  return letter.toUpperCase();
}

function renderQueue(queue) {
  const ul = $("queue");
  ul.replaceChildren();
  $("count").textContent = queue.length;
  $("longest").textContent = queue.length ? `maior espera: ${waitLabel(minutes(queue[0][1]))}` : "";
  if (!queue.length) {
    ul.append(el("li", "empty", "Ninguém aguardando"));
    return;
  }
  for (const [name, ts] of queue) {
    const min = minutes(ts);
    const who = el("div", "who");
    who.append(el("b", "", name), el("small", "", `entrou ${clock(ts)}`));
    const li = el("li", "row");
    li.append(el("span", "avatar", initial(name)), who, el("span", min >= LATE_MIN ? "pill late" : "pill", waitLabel(min)));
    ul.append(li);
  }
}

function renderHistory(history) {
  const ul = $("history");
  ul.replaceChildren();
  if (!history.length) {
    ul.append(el("li", "", "Nenhuma entrada ainda"));
    return;
  }
  for (const h of history.slice(0, 6)) {
    const li = el("li");
    li.append(el("span", "", h.name), el("span", "", clock(h.at)));
    ul.append(li);
  }
}

function renderCall(channel) {
  $("call").classList.toggle("on", Boolean(channel));
  $("callName").textContent = channel ?? (myName ? "Não encontrei você numa canaleta" : "Informe seu nome na call");
  $("callAs").textContent = myName ? `como ${myName}` : "clique no lápis para configurar";
}

async function render() {
  const s = await chrome.storage.session.get(["tabs", "known", "since", "history"]);
  const tabs = Object.values(s.tabs ?? {});
  const watching = tabs.some((t) => t.visible);

  $("chip").textContent = watching ? "Vigiando" : "Sem vigia";
  $("chip").classList.toggle("warn", !watching);
  $("hero").hidden = !watching;
  $("warnHero").hidden = watching;
  $("warnTitle").textContent = tabs.length ? "A sala saiu da tela" : "Nenhuma aba do Discord aberta";

  const since = s.since ?? {};
  renderQueue((s.known ?? []).map((n) => [n, since[n] ?? Date.now()]).sort((a, b) => a[1] - b[1]));
  renderHistory(s.history ?? []);
  renderCall(tabs.map((t) => t.myChannel).find(Boolean) ?? null);
}

async function init() {
  const settings = await chrome.storage.local.get({ ...SETTINGS_DEFAULTS, myName: "" });
  for (const key of Object.keys(SETTINGS_DEFAULTS)) {
    $(key).checked = settings[key];
    $(key).addEventListener("change", (e) => chrome.storage.local.set({ [key]: e.target.checked }));
  }

  myName = settings.myName;
  $("myName").value = myName;
  $("nameForm").hidden = Boolean(myName);
  $("editName").addEventListener("click", () => {
    $("nameForm").hidden = !$("nameForm").hidden;
    if (!$("nameForm").hidden) $("myName").focus();
  });
  $("nameForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    myName = $("myName").value.trim();
    await chrome.storage.local.set({ myName });
    $("nameForm").hidden = Boolean(myName);
    render();
  });

  $("test").addEventListener("click", () => chrome.runtime.sendMessage({ type: "test" }));
  chrome.storage.onChanged.addListener((_, area) => area === "session" && render());
  setInterval(render, 30000); // atualiza os minutos de espera
  render();
}

init();
