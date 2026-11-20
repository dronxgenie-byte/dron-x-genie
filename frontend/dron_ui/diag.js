/* Диагностика клиента: показывает ошибки на экране и присылает их на сервер.
   Подключается первым, чтобы поймать сбои ещё до app.js. */
(function () {
  function banner(text) {
    let box = document.getElementById("dx-banner");
    if (!box) {
      box = document.createElement("div");
      box.id = "dx-banner";
      box.style.cssText =
        "position:fixed;z-index:99999;left:50%;top:8px;transform:translateX(-50%);" +
        "max-width:min(900px,92vw);background:#7f1d1d;color:#fff;" +
        "font:14px/1.4 system-ui,-apple-system,Segoe UI,sans-serif;padding:10px 14px;" +
        "border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.35);cursor:pointer;text-align:left";
      box.title = "Нажмите, чтобы скрыть";
      box.addEventListener("click", () => box.remove());
      (document.body || document.documentElement).appendChild(box);
    }
    box.textContent = text;
  }

  function report(payload) {
    try {
      fetch("/api/client-log", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).catch(() => {});
    } catch (_) { /* глушим */ }
  }

  window.__appStage = function (stage, error) {
    var message = (error && (error.message || String(error))) || "неизвестно";
    banner("Сбой интерфейса на шаге «" + stage + "»: " + message + ". Нажмите, чтобы скрыть.");
    report({ stage: stage, message: message, stack: error && error.stack });
  };

  window.addEventListener("error", function (event) {
    var err = event.error || {};
    var message = event.message || err.message || "неизвестная ошибка";
    if (String(message).indexOf("user didn't interact") !== -1) return;
    banner("Ошибка JS: " + message + ". Нажмите, чтобы скрыть.");
    report({ stage: "window.error", message: message, stack: err.stack, source: event.filename, line: event.lineno });
  });

  window.addEventListener("unhandledrejection", function (event) {
    var reason = event.reason || {};
    var message = reason.message || String(reason);
    if (String(message).indexOf("user didn't interact") !== -1) return;
    banner("Ошибка запроса: " + message + ". Нажмите, чтобы скрыть.");
    report({ stage: "unhandledrejection", message: message, stack: reason.stack });
  });

  window.addEventListener("load", function () {
    setTimeout(function () {
      if (!window.__appReady) {
        banner("Интерфейс не инициализировался: кнопка «Отправить» может не работать. Обновите страницу (Ctrl+F5).");
        report({ stage: "watchdog", ready: false, bootDone: Boolean(window.__bootDone) });
      } else {
        report({ stage: "ready", bootDone: Boolean(window.__bootDone) });
      }
    }, 3000);
  });
})();
