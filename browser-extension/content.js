// Só lê a lista de canais e abre menus na tela. Não usa token, não chama API e
// nunca move ninguém: o clique final em "Mover para" é sempre do staff.
// Quem decide os avisos é o background.js.
// Salas de espera vigiadas.
const ROOMS = [
  { key: "suporte", label: "Aguardando Suporte", id: "1305663080826535937" },
  { key: "banido", label: "Aguardando Banido", id: "1566462788023492786" },
  { key: "entrevista", label: "Entrevista Staff", id: "1564794355766657035" },
];
const WORK_CHANNEL_IDS = [
  "1305663051990827039", // Atendimento 01 (e 02: veio com o mesmo ID)
  "1305663056868544593", // Atendimento 03
  "1305663065647349811", // Atendimento 04
  "1305663061721616425", // Atendimento 05
  "1305663067811745943", // Atendimento 06
  "1305663070063824927", // Atendimento 07
  "1305663071422775339", // Atendimento 08
];
const HIGHLIGHT_MS = 8000;

let myName = ""; // como o staff aparece na call (configurado no painel)

function channelLink(channelId) {
  return document.querySelector(`[data-list-item-id="channels___${channelId}"]`);
}

function channelName(channelId) {
  const link = channelLink(channelId);
  return (link?.querySelector('[class*="name"]') ?? link)?.textContent.trim() ?? "";
}

const roomLink = (room) => channelLink(room.id);

const voiceRows = (channelId) => voiceRowsOf(channelLink(channelId));

// [{ name, el, nameEl }] de quem está na call, ou null se o canal não está na tela.
function voiceRowsOf(link) {
  const item = link?.closest("li");
  if (!item) return null; // canal fora da tela (outro servidor ou lista rolada)
  // ponytail: depende das classes "voiceUser*"/"username*" do Discord; se ele mudar o HTML, ajustar aqui.
  return [...item.querySelectorAll('[class*="voiceUser"]')]
    .filter((el) => !el.parentElement.closest('[class*="voiceUser"]'))
    .map((el) => {
      const nameEl = el.querySelector('[class*="username"]') ?? el;
      return { name: nameEl.textContent.trim(), el, nameEl };
    })
    .filter((row) => row.name);
}

function myChannel() {
  if (!myName) return null;
  const me = myName.toLowerCase();
  for (const id of WORK_CHANNEL_IDS) {
    if (voiceRows(id)?.some((r) => r.name.toLowerCase() === me)) {
      return { id, name: channelName(id) };
    }
  }
  return null;
}

function beep() {
  const ctx = new AudioContext();
  [0, 0.25].forEach((start) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.3, ctx.currentTime + start);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + 0.2);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime + start);
    osc.stop(ctx.currentTime + start + 0.2);
  });
  setTimeout(() => ctx.close(), 1000);
}

// ---------- "Ir para o Discord": destaca o jogador e deixa o menu pronto ----------

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitFor(find, ms = 1500) {
  for (let t = 0; t < ms; t += 50) {
    const found = find();
    if (found) return found;
    await sleep(50);
  }
  return null;
}

function highlight(el) {
  el.style.outline = "2px solid #e8a33d";
  el.style.outlineOffset = "1px";
  el.style.borderRadius = "4px";
  setTimeout(() => (el.style.outline = ""), HIGHLIGHT_MS);
}

function pointAt(el) {
  const r = el.getBoundingClientRect();
  return { bubbles: true, cancelable: true, clientX: r.x + Math.min(20, r.width / 2), clientY: r.y + r.height / 2 };
}

function hover(el) {
  const at = pointAt(el);
  for (const type of ["pointerover", "pointerenter", "pointermove"]) el.dispatchEvent(new PointerEvent(type, at));
  for (const type of ["mouseover", "mouseenter", "mousemove"]) el.dispatchEvent(new MouseEvent(type, at));
}

const menuItems = () => [...document.querySelectorAll('[role="menuitem"]')];

async function focusUser(name, roomKey) {
  const room = ROOMS.find((r) => r.key === roomKey) ?? ROOMS[0];
  const rows = voiceRowsOf(roomLink(room));
  // Só o teste cai no primeiro da sala; aviso real nunca abre o menu de outro jogador.
  const row = rows?.find((r) => r.name === name) ?? (name === "Teste" ? rows?.[0] : null);
  if (!row) return;
  row.el.scrollIntoView({ block: "center" });
  highlight(row.el);
  await sleep(150); // deixa a rolagem assentar antes de abrir o menu

  // Abre o menu de botão direito do jogador (só a tela; nada é enviado ao Discord).
  row.nameEl.dispatchEvent(new MouseEvent("contextmenu", { ...pointAt(row.nameEl), button: 2 }));
  const moveItem = await waitFor(() => menuItems().find((i) => /mover para|move to/i.test(i.textContent)));
  if (!moveItem) return;
  highlight(moveItem);
  hover(moveItem); // abre o submenu "Mover para"

  const mine = myChannel();
  if (!mine?.name) return;
  const target = await waitFor(() =>
    menuItems().find((i) => i !== moveItem && i.textContent.includes(mine.name))
  );
  if (target) {
    target.scrollIntoView({ block: "nearest" });
    highlight(target); // o clique que move é do staff
  }
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "beep") beep();
  if (msg.type === "focusUser") focusUser(msg.name, msg.room);
});

// ---------- leitura contínua da sala ----------

let lastReport = "";

// MutationObserver em vez de setInterval: o Chrome limita timers de aba
// minimizada/em segundo plano a 1x por minuto, mas não segura o observer.
function check() {
  const rooms = {};
  for (const room of ROOMS) {
    const rows = voiceRowsOf(roomLink(room));
    rooms[room.key] = {
      label: room.label,
      visible: rows !== null,
      names: rows ? [...new Set(rows.map((r) => r.name))].sort() : [],
    };
  }
  const report = { rooms, myChannel: myChannel()?.name ?? null };
  const key = JSON.stringify(report);
  if (key === lastReport) return;
  lastReport = key;
  try {
    chrome.runtime.sendMessage({ type: "report", ...report }).catch(() => {});
  } catch {
    observer.disconnect(); // extensão recarregada: este script ficou órfão
  }
}

// Junta as rajadas de mudanças do Discord numa leitura só. O timer nasce do
// observer (não é encadeado), então em segundo plano roda no máximo 1x/s.
let pending = false;
const observer = new MutationObserver(() => {
  if (pending) return;
  pending = true;
  setTimeout(() => {
    pending = false;
    check();
  }, 250);
});
observer.observe(document.body, { childList: true, subtree: true });

function setMyName(value) {
  myName = (value ?? "").trim();
  lastReport = "";
  check();
}
chrome.storage.local.get({ myName: "" }).then((s) => setMyName(s.myName));
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.myName) setMyName(changes.myName.newValue);
});
check();
