/* ANANISIM OS — клиент
   Правила: Дрон слева, Джин справа, человек в середине.
   Обращение по имени: «Дрон, …» / «Джин, …». Недоступное — честно. */

const API = {
  health: "/api/health",
  settings: "/api/settings",
  council: "/api/council",
  finance: "/api/finance",
  ivan: "/api/ivan",
  dronChat: "/api/dron/chat",
  dronSpeak: "/api/dron/speak",
  genieChat: "/api/genie/chat",
  genieStatus: "/api/genie/status",
  xChat: "/api/x/chat",
  xStatus: "/api/x/status",
  xProviders: "/api/x/providers",
  providersRegistry: "/api/providers/registry",
  providersRefresh: "/api/providers/refresh",
  providersActive: "/api/providers/active",
  memory: "/api/memory",
  memoryCompact: "/api/memory/compact",
  commsStatus: "/api/comms/status",
  commsSend: "/api/comms/send",
  commsCall: "/api/comms/call",
  duet: "/api/duet",
  stt: "/api/stt",
  voice: "/api/voice",
  phrases: "/api/phrases",
};

const STATE = {
  settings: { default_agent: "dron", voice_autoplay: true },
  health: null,
  phrases: null,
  busy: false,
  council: null,
  history: { dron: [], genie: [], x: [] },
  xMode: false,
  xProvider: null,
  app: "stage",
};

const $ = (id) => document.getElementById(id);

/* Переписка не должна пропадать при обновлении страницы. */
const CHAT_STORE = "dxg_chat_v1";
const CHAT_LIMIT = 200;

function persistMessage(kind, text) {
  if (!text || kind === "skip") return;
  try {
    const list = JSON.parse(localStorage.getItem(CHAT_STORE) || "[]");
    list.push({ kind, text });
    localStorage.setItem(CHAT_STORE, JSON.stringify(list.slice(-CHAT_LIMIT)));
  } catch { /* приватный режим — просто живём без истории */ }
}

function restoreChat() {
  let list = [];
  try {
    list = JSON.parse(localStorage.getItem(CHAT_STORE) || "[]");
  } catch { return; }
  if (!Array.isArray(list) || !list.length) return;

  const log = $("chat-log");
  if (!log) return;
  log.innerHTML = "";
  for (const item of list) {
    if (!item || !item.text) continue;
    addMessage(item.kind || "system", item.text, { restore: true });
  }
}

function clearChatHistory() {
  try { localStorage.removeItem(CHAT_STORE); } catch { /* noop */ }
  const log = $("chat-log");
  if (log) log.innerHTML = "";
  addMessage("system", "Переписка очищена. Память Джинни на сервере осталась.");
}

/* ---------- утилиты ---------- */

const STATUS_RU = {
  ready: "готов",
  unavailable: "недоступен",
  unconfigured: "не настроен",
  missing: "нет данных",
  unknown: "неизвестно",
};

function statusLabel(value) { return STATUS_RU[value] || value || "неизвестно"; }
function statusClass(value) {
  if (value === "ready") return "ok";
  if (value === "unconfigured" || value === "missing") return "warn";
  return "err";
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function jsonFetch(url, options = {}) {
  const { timeoutMs = 120000, ...init } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...init,
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("сервер не ответил за 2 минуты");
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }

  let payload = null;
  try { payload = await response.json(); } catch { payload = null; }
  if (!response.ok) {
    throw new Error(payload?.error?.message || `Запрос не удался (HTTP ${response.status})`);
  }
  return payload;
}

/* ---------- часы ---------- */

function tickClock() {
  const now = new Date();
  const timeZone = STATE.settings?.timezone || "Europe/Moscow";
  $("clock-time").textContent = now.toLocaleTimeString("ru-RU", {
    timeZone, hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
  $("clock-date").textContent = now.toLocaleDateString("ru-RU", {
    timeZone, weekday: "long", day: "numeric", month: "long",
  });
}

/* ---------- сообщения ---------- */

function addMessage(kind, text, options = {}) {
  const log = $("chat-log");
  const article = el("article");
  const toward = options.toward || null;

  if (kind === "system") {
    article.className = "msg msg-system";
    article.append(el("p", "msg-text", text));
    log.append(article);
    log.scrollTop = log.scrollHeight;
    if (!options.restore) persistMessage("system", text);
    return article;
  }

  if (kind === "user") {
    article.className = `msg msg-user${toward ? ` toward-${toward}` : ""}`;
    const head = el("div", "msg-head");
  head.append(el("span", "who", "Ты"));
  article.append(head);
    article.append(el("p", "msg-text", text));
    log.append(article);
    log.scrollTop = log.scrollHeight;
    if (!options.restore) persistMessage("user", text);
    return article;
  }

  const isDron = kind === "dron";
  const isX = kind === "x";
  article.className = `msg ${isDron ? "msg-dron" : isX ? "msg-x" : "msg-genie"}`;
  const head = el("div", "msg-head");
  head.append(el("span", "who", isDron ? "Дрон" : isX ? "X" : "Джинни"));
  if (isDron && options.speakable !== false) {
    const button = el("button", "speak-btn", "🔈");
    button.type = "button";
    button.title = "Прослушать";
    button.addEventListener("click", () => speak(text, "dron"));
    head.append(button);
  }
  article.append(head, el("p", "msg-text", text));
  
  // Добавляем функциональные кнопки под сообщением
  if (!options.pending && kind !== "user") {
    const footer = el("div", "msg-footer");
    
    // Кнопка копирования
    const copyBtn = el("button", "action-btn", "📋");
    copyBtn.title = "Копировать";
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(text).then(() => {
        copyBtn.textContent = "✓";
        setTimeout(() => copyBtn.textContent = "📋", 1500);
      });
    });
    footer.append(copyBtn);
    
    // Токены и время (если есть в options)
    if (options.usage) {
      const stats = el("span", "msg-stats");
      const tokens = options.usage.prompt_tokens + options.usage.completion_tokens || 0;
      const seconds = Math.ceil(tokens / 50); // Примерно 50 токенов в секунду
      stats.textContent = `${tokens} токенов · ~${seconds}с`;
      footer.append(stats);
    }
    
    article.append(footer);
  }
  
  if (options.pending) article.classList.add("msg-pending");
  log.append(article);
  log.scrollTop = log.scrollHeight;
  if (!options.pending && !options.restore) persistMessage(kind, text);
  return article;
}

/* ---------- обращение по имени ---------- */

const ADDRESS_DRON = /^\s*(?:дрон|дроне|дрону)(?=[\s,!.…:;—–-]|$)[\s,!.…:;—–-]*/i;
const ADDRESS_GENIE = /^\s*(?:джин|джинн|джини|джинни|джину|джинна|джинни)(?=[\s,!.…:;—–-]|$)[\s,!.…:;—–-]*/i;
const ADDRESS_X = /^\s*(?:x|икс)(?=[\s,!.…:;—–-]|$)[\s,!.…:;—–-]*/i;

function detectAddress(text) {
  if (ADDRESS_DRON.test(text)) return "dron";
  if (ADDRESS_GENIE.test(text)) return "genie";
  if (ADDRESS_X.test(text)) return "x";
  return null;
}

function updateTargetBadge(addressed) {
  const badge = $("x-target");
  const names = { dron: "Дрон", genie: "Джинни", x: "X" };
  if (addressed) {
    badge.textContent = `обращение: ${names[addressed] || addressed}`;
    badge.className = "badge ok";
    return;
  }
  const fallback = STATE.settings?.default_agent === "genie" ? "Джинни" : "Дрон";
  badge.textContent = `по умолчанию: ${fallback}`;
  badge.className = "badge";
}

/* ---------- голос ---------- */

function playWavBase64(base64) {
  try {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    const url = URL.createObjectURL(new Blob([bytes], { type: "audio/wav" }));
    const audio = new Audio(url);
    audio.addEventListener("ended", () => URL.revokeObjectURL(url));
    audio.play().catch(() => URL.revokeObjectURL(url));
  } catch {
    /* озвучка не критична — текст уже показан */
  }
}

async function speak(text, agent) {
  if (agent !== "dron") {
    addMessage("system", "Голос Джинни включается кнопкой 🎙 внизу справа.");
    return;
  }
  try {
    const response = await fetch(API.dronSpeak, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok) {
      let message = `Синтез не удался (HTTP ${response.status})`;
      try { message = (await response.json())?.error?.message || message; } catch { /* noop */ }
      throw new Error(message);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.addEventListener("ended", () => URL.revokeObjectURL(url));
    await audio.play();
  } catch (error) {
    if (!String(error.message || "").includes("user didn't interact")) {
      addMessage("system", `Не смог озвучить: ${error.message}`);
    }
  }
}

/* ---------- микрофон ---------- */

const MIC = { recorder: null, stream: null, chunks: [], active: false };

const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

function pickMime() {
  if (!window.MediaRecorder) return null;
  for (const candidate of MIME_CANDIDATES) {
    if (MediaRecorder.isTypeSupported(candidate)) return candidate;
  }
  return "";
}

function micHint(text) { $("chat-hint").textContent = text; }

function releaseMic() {
  MIC.active = false;
  if (MIC.stream) {
    MIC.stream.getTracks().forEach((track) => track.stop());
    MIC.stream = null;
  }
  MIC.recorder = null;
  const button = $("mic");
  if (button) {
    button.textContent = "🎤";
    button.classList.remove("is-recording");
  }
}

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("браузер не даёт доступ к микрофону");
  const mime = pickMime();
  if (mime === null) throw new Error("MediaRecorder не поддерживается");

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  });
  const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
  MIC.stream = stream;
  MIC.recorder = recorder;
  MIC.chunks = [];
  recorder.addEventListener("dataavailable", (event) => {
    if (event.data && event.data.size) MIC.chunks.push(event.data);
  });
  recorder.start();
  MIC.active = true;
  const button = $("mic");
  button.textContent = "⏹";
  button.classList.add("is-recording");
  micHint("Слушаю… нажмите ⏹, чтобы закончить");
}

function stopRecording() {
  return new Promise((resolve) => {
    const recorder = MIC.recorder;
    if (!recorder) { resolve(null); return; }
    recorder.addEventListener("stop", () => {
      const blob = new Blob(MIC.chunks, { type: recorder.mimeType || "audio/webm" });
      MIC.chunks = [];
      releaseMic();
      resolve(blob);
    }, { once: true });
    recorder.stop();
  });
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",")[1] : result);
    };
    reader.onerror = () => reject(new Error("не удалось прочитать запись"));
    reader.readAsDataURL(blob);
  });
}

function formatFromMime(mime) {
  const value = String(mime || "").toLowerCase();
  if (value.includes("ogg")) return "ogg";
  if (value.includes("mp4")) return "mp4";
  if (value.includes("wav")) return "wav";
  return "webm";
}

async function toggleMic() {
  const button = $("mic");

  if (MIC.active) {
    button.disabled = true;
    try {
      const blob = await stopRecording();
      if (!blob || blob.size < 800) { micHint("Запись слишком короткая."); return; }
      micHint("Распознаю речь…");
      const audio = await blobToBase64(blob);
      const result = await jsonFetch(API.stt, {
        method: "POST",
        body: JSON.stringify({ audio, format: formatFromMime(blob.type) }),
      });
      const text = String(result.text || "").trim();
      if (!text) { micHint("Не разобрал речь. Попробуйте ещё раз."); return; }
      $("message").value = text;
      $("message").focus();
      micHint(`Распознано: «${text}» — проверьте и отправьте.`);
    } catch (error) {
      micHint(`Ошибка распознавания: ${error.message}`);
    } finally {
      button.disabled = false;
    }
    return;
  }

  try {
    await startRecording();
  } catch (error) {
    releaseMic();
    micHint(`Микрофон недоступен: ${error.message}`);
  }
}

/* ---------- отправка ---------- */

function stripAddress(text, agent) {
  const pattern = agent === "dron" ? ADDRESS_DRON : agent === "x" ? ADDRESS_X : ADDRESS_GENIE;
  return text.replace(pattern, "").trim() || text.trim();
}

async function send() {
  if (STATE.busy) {
    micHint("Ещё думаю над прошлым вопросом — секунду.");
    return;
  }
  const input = $("message");
  const raw = input.value.trim();
  if (!raw) return;

  const addressed = detectAddress(raw);
  addMessage("user", raw, { toward: addressed });
  input.value = "";
  updateTargetBadge(addressed);

  // X — внешний рабочий агент (харнесс или провайдер). Дрон остаётся по умолчанию.
  if (addressed === "x" || (STATE.xMode && !addressed)) {
    STATE.busy = true;
    $("send").classList.add("is-hidden");
    $("stop").classList.remove("is-hidden");

    const xText = stripAddress(raw, "x");
    STATE.history.x.push({ role: "user", content: xText });
    const pending = addMessage("x", "X думает…", { pending: true });

    try {
      bottomBarSetStatus("X работает…");
      const result = await jsonFetch(API.xChat, {
        method: "POST",
        body: JSON.stringify({
          message: xText,
          provider: STATE.xProvider || undefined,
          share_context: true,
          history: STATE.history.x.slice(-6, -1),
        }),
      });
      const meta = [
        result.provider,
        result.model,
        result.duration_s ? `${result.duration_s} c` : null,
        result.shared_context ? "контекст Дрона" : null,
      ].filter(Boolean).join(" · ");
      pending.querySelector(".msg-text").textContent = result.reply + (meta ? `\n\n[${meta}]` : "");
      pending.classList.remove("msg-pending");
      persistMessage("x", result.reply);
      STATE.history.x.push({ role: "assistant", content: result.reply });
    } catch (error) {
      pending.querySelector(".msg-text").textContent = `X не ответил: ${error.message}`;
      pending.classList.remove("msg-pending");
    } finally {
      bottomBarSetStatus("готов");
      STATE.busy = false;
      $("send").classList.remove("is-hidden");
      $("stop").classList.add("is-hidden");
    }
    return;
  }

  // Явно выбрана Джинни — облачный голосовой агент Yandex.
  if (addressed === "genie") {
    STATE.busy = true;
    $("send").classList.add("is-hidden");
    $("stop").classList.remove("is-hidden");

    const genieText = stripAddress(raw, "genie");
    STATE.history.genie.push({ role: "user", content: genieText });
    const pending = addMessage("genie", "Джинни думает…", { pending: true, speakable: false });

    try {
      const result = await jsonFetch(API.genieChat, {
        method: "POST",
        body: JSON.stringify({
          message: genieText,
          history: STATE.history.genie.slice(-10, -1),
          with_audio: Boolean($("autoplay-toggle")?.checked),
        }),
      });
      pending.querySelector(".msg-text").textContent = result.reply;
      pending.classList.remove("msg-pending");
      persistMessage("genie", result.reply);
      STATE.history.genie.push({ role: "assistant", content: result.reply });
      if ($("autoplay-toggle")?.checked && result.audio_wav) {
        playWavBase64(result.audio_wav);
      }
    } catch (error) {
      pending.querySelector(".msg-text").textContent = `Джинни не ответила: ${error.message}`;
      pending.classList.remove("msg-pending");
    } finally {
      STATE.busy = false;
      $("send").classList.remove("is-hidden");
      $("stop").classList.add("is-hidden");
    }
    return;
  }

  STATE.busy = true;
  $("send").classList.add("is-hidden");
  $("stop").classList.remove("is-hidden");

  const text = stripAddress(raw, "dron");
  STATE.history.dron.push({ role: "user", content: text });

  // Без обращения и с включённым дуэтом: сначала Джин, потом Дрон с резюме.
  const duet = !addressed && STATE.settings?.duet_mode !== false;

  try {
    if (duet) {
      const notice = addMessage("system", "Отвечают оба: сначала Джинни, потом Дрон с резюме…");
      let result;
      try {
        result = await jsonFetch(API.duet, {
          method: "POST",
          body: JSON.stringify({ message: text, history: STATE.history.dron.slice(-10, -1) }),
        });
      } finally {
        notice.remove();
      }

      const genie = result?.genie || {};
      if (genie.status === "ready" && genie.reply) {
        addMessage("genie", genie.reply);
      } else {
        addMessage("genie", genie.reason || "Джинни не ответила.");
      }

      const dronPart = result?.dron || {};
      if (dronPart.reply) {
        addMessage("dron", dronPart.reply);
        STATE.history.dron.push({ role: "assistant", content: dronPart.reply });
        if ($("autoplay-toggle")?.checked) await speak(dronPart.reply, "dron");
      } else {
        addMessage("dron", `Ошибка, чёрт побери. ${dronPart.error || "ответа нет"}`);
      }
      return;
    }

    const pending = addMessage("dron", "Думаю…", { pending: true, speakable: false });
    const result = await jsonFetch(API.dronChat, {
      method: "POST",
      body: JSON.stringify({ message: text, history: STATE.history.dron.slice(-10, -1) }),
    });
    const bubble = pending.querySelector(".msg-text");
    bubble.textContent = result.reply;
    pending.classList.remove("msg-pending");
    persistMessage("dron", result.reply);
    STATE.history.dron.push({ role: "assistant", content: result.reply });

    if ($("autoplay-toggle")?.checked) await speak(result.reply, "dron");
  } catch (error) {
    addMessage("dron", `Ошибка, чёрт побери. ${error.message}`);
  } finally {
    STATE.busy = false;
    $("send").classList.remove("is-hidden");
    $("stop").classList.add("is-hidden");
  }
}

/* ---------- модуль связи ---------- */

const COMMS_NAMES = {
  phone: "Телефон",
  telegram: "Telegram",
  max: "MAX",
  whatsapp: "WhatsApp",
};

function renderComms(state) {
  const box = $("comms-state");
  if (!box) return;

  const lines = [];
  lines.push(state?.dry_run ? "Режим: ЧЕРНОВИК — никто не звонит, ничего не уходит" : "Режим: боевой");
  const channels = state?.channels || {};
  for (const [key, info] of Object.entries(channels)) {
    const name = COMMS_NAMES[key] || key;
    const detail = info?.reason ? ` — ${info.reason}` : info?.device || info?.chat_id || "";
    lines.push(`${name}: ${info?.status || "—"}${detail}`);
  }
  box.textContent = lines.join("\n");
}

async function refreshComms() {
  try {
    renderComms(await jsonFetch(API.commsStatus));
  } catch (error) {
    const box = $("comms-state");
    if (box) box.textContent = `Связь недоступна: ${error.message}`;
  }
}

async function sendComms() {
  const channel = $("comms-channel")?.value || "telegram";
  const to = ($("comms-to")?.value || "").trim();
  const text = ($("comms-text")?.value || "").trim();
  if (!text) {
    addMessage("system", "Пустой текст сообщения — нечего отправлять.");
    return;
  }
  try {
    const result = await jsonFetch(API.commsSend, {
      method: "POST",
      body: JSON.stringify({ channel, to, text }),
    });
    if (result?.ok) {
      const mark = result.dry_run ? " (черновик)" : "";
      addMessage("system", `Отправлено в ${COMMS_NAMES[channel] || channel}${mark}.`);
      if ($("comms-text")) $("comms-text").value = "";
    } else {
      addMessage("system", `Не отправлено: ${result?.error || "неизвестная причина"}`);
    }
  } catch (error) {
    addMessage("system", `Связь: ${error.message}`);
  }
}

async function callContact() {
  const to = ($("comms-to")?.value || "").trim();
  if (!to) {
    addMessage("system", "Укажите номер, на который звонить.");
    return;
  }
  try {
    const result = await jsonFetch(API.commsCall, {
      method: "POST",
      body: JSON.stringify({ number: to }),
    });
    if (result?.ok) {
      const mark = result.dry_run ? " (черновик)" : "";
      addMessage("system", `Звоню на ${result.to}${mark}.`);
    } else {
      addMessage("system", `Звонок не удался: ${result?.error || "неизвестная причина"}`);
    }
  } catch (error) {
    addMessage("system", `Звонок: ${error.message}`);
  }
}

/* ---------- память Джинни ---------- */

function renderMemory(stats) {
  const box = $("memory-state");
  if (!box) return;

  box.innerHTML = "";
  const rows = [
    ["Реплик", String(stats?.turns ?? 0)],
    ["Сводка", stats?.summary_chars ? `${stats.summary_chars} симв.` : "ещё не сжата"],
    ["Обновлена", stats?.summary_updated || "—"],
    ["Порог", stats?.needs_compaction ? "пора сжимать" : "запас есть"],
  ];

  for (const [key, value] of rows) {
    const row = el("div", "mini-row");
    row.append(el("span", "", key), el("b", "", value));
    box.append(row);
  }

  const button = $("compact-memory");
  if (button) button.classList.toggle("primary", Boolean(stats?.needs_compaction));
}

async function compactMemory() {
  const button = $("compact-memory");
  if (button) button.disabled = true;
  addMessage("system", "Дрон сжимает память Джинни…");
  try {
    const result = await jsonFetch(API.memoryCompact, { method: "POST", timeoutMs: 240000 });
    if (result?.ok) {
      addMessage(
        "system",
        `Память сжата: ${result.compressed} реплик → сводка ${result.summary_chars} симв.`
      );
    } else {
      addMessage("system", `Сжать не вышло: ${result?.reason || "нечего сжимать"}`);
    }
    renderMemory(await jsonFetch(API.memory));
  } catch (error) {
    addMessage("system", `Ошибка сжатия памяти: ${error.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

/* ---------- панели агентов и состояние ---------- */

function renderHealth(health) {
  STATE.health = health;
  const components = health?.components || {};

  const badgeDron = $("badge-dron");
  badgeDron.textContent = statusLabel(components.dron);
  badgeDron.className = `badge ${statusClass(components.dron)}`;

  const badgeGenie = $("badge-genie");
  badgeGenie.textContent = statusLabel(components.genie);
  badgeGenie.className = `badge ${statusClass(components.genie)}`;

  const dronRows = [
    ["Модель", health?.agent_model || "—"],
    ["Голос", statusLabel(components.voice)],
    ["Слух", statusLabel(components.stt)],
    ["Vault", statusLabel(components.vault)],
    ["База", statusLabel(components.database)],
  ];
  const genieRows = [
    ["Голос", statusLabel(components.genie)],
    ["Ключ", components.genie === "ready" ? "настроен" : "не настроен"],
    ["Модель", health?.genie_model || "не задана"],
    ["Агент", health?.genie_prompt_id || "не задан"],
  ];

  fillMiniRows($("dron-state"), dronRows);
  fillMiniRows($("genie-state"), genieRows);

  $("diag").textContent = JSON.stringify(health, null, 2);
}

function fillMiniRows(container, rows) {
  if (!container) return;
  container.innerHTML = "";
  rows.forEach(([name, value]) => {
    const row = el("div", "mini-row");
    row.append(el("span", null, name), el("span", null, String(value)));
    container.append(row);
  });
}

/* ---------- приложение БАНК ---------- */

function renderBank(data) {
  const grid = $("bank-grid");
  const badge = $("bank-badge");
  grid.innerHTML = "";

  if (!data) {
    badge.textContent = "ошибка";
    badge.className = "badge err";
    grid.append(el("p", "error-text", "Финансы недоступны."));
    return;
  }

  const status = data.status;
  badge.textContent = statusLabel(status);
  badge.className = `badge ${statusClass(status)}`;

  if (status !== "ready" || !data.month) {
    grid.append(el("p", "error-text", "Каталог 60_FINANCE не найден или пуст."));
    return;
  }

  const month = data.month;

  // остаток
  const balanceCard = el("section", "card");
  balanceCard.append(cardHead("Остаток бюджета", data.period));
  const balanceBody = el("div", "card-body");
  balanceBody.append(el("p", "big-amount", `${month.closing_balance} ₽`));
  if (month.opening_balance !== null && month.opening_balance !== undefined) {
    balanceBody.append(el("p", "item-sub", `Перенос с прошлого месяца: ${month.opening_balance} ₽`));
  }
  balanceCard.append(balanceBody);
  grid.append(balanceCard);

  // взносы
  const contribCard = el("section", "card");
  contribCard.append(cardHead("Взносы", `${month.contributions_total} ₽`));
  const contribBody = el("div", "card-body");
  if (!month.contributions.length) {
    contribBody.append(el("p", "empty", "Взносов нет"));
  } else {
    month.contributions.forEach((row) => {
      const item = el("div", "status-row");
      item.append(el("span", "status-name", row.who), el("span", "status-value ok", `${row.rub} ₽`));
      contribBody.append(item);
    });
  }
  contribCard.append(contribBody);
  grid.append(contribCard);

  // расходы
  const expenseCard = el("section", "card");
  expenseCard.append(cardHead("Расходы", `${month.expenses_total} ₽`));
  const expenseBody = el("div", "card-body");
  const maxExpense = Math.max(1, ...month.expenses.map((e) => e.rub));
  if (!month.expenses.length) {
    expenseBody.append(el("p", "empty", "Расходов нет"));
  } else {
    const bars = el("div", "bars");
    month.expenses.forEach((row) => {
      const line = el("div", "bar-row");
      line.append(el("span", "bar-label", row.category));
      const track = el("div", "bar-track");
      const fill = el("div", `bar-fill${row.demo ? " genie" : ""}`);
      fill.style.width = `${Math.round((row.rub / maxExpense) * 100)}%`;
      track.append(fill);
      line.append(track, el("span", "bar-value", `${row.rub} ₽`));
      bars.append(line);
    });
    expenseBody.append(bars);
    if (month.demo_present) {
      expenseBody.append(el("p", "error-text", "Часть расходов — демо-разбивка (demo: true)."));
    }
  }
  expenseCard.append(expenseBody);
  grid.append(expenseCard);

  // сводка
  const sumCard = el("section", "card wide");
  sumCard.append(cardHead("Сводка месяца", data.period));
  const sumBody = el("div", "card-body");
  [
    ["Взносы", `${month.contributions_total} ₽`],
    ["Расходы", `${month.expenses_total} ₽`],
    ["Остаток", `${month.closing_balance} ₽`],
    ["Доступные месяцы", data.periods.join(", ") || "—"],
  ].forEach(([name, value]) => {
    const row = el("div", "status-row");
    row.append(el("span", "status-name", name), el("span", "status-value", value));
    sumBody.append(row);
  });
  sumCard.append(sumBody);
  grid.append(sumCard);

  // честно про будущее
  const soon = el("section", "card wide");
  soon.append(cardHead("Скоро", "не подключено"));
  const soonBody = el("div", "card-body");
  [
    "Финансовые новости",
    "Трейдинг и графики рынка",
    "ФИНАМ, Сбер и брокерские счета",
    "Учёт АНИС (₳) и журнал операций",
  ].forEach((text) => soonBody.append(el("p", "empty", `⏳ ${text}`)));
  soon.append(soonBody);
  grid.append(soon);
}

function cardHead(title, badge) {
  const head = el("div", "card-head");
  head.append(el("h2", null, title));
  if (badge) head.append(el("span", "badge", String(badge)));
  return head;
}

/* ---------- приложение I.VAN ---------- */

function renderIvan(data) {
  const grid = $("ivan-grid");
  const badge = $("ivan-badge");
  grid.innerHTML = "";

  if (!data) {
    badge.textContent = "ошибка";
    badge.className = "badge err";
    grid.append(el("p", "error-text", "Данные I.VAN недоступны."));
    return;
  }

  badge.textContent = statusLabel(data.homework_status);
  badge.className = `badge ${statusClass(data.homework_status)}`;

  // уроки
  const lessons = el("section", "card");
  lessons.append(cardHead("Уроки", statusLabel(data.lessons_status)));
  const lessonsBody = el("div", "card-body");
  lessonsBody.append(el("p", "empty", "Модуль уроков появится на этапе F."));
  lessons.append(lessonsBody);
  grid.append(lessons);

  // домашние задания
  viewListCard(grid, "Домашние задания", data.homework.map((t) => t.text), "Заданий нет", data.homework_status);

  // расписание
  viewListCard(
    grid,
    "Расписание Вани",
    data.schedule.map((e) => `${e.date || "—"} ${e.time || ""} · ${e.title}`.trim()),
    "Событий нет",
    data.schedule_status
  );

  // заметки
  viewListCard(grid, "Заметки", data.notes.map((n) => n.name), "Заметок нет", data.notes_status);

  // АНИС
  const anis = el("section", "card");
  anis.append(cardHead("АНИС Вани", statusLabel(data.anis?.status)));
  const anisBody = el("div", "card-body");
  anisBody.append(el("p", "empty", data.anis?.reason || "Данных нет"));
  anis.append(anisBody);
  grid.append(anis);
}

function viewListCard(grid, title, items, emptyText, status) {
  const card = el("section", "card");
  card.append(cardHead(title, statusLabel(status)));
  const body = el("div", "card-body");
  if (!items || !items.length) {
    body.append(el("p", "empty", emptyText));
  } else {
    items.slice(0, 8).forEach((text) => {
      const item = el("div", "item");
      const main = el("div", "item-main");
      main.append(el("div", "item-title", text));
      item.append(main);
      body.append(item);
    });
  }
  card.append(body);
  grid.append(card);
}

/* ---------- приложение СОВЕТ ---------- */

function renderCouncil(data) {
  const grid = $("council-grid");
  const badge = $("badge-council");
  const lead = $("council-lead");
  grid.innerHTML = "";

  if (!data) {
    badge.textContent = "ошибка";
    badge.className = "badge err";
    lead.textContent = "Сервер не ответил.";
    return;
  }

  const status = data.council?.status || "missing";
  badge.textContent = statusLabel(status);
  badge.className = `badge ${statusClass(status)}`;
  lead.textContent = status === "ready"
    ? `Повестка на ${data.council.date}. Источник: ${data.council.source}`
    : `Заметка на ${data.date} не найдена: создайте 80_FAMILY/council/${data.date}.md`;

  // финансы
  const month = data.finance?.month;
  const financeRows = [];
  if (data.finance?.status === "ready" && month) {
    if (month.opening_balance !== null && month.opening_balance !== undefined) {
      financeRows.push(["Перенос", `${month.opening_balance} ₽`]);
    }
    financeRows.push(["Взносы", `${month.contributions_total} ₽`]);
    financeRows.push(["Расходы", `${month.expenses_total} ₽`]);
    financeRows.push(["Остаток", `${month.closing_balance} ₽`, month.closing_balance >= 0 ? "ok" : "err"]);
    if (month.demo_present) financeRows.push(["Внимание", "есть демо-разбивка", "warn"]);
  } else {
    financeRows.push(["Состояние", statusLabel(data.finance?.status || "missing"), "warn"]);
  }
  grid.append(cardWithRows(`Финансы · ${data.finance?.period || "—"}`, financeRows));

  // разделы повестки
  const sections = data.council?.sections || [];
  sections.forEach((section) => {
    const card = el("section", "card");
    card.append(cardHead(section.title, section.items.length));
    const body = el("div", "card-body");
    if (!section.items.length) {
      body.append(el("p", "empty", "Пока пусто"));
    } else {
      section.items.forEach((item) => {
        const row = el("div", "item");
        const main = el("div", "item-main");
        main.append(el("div", "item-title", item.checked ? `✓ ${item.text}` : item.text));
        row.append(main);
        body.append(row);
      });
    }
    card.append(body);
    grid.append(card);
  });

  // задачи и расписание на завтра
  viewListCard(grid, `Задачи на ${data.tomorrow}`, (data.tasks_tomorrow || []).map((t) => t.text), "Задач нет", "ready");
  viewListCard(
    grid,
    `Расписание на ${data.tomorrow}`,
    (data.schedule_tomorrow || []).map((e) => `${e.time || "—"} · ${e.title}`),
    "Событий нет",
    "ready"
  );

  // АНИС и голос
  grid.append(cardWithRows("Поощрения и штрафы ₳", [
    ["Состояние", statusLabel(data.anis?.status), statusClass(data.anis?.status)],
    ["Причина", data.anis?.reason || "—"],
  ]));
  grid.append(cardWithRows("Решающий голос", [
    ["Правило", data.voting?.rule || "—"],
    ["Состояние", data.voting?.available ? "есть" : "не подсчитан", data.voting?.available ? "ok" : "warn"],
    ["Причина", data.voting?.reason || "—"],
  ]));
}

function cardWithRows(title, rows) {
  const card = el("section", "card");
  card.append(cardHead(title));
  const body = el("div", "card-body");
  rows.forEach(([name, value, cls]) => {
    const row = el("div", "status-row");
    row.append(el("span", "status-name", name));
    row.append(el("span", `status-value ${cls || ""}`, String(value)));
    body.append(row);
  });
  card.append(body);
  return card;
}

/* ---------- приложения: переключение ---------- */

const APP_LOADERS = {
  stage: async () => {},
  bank: async () => renderBank(await jsonFetch(API.finance)),
  ivan: async () => renderIvan(await jsonFetch(API.ivan)),
  council: async () => renderCouncil(await jsonFetch(API.council)),
};

async function switchApp(app) {
  STATE.app = app;
  ["stage", "ivan", "bank", "council"].forEach((name) => {
    $(`app-${name}`)?.classList.toggle("is-hidden", name !== app);
  });
  document.querySelectorAll(".app-btn").forEach((button) => {
    const active = button.dataset.app === app;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  });

  try {
    await APP_LOADERS[app]();
  } catch (error) {
    const target = { bank: $("bank-grid"), ivan: $("ivan-grid"), council: $("council-grid") }[app];
    if (target) {
      target.innerHTML = "";
      target.append(el("p", "error-text", `Не загрузилось: ${error.message}`));
    }
  }
}

/* ---------- настройки ---------- */

function updateCollapseArrows() {
  const collapsed = Boolean(STATE.settings?.panels_collapsed);
  const dron = document.querySelector('.panel-collapse[data-panel="dron"]');
  const genie = document.querySelector('.panel-collapse[data-panel="genie"]');
  if (dron) {
    dron.textContent = collapsed ? "▶" : "◀";
    dron.title = collapsed ? "Развернуть панель Дрона" : "Свернуть панель Дрона";
  }
  if (genie) {
    genie.textContent = collapsed ? "◀" : "▶";
    genie.title = collapsed ? "Развернуть панель Джина" : "Свернуть панель Джина";
  }
}

function applySettings(settings) {
  STATE.settings = settings;
  document.body.dataset.theme = settings.theme || "neon";
  document.body.classList.toggle("large-mode", Boolean(settings.large_mode));
  document.documentElement.style.setProperty("--scale", String(settings.scale || 1));

  const stage = $("app-stage");
  if (stage) stage.classList.toggle("panels-collapsed", Boolean(settings.panels_collapsed));

  if ($("profile-select")) $("profile-select").value = settings.profile || "dron";
  if ($("set-theme")) $("set-theme").value = settings.theme || "neon";
  if ($("set-default-agent")) $("set-default-agent").value = settings.default_agent || "dron";
  if ($("set-pitch")) $("set-pitch").value = String(settings.voice_pitch_factor ?? 0.88);
  if ($("autoplay-toggle")) $("autoplay-toggle").checked = Boolean(settings.voice_autoplay);
  if ($("set-autoplay")) $("set-autoplay").checked = Boolean(settings.voice_autoplay);
  if ($("set-animation")) $("set-animation").checked = Boolean(settings.animation);
  if ($("set-large")) $("set-large").checked = Boolean(settings.large_mode);
  if ($("set-voice")) $("set-voice").value = settings.voice_model || "";
  if ($("set-panels")) $("set-panels").checked = Boolean(settings.panels_collapsed);
  if ($("set-duet")) $("set-duet").checked = settings.duet_mode !== false;

  if ($("set-scale")) $("set-scale").value = String(settings.scale ?? 1);
  if ($("scale-value")) $("scale-value").textContent = Number(settings.scale ?? 1).toFixed(2);
  if ($("set-temperature")) $("set-temperature").value = String(settings.dron_temperature ?? 0.35);
  if ($("temp-value")) $("temp-value").textContent = Number(settings.dron_temperature ?? 0.35).toFixed(2);

  updateCollapseArrows();
  updateTargetBadge(null);
  renderControlPanel(settings);
}

async function patchSettings(patch) {
  try {
    applySettings(await jsonFetch(API.settings, { method: "PATCH", body: JSON.stringify(patch) }));
  } catch (error) {
    addMessage("system", `Настройки не сохранились: ${error.message}`);
  }
}

async function loadVoiceOptions(current) {
  try {
    const info = await jsonFetch(API.voice);
    const select = $("set-voice");
    select.innerHTML = "";
    (info.models || []).forEach((name) => {
      const option = el("option", null, name.replace("ru_RU-", "").replace("-medium", ""));
      option.value = name;
      select.append(option);
    });
    if (current) select.value = current;
  } catch { /* необязательно */ }
}

/* ---------- клавиатура ---------- */

function initKeyboard() {
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (MIC.active) { stopRecording(); micHint("Запись отменена."); event.preventDefault(); return; }
      if (!$("drawer").classList.contains("is-hidden")) { closeDrawer(); event.preventDefault(); }
      return;
    }

    const target = event.target;
    const isField = target instanceof HTMLTextAreaElement
      || target instanceof HTMLInputElement
      || target instanceof HTMLSelectElement;
    if (isField) return;

    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      const buttons = [...document.querySelectorAll(".app-btn")];
      const index = buttons.findIndex((button) => button.classList.contains("is-active"));
      if (index < 0) return;
      const next = event.key === "ArrowRight"
        ? (index + 1) % buttons.length
        : (index - 1 + buttons.length) % buttons.length;
      buttons[next].focus();
      switchApp(buttons[next].dataset.app);
      event.preventDefault();
    }
  });
}

function closeDrawer() {
  $("drawer").classList.add("is-hidden");
  $("open-settings")?.focus();
}

/* ---------- старт ---------- */

/* Обработчики навешиваем синхронно и сразу: даже если сеть, настройки или
   голосовой модуль затупят, «Отправить» и Enter должны работать. */

let coreWired = false;

function on(id, event, handler) {
  const node = $(id);
  if (node) node.addEventListener(event, handler);
}

/* ---------- нижний бар и быстрая панель ---------- */

function bottomBarSetAgent(agent) {
  const labels = { dron: "Дрон", genie: "Джин", x: "X" };
  STATE.xMode = agent === "x";
  ["dron", "genie", "x"].forEach((name) => {
    $(`bar-${name}`)?.classList.toggle("is-active", name === agent);
  });
  const cp = $("cp-agent");
  if (cp) cp.textContent = labels[agent] || agent;
  updateTargetBadge(agent);
  const box = $("message");
  if (box) {
    const prefix = agent === "dron" ? "Дрон, " : agent === "genie" ? "Джинни, " : "";
    if (prefix && !box.value.startsWith(prefix)) box.value = prefix;
    box.focus();
  }
}

function bottomBarSetStatus(text) {
  const node = $("bar-status");
  if (node) node.textContent = text;
}

function renderControlPanel(settings) {
  if (!settings) return;
  const voice = $("cp-voice");
  if (voice) voice.textContent = settings.voice_model || "—";
  const pitch = $("cp-pitch");
  if (pitch) pitch.textContent = String(settings.voice_pitch_factor ?? "—");
  const temp = $("cp-temp");
  if (temp) temp.textContent = String(settings.dron_temperature ?? "—");
  const auto = $("cp-autoplay");
  if (auto) auto.textContent = settings.voice_autoplay ? "вкл" : "выкл";
  const agent = $("cp-agent");
  if (agent) agent.textContent = settings.default_agent === "genie" ? "Джин" : "Дрон";
  $("bar-voice")?.classList.toggle("is-active", Boolean(settings.voice_autoplay));
}

function providersSection() {
  const panel = $("control-panel");
  if (!panel) return null;
  let section = $("cp-providers");
  if (section) return section;

  section = el("div", "cp-providers");
  section.id = "cp-providers";
  const head = el("div", "cp-providers-head");
  head.append(el("span", "cp-title", "Провайдеры и модели"));
  const button = el("button", "cp-refresh", "Проверить");
  button.type = "button";
  button.addEventListener("click", () => refreshProviders());
  head.append(button);
  section.append(head, el("p", "cp-empty", "Ещё не проверял. Нажмите «Проверить»."));

  const settings = $("cp-settings");
  if (settings && settings.parentElement === panel) panel.insertBefore(section, settings);
  else panel.append(section);
  return section;
}

function renderProvidersTable(providers) {
  const section = providersSection();
  if (!section || !Array.isArray(providers)) return;
  section.querySelectorAll(".prov-table, .cp-empty").forEach((node) => node.remove());

  const table = el("table", "prov-table");
  const headRow = el("tr");
  ["Провайдер", "План", "Статус"].forEach((label) => headRow.append(el("th", "", label)));
  const thead = el("thead");
  thead.append(headRow);
  const tbody = el("tbody");

  providers.forEach((provider) => {
    const row = el("tr");
    const name = el("td");
    name.append(el("span", "prov-name", provider.name || provider.id));
    const models = (provider.models || []).slice(0, 2).join(", ");
    if (models) name.append(el("span", "prov-models", models));
    row.append(name);

    const plan = el("td", "prov-plan");
    plan.textContent = provider.free_tier ? `бесплатно · ${provider.plan || ""}` : provider.plan || "—";
    row.append(plan);

    const status = el("td");
    const badge = el("span", `prov-badge is-${provider.status || (provider.connected ? "ready" : "unconfigured")}`);
    const labels = { ready: "готов", unconfigured: "нет ключа", unreachable: "недоступен" };
    badge.textContent = provider.verify && !provider.checked_at ? "не проверен" : labels[provider.status] || "не проверен";
    if (provider.latency_ms) badge.title = `${provider.latency_ms} мс`;
    status.append(badge);
    row.append(status);
    tbody.append(row);
  });

  table.append(thead, tbody);
  section.append(table);
}

async function loadProvidersTable() {
  try {
    const data = await jsonFetch(API.providersRegistry);
    renderProvidersTable(data.providers || []);
  } catch {
    /* реестр не критичен для чата */
  }
}

async function refreshProviders() {
  try {
    bottomBarSetStatus("проверяю провайдеров…");
    const data = await jsonFetch(API.providersRefresh, { method: "POST" });
    renderProvidersTable(data.providers || []);
    const changes = (data.changes || []).join("; ") || "изменений нет";
    const ready = (data.ready || []).join(", ") || "нет";
    addMessage("system", `Реестр проверен. Готовы: ${ready}. ${changes}`);
  } catch (error) {
    addMessage("system", `Реестр: ошибка проверки (${error.message}).`);
  } finally {
    bottomBarSetStatus("готов");
  }
}

async function loadXProviders() {
  try {
    const data = await jsonFetch(API.xProviders);
    const list = data.providers || [];
    const ready = list.filter((item) => item.ready);
    STATE.xProvider = (ready[0] || list[0] || {}).id || null;
    const summary = ready.map((item) => item.name).join(", ") || "нет готовых";
    addMessage("system", `X готов: ${summary}. Пиши «X, …» — отправлю в выбранного провайдера.`);
    return list;
  } catch (error) {
    STATE.xProvider = "local";
    addMessage("system", `X: провайдеры недоступны (${error.message}). Попробую локальную модель.`);
    return [];
  }
}

function initBottomBar() {
  on("bar-dron", "click", () => bottomBarSetAgent("dron"));
  on("bar-genie", "click", () => bottomBarSetAgent("genie"));
  on("bar-x", "click", () => {
    bottomBarSetAgent("x");
    loadXProviders();
  });

  on("bar-hear", "click", () => {
    $("bar-hear")?.classList.toggle("is-active");
    toggleMic();
  });

  on("bar-voice", "click", () => {
    const next = !STATE.settings?.voice_autoplay;
    patchSettings({ voice_autoplay: next });
  });

  const panel = $("control-panel");
  on("bar-panel", "click", () => {
    const open = panel?.classList.toggle("is-open");
    $("bar-panel")?.classList.toggle("is-active", Boolean(open));
    $("bar-panel")?.setAttribute("aria-expanded", open ? "true" : "false");
    panel?.setAttribute("aria-hidden", open ? "false" : "true");
    if (open) {
      renderControlPanel(STATE.settings);
      loadProvidersTable();
    }
  });

  on("cp-settings", "click", () => {
    $("drawer")?.classList.remove("is-hidden");
    $("close-settings")?.focus();
  });
  on("cp-compact", "click", () => compactMemory());
}

function wireCore() {
  if (coreWired) return;
  coreWired = true;

  restoreChat();
  initBottomBar();
  bottomBarSetStatus("готов");

  try {
    // 1. Самое важное: ввод и отправка.
    const composer = $("composer");
    if (composer) composer.addEventListener("submit", (event) => { event.preventDefault(); send(); });

    const input = $("message");
    if (input) {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); send(); }
      });
      input.addEventListener("input", () => updateTargetBadge(detectAddress(input.value)));
    }

    on("mic", "click", toggleMic);
    on("compact-memory", "click", compactMemory);
    on("clear-chat", "click", clearChatHistory);
    on("comms-send", "click", sendComms);
    on("comms-call", "click", callContact);
    on("open-settings", "click", () => { refreshComms(); });
    on("stop", "click", () => addMessage("system", "Остановка запроса появится на этапе C."));

    on("ask-dron", "click", () => {
      const box = $("message");
      if (box) { box.value = "Дрон, "; box.focus(); }
      updateTargetBadge("dron");
    });
    on("ask-genie", "click", () => {
      const box = $("message");
      if (box) { box.value = "Джинни, "; box.focus(); }
      updateTargetBadge("genie");
    });

    // 2. Навигация и панели.
    document.querySelectorAll(".app-btn").forEach((button) => {
      button.addEventListener("click", () => switchApp(button.dataset.app));
    });
    document.querySelectorAll(".panel-collapse").forEach((button) => {
      button.addEventListener("click", () => {
        patchSettings({ panels_collapsed: !STATE.settings?.panels_collapsed });
      });
    });

    // 3. Настройки и горячие клавиши.
    on("autoplay-toggle", "change", (event) => patchSettings({ voice_autoplay: event.target.checked }));
    on("profile-select", "change", (event) => patchSettings({ profile: event.target.value }));
    on("toggle-large", "click", () => patchSettings({ large_mode: !document.body.classList.contains("large-mode") }));

    on("open-settings", "click", () => {
      $("drawer")?.classList.remove("is-hidden");
      $("close-settings")?.focus();
    });
    on("close-settings", "click", closeDrawer);
    on("drawer", "click", (event) => { if (event.target === $("drawer")) closeDrawer(); });

    on("set-theme", "change", (event) => patchSettings({ theme: event.target.value }));
    on("set-default-agent", "change", (event) => patchSettings({ default_agent: event.target.value }));
    on("set-voice", "change", (event) => patchSettings({ voice_model: event.target.value }));
    on("set-pitch", "change", (event) => patchSettings({ voice_pitch_factor: Number(event.target.value) }));
    on("set-autoplay", "change", (event) => patchSettings({ voice_autoplay: event.target.checked }));
    on("set-animation", "change", (event) => patchSettings({ animation: event.target.checked }));
    on("set-large", "change", (event) => patchSettings({ large_mode: event.target.checked }));
    on("set-panels", "change", (event) => patchSettings({ panels_collapsed: event.target.checked }));
    on("set-duet", "change", (event) => patchSettings({ duet_mode: event.target.checked }));
    on("set-scale", "input", (event) => {
      if ($("scale-value")) $("scale-value").textContent = Number(event.target.value).toFixed(2);
    });
    on("set-scale", "change", (event) => patchSettings({ scale: Number(event.target.value) }));
    on("set-temperature", "input", (event) => {
      if ($("temp-value")) $("temp-value").textContent = Number(event.target.value).toFixed(2);
    });
    on("set-temperature", "change", (event) => patchSettings({ dron_temperature: Number(event.target.value) }));

    initKeyboard();
    window.__appReady = true;
  } catch (error) {
    window.__appStage?.("wire", error);
  }
}

async function boot() {
  tickClock();
  setInterval(tickClock, 1000);

  try {
    applySettings(await jsonFetch(API.settings));
    await loadVoiceOptions(STATE.settings.voice_model);
  } catch (error) {
    addMessage("system", `Настройки не загрузились: ${error.message}`);
  }

  try {
    const response = await fetch(API.phrases);
    if (response.ok) STATE.phrases = await response.json();
  } catch { /* необязательно */ }

  try {
    renderHealth(await jsonFetch(API.health));
  } catch (error) {
    addMessage("system", `Диагностика недоступна: ${error.message}`);
  }

  try {
    renderMemory(await jsonFetch(API.memory));
  } catch { /* память покажет «—» */ }
  setInterval(async () => {
    try { renderHealth(await jsonFetch(API.health)); } catch { /* тихо */ }
  }, 30000);

  window.__bootDone = true;
}

function start() {
  wireCore();
  boot().catch((error) => window.__appStage?.("boot", error));
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start);
} else {
  start();
}
