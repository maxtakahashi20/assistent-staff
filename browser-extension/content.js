// Só lê a lista de canais que já está na tela. Não usa token, não chama API,
// não clica nem envia nada no Discord.
const WAITING_ROOM_ID = "1305663080826535937"; // Aguardando Suporte

let known = null; // nomes já vistos na sala; null = ainda sem leitura

function usersInChannel(channelId) {
  const link = document.querySelector(`[data-list-item-id="channels___${channelId}"]`);
  const item = link?.closest("li");
  if (!item) return null; // canal fora da tela (outro servidor ou lista rolada)
  // ponytail: depende das classes "voiceUser*" do Discord; se ele mudar o HTML, ajustar aqui.
  const rows = [...item.querySelectorAll('[class*="voiceUser"]')].filter(
    (el) => !el.parentElement.closest('[class*="voiceUser"]')
  );
  return new Set(
    rows
      .map((el) => (el.querySelector('[class*="username"]') ?? el).textContent.trim())
      .filter(Boolean)
  );
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

// MutationObserver em vez de setInterval: o Chrome limita timers de aba
// minimizada/em segundo plano a 1x por minuto, mas não segura o observer.
function check() {
  const current = usersInChannel(WAITING_ROOM_ID);
  if (current === null) return; // não some com quem já estava só porque o canal saiu da tela
  if (known !== null) {
    const joined = [...current].filter((name) => !known.has(name));
    if (joined.length) {
      chrome.runtime.sendMessage({ type: "joined", names: joined });
      beep();
    }
  }
  known = current;
}

new MutationObserver(check).observe(document.body, { childList: true, subtree: true });
check();
