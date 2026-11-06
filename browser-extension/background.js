chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type !== "joined") return;
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icon.png",
    title: "Aguardando Suporte",
    message: `${msg.names.join(", ")} entrou na fila`,
    priority: 2,
    requireInteraction: true,
  });
});
