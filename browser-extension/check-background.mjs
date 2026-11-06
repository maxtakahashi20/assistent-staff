// Checagem rápida da lógica de avisos (node browser-extension/check-background.mjs).
import { readFileSync } from "node:fs";
import assert from "node:assert";

const session = {}, notes = [], beeps = [], listeners = {};
const on = (name) => ({ addListener: (fn) => (listeners[name] = fn) });
globalThis.chrome = {
  storage: {
    session: { get: async () => ({ ...structuredClone(session) }), set: async (v) => Object.assign(session, structuredClone(v)) },
    local: { get: async (d) => d },
  },
  notifications: { create: (id, o) => notes.push(o.message), onClicked: on("click"), onButtonClicked: on("btn"), onClosed: on("closed"), clear() {} },
  tabs: { sendMessage: async (id) => beeps.push(id), onRemoved: on("removed"), onUpdated: on("updated"), update() {} },
  action: { setBadgeText() {}, setBadgeBackgroundColor() {} },
  runtime: { onMessage: on("msg"), onStartup: on("s"), onInstalled: on("i") },
  windows: { update() {} },
};
eval(readFileSync(new URL("./background.js", import.meta.url), "utf8"));
const report = async (tab, visible, names) => {
  listeners.msg({ type: "report", visible, names }, { tab: { id: tab } });
  await new Promise((r) => setTimeout(r, 10));
};

await report(1, true, ["Já estava"]);            // primeira leitura: não avisa
assert.deepEqual(notes, []);
await report(1, true, ["Já estava", "Ana"]);     // entrou Ana
assert.deepEqual(notes, ["Ana entrou na fila"]);
assert.deepEqual(beeps, [1]);
await report(2, true, ["Já estava", "Ana"]);     // 2ª aba vendo o mesmo: sem aviso duplicado
assert.equal(notes.length, 1);
await report(1, false, []); await report(2, false, []); // sala saiu da tela
await report(2, true, ["Ana", "Bia"]);           // voltou: Bia entrou enquanto fora
assert.deepEqual(notes.at(-1), "Bia entrou na fila");
assert.deepEqual(session.known, ["Ana", "Bia"]);
console.log("ok");

listeners.updated(2, { status: "loading" });      // aba recarregou: deixa de contar como vigia
await new Promise((r) => setTimeout(r, 10));
assert.equal(session.tabs[2], undefined);
console.log("ok: aba recarregada");
