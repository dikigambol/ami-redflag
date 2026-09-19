/**
 * AM I THE RED FLAG? — BEHAVIORAL ASSESSMENT SIMULATOR
 * Frontend Application Logic
 */

document.addEventListener("DOMContentLoaded", () => {
  // --- STATE ---
  const state = {
    playerName: "",
    currentChapter: 1,
    pendingNextChapter: null,
    isTransitioning: false,
    exchangeCount: 0,
    minExchangesBeforeFinish: 2,
    chapterMessages: [],
    fullHistory: [],
    isSubmitting: false,
    currentResult: null,
  };

  let typingTimer = null;

  // --- CHAPTER CONFIGURATIONS ---
  const CHAPTERS = {
    1: {
      chapter: 1,
      title: "Bab 1: Hubungan Personal",
      timeLabel: "Pagi Hari &bull; 07:45",
      character: "Ayang",
      initial: "A",
      userStarts: true,
      initialNotice: "Semalam kamu menghilang tanpa kabar dan chat terakhirnya cuma kamu read. Pagi ini kamu yang harus memulai obrolan duluan.",
      initialMessage: null,
      transitionTime: "3 Jam Kemudian",
      transitionTitle: "Bab 2: Krisis Profesional",
      transitionDesc: "Jam makan siang baru saja berakhir. Di tengah persiapan mendesak menjelang rapat dewan direksi, rekan kerja mejamu menghubungimu dalam keadaan panik luar biasa.",
    },
    2: {
      chapter: 2,
      title: "Bab 2: Krisis Profesional",
      timeLabel: "Siang Hari &bull; 11:30",
      character: "Budi (Rekan Kerja)",
      initial: "B",
      initialMessage: "Gawat bro... Gue gak sengaja numpahin kopi terus file master proposal tender tim kita kehapus permanen dari laptop gue, padahal 30 menit lagi meeting sama direksi! Lo bisa bantuin gue ngomong ke bos gak plis?",
      transitionTime: "4 Jam Kemudian",
      transitionTitle: "Bab 3: Batasan Sosial",
      transitionDesc: "Pukul 17:30 sore. Tubuhmu sudah kelelahan setelah menyelesaikan serangkaian deadline kerja. Tiba-tiba salah seorang teman dekatmu mengirimkan pesan mendesak.",
    },
    3: {
      chapter: 3,
      title: "Bab 3: Batasan Sosial",
      timeLabel: "Sore Hari &bull; 17:30",
      character: "Dimas (Teman)",
      initial: "D",
      initialMessage: "Bro! Pokoknya lu WAJIB ikut nongkrong sore ini, anak-anak udah pada kumpul nih. Gak ada alesan capek atau kerjaan, masa lu gak solid banget sih?!",
      transitionTime: "3 Jam Kemudian",
      transitionTitle: "Bab 4: Integritas Etika",
      transitionDesc: "Pukul 20:30 malam. Kamu sedang bersantai di rumah setelah seharian beraktivitas. Tiba-tiba masuk notifikasi WhatsApp dari admin toko online tempat kamu membeli gadget bernilai jutaan rupiah yang paketnya baru tiba sore tadi...",
    },
    4: {
      chapter: 4,
      title: "Bab 4: Integritas Etika",
      timeLabel: "Malam Hari &bull; 20:30",
      character: "Clarissa (Admin Toko)",
      initial: "C",
      userStarts: false,
      initialMessage: "Malam Kak, maaf banget ya ganggu jam istirahatnya 🙏 Paket pesanan dari toko kami kan baru sampai sore tadi ya Kak? Staf gudang kami yang baru magang panik banget dan nangis, katanya pas packing tadi siang gak sengaja masukin 2 unit barang ke dalam kardus Kakak... Boleh tolong dicek kardus paketnya Kak? 🥺",
      transitionTime: "Evaluasi",
      transitionTitle: "Menganalisis Karakter",
      transitionDesc: "Seluruh skenario telah diselesaikan. Sistem sedang memproses riwayat interaksimu...",
    },
  };

  // --- DOM SELECTORS ---
  const screens = {
    welcome: document.getElementById("screen-welcome"),
    chat: document.getElementById("screen-chat"),
    transition: document.getElementById("screen-transition"),
    loading: document.getElementById("screen-loading"),
    result: document.getElementById("screen-result"),
  };

  // Welcome Form
  const formStart = document.getElementById("form-start");
  const inputPlayerName = document.getElementById("player-name");

  // Chat Elements
  const charAvatarInitial = document.getElementById("char-avatar-initial");
  const charName = document.getElementById("char-name");
  const charStatus = document.getElementById("char-status");
  const badgeChapterText = document.getElementById("badge-chapter-text");
  const chapterTimeLabel = document.getElementById("chapter-time-label");
  const exchangeIndicator = document.getElementById("exchange-indicator");
  const chatMessages = document.getElementById("chat-messages");
  const typingIndicator = document.getElementById("typing-indicator");
  const typingNameLabel = document.getElementById("typing-name-label");
  const chatInputText = document.getElementById("chat-input-text");
  const btnSendMessage = document.getElementById("btn-send-message");
  const btnChatRestart = document.getElementById("btn-chat-restart");
  const btnEndChapterHeader = document.getElementById("btn-end-chapter-header");
  const endChatSuggestion = document.getElementById("end-chat-suggestion");
  const btnAcceptEnd = document.getElementById("btn-accept-end");

  // Transition Elements
  const transitionTimePassed = document.getElementById("transition-time-passed");
  const transitionTitle = document.getElementById("transition-title");
  const transitionDesc = document.getElementById("transition-desc");
  const btnContinueChapter = document.getElementById("btn-continue-chapter");

  // Loading Elements
  const loadingStepText = document.getElementById("loading-step-text");

  // Result Elements
  const exportableIdCard = document.getElementById("exportable-id-card");
  const resultInitialLarge = document.getElementById("result-initial-large");
  const resultFlagPill = document.getElementById("result-flag-pill");
  const resultPlayerName = document.getElementById("result-player-name");
  const resultScoreNum = document.getElementById("result-score-num");
  const resultJulukan = document.getElementById("result-julukan");
  const resultKategoriText = document.getElementById("result-kategori-text");
  const resultAnalisisText = document.getElementById("result-analisis-text");
  const resultSaranText = document.getElementById("result-saran-text");

  const dimManipulasiVal = document.getElementById("dim-manipulasi-val");
  const dimManipulasiBar = document.getElementById("dim-manipulasi-bar");
  const dimEmpatiVal = document.getElementById("dim-empati-val");
  const dimEmpatiBar = document.getElementById("dim-empati-bar");
  const dimKebohonganVal = document.getElementById("dim-kebohongan-val");
  const dimKebohonganBar = document.getElementById("dim-kebohongan-bar");
  const dimKesabaranVal = document.getElementById("dim-kesabaran-val");
  const dimKesabaranBar = document.getElementById("dim-kesabaran-bar");

  const btnDownloadCard = document.getElementById("btn-download-card");
  const btnShareText = document.getElementById("btn-share-text");
  const btnPlayAgain = document.getElementById("btn-play-again");
  const toastNotif = document.getElementById("toast-notif");

  // --- SCREEN SWITCHER ---
  function showScreen(name) {
    Object.values(screens).forEach((s) => s.classList.remove("active"));
    if (screens[name]) {
      screens[name].classList.add("active");
    }
  }

  // --- TOAST NOTIFICATION ---
  function showToast(message) {
    toastNotif.textContent = message;
    toastNotif.classList.remove("hidden");
    setTimeout(() => toastNotif.classList.add("hidden"), 2600);
  }

  // --- TIME UTILITY ---
  function getCurrentTimeString() {
    const d = new Date();
    return d.getHours().toString().padStart(2, "0") + ":" + d.getMinutes().toString().padStart(2, "0");
  }

  // --- TEXTAREA AUTO-RESIZE & KEY HANDLING ---
  chatInputText.addEventListener("input", () => {
    chatInputText.style.height = "auto";
    chatInputText.style.height = Math.min(chatInputText.scrollHeight, 90) + "px";
  });

  chatInputText.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  btnSendMessage.addEventListener("click", () => {
    sendMessage();
  });

  // --- FORM START ---
  formStart.addEventListener("submit", (e) => {
    e.preventDefault();
    const name = inputPlayerName.value.trim();
    if (!name) return;

    state.playerName = name;
    state.currentChapter = 1;
    state.exchangeCount = 0;
    state.chapterMessages = [];
    state.fullHistory = [];

    initChapter(1);
  });

  // --- INITIALIZE CHAPTER ---
  function initChapter(chapterNum) {
    if (typingTimer) {
      clearTimeout(typingTimer);
      typingTimer = null;
    }

    state.currentChapter = Math.min(Math.max(Number(chapterNum), 1), 4);
    state.exchangeCount = 0;
    state.chapterMessages = [];
    state.isTransitioning = false;
    state.pendingNextChapter = null;

    if (btnContinueChapter) {
      btnContinueChapter.disabled = false;
    }

    const cfg = CHAPTERS[state.currentChapter];

    // Header Setup
    charAvatarInitial.textContent = cfg.initial;
    charName.textContent = cfg.character;
    charStatus.textContent = "online";
    badgeChapterText.textContent = `Bab ${state.currentChapter} / 4`;
    chapterTimeLabel.innerHTML = cfg.timeLabel;
    exchangeIndicator.textContent = "0 obrolan";

    // Hide suggestions
    endChatSuggestion.classList.add("hidden");
    btnEndChapterHeader.style.display = "none";

    // Clear and build chat view
    let introHtml = `
      <div class="wa-date-chip">
        <span>HARI INI</span>
      </div>
    `;

    if (cfg.initialNotice) {
      introHtml += `
        <div class="wa-system-notice">
          <p>${cfg.initialNotice}</p>
        </div>
      `;
    }

    chatMessages.innerHTML = introHtml;

    showScreen("chat");

    if (cfg.userStarts) {
      showTyping(false);
      chatInputText.placeholder = `Ketik pesan pertama ke ${cfg.character}...`;
      chatInputText.focus();
    } else {
      chatInputText.placeholder = "Ketik pesan...";
      // Display initial greeting with simulated typing
      showTyping(true, `${cfg.character} sedang mengetik...`);
      typingTimer = setTimeout(() => {
        showTyping(false);
        appendMessage("assistant", cfg.initialMessage);
        state.chapterMessages.push({
          role: "assistant",
          content: cfg.initialMessage,
        });
        chatInputText.focus();
      }, 750);
    }
  }

  // --- TYPING INDICATOR ---
  function showTyping(show, label = "sedang mengetik...") {
    if (show) {
      typingNameLabel.textContent = label;
      typingIndicator.classList.remove("hidden");
      scrollToBottom();
    } else {
      typingIndicator.classList.add("hidden");
    }
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // --- APPEND WHATSAPP BUBBLE ---
  function appendMessage(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `wa-bubble ${role === "user" ? "outgoing" : "incoming"}`;

    const textSpan = document.createElement("span");
    textSpan.className = "wa-msg-text";
    textSpan.textContent = text;

    const meta = document.createElement("div");
    meta.className = "wa-msg-meta";
    meta.innerHTML = `
      <span>${getCurrentTimeString()}</span>
      ${role === "user" ? '<span class="wa-ticks">✓✓</span>' : ""}
    `;

    bubble.appendChild(textSpan);
    bubble.appendChild(meta);
    chatMessages.appendChild(bubble);

    scrollToBottom();
  }

  // --- SEND MESSAGE ---
  async function sendMessage() {
    if (state.isSubmitting) return;

    const text = chatInputText.value.trim();
    if (!text) return;

    // Reset input box
    chatInputText.value = "";
    chatInputText.style.height = "auto";

    // Render User Message
    appendMessage("user", text);
    state.chapterMessages.push({
      role: "user",
      content: text,
    });

    state.exchangeCount++;
    exchangeIndicator.textContent = `${state.exchangeCount} respon`;

    // Check if user has engaged enough to allow manual finish
    if (state.exchangeCount >= state.minExchangesBeforeFinish) {
      btnEndChapterHeader.style.display = "inline-block";
    }

    // Disable inputs while waiting
    state.isSubmitting = true;
    btnSendMessage.disabled = true;
    chatInputText.disabled = true;

    const cfg = CHAPTERS[state.currentChapter];
    showTyping(true, `${cfg.character} sedang mengetik...`);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_name: state.playerName,
          chapter: state.currentChapter,
          exchange_count: state.exchangeCount,
          previous_history: state.fullHistory,
          messages: state.chapterMessages.map((m) => {
            const item = { role: m.role, content: m.content };
            if (m.reasoning_details) item.reasoning_details = m.reasoning_details;
            return item;
          }),
        }),
      });

      if (!response.ok) {
        throw new Error(`Status: ${response.status}`);
      }

      const data = await response.json();
      showTyping(false);

      // Render AI response
      appendMessage("assistant", data.reply);
      state.chapterMessages.push({
        role: "assistant",
        content: data.reply,
        reasoning_details: data.reasoning_details || null,
      });

      // If backend suggests ending chat or count >= 3, show subtle suggestion banner
      if (data.suggest_end || state.exchangeCount >= 3) {
        endChatSuggestion.classList.remove("hidden");
        scrollToBottom();
      }

    } catch (err) {
      console.error(err);
      showTyping(false);
      appendMessage("assistant", "*(Pesan tidak terkirim. Silakan periksa jaringan)*");
    } finally {
      state.isSubmitting = false;
      btnSendMessage.disabled = false;
      chatInputText.disabled = false;
      chatInputText.placeholder = "Ketik pesan...";
      chatInputText.focus();
    }
  }

  // --- FINISH CURRENT CHAPTER ---
  function finishCurrentChapter() {
    if (state.isTransitioning) return;
    state.isTransitioning = true;

    const cfg = CHAPTERS[state.currentChapter];
    state.fullHistory.push({
      chapter: state.currentChapter,
      chapter_title: cfg.title,
      character: cfg.character,
      messages: [...state.chapterMessages],
    });

    endChatSuggestion.classList.add("hidden");

    if (state.currentChapter < 4) {
      const nextChapter = state.currentChapter + 1;
      state.pendingNextChapter = nextChapter;
      const nextCfg = CHAPTERS[nextChapter];

      transitionTimePassed.textContent = cfg.transitionTime;
      transitionTitle.textContent = cfg.transitionTitle;
      transitionDesc.textContent = cfg.transitionDesc;

      btnContinueChapter.disabled = false;
      showScreen("transition");
    } else {
      // All 4 chapters complete -> Evaluate
      startEvaluation();
    }
  }

  btnEndChapterHeader.addEventListener("click", () => {
    finishCurrentChapter();
  });

  btnAcceptEnd.addEventListener("click", () => {
    finishCurrentChapter();
  });

  btnContinueChapter.addEventListener("click", () => {
    if (!state.pendingNextChapter || btnContinueChapter.disabled) return;
    btnContinueChapter.disabled = true;

    const target = state.pendingNextChapter;
    state.pendingNextChapter = null;
    initChapter(target);
  });

  // --- EVALUATION ---
  async function startEvaluation() {
    showScreen("loading");

    const steps = [
      "Mengukur parameter respon emosional...",
      "Mendeteksi pola defensif dan manipulatif...",
      "Menganalisis konsistensi empati dan kejujuran...",
      "Menyusun profil psikologis objektif...",
    ];

    let idx = 0;
    const interval = setInterval(() => {
      idx = (idx + 1) % steps.length;
      loadingStepText.textContent = steps[idx];
    }, 900);

    try {
      const response = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          player_name: state.playerName,
          full_history: state.fullHistory,
        }),
      });

      clearInterval(interval);

      if (!response.ok) throw new Error("Gagal evaluasi");

      const result = await response.json();
      state.currentResult = result;
      renderResult(result);
    } catch (err) {
      clearInterval(interval);
      console.error(err);
      const fallback = {
        skor_red_flag: 52,
        kategori: "Yellow Flag",
        julukan: "Diplomat Pragmatis",
        analisis: `${state.playerName} cenderung mencari jalan aman saat menghadapi tekanan sosial. Masih memiliki pertimbangan etis namun berpotensi defensif jika sudut pandangnya dipojokkan.`,
        saran: "Tingkatkan ketegasan dan sampaikan batasan pribadimu tanpa harus merasa bersalah.",
        dimensi: { manipulasi: 45, empati: 60, kebohongan: 35, kesabaran: 60 },
      };
      state.currentResult = fallback;
      renderResult(fallback);
    }
  }

  // --- RENDER ID CARD RESULT ---
  function renderResult(data) {
    const score = data.skor_red_flag || 50;
    const kategori = data.kategori || (score >= 70 ? "Red Flag" : score >= 36 ? "Yellow Flag" : "Green Flag");

    resultPlayerName.textContent = state.playerName;
    resultInitialLarge.textContent = (state.playerName[0] || "U").toUpperCase();
    resultJulukan.textContent = data.julukan || "Pribadi Netral";
    resultAnalisisText.textContent = data.analisis || "";
    resultSaranText.textContent = data.saran || "";
    resultScoreNum.textContent = score;

    // Reset themes
    exportableIdCard.classList.remove("flag-theme-red", "flag-theme-yellow", "flag-theme-green");
    resultFlagPill.classList.remove("pill-red", "pill-yellow", "pill-green");

    if (kategori.toLowerCase().includes("red") || score >= 70) {
      exportableIdCard.classList.add("flag-theme-red");
      resultFlagPill.classList.add("pill-red");
      resultFlagPill.textContent = "HIGH RISK // RED FLAG";
      resultJulukan.style.color = "#e57373";
      resultKategoriText.textContent = "Kategori: Risiko Perilaku Tinggi";
    } else if (kategori.toLowerCase().includes("yellow") || score >= 36) {
      exportableIdCard.classList.add("flag-theme-yellow");
      resultFlagPill.classList.add("pill-yellow");
      resultFlagPill.textContent = "MODERATE // YELLOW FLAG";
      resultJulukan.style.color = "#ffb74d";
      resultKategoriText.textContent = "Kategori: Risiko Ambivalen / Situasional";
    } else {
      exportableIdCard.classList.add("flag-theme-green");
      resultFlagPill.classList.add("pill-green");
      resultFlagPill.textContent = "HEALTHY // GREEN FLAG";
      resultJulukan.style.color = "#81c784";
      resultKategoriText.textContent = "Kategori: Integritas & Respon Positif";
    }

    // Dimensions
    const dims = data.dimensi || { manipulasi: 50, empati: 50, kebohongan: 50, kesabaran: 50 };
    dimManipulasiVal.textContent = `${dims.manipulasi}%`;
    dimManipulasiBar.style.width = `${dims.manipulasi}%`;

    dimEmpatiVal.textContent = `${dims.empati}%`;
    dimEmpatiBar.style.width = `${dims.empati}%`;

    dimKebohonganVal.textContent = `${dims.kebohongan}%`;
    dimKebohonganBar.style.width = `${dims.kebohongan}%`;

    dimKesabaranVal.textContent = `${dims.kesabaran}%`;
    dimKesabaranBar.style.width = `${dims.kesabaran}%`;

    showScreen("result");
  }

  // --- DOWNLOAD ID CARD AS PNG ---
  btnDownloadCard.addEventListener("click", async () => {
    btnDownloadCard.disabled = true;
    const oldHtml = btnDownloadCard.innerHTML;
    btnDownloadCard.innerHTML = "<span>Memproses...</span>";

    try {
      const canvas = await html2canvas(exportableIdCard, {
        scale: 2.5,
        useCORS: true,
        backgroundColor: "#0d121a",
        logging: false,
      });

      const link = document.createElement("a");
      link.download = `Assessment-${state.playerName || "User"}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
      showToast("Kartu berhasil diunduh");
    } catch (err) {
      console.error(err);
      showToast("Gagal mengunduh kartu");
    } finally {
      btnDownloadCard.disabled = false;
      btnDownloadCard.innerHTML = oldHtml;
    }
  });

  // --- SHARE RESULT TEXT ---
  btnShareText.addEventListener("click", async () => {
    if (!state.currentResult) return;

    const text = 
      `BEHAVIORAL RISK ASSESSMENT REPORT\n` +
      `Subjek: ${state.playerName}\n` +
      `Indeks Red Flag: ${state.currentResult.skor_red_flag}/100\n` +
      `Klasifikasi: ${state.currentResult.julukan}\n` +
      `Catatan: ${state.currentResult.saran}\n\n` +
      `Diuji melalui AI Chat Simulator`;

    if (navigator.share) {
      try {
        await navigator.share({ title: "Assessment Report", text });
        return;
      } catch (e) {}
    }

    navigator.clipboard.writeText(text).then(() => {
      showToast("Ringkasan disalin ke clipboard");
    });
  });

  // --- RESTART ---
  btnPlayAgain.addEventListener("click", () => showScreen("welcome"));
  btnChatRestart.addEventListener("click", () => {
    if (confirm("Kembali ke layar utama dan ulangi simulasi?")) {
      showScreen("welcome");
    }
  });
});
