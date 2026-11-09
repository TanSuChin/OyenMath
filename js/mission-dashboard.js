/**
 * Oyen Math - Autonomous Learning Mission Dashboard (Milestone M5)
 * Integrates the 12-node persistent LangGraph Autonomous Mission system into the OyenMath UI.
 * Preserves Oyen mascot, orange/cream theme, and Bahasa Melayu / English bilingual support.
 */
const OyenMissionDashboard = (() => {
  const STORAGE_KEY_MISSION_ID = "oyen_active_mission_id";
  let currentMission = null;
  let pollTimer = null;
  let isSubmitting = false;
  let lastFeedback = null;

  const PRESET_OBJECTIVES = {
    ms: [
      {
        label: "Kuasai Pembezaan sekurang-kurangnya 80%",
        topic: "dif",
        target: 0.80,
        goal: "Master Differentiation (Pembezaan) to at least 80% verified mastery"
      },
      {
        label: "Kenal pasti & baiki kelemahan dalam Pengamiran",
        topic: "integ",
        target: 0.80,
        goal: "Identify and remediate weaknesses in Indefinite & Definite Integration"
      },
      {
        label: "Tingkatkan kefahaman Petua Rantai & Kuasa",
        topic: "dif",
        target: 0.85,
        goal: "Improve understanding of power-rule and chain-rule differentiation"
      },
      {
        label: "Ulang kaji prasyarat Hukum Indeks sebelum Pengamiran",
        topic: "ind",
        target: 0.75,
        goal: "Complete prerequisite revision on Laws of Indices before Integration"
      },
      {
        label: "Program latihan peribadi Fungsi Kuadratik (80%)",
        topic: "quad",
        target: 0.80,
        goal: "Complete a personalised Quadratic Functions mastery programme"
      }
    ],
    en: [
      {
        label: "Master Differentiation to at least 80%",
        topic: "dif",
        target: 0.80,
        goal: "Master Differentiation to at least 80% verified mastery"
      },
      {
        label: "Identify and remediate weaknesses in Integration",
        topic: "integ",
        target: 0.80,
        goal: "Identify and remediate weaknesses in Integration"
      },
      {
        label: "Improve understanding of chain-rule differentiation",
        topic: "dif",
        target: 0.85,
        goal: "Improve understanding of chain-rule differentiation"
      },
      {
        label: "Complete prerequisite revision before beginning Integration",
        topic: "ind",
        target: 0.75,
        goal: "Complete prerequisite revision on Laws of Indices before beginning Integration"
      },
      {
        label: "Complete a personalised Quadratic Functions programme",
        topic: "quad",
        target: 0.80,
        goal: "Complete a personalised Quadratic Functions learning programme"
      }
    ]
  };

  function _lang() {
    return typeof OyenI18n !== "undefined" ? OyenI18n.getLang() : "ms";
  }

  function _topicName(topicId) {
    if (typeof OyenCurriculum !== "undefined" && OyenCurriculum.getTopic) {
      const t = OyenCurriculum.getTopic(topicId);
      if (t && t.name) return t.name;
    }
    const names = {
      dif: _lang() === "ms" ? "Pembezaan (Differentiation)" : "Differentiation",
      integ: _lang() === "ms" ? "Pengamiran (Integration)" : "Integration",
      ind: _lang() === "ms" ? "Hukum Indeks (Laws of Indices)" : "Laws of Indices",
      quad: _lang() === "ms" ? "Fungsi Kuadratik (Quadratic Functions)" : "Quadratic Functions"
    };
    return names[topicId] || topicId;
  }

  function _statusMeta(status) {
    const s = String(status || "CREATED").toUpperCase();
    const ms = _lang() === "ms";
    const map = {
      CREATED: { bg: "#e2e8f0", fg: "#334155", icon: "🆕", text: ms ? "Dicipta" : "Created", active: false },
      QUEUED: { bg: "#dbeafe", fg: "#1d4ed8", icon: "⏳", text: ms ? "Dalam Giliran" : "Queued", active: true },
      RUNNING: { bg: "#fef3c7", fg: "#b45309", icon: "⚙️", text: ms ? "Ejen Sedang Berjalan..." : "Agent Executing...", active: true },
      WAITING_FOR_STUDENT: { bg: "#ffedd5", fg: "#c2410c", icon: "✍️", text: ms ? "Menunggu Jawapan Pelajar" : "Waiting for Student Input", active: false },
      PAUSED: { bg: "#f1f5f9", fg: "#475569", icon: "⏸️", text: ms ? "Dijeda (Paused)" : "Paused", active: false },
      COMPLETED: { bg: "#dcfce7", fg: "#15803d", icon: "🏆", text: ms ? "Misi Selesai!" : "Mission Completed!", active: false },
      CANCELLED: { bg: "#fee2e2", fg: "#b91c1c", icon: "🛑", text: ms ? "Dibatalkan" : "Cancelled", active: false },
      FAILED: { bg: "#fee2e2", fg: "#991b1b", icon: "⚠️", text: ms ? "Ralat Pelaksanaan" : "Execution Failed", active: false },
      BUDGET_EXHAUSTED: { bg: "#fef9c3", fg: "#854d0e", icon: "🔋", text: ms ? "Bajet Langkah Tamat" : "Budget Exhausted", active: false }
    };
    return map[s] || { bg: "#e2e8f0", fg: "#334155", icon: "📌", text: s, active: false };
  }

  function _stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function _startPollingIfNeeded() {
    _stopPolling();
    if (!currentMission || !currentMission.mission_id) return;
    const st = String(currentMission.status || "").toUpperCase();
    if (st === "RUNNING" || st === "QUEUED") {
      pollTimer = setInterval(async () => {
        if (!currentMission || !currentMission.mission_id) {
          _stopPolling();
          return;
        }
        const res = await OyenAgentAPI.getMissionStatus(currentMission.mission_id);
        if (res && !res.error && res.mission_id) {
          currentMission = Object.assign({}, currentMission, res);
          _syncToAppGraph(currentMission);
          const stage = document.getElementById("mainAppStage");
          if (stage && stage.dataset.activeView === "autonomous") {
            render(stage);
          }
          if (res.status !== "RUNNING" && res.status !== "QUEUED") {
            _stopPolling();
          }
        }
      }, 1500);
    }
  }

  function _syncToAppGraph(mission) {
    if (!mission || typeof OyenApp === "undefined" || !OyenApp.getGraph) return;
    const g = OyenApp.getGraph();
    if (!g) return;

    // Sync verified mastery scores to client state
    const vm = mission.verified_mastery || mission.mastery || {};
    Object.keys(vm).forEach(k => {
      if (typeof vm[k] === "number") {
        g.state.mastery[k] = vm[k];
      }
    });

    // Sync latest trace line into side panel
    const traces = mission.trace || [];
    if (traces.length > 0) {
      const latest = traces[traces.length - 1];
      const existingMsgs = g.state.traceLog.map(t => t.message);
      if (!existingMsgs.includes(latest)) {
        g.logDecision("O", latest);
      }
    }
  }

  async function restoreActiveMission() {
    try {
      const savedId = localStorage.getItem(STORAGE_KEY_MISSION_ID);
      if (savedId) {
        const res = await OyenAgentAPI.getMission(savedId);
        if (res && !res.error && res.mission_id) {
          currentMission = res;
          _syncToAppGraph(currentMission);
          return currentMission;
        }
      }
      // Otherwise check server list for most recent mission
      const listRes = await OyenAgentAPI.listMissions();
      if (listRes && Array.isArray(listRes.missions) && listRes.missions.length > 0) {
        const latestId = listRes.missions[0].mission_id;
        if (latestId) {
          const full = await OyenAgentAPI.getMission(latestId);
          if (full && !full.error && full.mission_id) {
            currentMission = full;
            localStorage.setItem(STORAGE_KEY_MISSION_ID, full.mission_id);
            _syncToAppGraph(currentMission);
            return currentMission;
          }
        }
      }
    } catch (e) {
      console.warn("Mission restore warning:", e);
    }
    return null;
  }

  async function launchMissionFromForm() {
    const topicEl = document.getElementById("missionTopicSelect");
    const goalEl = document.getElementById("missionGoalInput");
    const targetEl = document.getElementById("missionTargetSelect");
    const stepsEl = document.getElementById("missionMaxStepsSelect");

    const topic_id = topicEl ? topicEl.value : "dif";
    const target_mastery = targetEl ? parseFloat(targetEl.value) : 0.80;
    const max_steps = stepsEl ? parseInt(stepsEl.value, 10) : 25;
    const goalText = (goalEl && goalEl.value.trim())
      ? goalEl.value.trim()
      : `Master ${_topicName(topic_id)} to ${Math.round(target_mastery * 100)}%`;

    let initial_mastery = {};
    if (typeof OyenApp !== "undefined" && OyenApp.getGraph && OyenApp.getGraph()) {
      initial_mastery = Object.assign({}, OyenApp.getGraph().state.mastery);
    }

    lastFeedback = null;
    isSubmitting = true;
    const stage = document.getElementById("mainAppStage");
    if (stage) render(stage);

    const res = await OyenAgentAPI.startMission({
      topic_id,
      target_mastery,
      goal: {
        topic: topic_id,
        topic_id,
        description: goalText,
        target_mastery,
        goal_type: "mastery"
      },
      budget: {
        max_steps,
        max_tool_calls: max_steps * 2,
        max_duration_seconds: 1800
      },
      language: _lang(),
      initial_mastery,
      idempotency_key: "start_" + Date.now()
    });

    isSubmitting = false;
    if (res && !res.error && res.mission_id) {
      currentMission = res;
      try {
        localStorage.setItem(STORAGE_KEY_MISSION_ID, res.mission_id);
      } catch (e) {}
      _syncToAppGraph(currentMission);
      _startPollingIfNeeded();
    } else {
      alert((res && res.error) ? res.error : "Gagal memulakan misi autonomi.");
    }
    if (stage) render(stage);
  }

  function applyPreset(index) {
    const list = PRESET_OBJECTIVES[_lang()] || PRESET_OBJECTIVES.ms;
    const item = list[index];
    if (!item) return;
    const topicEl = document.getElementById("missionTopicSelect");
    const goalEl = document.getElementById("missionGoalInput");
    const targetEl = document.getElementById("missionTargetSelect");
    if (topicEl) topicEl.value = item.topic;
    if (goalEl) goalEl.value = item.goal;
    if (targetEl) targetEl.value = String(item.target);
  }

  async function submitChallengeResponse() {
    if (!currentMission || !currentMission.mission_id || isSubmitting) return;
    const inputEl = document.getElementById("missionAnswerInput");
    const answer = inputEl ? inputEl.value.trim() : "";
    if (!answer) {
      alert(_lang() === "ms" ? "Sila masukkan jawapan matematik atau 'faham' untuk meneruskan!" : "Please enter your answer or 'understood' to continue!");
      return;
    }

    isSubmitting = true;
    const stage = document.getElementById("mainAppStage");
    if (stage) render(stage);

    const res = await OyenAgentAPI.respondMission(currentMission.mission_id, {
      answer,
      time_spent_sec: 12.0
    });

    isSubmitting = false;
    if (res && !res.error && res.mission_id) {
      currentMission = res;
      if (res.verification) {
        lastFeedback = res.verification;
      }
      _syncToAppGraph(currentMission);
      _startPollingIfNeeded();
    } else {
      alert((res && res.error) ? res.error : "Gagal menghantar jawapan.");
    }
    if (stage) render(stage);
  }

  async function acknowledgeTeachingStep() {
    if (!currentMission || !currentMission.mission_id || isSubmitting) return;
    const act = currentMission.current_activity || {};
    const autoAnswer = act.expected_answer || act.correct_answer || "x";
    isSubmitting = true;
    const stage = document.getElementById("mainAppStage");
    if (stage) render(stage);

    const res = await OyenAgentAPI.respondMission(currentMission.mission_id, {
      answer: autoAnswer,
      time_spent_sec: 8.0
    });
    isSubmitting = false;
    if (res && !res.error && res.mission_id) {
      currentMission = res;
      lastFeedback = res.verification || null;
      _syncToAppGraph(currentMission);
      _startPollingIfNeeded();
    }
    if (stage) render(stage);
  }

  async function pauseCurrentMission() {
    if (!currentMission || !currentMission.mission_id) return;
    const res = await OyenAgentAPI.pauseMission(currentMission.mission_id);
    if (res && !res.error) {
      currentMission = res;
      _stopPolling();
      const stage = document.getElementById("mainAppStage");
      if (stage) render(stage);
    }
  }

  async function resumeCurrentMission() {
    if (!currentMission || !currentMission.mission_id) return;
    const res = await OyenAgentAPI.resumeMission(currentMission.mission_id);
    if (res && !res.error) {
      currentMission = res;
      _startPollingIfNeeded();
      const stage = document.getElementById("mainAppStage");
      if (stage) render(stage);
    }
  }

  async function cancelCurrentMission() {
    if (!currentMission || !currentMission.mission_id) return;
    const res = await OyenAgentAPI.cancelMission(currentMission.mission_id);
    if (res && !res.error) {
      currentMission = res;
      _stopPolling();
      const stage = document.getElementById("mainAppStage");
      if (stage) render(stage);
    }
  }

  async function refreshCurrentMission() {
    if (!currentMission || !currentMission.mission_id) return;
    const res = await OyenAgentAPI.getMission(currentMission.mission_id);
    if (res && !res.error) {
      currentMission = res;
      _syncToAppGraph(currentMission);
      const stage = document.getElementById("mainAppStage");
      if (stage) render(stage);
    }
  }

  function clearForNewMission() {
    _stopPolling();
    currentMission = null;
    lastFeedback = null;
    try {
      localStorage.removeItem(STORAGE_KEY_MISSION_ID);
    } catch (e) {}
    const stage = document.getElementById("mainAppStage");
    if (stage) render(stage);
  }

  function render(container) {
    if (!container) return;
    container.dataset.activeView = "autonomous";
    const ms = _lang() === "ms";
    const presets = PRESET_OBJECTIVES[_lang()] || PRESET_OBJECTIVES.ms;

    if (!currentMission) {
      container.innerHTML = `
        <div class="autonomous-dashboard" style="display:flex;flex-direction:column;gap:18px;">
          <!-- Banner -->
          <div style="background:linear-gradient(135deg, #FFF3E0, #FFE0B2);border:2px solid var(--primary-orange);border-radius:var(--radius-lg);padding:20px;display:flex;align-items:center;gap:18px;flex-wrap:wrap;">
            <div style="flex-shrink:0;">
              ${typeof OyenCharacter !== "undefined" ? OyenCharacter.render("excited", 96) : "🐱"}
            </div>
            <div style="flex:1;min-width:240px;">
              <div style="display:inline-block;background:var(--dark-orange);color:#fff;font-size:11px;font-weight:800;padding:3px 10px;border-radius:20px;margin-bottom:6px;">
                🤖 ${ms ? "MISI PEMBELAJARAN AUTONOMI LANGGRAPH" : "AUTONOMOUS LANGGRAPH LEARNING MISSION"}
              </div>
              <h2 style="font-size:21px;font-weight:900;color:var(--dark-text);margin:0 0 6px;">
                ${ms ? "Biarkan Ejen Oyen Mengurus Misi Pembelajaran Anda!" : "Let Agent Oyen Independently Manage Your Learning Mission!"}
              </h2>
              <p style="font-size:13px;color:var(--muted-text);margin:0;line-height:1.5;">
                ${ms
                  ? "Tetapkan sasaran anda. Oyen akan mendiagnosis jurang prasyarat, membina pelan pembelajaran adaptif, mengesahkan jawapan dengan SymPy, dan mengulang kaji strategi sehingga sasaran tercapai."
                  : "Set your learning goal. Oyen will diagnose prerequisite gaps, generate an adaptive learning plan, verify answers deterministically via SymPy, and replan autonomously until you reach mastery."}
              </p>
            </div>
          </div>

          <!-- Mission Launcher Card -->
          <div class="card" style="padding:20px;border:2px solid var(--border-color);">
            <h3 style="margin:0 0 12px;font-size:16px;font-weight:800;color:var(--dark-orange);">
              🎯 ${ms ? "1. Pilih Objektif Misi atau Tetapkan Sasaran Sendiri" : "1. Choose a Preset Objective or Define Your Goal"}
            </h3>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;">
              ${presets.map((p, idx) => `
                <button type="button" class="btn btn-secondary btn-sm" onclick="OyenMissionDashboard.applyPreset(${idx})" style="font-size:12px;">
                  ✨ ${p.label}
                </button>
              `).join("")}
            </div>

            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:12px;margin-bottom:14px;">
              <div>
                <label style="font-size:12px;font-weight:700;display:block;margin-bottom:4px;">
                  📚 ${ms ? "Topik Sasaran SPM" : "Target SPM Topic"}
                </label>
                <select id="missionTopicSelect" class="math-input" style="width:100%;font-size:14px;padding:9px;text-align:left;">
                  <option value="dif">${_topicName("dif")}</option>
                  <option value="integ">${_topicName("integ")}</option>
                  <option value="ind">${_topicName("ind")}</option>
                  <option value="quad">${_topicName("quad")}</option>
                </select>
              </div>
              <div>
                <label style="font-size:12px;font-weight:700;display:block;margin-bottom:4px;">
                  🎖️ ${ms ? "Sasaran Penguasaan (Verified Mastery)" : "Target Verified Mastery"}
                </label>
                <select id="missionTargetSelect" class="math-input" style="width:100%;font-size:14px;padding:9px;text-align:left;">
                  <option value="0.70">70% (${ms ? "Asas Kukuh" : "Solid Foundation"})</option>
                  <option value="0.80" selected>80% (${ms ? "Cemerlang SPM" : "SPM Distinction"})</option>
                  <option value="0.90">90% (${ms ? "Pakar Topik" : "Topic Master"})</option>
                </select>
              </div>
              <div>
                <label style="font-size:12px;font-weight:700;display:block;margin-bottom:4px;">
                  🔋 ${ms ? "Bajet Langkah Ejen Maksimum" : "Max Autonomous Agent Steps"}
                </label>
                <select id="missionMaxStepsSelect" class="math-input" style="width:100%;font-size:14px;padding:9px;text-align:left;">
                  <option value="20">20 ${ms ? "langkah" : "steps"}</option>
                  <option value="30" selected>30 ${ms ? "langkah" : "steps"}</option>
                  <option value="50">50 ${ms ? "langkah" : "steps"}</option>
                </select>
              </div>
            </div>

            <div style="margin-bottom:16px;">
              <label style="font-size:12px;font-weight:700;display:block;margin-bottom:4px;">
                📝 ${ms ? "Penerangan Objektif Misi" : "Mission Objective Description"}
              </label>
              <input id="missionGoalInput" type="text" class="math-input" style="width:100%;font-size:14px;padding:10px;text-align:left;"
                value="${presets[0].goal}" />
            </div>

            <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
              <button type="button" class="btn btn-primary" onclick="OyenMissionDashboard.launchMissionFromForm()" ${isSubmitting ? "disabled" : ""}>
                🚀 ${isSubmitting
                  ? (ms ? "Memulakan Misi Autonomi..." : "Starting Autonomous Mission...")
                  : (ms ? "Mulakan Misi Pembelajaran Autonomi" : "Start Autonomous Learning Mission")}
              </button>
              <span style="font-size:12px;color:var(--muted-text);">
                🔒 ${ms
                  ? "Pengesahan jawapan dikawal sepenuhnya oleh enjin deterministik SymPy."
                  : "Answer correctness is verified deterministically by SymPy."}
              </span>
            </div>
          </div>
        </div>
      `;
      return;
    }

    // Active or historical mission view
    const m = currentMission;
    const stMeta = _statusMeta(m.status);
    const goal = m.goal || {};
    const topicId = m.topic_id || goal.topic || "dif";
    const prog = m.progress_summary || {};
    const initialM = Math.round((prog.initial_mastery || 0) * 100);
    const verifiedM = Math.round(
      ((prog.current_verified_mastery !== undefined
        ? prog.current_verified_mastery
        : (m.verified_mastery && m.verified_mastery[topicId]) || 0) * 100)
    );
    const targetM = Math.round((goal.target_mastery || 0.8) * 100);
    const goalPct = Math.min(100, Math.round((verifiedM / Math.max(1, targetM)) * 100));
    const planActs = (m.plan && Array.isArray(m.plan.activities)) ? m.plan.activities : [];
    const curAct = m.current_activity || prog.next_recommended_activity || null;
    const waitInfo = m.waiting_interaction || {};
    const budget = m.budget || {};
    const traces = Array.isArray(m.trace) ? m.trace : [];
    const misconceptions = Array.isArray(m.identified_misconceptions) ? m.identified_misconceptions : [];
    const authLabel = m.auth_label || (m.auth_mode === "cloud" ? "☁️ Firebase Cloud" : "💾 Offline Dev Mode (dev-local)");

    const isWaiting = String(m.status).toUpperCase() === "WAITING_FOR_STUDENT";
    const isRunning = String(m.status).toUpperCase() === "RUNNING" || String(m.status).toUpperCase() === "QUEUED";
    const isPaused = String(m.status).toUpperCase() === "PAUSED";
    const isTerminal = ["COMPLETED", "CANCELLED", "FAILED", "BUDGET_EXHAUSTED"].includes(String(m.status).toUpperCase());

    container.innerHTML = `
      <div class="autonomous-dashboard" style="display:flex;flex-direction:column;gap:16px;">
        <!-- 1. MISSION OVERVIEW & CONTROLS HEADER -->
        <div class="card" style="padding:18px;border:2px solid var(--primary-orange);background:linear-gradient(180deg,#FFFBF5,#FFFFFF);">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
            <div>
              <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px;">
                <span style="background:${stMeta.bg};color:${stMeta.fg};font-weight:800;font-size:12px;padding:4px 10px;border-radius:20px;border:1px solid ${stMeta.fg}33;">
                  ${stMeta.icon} ${stMeta.text} (${m.status})
                </span>
                <span style="background:#f1f5f9;color:#475569;font-size:11px;font-weight:700;padding:3px 8px;border-radius:12px;">
                  🆔 ${m.mission_id}
                </span>
                <span style="background:#eef2ff;color:#4338ca;font-size:11px;font-weight:700;padding:3px 8px;border-radius:12px;" title="Authentication & Ownership Isolation Mode">
                  🛡️ ${authLabel}
                </span>
              </div>
              <h2 style="font-size:19px;font-weight:900;color:var(--dark-text);margin:0 0 4px;">
                🎯 ${goal.description || _topicName(topicId)}
              </h2>
              <div style="font-size:13px;color:var(--muted-text);">
                📚 <b>${ms ? "Topik Semasa" : "Current Topic"}:</b> ${_topicName(topicId)} &nbsp;|&nbsp;
                🤖 <b>${ms ? "Ejen Aktif" : "Active Agent"}:</b> <code>${m.current_agent || "orchestrator"}</code>
              </div>
            </div>

            <!-- Mission Controls -->
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              ${!isTerminal && !isPaused ? `
                <button type="button" class="btn btn-secondary btn-sm" onclick="OyenMissionDashboard.pauseCurrentMission()">
                  ⏸️ ${ms ? "Jeda (Pause)" : "Pause"}
                </button>
              ` : ""}
              ${isPaused ? `
                <button type="button" class="btn btn-primary btn-sm" onclick="OyenMissionDashboard.resumeCurrentMission()">
                  ▶️ ${ms ? "Sambung (Resume)" : "Resume"}
                </button>
              ` : ""}
              ${!isTerminal ? `
                <button type="button" class="btn btn-alt btn-sm" onclick="OyenMissionDashboard.cancelCurrentMission()">
                  🛑 ${ms ? "Henti Misi" : "Stop Mission"}
                </button>
              ` : ""}
              <button type="button" class="btn btn-secondary btn-sm" onclick="OyenMissionDashboard.refreshCurrentMission()">
                🔄 ${ms ? "Segar Semula" : "Refresh"}
              </button>
              <button type="button" class="btn btn-primary btn-sm" onclick="OyenMissionDashboard.clearForNewMission()">
                ➕ ${ms ? "Misi Baharu" : "New Mission"}
              </button>
            </div>
          </div>

          <!-- Progress toward Mastery Target -->
          <div style="background:var(--cream-bg);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:12px;">
            <div style="display:flex;justify-content:space-between;font-size:13px;font-weight:800;margin-bottom:6px;">
              <span>📈 ${ms ? "Kemajuan ke Sasaran Penguasaan" : "Progress Toward Mastery Goal"} (${verifiedM}% / ${targetM}%)</span>
              <span style="color:var(--dark-orange);">${goalPct}%</span>
            </div>
            <div class="mastery-track" style="height:12px;">
              <div class="mastery-fill" style="width:${goalPct}%;"></div>
            </div>
          </div>
        </div>

        <!-- 2. ACTIVE WORKSPACE (WAITING FOR STUDENT / AGENT EXECUTING / COMPLETED) -->
        ${isRunning ? `
          <div class="card" style="padding:20px;text-align:center;border:2px dashed var(--primary-orange);">
            <div style="font-size:32px;margin-bottom:8px;">⚙️🐱</div>
            <h3 style="margin:0 0 6px;color:var(--dark-orange);">
              ${ms ? "Ejen AI Sedang Melaksanakan Kitaran Keputusan Autonomi..." : "AI Agents Actively Executing Autonomous Decision Cycle..."}
            </h3>
            <p style="font-size:13px;color:var(--muted-text);margin:0;">
              ${ms ? "Menganalisis prestasi, menyemak prasyarat, dan memilih aktiviti terbaik seterusnya." : "Analysing performance, checking prerequisites, and selecting the next optimal activity."}
            </p>
          </div>
        ` : ""}

        ${isWaiting && curAct ? `
          <div class="card" style="padding:20px;border:2px solid #f97316;background:#fffaf5;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px;">
              <span style="background:#ffedd5;color:#c2410c;font-weight:800;font-size:12px;padding:4px 10px;border-radius:16px;">
                ✍️ ${ms ? "INTERAKSI PELAJAR DIPERLUKAN" : "STUDENT PARTICIPATION REQUIRED"} · ${String(curAct.type || "challenge").toUpperCase()}
              </span>
              <span style="font-size:12px;color:var(--muted-text);font-weight:700;">
                ${ms ? "Tahap Kesukaran" : "Difficulty Level"}: ${curAct.difficulty || curAct.level || 1}
              </span>
            </div>

            <h3 style="margin:0 0 8px;font-size:17px;font-weight:800;color:var(--dark-text);">
              ${curAct.title || _topicName(curAct.topic || topicId)}
            </h3>

            ${(curAct.content || waitInfo.prompt) ? `
              <div style="background:#ffffff;border-left:4px solid var(--primary-orange);padding:12px 14px;border-radius:8px;margin-bottom:12px;font-size:14px;line-height:1.5;">
                ${curAct.content || waitInfo.prompt}
              </div>
            ` : ""}

            ${Array.isArray(curAct.solution_steps) && curAct.solution_steps.length > 0 ? `
              <div style="background:#f8fafc;border:1px solid #e2e8f0;padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:13px;">
                <b>💡 ${ms ? "Langkah & Panduan Oyen:" : "Oyen's Guided Steps:"}</b>
                <ul style="margin:6px 0 0;padding-left:18px;">
                  ${curAct.solution_steps.map(st => `<li>${st}</li>`).join("")}
                </ul>
              </div>
            ` : ""}

            ${(curAct.question || waitInfo.question) ? `
              <div style="background:#fff3e0;border:1px solid #fdba74;padding:14px;border-radius:10px;margin-bottom:14px;">
                <div style="font-size:12px;font-weight:800;color:#9a3412;margin-bottom:4px;">
                  📐 ${ms ? "SOALAN CABARAN:" : "CHALLENGE QUESTION:"}
                </div>
                <div style="font-size:18px;font-weight:900;color:var(--dark-text);">
                  ${curAct.question || waitInfo.question}
                </div>
              </div>
            ` : ""}

            ${lastFeedback ? `
              <div style="background:${lastFeedback.is_correct ? '#dcfce7' : '#fee2e2'};border:1px solid ${lastFeedback.is_correct ? '#86efac' : '#fca5a5'};padding:10px 14px;border-radius:8px;margin-bottom:12px;font-size:13px;">
                <b>${lastFeedback.is_correct ? "✅ SymPy Verified Correct!" : "❌ SymPy Verification Feedback:"}</b>
                ${lastFeedback.feedback || lastFeedback.explanation || ""}
                ${lastFeedback.error_tag ? `<span style="margin-left:8px;background:#fff;padding:2px 6px;border-radius:6px;font-size:11px;">Tag: ${lastFeedback.error_tag}</span>` : ""}
              </div>
            ` : ""}

            <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
              <input id="missionAnswerInput" type="text" class="math-input"
                style="flex:1;min-width:220px;font-size:15px;padding:10px 14px;text-align:left;"
                placeholder="${ms ? 'Masukkan jawapan matematik (cth: 6*x + 5 atau x^3 + C)...' : 'Enter math answer (e.g. 6*x + 5 or x^3 + C)...'}"
                onkeydown="if(event.key==='Enter'){event.preventDefault();OyenMissionDashboard.submitChallengeResponse();}" />
              <button type="button" class="btn btn-primary" onclick="OyenMissionDashboard.submitChallengeResponse()" ${isSubmitting ? "disabled" : ""}>
                ✔ ${isSubmitting ? (ms ? "Menyemak..." : "Verifying...") : (ms ? "Hantar Jawapan (SymPy)" : "Submit Answer (SymPy)")}
              </button>
              ${curAct.type === "teaching" || curAct.type === "prerequisite" ? `
                <button type="button" class="btn btn-secondary" onclick="OyenMissionDashboard.acknowledgeTeachingStep()" ${isSubmitting ? "disabled" : ""}>
                  👍 ${ms ? "Saya Faham → Teruskan" : "I Understand → Continue"}
                </button>
              ` : ""}
            </div>
          </div>
        ` : ""}

        ${isTerminal ? `
          <div class="card" style="padding:20px;border:2px solid ${m.status === 'COMPLETED' ? '#22c55e' : '#f59e0b'};background:${m.status === 'COMPLETED' ? '#f0fdf4' : '#fffbeb'};">
            <h3 style="margin:0 0 6px;font-size:18px;font-weight:900;">
              ${stMeta.icon} ${stMeta.text}
            </h3>
            <p style="font-size:13px;color:var(--dark-text);margin:0 0 10px;">
              ${m.message || m.termination_reason || (ms ? "Misi telah tamat." : "Mission has concluded.")}
            </p>
            <button type="button" class="btn btn-primary btn-sm" onclick="OyenMissionDashboard.clearForNewMission()">
              🚀 ${ms ? "Mulakan Misi Baharu" : "Start Another Mission"}
            </button>
          </div>
        ` : ""}

        <!-- 3. TWO-COLUMN GRID: LEARNING PLAN ROADMAP + AI ACTIVITY MONITOR & RESULTS -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(290px, 1fr));gap:16px;">
          <!-- Generated Learning Plan Roadmap -->
          <div class="card" style="padding:16px;">
            <div class="card-title" style="margin-bottom:10px;">
              <span>🗺️ ${ms ? "PELAN PEMBELAJARAN ADAPTIF" : "GENERATED LEARNING PLAN"}</span>
              <span style="font-size:11px;color:var(--muted-text);">${planActs.length} ${ms ? "aktiviti" : "activities"}</span>
            </div>
            ${planActs.length === 0 ? `
              <p style="font-size:13px;color:var(--muted-text);">
                ${ms ? "Pelan sedang dijana oleh Ejen Perancang..." : "Plan is being generated by the Learning Plan Generator..."}
              </p>
            ` : `
              <div style="display:flex;flex-direction:column;gap:8px;max-height:320px;overflow-y:auto;">
                ${planActs.map((act, idx) => {
                  const st = String(act.status || "PENDING").toUpperCase();
                  const isDone = st === "COMPLETED";
                  const isCur = (curAct && curAct.activity_id === act.activity_id) || st === "IN_PROGRESS";
                  const badge = isDone ? "✅" : (isCur ? "▶️" : "⏳");
                  const border = isCur ? "2px solid var(--primary-orange)" : "1px solid var(--border-color)";
                  const bg = isDone ? "#f0fdf4" : (isCur ? "#fff7ed" : "#ffffff");
                  return `
                    <div style="border:${border};background:${bg};border-radius:10px;padding:10px 12px;font-size:13px;">
                      <div style="display:flex;justify-content:space-between;font-weight:800;">
                        <span>${badge} ${idx + 1}. ${act.title || act.type.toUpperCase()} (${_topicName(act.topic || topicId)})</span>
                        <span style="font-size:11px;color:var(--muted-text);">${st}</span>
                      </div>
                      ${act.question ? `<div style="font-size:12px;color:var(--muted-text);margin-top:4px;">📐 ${act.question}</div>` : ""}
                    </div>
                  `;
                }).join("")}
              </div>
            `}
          </div>

          <!-- Learning Results & Resource Budget -->
          <div class="card" style="padding:16px;">
            <div class="card-title" style="margin-bottom:10px;">
              <span>📊 ${ms ? "HASIL PEMBELAJARAN & BAJET" : "LEARNING RESULTS & BUDGET"}</span>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;font-size:13px;">
              <div style="background:var(--cream-bg);padding:10px;border-radius:8px;">
                <div style="font-size:11px;color:var(--muted-text);">${ms ? "Penguasaan Awal" : "Initial Mastery"}</div>
                <div style="font-size:18px;font-weight:900;">${initialM}%</div>
              </div>
              <div style="background:#ecfdf5;padding:10px;border-radius:8px;">
                <div style="font-size:11px;color:#047857;">${ms ? "Penguasaan Disahkan (SymPy)" : "Verified Mastery (SymPy)"}</div>
                <div style="font-size:18px;font-weight:900;color:#047857;">${verifiedM}%</div>
              </div>
              <div style="background:var(--cream-bg);padding:10px;border-radius:8px;">
                <div style="font-size:11px;color:var(--muted-text);">${ms ? "Aktiviti Selesai / Soalan" : "Completed / Answered"}</div>
                <div style="font-size:16px;font-weight:800;">
                  ${(m.completed_activities || []).length} / ${(m.learning_history || []).length}
                </div>
              </div>
              <div style="background:var(--cream-bg);padding:10px;border-radius:8px;">
                <div style="font-size:11px;color:var(--muted-text);">${ms ? "Langkah Ejen / Panggilan Alat" : "Agent Steps / Tool Calls"}</div>
                <div style="font-size:16px;font-weight:800;">
                  ${budget.steps_taken || 0}/${budget.max_steps || 30} · 🛠️ ${budget.tool_calls || 0}
                </div>
              </div>
            </div>

            <div style="font-size:12px;font-weight:800;margin-bottom:6px;">
              🔍 ${ms ? "Salah Faham Dikesan (Misconceptions):" : "Identified Misconceptions:"}
            </div>
            <div style="font-size:12px;color:var(--muted-text);margin-bottom:12px;">
              ${misconceptions.length === 0
                ? (ms ? "Tiada salah faham kritikal dikesan setakat ini." : "No critical misconceptions detected so far.")
                : misconceptions.map(mc => `<span style="display:inline-block;background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:12px;margin:2px;">⚠️ ${mc.tag || mc.description || JSON.stringify(mc)}</span>`).join("")}
            </div>

            <div style="font-size:12px;font-weight:800;margin-bottom:6px;">
              🧠 ${ms ? "Jejak Keputusan Ejen AI (Live Activity Monitor):" : "AI Activity Monitor (Live Decision Trace):"}
            </div>
            <div style="background:#0f172a;color:#e2e8f0;font-family:monospace;font-size:11px;padding:10px;border-radius:8px;max-height:150px;overflow-y:auto;">
              ${traces.length === 0
                ? "Waiting for agent trace..."
                : traces.slice(-12).map(t => `<div style="margin-bottom:4px;">&gt; ${t}</div>`).join("")}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  return {
    render,
    restoreActiveMission,
    launchMissionFromForm,
    applyPreset,
    submitChallengeResponse,
    acknowledgeTeachingStep,
    pauseCurrentMission,
    resumeCurrentMission,
    cancelCurrentMission,
    refreshCurrentMission,
    clearForNewMission,
    getCurrentMission: () => currentMission
  };
})();

if (typeof window !== "undefined") window.OyenMissionDashboard = OyenMissionDashboard;
if (typeof module !== "undefined" && module.exports) module.exports = OyenMissionDashboard;

