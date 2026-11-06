// Checagem rápida da lógica de avisos (node browser-extension/check-background.mjs).
import { readFileSync } from "node:fs";
import assert from "node:assert";

const session = {}, notes = [], beeps = [], listeners = {}, badge = {};
const on = (name) => ({ addListener: (fn) => (listeners[name] = fn) });
globalThis.chrome = {
  storage: {
    session: { get: async () => structuredClone(session), set: async (v) => Object.assign(session, structuredClone(v)), remove: async () => {} },
    local: { get: async (d) => d },
  },
  notifications: { create: (id, o) => notes.push(`${o.title}: ${o.message}`), onClicked: on("click"), onButtonClicked: on("btn"), onClosed: on("closed"), clear() {} },
  tabs: { sendMessage: async (id) => beeps.push(id), onRemoved: on("removed"), onUpdated: on("updated"), update() {} },
  action: { setBadgeText: (o) => (badge.text = o.text), setBadgeBackgroundColor: (o) => (badge.color = o.color) },
  runtime: { onMessage: on("msg"), onStartup: on("s"), onInstalled: on("i") },
  windows: { update() {} },
};
eval(readFileSync(new URL("./background.js", import.meta.url), "utf8"));
const tick = () => new Promise((r) => setTimeout(r, 10));
const room = (label, names, visible = true) => ({ label, visible, names });
const report = async (tab, suporte, banido) => {
  listeners.msg({ type: "report", rooms: { suporte, banido }, myChannel: null }, { tab: { id: tab } });
  await tick();
};
const S = "Aguardando Suporte", B = "Aguardando Banido";

await report(1, room(S, ["Já estava"]), room(B, []));                 // primeira leitura: não avisa
assert.deepEqual(notes, []);
await report(1, room(S, ["Já estava", "Ana"]), room(B, ["Caio"]));    // uma entrada em cada sala
assert.deepEqual(notes, [`${S}: Ana entrou na fila`, `${B}: Caio entrou na fila`]);
assert.deepEqual(beeps, [1]);                                          // duas salas, um bipe só
assert.deepEqual(badge, { text: "3", color: "#3ba55d" });
await report(2, room(S, ["Já estava", "Ana"]), room(B, ["Caio"]));    // 2ª aba igual: sem aviso duplicado
assert.equal(notes.length, 2);
await report(1, room(S, [], false), room(B, ["Caio"]));               // Suporte saiu da tela numa aba...
await report(2, room(S, [], false), room(B, ["Caio"]));               // ...e na outra
assert.deepEqual(badge, { text: "1", color: "#e8a33d" });              // parcial: conta só Banido, em laranja
await report(2, room(S, ["Ana", "Bia"]), room(B, ["Caio"]));          // voltou: Bia entrou enquanto fora
assert.equal(notes.at(-1), `${S}: Bia entrou na fila`);
assert.deepEqual(session.known, { suporte: ["Ana", "Bia"], banido: ["Caio"] });
listeners.updated(2, { status: "loading" });                         // aba recarregou: deixa de vigiar
await tick();
assert.equal(session.tabs[2], undefined);
console.log("ok");
