/* GENIE VOICE — голосовой разговор с Джинни через /ws/genie.
   Микрофон → PCM16 44 100 Гц → сервер → Yandex Realtime.
   Обратно: текст, транскрипт и голос Джинни.
   Ключ Yandex живёт на сервере, в браузере его нет. */

(function () {
  const RATE = 44100;
  const CHUNK = 4096;

  const state = {
    ws: null,
    ctx: null,
    stream: null,
    source: null,
    node: null,
    sink: null,
    nextTime: 0,
    playing: new Set(),
    open: false,
    partial: "",
    finalText: "",
  };

  let ui = null;

  /* ---------- утилиты ---------- */

  function b64FromBytes(bytes) {
    let binary = "";
    const step = 0x8000;
    for (let i = 0; i < bytes.length; i += step) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
    }
    return btoa(binary);
  }

  function bytesFromB64(b64) {
    const binary = atob(b64);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) out[i] = binary.charCodeAt(i);
    return out;
  }

  function floatToInt16(f32) {
    const out = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i += 1) {
      const v = Math.max(-1, Math.min(1, f32[i]));
      out[i] = v < 0 ? v * 0x8000 : v * 0x7fff;
    }
    return out;
  }

  function resampleLinear(f32, from, to) {
    if (from === to) return f32;
    const ratio = from / to;
    const length = Math.max(1, Math.round(f32.length / ratio));
    const out = new Float32Array(length);
    for (let i = 0; i < length; i += 1) {
      const pos = i * ratio;
      const idx = Math.floor(pos);
      const frac = pos - idx;
      const a = f32[idx] || 0;
      const b = f32[idx + 1] || a;
      out[i] = a + (b - a) * frac;
    }
    return out;
  }

  /* ---------- интерфейс ---------- */

  function buildUi() {
    const panel = document.createElement("section");
    panel.className = "gv-panel is-hidden";
    panel.id = "gv-panel";
    panel.innerHTML = `
      <div class="gv-head">
        <span class="gv-dot" id="gv-dot"></span>
        <strong>Джинни · голос</strong>
        <span class="gv-state" id="gv-state">выключено</span>
        <button type="button" class="control tab-btn gv-close" id="gv-close" aria-label="Закрыть">✕</button>
      </div>
      <div class="gv-body">
        <p class="gv-line"><span class="gv-label">Ты:</span> <span id="gv-user">—</span></p>
        <p class="gv-line"><span class="gv-label">Джинни:</span> <span id="gv-genie">—</span></p>
      </div>
      <div class="gv-actions">
        <button type="button" class="control primary" id="gv-toggle">🎙 Говорить</button>
        <button type="button" class="control danger is-hidden" id="gv-stop">⏹ Стоп</button>
      </div>
      <p class="gv-hint" id="gv-hint">Нажмите «Говорить» и просто говорите — Джинни слушает без кнопок.</p>
    `;
    document.body.append(panel);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "control";
    button.id = "genie-voice";
    button.title = "Голосовой разговор с Джинни (Yandex Realtime)";
    button.textContent = "🎙 Джинни";

    const actions = document.querySelector(".composer-actions");
    if (actions) actions.insertBefore(button, actions.querySelector("#send"));

    ui = {
      panel,
      dot: panel.querySelector("#gv-dot"),
      state: panel.querySelector("#gv-state"),
      user: panel.querySelector("#gv-user"),
      genie: panel.querySelector("#gv-genie"),
      hint: panel.querySelector("#gv-hint"),
      toggle: panel.querySelector("#gv-toggle"),
      stop: panel.querySelector("#gv-stop"),
      close: panel.querySelector("#gv-close"),
      button,
    };

    ui.toggle.addEventListener("click", () => (state.open ? stop() : start()));
    ui.stop.addEventListener("click", stop);
    ui.close.addEventListener("click", stop);
    button.addEventListener("click", () => {
      ui.panel.classList.remove("is-hidden");
      if (!state.open) start();
    });
  }

  function setStatus(text, kind) {
    if (!ui) return;
    ui.state.textContent = text;
    ui.dot.className = `gv-dot${kind ? ` is-${kind}` : ""}`;
  }

  function setHint(text) {
    if (ui) ui.hint.textContent = text;
  }

  /* ---------- микрофон ---------- */

  async function openMic(ctx) {
    state.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    state.source = ctx.createMediaStreamSource(state.stream);

    state.node = ctx.createScriptProcessor(CHUNK, 1, 1);
    state.node.onaudioprocess = (event) => {
      if (!state.ws || state.ws.readyState !== WebSocket.OPEN) return;
      const raw = event.inputBuffer.getChannelData(0);
      const pcm = floatToInt16(resampleLinear(raw, ctx.sampleRate, RATE));
      const bytes = new Uint8Array(pcm.buffer);
      state.ws.send(JSON.stringify({ type: "audio", pcm: b64FromBytes(bytes) }));
    };

    // ScriptProcessor работает только при подключении к выходу,
    // поэтому глушим его нулевой громкостью — иначе будет эхо.
    state.sink = ctx.createGain();
    state.sink.gain.value = 0;
    state.source.connect(state.node);
    state.node.connect(state.sink);
    state.sink.connect(ctx.destination);
  }

  /* ---------- воспроизведение ---------- */

  function playPcm(b64) {
    const ctx = state.ctx;
    if (!ctx) return;

    const bytes = bytesFromB64(b64);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const count = Math.floor(bytes.byteLength / 2);
    const f32 = new Float32Array(count);
    for (let i = 0; i < count; i += 1) f32[i] = view.getInt16(i * 2, true) / 0x8000;

    const samples = resampleLinear(f32, RATE, ctx.sampleRate);
    const buffer = ctx.createBuffer(1, samples.length, ctx.sampleRate);
    buffer.copyToChannel(samples, 0);

    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);

    const now = ctx.currentTime;
    const startAt = Math.max(state.nextTime, now + 0.03);
    source.start(startAt);
    state.nextTime = startAt + buffer.duration;

    state.playing.add(source);
    source.onended = () => state.playing.delete(source);
  }

  function flushAudio() {
    state.playing.forEach((source) => {
      try {
        source.stop();
      } catch (_) {
        /* уже остановлен */
      }
    });
    state.playing.clear();
    if (state.ctx) state.nextTime = state.ctx.currentTime;
  }

  /* ---------- websocket ---------- */

  function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/genie`);
    state.ws = ws;

    ws.onopen = () => setStatus("подключаюсь…", "wait");

    ws.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (_) {
        return;
      }

      if (data.type === "ready") {
        setStatus("слушаю", "on");
        setHint("Говорите. Джинни отвечает голосом, можно перебивать.");
        ui.user.textContent = "—";
        ui.genie.textContent = "—";
        state.finalText = "";
        state.partial = "";
      } else if (data.type === "user_text") {
        ui.user.textContent = data.text;
        state.finalText = "";
        state.partial = "";
        ui.genie.textContent = "…";
      } else if (data.type === "text") {
        state.partial += data.text;
        ui.genie.textContent = state.partial;
        setStatus("говорит", "talk");
      } else if (data.type === "audio") {
        playPcm(data.pcm);
      } else if (data.type === "interrupt") {
        flushAudio();
        setStatus("слушаю", "on");
      } else if (data.type === "done") {
        if (state.partial.trim()) {
          state.finalText = state.partial.trim();
          if (typeof addMessage === "function") {
            addMessage("genie", state.finalText, { speakable: false });
          }
        }
        setStatus("слушаю", "on");
      } else if (data.type === "error") {
        setStatus("ошибка", "err");
        setHint(data.message || "Ошибка голосового канала.");
      }
    };

    ws.onerror = () => {
      setStatus("нет связи", "err");
      setHint("Не удалось открыть голосовой канал /ws/genie.");
    };

    ws.onclose = () => {
      setStatus("выключено");
      if (state.open) setHint("Канал закрыт. Нажмите «Говорить», чтобы начать снова.");
    };
  }

  /* ---------- старт / стоп ---------- */

  async function start() {
    if (state.open) return;
    state.open = true;

    ui.panel.classList.remove("is-hidden");
    ui.toggle.textContent = "⏸ Пауза";
    ui.stop.classList.remove("is-hidden");
    setStatus("запускаюсь…", "wait");
    setHint("Разрешите доступ к микрофону, если браузер спросит.");

    try {
      state.ctx = new AudioContext({ sampleRate: RATE });
      if (state.ctx.state === "suspended") await state.ctx.resume();
      await openMic(state.ctx);
      connect();
    } catch (error) {
      state.open = false;
      setStatus("ошибка", "err");
      setHint(`Микрофон недоступен: ${error.message}`);
    }
  }

  function stop() {
    if (!state.open) {
      if (ui) ui.panel.classList.add("is-hidden");
      return;
    }
    state.open = false;

    flushAudio();

    if (state.node) {
      state.node.onaudioprocess = null;
      try {
        state.node.disconnect();
      } catch (_) {
        /* уже отключён */
      }
    }
    if (state.source) {
      try {
        state.source.disconnect();
      } catch (_) {
        /* уже отключён */
      }
    }
    if (state.sink) {
      try {
        state.sink.disconnect();
      } catch (_) {
        /* уже отключён */
      }
    }
    if (state.stream) {
      state.stream.getTracks().forEach((track) => track.stop());
    }
    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
      state.ws.send(JSON.stringify({ type: "close" }));
      state.ws.close();
    }
    if (state.ctx) state.ctx.close().catch(() => {});

    state.ws = null;
    state.ctx = null;
    state.stream = null;
    state.source = null;
    state.node = null;
    state.sink = null;

    if (ui) {
      ui.toggle.textContent = "🎙 Говорить";
      ui.stop.classList.add("is-hidden");
      setStatus("выключено");
      setHint("Разговор завершён. Нажмите «Говорить», чтобы продолжить.");
    }
  }

  /* ---------- инициализация ---------- */

  function init() {
    if (!document.getElementById("chat-log")) return;
    buildUi();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
