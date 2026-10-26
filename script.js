/* =========================================================
   Circle Dance — interactions
   - scales the 1512 × 982 design to the window
   - hash routing between hero / history / infographics / gallery
   - hover (or tap / focus) a figure to show its panel content
   - sound toggle (plays assets/ambience.mp3 if present,
     otherwise a soft generated outdoor ambience)
   - gallery: upload a photo + memory, it joins the circle
   ========================================================= */

(() => {
  "use strict";

  const STAGE_W = 1512;
  const STAGE_H = 982;
  const VIEWS = ["hero", "history", "infographics", "gallery"];

  /* ---------------------------------------------------------
     Content for each of the 11 figures.
     Swap in a different image per figure when you have it.
     In the Figma file all 11 history frames use the same chart.
     Infographic images weren't designed yet, so they show the
     figure number until you add an image path.
     --------------------------------------------------------- */
  const FIGURES = Array.from({ length: 11 }, (_, i) => ({
    history: { img: "assets/info-1.png", alt: "Chart of the sculpture's figures and the people gathered around them" },
    infographics: { img: null, alt: "" },
  }));

  /* Dot centres from the Figma HISTORY PAGE frame (stage coords). */
  const DOTS = [
    [1119, 560], [1236, 547], [1337, 534], [1380, 482], [1350, 434], [1280, 434],
    [1189, 414], [1084, 427], [994, 440], [960, 495], [1003, 521],
  ];
  const FIGURES_ORIGIN = [900, 248];
  const DOT_SIZE = 49;

  /* Gallery tile slots from the GALLERY PAGE frame, clockwise from the top. */
  const TILES = [
    { x: 883, y: 229 }, { x: 1055, y: 229, w: 132 }, { x: 1261, y: 286, w: 132 }, { x: 1344, y: 396 },
    { x: 1273, y: 485 }, { x: 1187, y: 571, w: 134 }, { x: 1084, y: 646 }, { x: 973, y: 670 },
    { x: 817, y: 662 }, { x: 817, y: 532 }, { x: 741, y: 443 }, { x: 779, y: 320, square: true },
  ];
  const STORAGE_KEY = "circle-dance-gallery-v1";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ---------- Scale the stage to the window ---------- */
  const fit = () => {
    const s = Math.min(window.innerWidth / STAGE_W, window.innerHeight / STAGE_H);
    document.documentElement.style.setProperty("--scale", s.toFixed(4));
  };
  window.addEventListener("resize", fit);
  fit();

  /* ---------- Routing ---------- */
  const show = (name) => {
    const view = VIEWS.includes(name) ? name : "hero";
    document.body.dataset.view = view;
    $$(".view").forEach((el) => {
      const on = el.dataset.view === view;
      el.classList.toggle("is-active", on);
      el.inert = !on;
    });
    $$(".nav__btn").forEach((btn) => {
      const on = btn.dataset.nav === view;
      btn.classList.toggle("is-current", on);
      if (on) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
    resetPanels();
  };
  const route = () => show(location.hash.replace("#", ""));
  window.addEventListener("hashchange", route);

  $$("[data-go]").forEach((el) =>
    el.addEventListener("click", () => { location.hash = el.dataset.go; })
  );

  /* ---------- Figures + panels ---------- */
  const buildFigures = (section) => {
    const kind = section.dataset.view; // "history" | "infographics"
    const wrap = $("[data-figures]", section);
    const panel = $(".panel", section);
    const img = $(".panel__img", panel);
    const prompt = $(".panel__prompt", panel);
    const label = $(".panel__figure-label", panel);
    const defaultPrompt = prompt.textContent;

    const activate = (i) => {
      $$(".dot", wrap).forEach((d, j) => d.classList.toggle("is-active", j === i));
      const item = FIGURES[i][kind];
      const num = String(i + 1).padStart(2, "0");
      panel.classList.add("has-content");
      label.textContent = `FIGURE ${num} / 11`;
      if (item && item.img) {
        panel.classList.remove("is-empty");
        if (img.getAttribute("src") !== item.img) img.src = item.img;
        img.alt = item.alt || "";
        prompt.textContent = defaultPrompt;
      } else {
        panel.classList.add("is-empty");
        img.removeAttribute("src");
        img.alt = "";
        prompt.textContent = `FIGURE ${num}`;
        label.textContent = "";
      }
    };

    const clear = () => {
      $$(".dot", wrap).forEach((d) => d.classList.remove("is-active"));
      panel.classList.remove("has-content", "is-empty");
      prompt.textContent = defaultPrompt;
      label.textContent = "";
    };

    DOTS.forEach(([cx, cy], i) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "dot";
      dot.style.setProperty("--i", i);
      dot.style.left = `${cx - FIGURES_ORIGIN[0] - DOT_SIZE / 2}px`;
      dot.style.top = `${cy - FIGURES_ORIGIN[1] - DOT_SIZE / 2}px`;
      dot.setAttribute("aria-label", `Figure ${i + 1}`);
      dot.innerHTML = '<img src="assets/dot.png" width="49" height="49" alt="">';
      dot.addEventListener("mouseenter", () => activate(i));
      dot.addEventListener("focus", () => activate(i));
      dot.addEventListener("click", () => activate(i));
      wrap.appendChild(dot);
    });

    // Return to "HOVER A FIGURE" once the pointer leaves the sculpture.
    wrap.addEventListener("mouseleave", clear);
    wrap.addEventListener("focusout", (e) => { if (!wrap.contains(e.relatedTarget)) clear(); });

    section._clear = clear;
  };

  $$(".view--explore").forEach(buildFigures);
  const resetPanels = () => $$(".view--explore").forEach((s) => s._clear && s._clear());

  /* ---------- Sound ---------- */
  const soundBtn = $("#soundToggle");
  const soundLabel = $("#soundLabel");
  let soundOn = false;
  let fileAudio = null;
  let useFile = true;
  let synth = null;

  const makeSynth = () => {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    const ctx = new Ctx();

    // ~4 s of soft brown noise, looped — reads as wind and distant campus hum.
    const len = ctx.sampleRate * 4;
    const buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      let last = 0;
      for (let i = 0; i < len; i++) {
        last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02;
        d[i] = last * 3.2;
      }
    }
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;

    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 700;

    // Slow swell, like breeze moving through trees.
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    lfo.frequency.value = 0.08;
    lfoGain.gain.value = 320;
    lfo.connect(lfoGain).connect(filter.frequency);

    const master = ctx.createGain();
    master.gain.value = 0;
    src.connect(filter).connect(master).connect(ctx.destination);
    src.start();
    lfo.start();

    // Occasional soft bird chirps.
    let chirpTimer = null;
    const chirp = () => {
      const t = ctx.currentTime;
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      const base = 2400 + Math.random() * 1600;
      o.type = "sine";
      o.frequency.setValueAtTime(base, t);
      o.frequency.exponentialRampToValueAtTime(base * 1.35, t + 0.07);
      o.frequency.exponentialRampToValueAtTime(base * 0.9, t + 0.14);
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(0.025, t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.18);
      o.connect(g).connect(master);
      o.start(t);
      o.stop(t + 0.2);
      chirpTimer = setTimeout(chirp, 2500 + Math.random() * 6000);
    };

    return {
      on() {
        ctx.resume();
        master.gain.cancelScheduledValues(ctx.currentTime);
        master.gain.linearRampToValueAtTime(0.5, ctx.currentTime + 1.2);
        clearTimeout(chirpTimer);
        chirpTimer = setTimeout(chirp, 1500);
      },
      off() {
        clearTimeout(chirpTimer);
        master.gain.cancelScheduledValues(ctx.currentTime);
        master.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.6);
      },
    };
  };

  const startSound = async () => {
    if (useFile) {
      try {
        if (!fileAudio) {
          fileAudio = new Audio("assets/ambience.mp3");
          fileAudio.loop = true;
          fileAudio.volume = 0.6;
        }
        await fileAudio.play();
        return;
      } catch (_) {
        useFile = false; // no recording supplied — fall back to the generated ambience
      }
    }
    if (!synth) synth = makeSynth();
    if (synth) synth.on();
  };

  const stopSound = () => {
    if (fileAudio && useFile) fileAudio.pause();
    if (synth) synth.off();
  };

  soundBtn.addEventListener("click", () => {
    soundOn = !soundOn;
    soundBtn.setAttribute("aria-pressed", String(soundOn));
    soundLabel.textContent = soundOn ? "SOUND ON" : "SOUND OFF";
    if (soundOn) startSound();
    else stopSound();
  });

  /* ---------- Gallery ---------- */
  const tilesEl = $("#tiles");
  const form = $("#shareForm");
  const drop = $("#dropZone");
  const fileInput = $("#photoInput");
  const preview = $("#photoPreview");
  const memory = $("#memoryInput");
  const msg = $("#shareMsg");
  let pendingPhoto = null;
  let msgTimer = null;

  const load = () => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }
    catch (_) { return []; }
  };
  const save = (items) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); return true; }
    catch (_) { return false; }
  };
  let entries = load(); // [{ photo, text, slot }]

  const escapeHTML = (s) =>
    s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const renderTiles = (newSlot = -1) => {
    tilesEl.innerHTML = "";
    TILES.forEach((t, i) => {
      const li = document.createElement("li");
      li.className = "tile" + (t.square ? " tile--sq" : "") + (t.y < 300 ? " tile--top" : "");
      li.style.left = `${t.x}px`;
      li.style.top = `${t.y}px`;
      li.style.width = `${t.w || 133}px`;
      const entry = entries.find((e) => e.slot === i);
      if (entry) {
        li.classList.add("is-filled");
        li.tabIndex = 0;
        li.innerHTML =
          `<img class="tile__photo" src="${entry.photo}" alt="Shared photo">` +
          (entry.text ? `<p class="tile__note">${escapeHTML(entry.text)}</p>` : "");
        li.setAttribute("aria-label", entry.text ? `Memory: ${entry.text}` : "Shared photo");
        if (i === newSlot) li.classList.add("is-new");
      } else {
        li.innerHTML = '<span class="tile__blank"></span>';
        li.setAttribute("aria-hidden", "true");
      }
      tilesEl.appendChild(li);
    });
  };

  const nextSlot = () => {
    for (let i = 0; i < TILES.length; i++) if (!entries.some((e) => e.slot === i)) return i;
    // Circle is full: replace the oldest memory.
    const oldest = entries.shift();
    return oldest.slot;
  };

  // Downscale so photos stay light enough to keep in the browser.
  const toDataURL = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = reject;
      reader.onload = () => {
        const im = new Image();
        im.onerror = reject;
        im.onload = () => {
          const max = 360;
          const r = Math.min(1, max / Math.max(im.width, im.height));
          const c = document.createElement("canvas");
          c.width = Math.round(im.width * r);
          c.height = Math.round(im.height * r);
          const g = c.getContext("2d");
          g.fillStyle = "#ffffff"; // transparent PNGs would otherwise turn black as JPEG
          g.fillRect(0, 0, c.width, c.height);
          g.drawImage(im, 0, 0, c.width, c.height);
          resolve(c.toDataURL("image/jpeg", 0.82));
        };
        im.src = reader.result;
      };
      reader.readAsDataURL(file);
    });

  const say = (text, hold = 3500) => {
    msg.textContent = text;
    msg.classList.add("is-visible");
    form.classList.add("is-messaging");
    clearTimeout(msgTimer);
    msgTimer = setTimeout(() => {
      msg.classList.remove("is-visible");
      form.classList.remove("is-messaging");
    }, hold);
  };

  const takeFile = async (file) => {
    if (!file) return;
    if (!/^image\/(png|jpe?g)$/.test(file.type)) {
      say("Please choose a JPG or PNG image.");
      return;
    }
    try {
      pendingPhoto = await toDataURL(file);
      preview.src = pendingPhoto;
      drop.classList.add("has-photo");
      $(".drop__main", drop).textContent = "Change photo";
    } catch (_) {
      say("That image couldn't be read. Try another one.");
    }
  };

  fileInput.addEventListener("change", () => takeFile(fileInput.files[0]));

  ["dragenter", "dragover"].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("is-dragging"); })
  );
  ["dragleave", "drop"].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("is-dragging"); })
  );
  drop.addEventListener("drop", (e) => takeFile(e.dataTransfer.files[0]));

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!pendingPhoto) {
      say("Add a photo first, then share your memory.");
      return;
    }
    const slot = nextSlot();
    entries.push({ photo: pendingPhoto, text: memory.value.trim(), slot });
    const kept = save(entries);
    renderTiles(slot);

    form.reset();
    pendingPhoto = null;
    preview.removeAttribute("src");
    drop.classList.remove("has-photo");
    $(".drop__main", drop).textContent = "Upload a JPG or PNG";
    say(
      kept
        ? "Thank you for sharing your memory! Your moment is now part of our growing circle."
        : "Thank you! Your moment joined the circle (it won't be saved after you close this page).",
      4500
    );
  });

  renderTiles();
  route();
})();
