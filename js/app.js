/**
 * Oyen Math - Main Application Controller
 * Coordinates the UI, LangGraph StateGraph, Audio, Detective Scanner, and Firebase layer.
 */

const OyenApp = (() => {
  let graph = null;
  let currentView = "adventure"; // 'adventure' | 'learning' | 'detective' | 'recovery' | 'leaderboard' | 'achievements'
  let canvasController = null;

  function init() {
    // 1. Initialize Firebase Auth / Local Offline Store
    OyenFirebase.init();

    // 2. Initialize Agentic LangGraph
    const savedUser = OyenFirebase.getCurrentUser();
    graph = new OyenAgenticGraph({
      studentId: savedUser ? savedUser.uid : null,
      studentName: savedUser ? savedUser.displayName : "Pelajar Oyen",
      language: OyenI18n.getLang()
    });

    // Try restoring saved progress from Firestore / localStorage
    OyenFirebase.loadStudentProfile().then(data => {
      if (data) {
        if (data.mastery) graph.state.mastery = Object.assign(graph.state.mastery, data.mastery);
        if (data.hearts !== undefined) graph.state.hearts = data.hearts;
        if (data.normalPoints) graph.state.normalPoints = data.normalPoints;
        if (data.recoveryPoints) graph.state.recoveryPoints = data.recoveryPoints;
        if (data.fishCoins) graph.state.fishCoins = data.fishCoins;
        updateHeaderStats();
        renderMasteryBars();
      }
    });

    // 3. Subscribe to Graph Events
    graph.subscribe((event, data, state) => {
      handleGraphEvent(event, data, state);
    });

    // 4. Bind UI Listeners
    setupEventListeners();

    // 5. Initial Render
    updateHeaderStats();
    renderSidePanel();
    switchView("adventure");
    renderOyenSideAvatar("happy");

    // Welcome greeting
    graph.logDecision("O", "Selamat datang ke Oyen Math! Sistem bersedia membimbing anda dalam Matematik Tambahan SPM.");
  }

  function setupEventListeners() {
    // Language toggle
    const langBtn = document.getElementById("langToggleBtn");
    if (langBtn) {
      langBtn.addEventListener("click", () => {
        const nextLang = OyenI18n.getLang() === "ms" ? "en" : "ms";
        OyenI18n.setLang(nextLang);
        langBtn.textContent = nextLang === "ms" ? "🇲🇾 BM" : "🇬🇧 EN";
        updateAllUIText();
      });
    }

    // Audio toggle
    const audioBtn = document.getElementById("audioToggleBtn");
    if (audioBtn) {
      audioBtn.addEventListener("click", () => {
        const isEnabled = OyenAudio.toggle();
        audioBtn.textContent = isEnabled ? "🔊" : "🔇";
      });
    }

    // Navigation Tabs
    document.querySelectorAll(".nav-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        const targetView = tab.dataset.view;
        if (targetView) switchView(targetView);
      });
    });

    // Auth Modal
    const authBtn = document.getElementById("userProfileBtn");
    const authModal = document.getElementById("authModal");
    const closeAuthBtn = document.getElementById("closeAuthModal");
    if (authBtn && authModal) {
      authBtn.addEventListener("click", () => authModal.classList.add("open"));
    }
    if (closeAuthBtn && authModal) {
      closeAuthBtn.addEventListener("click", () => authModal.classList.remove("open"));
    }

    // Auth Form
    const loginForm = document.getElementById("authForm");
    if (loginForm) {
      loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("authEmail").value;
        const pass = document.getElementById("authPassword").value;
        const name = document.getElementById("authName").value;
        try {
          await OyenFirebase.registerUser(email, pass, name);
          authModal.classList.remove("open");
          updateUserProfileUI();
          graph.logDecision("O", `Pengguna berjaya didaftarkan: ${name || email}`);
        } catch (err) {
          alert(err.message);
        }
      });
    }

    const guestBtn = document.getElementById("btnGuestContinue");
    if (guestBtn && authModal) {
      guestBtn.addEventListener("click", () => {
        OyenFirebase.continueAsGuest();
        authModal.classList.remove("open");
        updateUserProfileUI();
      });
    }

    // Listen for language changes
    window.addEventListener("oyen_language_changed", () => {
      updateAllUIText();
    });
  }

  function updateHeaderStats() {
    const s = graph.state;
    const heartsEl = document.getElementById("headerHeartsVal");
    const ptsEl = document.getElementById("headerPointsVal");
    const fishEl = document.getElementById("headerFishVal");
    if (heartsEl) heartsEl.textContent = "💖 " + s.hearts + "/" + s.maxHearts;
    if (ptsEl) ptsEl.textContent = "⭐ " + s.normalPoints + " XP";
    if (fishEl) fishEl.textContent = "🐟 " + s.fishCoins;
  }

  function updateUserProfileUI() {
    const user = OyenFirebase.getCurrentUser();
    const btn = document.getElementById("userProfileBtn");
    if (btn && user) {
      btn.textContent = user.isGuest ? `🐾 ${user.displayName}` : `👤 ${user.displayName}`;
    }
  }

  function renderSidePanel() {
    renderMasteryBars();
    renderAgentTraceLog();
  }

  function renderOyenSideAvatar(pose = "happy") {
    const avatarContainer = document.getElementById("sideOyenAvatar");
    if (avatarContainer) {
      OyenCharacter.setPose(avatarContainer, pose, 130);
    }
    const quoteEl = document.getElementById("sideOyenDialogue");
    if (quoteEl) {
      const quotes = OyenI18n.translations[OyenI18n.getLang()].oyenQuotes;
      if (pose === "happy") quoteEl.textContent = quotes.correct;
      else if (pose === "sad") quoteEl.textContent = quotes.incorrect;
      else if (pose === "thinking") quoteEl.textContent = quotes.difficult;
      else if (pose === "determined") quoteEl.textContent = quotes.recoveryExercise;
      else if (pose === "excited") quoteEl.textContent = quotes.levelCompleted;
      else if (pose === "detective") quoteEl.textContent = quotes.detectiveScanning;
      else quoteEl.textContent = quotes.welcomeBack;
    }
  }

  function renderMasteryBars() {
    const container = document.getElementById("masteryBarsContainer");
    if (!container) return;

    const topics = [
      { id: "dif", name: OyenCurriculum.getTopic("dif").name },
      { id: "integ", name: OyenCurriculum.getTopic("integ").name },
      { id: "ind", name: OyenCurriculum.getTopic("ind").name },
      { id: "quad", name: OyenCurriculum.getTopic("quad").name }
    ];

    container.innerHTML = topics.map(t => {
      const score = Math.round((graph.state.mastery[t.id] || 0) * 100);
      return `
        <div class="mastery-row">
          <div class="mastery-header">
            <span>${t.name}</span>
            <span>${score}%</span>
          </div>
          <div class="mastery-track">
            <div class="mastery-fill" style="width: ${score}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  }

  function renderAgentTraceLog() {
    const container = document.getElementById("agentBrainFeed");
    if (!container) return;

    if (graph.state.traceLog.length === 0) {
      container.innerHTML = `<span style="font-size:12px;color:var(--muted-text);">Belum ada aktiviti ejen / No agent decisions logged yet.</span>`;
      return;
    }

    const lang = OyenI18n.getLang();
    container.innerHTML = graph.state.traceLog.map(item => {
      const meta = item.agentMeta || {};
      const agentLabel = lang === "ms" ? (meta.ms || "Ejen AI") : (meta.en || "AI Agent");
      return `
        <div class="trace-item" style="border-left-color: ${meta.color || '#FF8C24'}">
          <div class="trace-header">
            <span class="trace-agent-badge" style="color: ${meta.color || '#FF8C24'}">${agentLabel}</span>
            <span class="trace-time">${item.timestamp}</span>
          </div>
          <div class="trace-msg">${item.message}</div>
        </div>
      `;
    }).join("");
  }

  function switchView(viewName) {
    currentView = viewName;
    document.querySelectorAll(".nav-tab").forEach(tab => {
      tab.classList.toggle("active", tab.dataset.view === viewName);
    });

    const stage = document.getElementById("mainAppStage");
    if (!stage) return;

    if (viewName === "adventure") {
      renderAdventureMap(stage);
      renderOyenSideAvatar("happy");
    } else if (viewName === "learning") {
      // In learning view, if no active question, start current topic
      if (!graph.state.currentQuestion) {
        graph.startSession(graph.state.currentTopicId || "dif");
      } else {
        renderQuestionStage(stage);
      }
    } else if (viewName === "detective") {
      renderDetectiveWorkbench(stage);
      renderOyenSideAvatar("detective");
    } else if (viewName === "recovery") {
      graph.triggerRecoveryMode();
      renderOyenSideAvatar("determined");
    } else if (viewName === "leaderboard") {
      renderLeaderboardView(stage);
      renderOyenSideAvatar("excited");
    } else if (viewName === "achievements") {
      renderAchievementsView(stage);
      renderOyenSideAvatar("excited");
    }
  }

  // ==========================================
  // VIEW: ADVENTURE MAP
  // ==========================================
  function renderAdventureMap(container) {
    const lang = OyenI18n.getLang();
    const dif = OyenCurriculum.getTopic("dif");
    const integ = OyenCurriculum.getTopic("integ");
    const ind = OyenCurriculum.getTopic("ind");
    const quad = OyenCurriculum.getTopic("quad");

    container.innerHTML = `
      <div class="adventure-map">
        <!-- Hero Introduction Banner with Oyen Mascot -->
        <div style="background: linear-gradient(135deg, var(--light-orange), #FFE8D1); border: 2px solid var(--border-color); border-radius: var(--radius-lg); padding: 24px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap;">
          <div style="flex-shrink: 0;" id="heroOyenBanner">
            ${OyenCharacter.render("happy", 110)}
          </div>
          <div style="flex: 1; min-width: 240px;">
            <div style="display:inline-block;background:var(--primary-orange);color:#fff;font-size:11px;font-weight:800;padding:3px 10px;border-radius:20px;margin-bottom:6px;">
              ${lang === "ms" ? "PENGEMBARAAN SPM OYEN" : "OYEN'S SPM ADVENTURE"}
            </div>
            <h2 style="font-size:24px;font-weight:900;color:var(--dark-orange);margin-bottom:6px;">
              ${lang === "ms" ? "Selamat Datang ke Oyen Math!" : "Welcome to Oyen Math!"}
            </h2>
            <p style="font-size:14px;color:var(--dark-text);line-height:1.6;">
              ${lang === "ms" 
                ? "Bantu Oyen, anak kucing oren comel yang bercita-cita tinggi menakluki Matematik Tambahan SPM. Setiap soalan yang anda selesaikan membawa Oyen selangkah lebih dekat dengan impian besarnya!" 
                : "Guide Oyen, an ambitious orange cat, on his journey to master SPM Additional Mathematics. Every challenge solved brings Oyen one step closer to his big dreams!"}
            </p>
          </div>
        </div>

        <!-- Level 1: Differentiation -->
        <div class="chapter-card highlight">
          <div class="chapter-header">
            <div>
              <span class="chapter-badge">${lang === "ms" ? "Tahap 1 · Bab Wajib" : "Level 1 · Core Chapter"}</span>
              <h3 class="chapter-title">${lang === "ms" ? dif.name : dif.nameEn}</h3>
              <div class="chapter-subtitle">🐾 ${lang === "ms" ? dif.chapterName : dif.chapterNameEn}</div>
            </div>
            <button class="btn btn-primary" onclick="OyenApp.startChapter('dif')">
              ${lang === "ms" ? "Mula Bab Ini" : "Start Chapter"} →
            </button>
          </div>
          <p class="chapter-desc">
            ${lang === "ms" ? dif.storyScene.intro : dif.storyScene.introEn}
          </p>
          
          <!-- Paw trail level nodes -->
          <div class="paw-trail">
            <div class="node-point" onclick="OyenApp.startChapter('dif', 1)">
              <div class="node-circle active">1</div>
              <span class="node-label">${lang === "ms" ? "Petua Kuasa" : "Power Rule"}</span>
            </div>
            <span class="paw-step-divider">🐾</span>
            <div class="node-point" onclick="OyenApp.startChapter('dif', 2)">
              <div class="node-circle">2</div>
              <span class="node-label">${lang === "ms" ? "Polinomial" : "Polynomials"}</span>
            </div>
            <span class="paw-step-divider">🐾</span>
            <div class="node-point" onclick="OyenApp.startChapter('dif', 3)">
              <div class="node-circle">3</div>
              <span class="node-label">${lang === "ms" ? "Kecerunan Tangen" : "Tangent Slopes"}</span>
            </div>
          </div>
        </div>

        <!-- Level 2: Integration (Direct Story Continuation) -->
        <div class="chapter-card">
          <div class="chapter-header">
            <div>
              <span class="chapter-badge">${lang === "ms" ? "Tahap 2 · Sambungan Terus" : "Level 2 · Direct Continuation"}</span>
              <h3 class="chapter-title">${lang === "ms" ? integ.name : integ.nameEn}</h3>
              <div class="chapter-subtitle">🐾 ${lang === "ms" ? integ.chapterName : integ.chapterNameEn}</div>
            </div>
            <button class="btn btn-secondary" onclick="OyenApp.startChapter('integ')">
              ${lang === "ms" ? "Mula Bab Ini" : "Start Chapter"} →
            </button>
          </div>
          <p class="chapter-desc">
            ${lang === "ms" ? integ.storyScene.intro : integ.storyScene.introEn}
          </p>
          
          <!-- Paw trail level nodes -->
          <div class="paw-trail">
            <div class="node-point" onclick="OyenApp.startChapter('integ', 1)">
              <div class="node-circle active">1</div>
              <span class="node-label">${lang === "ms" ? "Kamiran ax" : "Integral ax"}</span>
            </div>
            <span class="paw-step-divider">🐾</span>
            <div class="node-point" onclick="OyenApp.startChapter('integ', 2)">
              <div class="node-circle">2</div>
              <span class="node-label">${lang === "ms" ? "Pemalar + C" : "Constant + C"}</span>
            </div>
            <span class="paw-step-divider">🐾</span>
            <div class="node-point" onclick="OyenApp.startChapter('integ', 3)">
              <div class="node-circle">3</div>
              <span class="node-label">${lang === "ms" ? "Kamiran Tentu" : "Definite Area"}</span>
            </div>
          </div>
        </div>

        <!-- Prerequisite Interventions Row -->
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
          <div class="chapter-card" style="padding:18px;">
            <span class="chapter-badge">${lang === "ms" ? "Prasyarat" : "Prerequisite"}</span>
            <h4 style="font-size:16px;font-weight:800;margin-top:6px;">${lang === "ms" ? ind.name : ind.nameEn}</h4>
            <p style="font-size:12px;color:var(--muted-text);margin:6px 0 12px;">${lang === "ms" ? ind.tag : ind.tagEn}</p>
            <button class="btn btn-alt btn-sm" onclick="OyenApp.startChapter('ind')">
              ${lang === "ms" ? "Ulang Kaji Indeks" : "Review Indices"}
            </button>
          </div>

          <div class="chapter-card" style="padding:18px;">
            <span class="chapter-badge">${lang === "ms" ? "Prasyarat" : "Prerequisite"}</span>
            <h4 style="font-size:16px;font-weight:800;margin-top:6px;">${lang === "ms" ? quad.name : quad.nameEn}</h4>
            <p style="font-size:12px;color:var(--muted-text);margin:6px 0 12px;">${lang === "ms" ? quad.tag : quad.tagEn}</p>
            <button class="btn btn-alt btn-sm" onclick="OyenApp.startChapter('quad')">
              ${lang === "ms" ? "Ulang Kaji Kuadratik" : "Review Quadratics"}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function startChapter(topicId, level = 1) {
    graph.state.level = level;
    graph.startSession(topicId);
    switchView("learning");
  }

  // ==========================================
  // VIEW: LEARNING & QUESTION INTERACTION
  // ==========================================
  function renderQuestionStage(container) {
    const q = graph.state.currentQuestion;
    if (!q) {
      container.innerHTML = `<p>Tiada soalan aktif. Sila pilih bab daripada Peta Pengembaraan.</p>`;
      return;
    }

    const lang = OyenI18n.getLang();
    const topic = OyenCurriculum.getTopic(graph.state.currentTopicId);
    const isDiag = graph.state.phase === "diagnostic";
    const phaseLabel = isDiag 
      ? (lang === "ms" ? "Diagnostik Konsep Awal" : "Initial Diagnostic")
      : (lang === "ms" ? "Misi Cabaran Oyen" : "Oyen's Challenge Mission");

    const questionText = (lang === "en" && q.qEn) ? q.qEn : q.q;
    const missionText = (lang === "en" && topic.missionEn) ? topic.missionEn : topic.mission;

    container.innerHTML = `
      <div class="question-zone">
        <div class="question-top">
          <span class="chapter-badge">${phaseLabel} · Soalan ${graph.state.stepInPhase + 1}/3 · Tahap ${q.level}</span>
          <div style="font-size:13px;font-weight:700;color:var(--dark-orange);">
            ${topic.name}
          </div>
        </div>

        ${!isDiag ? `<div class="mission-box">${missionText}</div>` : ""}

        <div class="question-text-box">
          <div class="math-q">${questionText}</div>
        </div>

        <div class="input-group">
          <input type="text" id="studentMathInput" class="math-input" 
            placeholder="${lang === "ms" ? "cth: 6x^2 + 5 atau 3/2" : "e.g., 6x^2 + 5 or 3/2"}" 
            autocomplete="off" />
          
          <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;">
            <button class="btn btn-primary" id="btnSubmitAnswer" onclick="OyenApp.submitAnswer()">
              ${lang === "ms" ? "Semak Jawapan" : "Check Answer"}
            </button>
            <button class="btn btn-alt" onclick="OyenApp.switchView('detective')">
              🔍 ${lang === "ms" ? "Semak Jalan Kerja Tulisan Tangan" : "Inspect Working"}
            </button>
          </div>
        </div>

        <div id="answerFeedbackContainer"></div>
      </div>
    `;

    const inputEl = document.getElementById("studentMathInput");
    if (inputEl) {
      inputEl.focus();
      inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter") submitAnswer();
      });
    }
  }

  function submitAnswer() {
    const input = document.getElementById("studentMathInput");
    if (!input || !input.value.trim()) return;
    graph.submitAnswer(input.value.trim());
  }

  // ==========================================
  // VIEW: TEACHING PHASE (MULTIMODAL)
  // ==========================================
  function renderTeachingView(container, data) {
    const lang = OyenI18n.getLang();
    const topic = OyenCurriculum.getTopic(graph.state.currentTopicId);
    const methodNames = OyenI18n.translations[lang].teachMethods;

    container.innerHTML = `
      <div style="display:flex;flex-direction:column;gap:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span class="chapter-badge">
            ${lang === "ms" ? "Ejen Pengajaran Oyen" : "Oyen's Teaching Agent"} · ${methodNames[data.method] || data.method}
          </span>
          <span style="font-size:12px;color:var(--muted-text);">${topic.name}</span>
        </div>

        <div style="background:var(--cream-bg);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:24px;line-height:1.7;">
          ${data.content}
        </div>

        <div style="display:flex;gap:12px;flex-wrap:wrap;">
          <button class="btn btn-primary" onclick="OyenApp.proceedToChallenge()">
            ${lang === "ms" ? "Saya Faham → Ke Cabaran Oyen" : "I Understand → Go to Challenges"} 🚀
          </button>
          <button class="btn btn-secondary" onclick="OyenApp.switchTeachingStrategy()">
            🔄 ${lang === "ms" ? "Masih Keliru, Cuba Kaedah Lain" : "Still Confused, Try Another Method"}
          </button>
        </div>
      </div>
    `;

    renderOyenSideAvatar("thinking");
  }

  function proceedToChallenge() {
    graph.startChallengePhase();
  }

  function switchTeachingStrategy() {
    graph.retryTeachingWithDifferentMethod();
  }

  // ==========================================
  // VIEW: DETECTIVE OYEN HANDWRITING SCANNER
  // ==========================================
  function renderDetectiveWorkbench(container) {
    const lang = OyenI18n.getLang();
    const samples = OyenDetectiveScanner.sampleCalculations;

    container.innerHTML = `
      <div>
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px;">
          <div style="width:54px;height:54px;">
            ${OyenCharacter.render("detective", 54)}
          </div>
          <div>
            <h3 style="font-size:20px;font-weight:900;color:var(--dark-orange);">
              ${OyenI18n.t("detectiveTitle")}
            </h3>
            <p style="font-size:13px;color:var(--muted-text);">
              ${OyenI18n.t("detectiveSubtitle")}
            </p>
          </div>
        </div>

        <div class="detective-workbench">
          <!-- Left: Drawing Canvas / Image Upload -->
          <div class="canvas-container">
            <div style="font-size:12px;font-weight:700;color:var(--dark-text);width:100%;display:flex;justify-content:space-between;align-items:center;">
              <span>📝 ${lang === "ms" ? "Kertas Conteng Tulisan Tangan" : "Handwritten Scratchpad"}</span>
              <button class="btn btn-alt btn-sm" onclick="OyenApp.clearCanvas()">
                ${lang === "ms" ? "Padam" : "Clear"}
              </button>
            </div>
            
            <canvas id="oyenScratchpad" width="420" height="260"></canvas>
            
            <div style="width:100%;display:flex;gap:8px;align-items:center;margin-top:6px;">
              <input type="file" id="handwrittenUpload" accept="image/*" style="display:none;" onchange="OyenApp.handleImageUpload(event)" />
              <button class="btn btn-secondary btn-sm" style="flex:1;" onclick="document.getElementById('handwrittenUpload').click()">
                📷 ${lang === "ms" ? "Muat Naik Gambar Kertas" : "Upload Notebook Photo"}
              </button>
              <button class="btn btn-primary btn-sm" style="flex:1;" onclick="OyenApp.analyzeCurrentCanvas()">
                🔎 ${lang === "ms" ? "Siasat Sekarang" : "Investigate Now"}
              </button>
            </div>
          </div>

          <!-- Right: Preloaded Test Samples & Inspection Results -->
          <div>
            <div style="font-size:13px;font-weight:800;color:var(--dark-orange);text-transform:uppercase;margin-bottom:8px;">
              ${lang === "ms" ? "Contoh Jalan Kerja SPM Terpilih" : "Curated SPM Working Samples"}
            </div>
            <div class="sample-selector">
              ${samples.map((s, idx) => `
                <button class="sample-btn" onclick="OyenApp.loadCalculationSample(${idx})">
                  <b>${lang === "ms" ? s.title : s.titleEn}</b>
                  <div style="font-size:11px;color:var(--muted-text);margin-top:2px;">${s.equation}</div>
                </button>
              `).join("")}
            </div>

            <!-- Inspection Report Box -->
            <div id="detectiveReportArea" style="margin-top:16px;"></div>
          </div>
        </div>
      </div>
    `;

    // Initialize drawing canvas
    setTimeout(() => {
      canvasController = OyenDetectiveScanner.initDrawingCanvas("oyenScratchpad");
    }, 50);
  }

  function clearCanvas() {
    if (canvasController) canvasController.clear();
  }

  function handleImageUpload(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        if (canvasController) {
          canvasController.clear();
          canvasController.ctx.drawImage(img, 0, 0, canvasController.canvas.width, canvasController.canvas.height);
          // Run inspection
          analyzeCurrentCanvas();
        }
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  }

  function loadCalculationSample(index) {
    const sample = OyenDetectiveScanner.sampleCalculations[index];
    if (!sample) return;

    const reportEl = document.getElementById("detectiveReportArea");
    if (!reportEl) return;

    const inspection = OyenDetectiveScanner.inspectCalculation(sample.lines, sample.topic);
    renderInspectionResults(reportEl, sample, inspection);
  }

  function analyzeCurrentCanvas() {
    const sample = OyenDetectiveScanner.sampleCalculations[0];
    loadCalculationSample(0);
  }

  function renderInspectionResults(container, sample, inspection) {
    const lang = OyenI18n.getLang();
    const isClean = inspection.allValid;

    container.innerHTML = `
      <div style="background:var(--cream-bg);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:16px;animation:slideIn 0.2s ease;">
        <div style="display:flex;align-items:center;gap:8px;font-weight:800;color:${isClean ? 'var(--color-success)' : 'var(--color-danger)'};margin-bottom:8px;">
          <span>${isClean ? '✔' : '🔍'}</span>
          <span>${isClean ? (lang === "ms" ? "Semua Baris Tepat!" : "All Steps Sound!") : (lang === "ms" ? "Laporan Detektif Oyen" : "Detective Oyen's Report")}</span>
        </div>
        <p style="font-size:13px;line-height:1.5;margin-bottom:12px;">${inspection.summary}</p>
        
        <div style="display:flex;flex-direction:column;gap:6px;font-size:12px;">
          ${sample.lines.map((line, i) => `
            <div style="background:#fff;padding:8px 12px;border-radius:6px;border-left:3px solid ${line.valid !== false ? 'var(--color-success)' : 'var(--color-danger)'};">
              <b>${line.text}</b>
              ${line.error ? `<div style="color:var(--color-danger);margin-top:4px;">⚠️ ${line.error}</div>` : ""}
              ${line.note ? `<div style="color:var(--color-success);margin-top:4px;">✨ ${line.note}</div>` : ""}
            </div>
          `).join("")}
        </div>

        <div style="margin-top:12px;padding-top:8px;border-top:1px dashed var(--border-color);font-size:12px;font-weight:700;color:var(--dark-orange);">
          🎯 ${lang === "ms" ? "Skema Jawapan Tepat" : "Target SPM Solution"}: ${sample.correctSolution}
        </div>
      </div>
    `;

    renderOyenSideAvatar(isClean ? "excited" : "detective");
    if (isClean) {
      OyenAudio.playSuccess();
    } else {
      OyenAudio.playWrong();
    }
  }

  // ==========================================
  // VIEW: LEADERBOARD
  // ==========================================
  async function renderLeaderboardView(container) {
    const lang = OyenI18n.getLang();
    const list = await OyenFirebase.getLeaderboard(graph.state.normalPoints, "happy");

    container.innerHTML = `
      <div>
        <div style="margin-bottom:16px;">
          <h3 style="font-size:22px;font-weight:900;color:var(--dark-orange);">
            🏆 ${lang === "ms" ? "Papan Pendahulu SPM Malaysia" : "SPM Malaysia Leaderboard"}
          </h3>
          <p style="font-size:13px;color:var(--muted-text);">
            ${lang === "ms" 
              ? "Kedudukan pelajar paling aktif dan konsisten dalam menakluki Matematik Tambahan!" 
              : "Top active and consistent students mastering SPM Additional Mathematics!"}
          </p>
        </div>

        <div class="leaderboard-list">
          ${list.map(item => `
            <div class="leader-item ${item.isUser ? 'highlight-user' : ''}">
              <div class="leader-rank">#${item.rank}</div>
              <div class="leader-info">
                <div style="width:36px;height:36px;">
                  ${OyenCharacter.render(item.avatar || "happy", 36)}
                </div>
                <div>
                  <div class="leader-name">${item.name}</div>
                  <div class="leader-school">${item.school}</div>
                </div>
              </div>
              <div style="text-align:right;">
                <div class="leader-score">${item.points} XP</div>
                <div style="font-size:11px;color:var(--muted-text);">🐟 ${item.fishCoins}</div>
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // ==========================================
  // VIEW: ACHIEVEMENTS
  // ==========================================
  function renderAchievementsView(container) {
    const lang = OyenI18n.getLang();
    const badges = [
      { id: "b1", title: "Langkah Tapak Pertama", titleEn: "First Paw Step", desc: "Menyelesaikan soalan Pembezaan yang pertama.", unlocked: true, icon: "🐾" },
      { id: "b2", title: "Raja Petua Kuasa", titleEn: "Power Rule Prodigy", desc: "Berjaya menyelesaikan 5 soalan pembezaan berturut-turut.", unlocked: graph.state.normalPoints >= 50, icon: "⚡" },
      { id: "b3", title: "Detektif + C", titleEn: "Plus C Detective", desc: "Sentiasa ingat menulis + C dalam kamiran tak tentu.", unlocked: graph.state.mastery.integ > 0.3, icon: "🔍" },
      { id: "b4", title: "Wira LOCK IN!", titleEn: "Lock In Hero", desc: "Berjaya memulihkan 5 jantung dalam satu sesi pemulihan.", unlocked: graph.state.recoveryPoints > 0, icon: "🐈" },
      { id: "b5", title: "Legenda AddMath SPM", titleEn: "SPM AddMath Legend", desc: "Mencapai 100% penguasaan dalam Pembezaan dan Pengamiran.", unlocked: graph.state.mastery.dif >= 0.9 && graph.state.mastery.integ >= 0.9, icon: "👑" }
    ];

    container.innerHTML = `
      <div>
        <div style="margin-bottom:16px;">
          <h3 style="font-size:22px;font-weight:900;color:var(--dark-orange);">
            🎖️ ${lang === "ms" ? "Pencapaian & Lencana Oyen" : "Oyen's Achievements & Badges"}
          </h3>
          <p style="font-size:13px;color:var(--muted-text);">
            ${lang === "ms" 
              ? "Kumpul semua lencana kucing dan trofi emas sepanjang pengembaraan SPM anda!" 
              : "Collect every cat badge and golden trophy throughout your SPM adventure!"}
          </p>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:16px;">
          ${badges.map(b => `
            <div class="chapter-card" style="padding:18px;text-align:center;opacity:${b.unlocked ? 1 : 0.6};border-color:${b.unlocked ? 'var(--primary-orange)' : 'var(--border-color)'};">
              <div style="font-size:36px;margin-bottom:8px;">${b.icon}</div>
              <h4 style="font-size:15px;font-weight:800;color:var(--dark-text);">${lang === "ms" ? b.title : b.titleEn}</h4>
              <p style="font-size:12px;color:var(--muted-text);margin-top:6px;line-height:1.4;">${b.desc}</p>
              <div style="margin-top:10px;font-size:11px;font-weight:800;color:${b.unlocked ? 'var(--color-success)' : 'var(--muted-text)'};">
                ${b.unlocked ? (lang === "ms" ? "✔ TERCAPAI" : "✔ UNLOCKED") : (lang === "ms" ? "🔒 TERKUNCI" : "🔒 LOCKED")}
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  // ==========================================
  // GRAPH EVENT HANDLER
  // ==========================================
  function handleGraphEvent(event, data, state) {
    updateHeaderStats();
    renderSidePanel();

    // Auto-sync to Firebase / localStorage
    OyenFirebase.saveStudentProfile(state);

    if (event === "question_ready") {
      if (currentView === "learning" || currentView === "recovery") {
        const stage = document.getElementById("mainAppStage");
        if (stage) renderQuestionStage(stage);
      }
      renderOyenSideAvatar(state.phase === "recovery" ? "determined" : "happy");
    }

    if (event === "answer_evaluated") {
      const fbContainer = document.getElementById("answerFeedbackContainer");
      const lang = OyenI18n.getLang();
      const q = state.currentQuestion;

      if (data.isCorrect) {
        OyenAudio.playSuccess();
        renderOyenSideAvatar("happy");
      } else {
        OyenAudio.playWrong();
        renderOyenSideAvatar(state.hearts <= 1 ? "sad" : "confused");
      }

      if (fbContainer) {
        const targetAns = q ? q.t : "";
        const isCorrect = data.isCorrect;
        fbContainer.innerHTML = `
          <div class="feedback-banner ${isCorrect ? 'correct' : 'incorrect'}">
            <div style="font-size:24px;">${isCorrect ? '✔' : '✘'}</div>
            <div style="flex:1;">
              <div style="font-weight:800;font-size:15px;margin-bottom:4px;">
                ${isCorrect ? OyenI18n.t("oyenQuotes.correct") : (data.result.msg || OyenI18n.t("oyenQuotes.incorrect"))}
              </div>
              ${!isCorrect ? `<div style="font-size:13px;color:var(--dark-text);">Jawapan tepat / Correct Answer: <b>${targetAns}</b></div>` : ""}
            </div>
          </div>
          <div style="margin-top:14px;text-align:right;">
            <button class="btn btn-primary" onclick="OyenApp.advanceStep()">
              ${lang === "ms" ? "Seterusnya" : "Next"} →
            </button>
          </div>
        `;
      }
    }

    if (event === "answer_format_error") {
      const fbContainer = document.getElementById("answerFeedbackContainer");
      if (fbContainer) {
        fbContainer.innerHTML = `
          <div class="feedback-banner incorrect">
            <div style="font-size:20px;">⚠️</div>
            <div style="font-size:13px;font-weight:600;">${data.msg}</div>
          </div>
        `;
      }
      renderOyenSideAvatar("confused");
      OyenAudio.playWrong();
    }

    if (event === "prerequisite_suggested") {
      const stage = document.getElementById("mainAppStage");
      const lang = OyenI18n.getLang();
      if (stage) {
        stage.innerHTML = `
          <div style="background:var(--cream-bg);border:2px solid var(--primary-orange);border-radius:var(--radius-lg);padding:24px;text-align:center;">
            <div style="width:100px;height:100px;margin:0 auto 12px;">
              ${OyenCharacter.render("thinking", 100)}
            </div>
            <h3 style="font-size:20px;font-weight:900;color:var(--dark-orange);">
              ${lang === "ms" ? "Cadangan Orchestrator AI" : "AI Orchestrator Recommendation"}
            </h3>
            <p style="font-size:14px;color:var(--dark-text);max-width:540px;margin:8px auto 16px;line-height:1.6;">
              ${lang === "ms"
                ? `Oyen mengesan corak kesilapan anda berpunca daripada penguasaan hukum indeks. Sebelum meneruskan Pembezaan, Oyen mengesyorkan mengulang kaji modul <b>${data.prereqName}</b>!`
                : `Oyen detected repeated errors linked to index manipulation rules. Before continuing Differentiation, we recommend reviewing <b>${data.prereqName}</b> first!`}
            </p>
            <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
              <button class="btn btn-primary" onclick="OyenApp.startChapter('${data.prereqId}')">
                ✔ ${OyenI18n.t("btnAcceptPrereq")}
              </button>
              <button class="btn btn-alt" onclick="OyenApp.proceedToTeachingDirectly()">
                ${OyenI18n.t("btnSkipPrereq")}
              </button>
            </div>
          </div>
        `;
      }
    }

    if (event === "teaching_ready") {
      const stage = document.getElementById("mainAppStage");
      if (stage) renderTeachingView(stage, data);
    }

    if (event === "evaluation_completed") {
      const stage = document.getElementById("mainAppStage");
      const lang = OyenI18n.getLang();
      if (stage) {
        stage.innerHTML = `
          <div style="text-align:center;padding:10px 0;">
            <div style="width:110px;height:110px;margin:0 auto 10px;">
              ${OyenCharacter.render("excited", 110)}
            </div>
            <h3 style="font-size:24px;font-weight:900;color:var(--dark-orange);">
              ${lang === "ms" ? "Laporan Kemajuan Sesi" : "Session Progress Report"}
            </h3>
            <p style="font-size:14px;color:var(--muted-text);margin-bottom:16px;">
              ${data.recommendation}
            </p>

            <div style="background:var(--cream-bg);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:18px;max-width:440px;margin:0 auto 20px;text-align:left;">
              <div style="display:flex;justify-content:space-between;font-size:13px;font-weight:700;margin-bottom:4px;">
                <span>${lang === "ms" ? "Penguasaan Baharu" : "New Mastery Score"}:</span>
                <span style="color:var(--dark-orange);">${Math.round(data.newMastery * 100)}%</span>
              </div>
              <div class="mastery-track" style="height:12px;">
                <div class="mastery-fill" style="width:${Math.round(data.newMastery * 100)}%;"></div>
              </div>
            </div>

            <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
              <button class="btn btn-primary" onclick="OyenApp.switchView('adventure')">
                🗺️ ${OyenI18n.t("btnBackMap")}
              </button>
              <button class="btn btn-secondary" onclick="OyenApp.startChapter('${state.currentTopicId}')">
                🔁 ${lang === "ms" ? "Ulang Bab Ini" : "Repeat Chapter"}
              </button>
            </div>
          </div>
        `;
      }
      renderOyenSideAvatar("excited");
      OyenAudio.playMeow();
    }

    if (event === "recovery_mode_started") {
      switchView("learning");
      renderOyenSideAvatar("determined");
    }

    if (event === "heart_recovered") {
      OyenAudio.playRecovery();
      alert("💖 Meow! 1 Jantung berjaya dipulihkan! Teruskan usaha!");
      switchView("adventure");
    }
  }

  function advanceStep() {
    graph.nextStep();
  }

  function proceedToTeachingDirectly() {
    graph.startTeachingPhase();
  }

  function updateAllUIText() {
    updateHeaderStats();
    updateUserProfileUI();
    renderSidePanel();
    switchView(currentView);
  }

  return {
    init,
    switchView,
    startChapter,
    submitAnswer,
    advanceStep,
    proceedToChallenge,
    switchTeachingStrategy,
    proceedToTeachingDirectly,
    clearCanvas,
    handleImageUpload,
    loadCalculationSample,
    analyzeCurrentCanvas,
    getGraph: () => graph
  };
})();

// Start application when DOM is ready
if (typeof window !== "undefined") {
  window.addEventListener("DOMContentLoaded", () => {
    OyenApp.init();
  });
}

