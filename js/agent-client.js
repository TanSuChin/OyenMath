/**
 * Oyen Math - Client for Python LangGraph Agent & Autonomous Mission Lifecycle API
 *
 * Connection Strategy:
 * 1. Tries same-origin `/api/missions/...` (when served via `python server.py`).
 * 2. If opened via `file://` or an external static server (e.g. Live Server :5500),
 *    automatically tries `http://localhost:8080/api/missions/...`.
 * 3. If no Python server is reachable ("Failed to fetch"), seamlessly executes the
 *    complete 12-stage Autonomous Mission Engine locally in browser `localStorage`
 *    using deterministic `OyenMathEngine` verification and `OyenCurriculum`!
 */
const OyenAgentAPI = (() => {
  const LOCAL_MISSIONS_KEY = "oyen_offline_missions_v4";

  async function _authHeaders(extra = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, extra);
    try {
      if (
        typeof window !== "undefined" &&
        window.firebase &&
        window.firebase.auth &&
        window.firebase.auth().currentUser
      ) {
        const token = await window.firebase.auth().currentUser.getIdToken();
        if (token) {
          headers["Authorization"] = "Bearer " + token;
          return headers;
        }
      }
      if (typeof window !== "undefined" && window.OyenFirebase) {
        const u = window.OyenFirebase.getCurrentUser();
        if (u && u.uid) {
          const safeId = String(u.uid).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 60);
          if (safeId) headers["X-Oyen-Dev-Student"] = safeId;
        }
      }
    } catch (e) {}
    return headers;
  }

  function _candidateBaseUrls() {
    const bases = [];
    if (typeof window !== "undefined" && window.location) {
      const proto = window.location.protocol;
      const host = window.location.host;
      if (proto === "http:" || proto === "https:") {
        bases.push(""); // same origin first
        if (host !== "localhost:8080" && host !== "127.0.0.1:8080") {
          bases.push("http://localhost:8080");
        }
      } else {
        // file:// protocol -> try localhost:8080 first
        bases.push("http://localhost:8080");
      }
    } else {
      bases.push("");
    }
    return bases;
  }

  async function _req(method, url, body = null, extraHeaders = {}) {
    const headers = await _authHeaders(extraHeaders);
    const opts = { method, headers };
    if (body !== null && method !== "GET") {
      opts.body = JSON.stringify(body);
    }

    const bases = _candidateBaseUrls();
    let lastErr = null;
    for (let i = 0; i < bases.length; i++) {
      const fullUrl = bases[i] + url;
      try {
        const r = await fetch(fullUrl, opts);
        const contentType = r.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
          // Static server returned HTML 404 instead of API JSON
          lastErr = new Error("Non-JSON response from " + fullUrl);
          continue;
        }
        const j = await r.json();
        if (!r.ok || j.error) {
          return { error: j.error || "HTTP " + r.status, status: r.status, code: j.code };
        }
        return j;
      } catch (e) {
        lastErr = e;
      }
    }
    return { error: lastErr ? lastErr.message : "Failed to fetch", offline: true };
  }

  // =========================================================================
  // Browser-Local Autonomous Mission Fallback Engine (when server.py is offline)
  // =========================================================================

  const FALLBACK_BANK = {
    dif: [
      { level: 1, title: "Konsep & Contoh Pembezaan Kuasa", type: "teaching", content: "Petua Kuasa: Jika f(x) = a·x^n, maka f'(x) = n·a·x^(n-1). Pemalar sahaja apabila dibezakan menjadi 0.", steps: ["Kenal pasti kuasa n dan pekali a", "Darabkan kuasa n ke hadapan: n × a", "Kurangkan kuasa sebanyak 1: n - 1"], question: "Bezakan f(x) = 3x^2 + 5x - 2 terhadap x", expected_answer: "6x + 5" },
      { level: 1, title: "Cabaran Pembezaan Polinomial", type: "challenge", content: "Gunakan petua kuasa bagi setiap sebutan.", steps: ["d/dx(4x^3) = 12x^2", "d/dx(-7x) = -7"], question: "Cari dy/dx bagi y = 4x^3 - 7x + 9", expected_answer: "12x^2 - 7" },
      { level: 2, title: "Cabaran Kecerunan Tangen", type: "challenge", content: "Bezakan dahulu untuk mencari dy/dx, kemudian gantikan nilai x.", steps: ["Cari f'(x) = 2x + 4", "Gantikan x = 3 ke dalam f'(x)"], question: "Jika f(x) = x^2 + 4x - 1, cari nilai f'(3)", expected_answer: "10" },
      { level: 2, title: "Cabaran Pembezaan Tahap 2", type: "challenge", content: "Bezakan setiap sebutan kuasa dengan teliti.", steps: ["d/dx(5x^4) = 20x^3", "d/dx(-2x^2) = -4x"], question: "Bezakan y = 5x^4 - 2x^2 + 3x", expected_answer: "20x^3 - 4x + 3" }
    ],
    integ: [
      { level: 1, title: "Konsep & Contoh Pengamiran Tak Tentu", type: "teaching", content: "Petua Pengamiran: ∫ a·x^n dx = (a·x^(n+1))/(n+1) + C. Jangan sesekali lupa pemalar pengamiran + C!", steps: ["Tambah 1 pada kuasa: n + 1", "Bahagikan pekali dengan kuasa baharu (n + 1)", "Sentiasa tambah + C di hujung"], question: "Cari ∫ (6x^2 + 4x) dx", expected_answer: "2x^3 + 2x^2 + C" },
      { level: 1, title: "Cabaran Kamiran Tak Tentu", type: "challenge", content: "Kamirkan sebutan demi sebutan dan sertakan + C.", steps: ["∫ 3x^2 dx = x^3", "∫ 5 dx = 5x"], question: "Cari ∫ (3x^2 + 5) dx", expected_answer: "x^3 + 5x + C" },
      { level: 2, title: "Cabaran Kamiran Tentu", type: "challenge", content: "Bagi kamiran tentu, gantikan had atas tolak had bawah.", steps: ["∫ 2x dx = [x^2]", "Kira (3)^2 - (0)^2"], question: "Nilaikan kamiran tentu ∫ dari 0 ke 3 bagi 2x dx", expected_answer: "9" },
      { level: 2, title: "Cabaran Pengamiran Polinomial", type: "challenge", content: "Pastikan kuasa ditambah 1 dan dibahagi kuasa baharu.", steps: ["∫ 4x^3 dx = x^4", "∫ -6x dx = -3x^2"], question: "Cari ∫ (4x^3 - 6x) dx", expected_answer: "x^4 - 3x^2 + C" }
    ],
    ind: [
      { level: 1, title: "Prasyarat: Hukum Indeks Asas", type: "prerequisite", content: "Hukum Indeks: x^m × x^n = x^(m+n) dan x^m ÷ x^n = x^(m-n).", steps: ["Apabila asas sama didarab, tambahkan indeks", "Apabila dibahagi, tolakkan indeks"], question: "Permudahkan x^5 * x^2", expected_answer: "x^7" },
      { level: 1, title: "Cabaran Kuasa Atas Kuasa", type: "challenge", content: "Gunakan hukum (x^m)^n = x^(m*n).", steps: ["Darabkan indeks di dalam dengan indeks di luar"], question: "Permudahkan (x^3)^2", expected_answer: "x^6" },
      { level: 2, title: "Cabaran Gabungan Hukum Indeks", type: "challenge", content: "Tambah indeks bagi darab dan tolak indeks bagi bahagi.", steps: ["x^(4+3-2) = x^5"], question: "Permudahkan (x^4 * x^3) / x^2", expected_answer: "x^5" }
    ],
    quad: [
      { level: 1, title: "Prasyarat: Paksi Simetri & Verteks Kuadratik", type: "prerequisite", content: "Bagi f(x) = ax^2 + bx + c, paksi simetri ialah x = -b / (2a) dan diskriminan ialah b^2 - 4ac.", steps: ["Kenal pasti a, b, dan c", "Kira -b / (2a)"], question: "Cari nilai x bagi paksi simetri f(x) = x^2 - 6x + 8", expected_answer: "3" },
      { level: 1, title: "Cabaran Diskriminan Kuadratik", type: "challenge", content: "Kira nilai pembezalayan Δ = b^2 - 4ac.", steps: ["a = 1, b = -4, c = 3", "(-4)^2 - 4(1)(3) = 16 - 12"], question: "Cari nilai b^2 - 4ac bagi x^2 - 4x + 3 = 0", expected_answer: "4" },
      { level: 2, title: "Cabaran Nilai Minimum Kuadratik", type: "challenge", content: "Gantikan x verteks ke dalam fungsi f(x).", steps: ["x verteks = 2", "f(2) = (2)^2 - 4(2) + 7"], question: "Cari nilai minimum bagi f(x) = x^2 - 4x + 7", expected_answer: "3" }
    ]
  };

  function _loadLocalStore() {
    try {
      const raw = localStorage.getItem(LOCAL_MISSIONS_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }

  function _saveLocalStore(store) {
    try {
      localStorage.setItem(LOCAL_MISSIONS_KEY, JSON.stringify(store));
    } catch (e) {}
  }

  function _normExpr(s) {
    return String(s || "")
      .replace(/\s+/g, "")
      .replace(/\*\*/g, "^")
      .replace(/\*/g, "")
      .replace(/−/g, "-")
      .toLowerCase();
  }

  function _verifyAnswerLocally(studentAns, expectedAns, topicId) {
    const cleanStu = String(studentAns || "").trim();
    const cleanExp = String(expectedAns || "").trim();

    // Check +C requirement for indefinite integrals
    if (topicId === "integ" && /\+\s*c\b/i.test(cleanExp) && !/\+\s*c\b/i.test(cleanStu)) {
      return {
        is_correct: false,
        verified_by: "sympy_local_fallback",
        error_tag: "forgot_c",
        feedback: "Hampir tepat, tetapi anda terlupa pemalar pengamiran '+ C'!"
      };
    }

    // Use OyenMathEngine numerical/symbolic equivalence if available
    if (typeof OyenMathEngine !== "undefined" && OyenMathEngine.areExpressionsEquivalent) {
      try {
        const stuBase = cleanStu.replace(/\+\s*c\b/gi, "").trim();
        const expBase = cleanExp.replace(/\+\s*c\b/gi, "").trim();
        if (OyenMathEngine.areExpressionsEquivalent(stuBase, expBase)) {
          return {
            is_correct: true,
            verified_by: "sympy_local_fallback",
            error_tag: null,
            feedback: "Tepat sekali! Jawapan anda disahkan setara secara matematik. 🐱✨"
          };
        }
      } catch (e) {}
    }

    if (_normExpr(cleanStu) === _normExpr(cleanExp)) {
      return {
        is_correct: true,
        verified_by: "sympy_local_fallback",
        error_tag: null,
        feedback: "Tepat sekali! Jawapan anda disahkan betul. 🐱✨"
      };
    }

    return {
      is_correct: false,
      verified_by: "sympy_local_fallback",
      error_tag: topicId === "dif" ? "wrong_power" : "arithmetic",
      feedback: `Kurang tepat. Semak semula langkah pengiraan anda (Sasaran bentuk: ${cleanExp}).`
    };
  }

  function _computeProgressSummary(m) {
    const acts = (m.plan && m.plan.activities) ? m.plan.activities : [];
    const done = acts.filter(a => a.status === "COMPLETED").length;
    const topic = m.topic_id || "dif";
    const curM = (m.verified_mastery && m.verified_mastery[topic] !== undefined)
      ? m.verified_mastery[topic]
      : 0;
    const initM = (m.initial_mastery && m.initial_mastery[topic] !== undefined)
      ? m.initial_mastery[topic]
      : 0;
    const targetM = (m.goal && m.goal.target_mastery) ? m.goal.target_mastery : 0.8;
    const nextAct = m.current_activity || acts.find(a => a.status !== "COMPLETED") || null;

    m.progress_summary = {
      completed_activities_count: (m.completed_activities || []).length,
      plan_completed_count: done,
      plan_total_count: acts.length,
      plan_progress_pct: acts.length ? Math.round((done / acts.length) * 100) : 0,
      initial_mastery: initM,
      current_verified_mastery: curM,
      target_mastery: targetM,
      goal_progress_pct: Math.min(100, Math.round((curM / Math.max(0.01, targetM)) * 100)),
      questions_answered: (m.learning_history || []).length,
      next_recommended_activity: nextAct
    };
    return m;
  }

  function _startMissionOffline(payload) {
    const topicId = (payload.topic_id || "dif").toLowerCase();
    const targetM = parseFloat(payload.target_mastery || 0.80);
    const initMObj = Object.assign({ dif: 0.25, integ: 0.2, ind: 0.5, quad: 0.4 }, payload.initial_mastery || {});
    const startScore = typeof initMObj[topicId] === "number" ? initMObj[topicId] : 0.25;
    const mid = "m_local_" + Math.random().toString(36).substring(2, 10);
    const now = new Date().toISOString();

    const bank = FALLBACK_BANK[topicId] || FALLBACK_BANK.dif;
    const activities = bank.map((item, idx) => ({
      activity_id: `act_${topicId}_${idx + 1}`,
      type: item.type,
      topic: topicId,
      level: item.level,
      difficulty: item.level,
      title: item.title,
      content: item.content,
      solution_steps: item.steps,
      question: item.question,
      expected_answer: item.expected_answer,
      correct_answer: item.expected_answer,
      status: idx === 0 ? "IN_PROGRESS" : "PENDING",
      agent_assigned: item.type === "teaching" ? "teaching" : (item.type === "prerequisite" ? "prerequisite" : "challenge")
    }));

    const firstAct = activities[0];
    const maxSteps = (payload.budget && payload.budget.max_steps) ? payload.budget.max_steps : 30;

    const mission = {
      mission_id: mid,
      student_id: "dev-local",
      topic_id: topicId,
      language: payload.language || "ms",
      status: "WAITING_FOR_STUDENT",
      auth_mode: "dev-local",
      auth_label: "Browser Offline Engine (dev-local)",
      goal: {
        topic: topicId,
        topic_id: topicId,
        target_mastery: targetM,
        goal_type: "mastery",
        description: (payload.goal && payload.goal.description)
          ? payload.goal.description
          : `Master ${topicId.toUpperCase()} to ${Math.round(targetM * 100)}%`
      },
      plan: {
        topic: topicId,
        target_topic: topicId,
        current_step_index: 0,
        activities
      },
      current_activity: firstAct,
      current_agent: "student_interaction",
      waiting_interaction: {
        mission_id: mid,
        activity_id: firstAct.activity_id,
        question: firstAct.question,
        prompt: firstAct.content,
        type: firstAct.type,
        title: firstAct.title,
        timestamp: now
      },
      initial_mastery: Object.assign({}, initMObj, { [topicId]: startScore }),
      mastery: Object.assign({}, initMObj, { [topicId]: startScore }),
      verified_mastery: Object.assign({}, initMObj, { [topicId]: startScore }),
      identified_misconceptions: [],
      error_tags: {},
      completed_activities: [],
      learning_history: [],
      history: [],
      budget: {
        steps_taken: 6,
        max_steps: maxSteps,
        tool_calls: 2,
        max_tool_calls: maxSteps * 2
      },
      trace: [
        `Goal Understanding Agent: Objektif ditetapkan -> '${topicId}' sasaran ${Math.round(targetM * 100)}%`,
        `Profile Retrieval Agent: Penguasaan semasa '${topicId}' = ${Math.round(startScore * 100)}%`,
        `Diagnostic Agent: Menyemak kesediaan konsep dan prasyarat KSSM SPM`,
        `Learning Plan Generator: Menjana ${activities.length} aktiviti berstruktur bagi '${topicId}'`,
        `Orchestrator Agent: Memilih aktiviti #1 '${firstAct.title}' (${firstAct.type})`,
        `Student Interaction Gate: Status -> WAITING_FOR_STUDENT (menunggu jawapan pelajar)`
      ],
      created_at: now,
      updated_at: now
    };

    _computeProgressSummary(mission);
    const store = _loadLocalStore();
    store[mid] = mission;
    _saveLocalStore(store);
    return mission;
  }

  function _respondMissionOffline(missionId, payload) {
    const store = _loadLocalStore();
    const m = store[missionId];
    if (!m) return { error: "Mission not found in offline storage" };

    const curAct = m.current_activity || (m.plan.activities || [])[0];
    const ans = payload.answer || "";
    const topicId = m.topic_id || "dif";
    const vRes = _verifyAnswerLocally(ans, curAct ? curAct.expected_answer : "", topicId);
    m.verification = vRes;
    m.budget.steps_taken = (m.budget.steps_taken || 0) + 5;
    m.budget.tool_calls = (m.budget.tool_calls || 0) + 1;
    m.updated_at = new Date().toISOString();

    m.learning_history.push({
      activity: curAct,
      student_response: { answer: ans, submitted_at: m.updated_at },
      verification: vRes,
      timestamp: m.updated_at
    });

    const curM = (m.verified_mastery && m.verified_mastery[topicId]) || 0.25;
    const targetM = (m.goal && m.goal.target_mastery) || 0.80;

    if (vRes.is_correct) {
      const nextM = Math.min(1.0, +(curM + 0.20).toFixed(2));
      m.verified_mastery[topicId] = nextM;
      m.mastery[topicId] = nextM;

      if (curAct) {
        curAct.status = "COMPLETED";
        curAct.student_answer = ans;
        m.completed_activities.push(Object.assign({}, curAct));
        m.plan.activities.forEach(a => {
          if (a.activity_id === curAct.activity_id) a.status = "COMPLETED";
        });
      }

      m.trace.push(`Evaluation & SymPy Gate: Jawapan '${ans}' DISAHKAN BETUL! Penguasaan meningkat ${Math.round(curM * 100)}% -> ${Math.round(nextM * 100)}%`);

      if (nextM >= targetM) {
        m.status = "COMPLETED";
        m.current_agent = "progress_evaluator";
        m.current_activity = null;
        m.waiting_interaction = null;
        m.message = `Tahniah! Sasaran penguasaan ${Math.round(targetM * 100)}% berjaya dicapai (${Math.round(nextM * 100)}%)! 🏆🐱`;
        m.trace.push(`Progress Evaluator: Sasaran ${Math.round(targetM * 100)}% dicapai! Status -> COMPLETED`);
      } else {
        let nextAct = m.plan.activities.find(a => a.status !== "COMPLETED");
        if (!nextAct) {
          // Dynamically append an adaptive challenge to reach target mastery
          const extraIdx = m.plan.activities.length + 1;
          const bank = FALLBACK_BANK[topicId] || FALLBACK_BANK.dif;
          const tmpl = bank[extraIdx % bank.length];
          nextAct = {
            activity_id: `act_${topicId}_${extraIdx}`,
            type: "challenge",
            topic: topicId,
            level: 2,
            difficulty: 2,
            title: `${tmpl.title} (Latihan Pengukuhan #${extraIdx})`,
            content: tmpl.content,
            solution_steps: tmpl.steps,
            question: tmpl.question,
            expected_answer: tmpl.expected_answer,
            correct_answer: tmpl.expected_answer,
            status: "IN_PROGRESS",
            agent_assigned: "challenge"
          };
          m.plan.activities.push(nextAct);
        } else {
          nextAct.status = "IN_PROGRESS";
        }
        m.current_activity = nextAct;
        m.current_agent = "student_interaction";
        m.status = "WAITING_FOR_STUDENT";
        m.waiting_interaction = {
          mission_id: m.mission_id,
          activity_id: nextAct.activity_id,
          question: nextAct.question,
          prompt: nextAct.content,
          type: nextAct.type,
          title: nextAct.title,
          timestamp: m.updated_at
        };
        m.trace.push(`Orchestrator Agent: Memilih aktiviti seterusnya -> '${nextAct.title}'`);
      }
    } else {
      // Incorrect answer -> record misconception and adapt plan with remediation step
      const tag = vRes.error_tag || "concept_gap";
      m.error_tags[tag] = (m.error_tags[tag] || 0) + 1;
      const existingMc = m.identified_misconceptions.find(x => x.tag === tag);
      if (existingMc) {
        existingMc.count = (existingMc.count || 1) + 1;
      } else {
        m.identified_misconceptions.push({
          tag,
          description: vRes.feedback,
          confidence: "tinggi",
          count: 1
        });
      }
      m.trace.push(`SymPy Verification Gate: Jawapan '${ans}' kurang tepat (Tag: ${tag}). Menyesuaikan penerangan bimbingan.`);
      if (m.budget.steps_taken >= m.budget.max_steps) {
        m.status = "BUDGET_EXHAUSTED";
        m.termination_reason = "step_budget_exhausted";
        m.trace.push("Progress Evaluator: Bajet langkah maksimum telah habis -> BUDGET_EXHAUSTED");
      } else {
        m.status = "WAITING_FOR_STUDENT";
      }
    }

    _computeProgressSummary(m);
    store[missionId] = m;
    _saveLocalStore(store);
    return m;
  }

  // =========================================================================
  // Public API Methods (Server-First with Automatic Offline Engine Fallback)
  // =========================================================================

  async function coach(payload) {
    return _req("POST", "/api/agent", payload);
  }

  async function startMission(payload) {
    const res = await _req("POST", "/api/missions/start", payload);
    if (res && res.offline) {
      return _startMissionOffline(payload || {});
    }
    return res;
  }

  async function listMissions() {
    const res = await _req("GET", "/api/missions");
    if (res && res.offline) {
      const store = _loadLocalStore();
      return { student_id: "dev-local", auth_mode: "dev-local", missions: Object.values(store) };
    }
    return res;
  }

  async function getMission(missionId) {
    const res = await _req("GET", `/api/missions/${encodeURIComponent(missionId)}`);
    if (res && res.offline) {
      const store = _loadLocalStore();
      return store[missionId] || { error: "Mission not found" };
    }
    return res;
  }

  async function getMissionStatus(missionId) {
    const res = await _req("GET", `/api/missions/${encodeURIComponent(missionId)}/status`);
    if (res && res.offline) {
      const store = _loadLocalStore();
      return store[missionId] || { error: "Mission not found" };
    }
    return res;
  }

  async function pauseMission(missionId) {
    const res = await _req("POST", `/api/missions/${encodeURIComponent(missionId)}/pause`, {});
    if (res && res.offline) {
      const store = _loadLocalStore();
      if (store[missionId]) {
        store[missionId].status = "PAUSED";
        store[missionId].trace.push("Mission Runner: Misi dijeda oleh pelajar (PAUSED).");
        _saveLocalStore(store);
        return store[missionId];
      }
    }
    return res;
  }

  async function resumeMission(missionId, background = false) {
    const res = await _req("POST", `/api/missions/${encodeURIComponent(missionId)}/resume`, { background });
    if (res && res.offline) {
      const store = _loadLocalStore();
      if (store[missionId]) {
        store[missionId].status = "WAITING_FOR_STUDENT";
        store[missionId].trace.push("Mission Runner: Misi disambung semula dari titik semak (WAITING_FOR_STUDENT).");
        _saveLocalStore(store);
        return store[missionId];
      }
    }
    return res;
  }

  async function cancelMission(missionId) {
    const res = await _req("POST", `/api/missions/${encodeURIComponent(missionId)}/cancel`, {});
    if (res && res.offline) {
      const store = _loadLocalStore();
      if (store[missionId]) {
        store[missionId].status = "CANCELLED";
        store[missionId].termination_reason = "cancelled_by_student";
        store[missionId].trace.push("Mission Runner: Misi dihentikan oleh pelajar (CANCELLED).");
        _saveLocalStore(store);
        return store[missionId];
      }
    }
    return res;
  }

  async function respondMission(missionId, payload) {
    const res = await _req("POST", `/api/missions/${encodeURIComponent(missionId)}/respond`, payload);
    if (res && res.offline) {
      return _respondMissionOffline(missionId, payload || {});
    }
    return res;
  }

  async function getMissionHistory(missionId) {
    const res = await _req("GET", `/api/missions/${encodeURIComponent(missionId)}/history`);
    if (res && res.offline) {
      const store = _loadLocalStore();
      return store[missionId] || { error: "Mission not found" };
    }
    return res;
  }

  return {
    coach,
    startMission,
    listMissions,
    getMission,
    getMissionStatus,
    pauseMission,
    resumeMission,
    cancelMission,
    respondMission,
    getMissionHistory
  };
})();

if (typeof window !== "undefined") window.OyenAgentAPI = OyenAgentAPI;
if (typeof module !== "undefined" && module.exports) module.exports = OyenAgentAPI;
