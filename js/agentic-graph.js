/**
 * Oyen Math - LangGraph Multi-Agent Orchestrator
 * Implements a stateful directed graph coordinating:
 * - Learning Orchestrator
 * - Diagnostic Agent
 * - Teaching Agent
 * - Challenge Agent
 * - Evaluation Agent
 * - Math Solver Engine
 */

class OyenAgenticGraph {
  constructor(initialState = {}) {
    this.state = {
      studentId: initialState.studentId || "guest_" + Math.random().toString(36).substring(2, 7),
      studentName: initialState.studentName || "Pelajar Oyen",
      language: initialState.language || "ms",
      currentTopicId: initialState.currentTopicId || "dif",
      currentNodeIndex: 0,
      phase: "idle", // 'idle' | 'diagnostic' | 'teaching' | 'challenge' | 'evaluation' | 'recovery' | 'detective'
      level: 1,      // 1..3
      hearts: initialState.hearts !== undefined ? initialState.hearts : 5,
      maxHearts: 5,
      normalPoints: initialState.normalPoints || 0,
      recoveryPoints: initialState.recoveryPoints || 0,
      fishCoins: initialState.fishCoins || 10,
      streak: 0,
      round: 0,
      stepInPhase: 0,
      diagnosticScores: [],
      challengeScores: [],
      errorTags: {},
      errorMessages: {},
      teachingMethodsTried: [],
      currentTeachingMethod: "worked",
      mastery: Object.assign({
        ind: 0.2,
        dif: 0.1,
        integ: 0.0,
        quad: 0.1
      }, initialState.mastery || {}),
      currentQuestion: null,
      lastAnswerFeedback: null,
      prerequisiteRecommended: null,
      traceLog: []
    };

    this.listeners = new Set();
  }

  subscribe(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  notify(event, data) {
    this.listeners.forEach(cb => {
      try { cb(event, data, this.state); } catch (e) { console.error("Listener error:", e); }
    });
  }

  logDecision(agentCode, message, details = null) {
    const agentNames = {
      O: { ms: "Orchestrator Pembelajaran", en: "Learning Orchestrator", color: "#FF8C24" },
      D: { ms: "Ejen Diagnostik", en: "Diagnostic Agent", color: "#0E7490" },
      T: { ms: "Ejen Pengajaran", en: "Teaching Agent", color: "#D97706" },
      C: { ms: "Ejen Cabaran", en: "Challenge Agent", color: "#9333EA" },
      E: { ms: "Ejen Penilaian", en: "Evaluation Agent", color: "#16A34A" },
      M: { ms: "Penyelesai Matematik", en: "Math Solver", color: "#64748B" },
      DET: { ms: "Detektif Oyen", en: "Detective Oyen", color: "#854D0E" }
    };

    const entry = {
      timestamp: new Date().toLocaleTimeString(),
      agentCode,
      agentMeta: agentNames[agentCode] || { ms: "Ejen AI", en: "AI Agent", color: "#FF8C24" },
      message,
      details
    };

    this.state.traceLog.unshift(entry);
    if (this.state.traceLog.length > 25) {
      this.state.traceLog.pop();
    }

    this.notify("log_added", entry);
  }

  /**
   * Node 1: Start a Learning Journey Session
   */
  startSession(topicId, keepHistory = false) {
    const topic = OyenCurriculum.getTopic(topicId);
    this.state.currentTopicId = topicId;
    this.state.phase = "diagnostic";
    this.state.stepInPhase = 0;
    this.state.diagnosticScores = [];
    this.state.challengeScores = [];
    this.state.errorTags = {};
    this.state.errorMessages = {};
    this.state.teachingMethodsTried = [];
    this.state.round = 0;
    this.state.prerequisiteRecommended = null;

    if (!keepHistory) {
      this.state.traceLog = [];
    }

    this.logDecision("O", `Sesi baharu dimulakan: ${topic.name}. Mengaktifkan Ejen Diagnostik untuk menilai tahap pemahaman awal.`);
    this.nextQuestion();
  }

  /**
   * Node 2: Question Generation & Dispatch
   */
  nextQuestion() {
    // Check if hearts depleted
    if (this.state.hearts <= 0 && this.state.phase !== "recovery") {
      this.triggerRecoveryMode();
      return;
    }

    const topic = OyenCurriculum.getTopic(this.state.currentTopicId);
    const questionLevel = this.state.phase === "diagnostic" 
      ? [1, 2, 3][Math.min(2, this.state.stepInPhase)]
      : this.state.level;

    const qData = topic.gen(questionLevel);
    qData.level = questionLevel;
    this.state.currentQuestion = qData;
    this.state.lastAnswerFeedback = null;

    const agent = this.state.phase === "diagnostic" ? "D" : "C";
    this.logDecision(agent, `Menjana soalan Tahap ${questionLevel} bagi ${topic.name} (${this.state.phase === "diagnostic" ? "Ujian Diagnostik" : "Misi Cabaran Oyen"}).`);
    this.notify("question_ready", qData);
  }

  /**
   * Node 3: Answer Submission & Evaluation Gate
   */
  submitAnswer(rawInput) {
    if (!this.state.currentQuestion) return;

    const q = this.state.currentQuestion;
    const result = OyenMathEngine.checkAnswer(rawInput, q);

    if (result.bad) {
      this.notify("answer_format_error", result);
      return;
    }

    this.state.lastAnswerFeedback = result;
    const isDiag = this.state.phase === "diagnostic";
    const historyList = isDiag ? this.state.diagnosticScores : this.state.challengeScores;

    historyList.push({
      ok: result.ok,
      level: q.level,
      tag: result.tag || null
    });

    if (result.tag) {
      this.state.errorTags[result.tag] = (this.state.errorTags[result.tag] || 0) + 1;
      this.state.errorMessages[result.tag] = result.msg;
    }

    this.logDecision("M", `Mengesahkan input “${rawInput}”: ${result.ok ? "TEPAT ✔" : "SALAH ✘"}${result.tag ? " (Corak ralat: " + result.tag + ")" : ""}.`);

    if (result.ok) {
      // Rewards
      const pts = q.level * 15;
      const coins = q.level * 2;
      this.state.normalPoints += pts;
      this.state.fishCoins += coins;
      this.state.streak += 1;
      this.logDecision("E", `Jawapan betul! +${pts} mata XP, +${coins} Ikan Emas. Rentetan: ${this.state.streak}.`);
    } else {
      this.state.streak = 0;
      if (this.state.phase !== "diagnostic") {
        this.state.hearts = Math.max(0, this.state.hearts - 1);
        this.logDecision("E", `Jawapan belum tepat. 1 jantung ditolak. Baki jantung: ${this.state.hearts}/5.`);
      }
    }

    // Dynamic difficulty adjustment in challenge phase
    if (this.state.phase === "challenge") {
      const prevLvl = this.state.level;
      if (result.ok) {
        this.state.level = Math.min(3, prevLvl + 1);
      } else {
        this.state.level = Math.max(1, prevLvl - 1);
      }
      if (this.state.level !== prevLvl) {
        this.logDecision("C", `Menyelaras tahap kesukaran cabaran: Tahap ${prevLvl} → Tahap ${this.state.level}.`);
      }
    }

    this.notify("answer_evaluated", {
      result,
      isCorrect: result.ok,
      hearts: this.state.hearts,
      normalPoints: this.state.normalPoints,
      fishCoins: this.state.fishCoins
    });
  }

  /**
   * Node 4: Advance step or transition phase
   */
  nextStep() {
    this.state.stepInPhase += 1;

    if (this.state.phase === "diagnostic") {
      if (this.state.stepInPhase < 3) {
        this.nextQuestion();
      } else {
        this.postDiagnosticOrchestration();
      }
    } else if (this.state.phase === "challenge") {
      if (this.state.stepInPhase < 3) {
        this.nextQuestion();
      } else {
        this.evaluateChallengeResults();
      }
    } else if (this.state.phase === "recovery") {
      // Heart recovery succeeded
      this.state.hearts = Math.min(this.state.maxHearts, this.state.hearts + 1);
      this.state.recoveryPoints += 25;
      this.logDecision("O", `Latihan pemulihan berjaya! 1 Jantung dipulihkan. Semangat Oyen melonjak!`);
      this.notify("heart_recovered", { hearts: this.state.hearts });
    }
  }

  /**
   * Node 5: Post-Diagnostic Analysis & Prerequisite Router
   */
  postDiagnosticOrchestration() {
    const totalPossible = this.state.diagnosticScores.reduce((acc, s) => acc + s.level, 0);
    const earned = this.state.diagnosticScores.reduce((acc, s) => acc + (s.ok ? s.level : 0), 0);
    const ratio = totalPossible > 0 ? earned / totalPossible : 0;
    const errorKeys = Object.keys(this.state.errorTags);

    this.logDecision("D", `Diagnosis lengkap: Skor pra-penilaian ${(ratio * 100).toFixed(0)}%. Ralat dikesan: ${errorKeys.length ? errorKeys.join(", ") : "Tiada"}.`);

    // Prerequisite intervention check:
    // If student is in Differentiation and struggled with exponent rules while Index mastery < 60%
    if (this.state.currentTopicId === "dif" && (this.state.errorTags["exp"] || this.state.errorTags["coef"]) && this.state.mastery.ind < 0.6) {
      this.state.prerequisiteRecommended = "ind";
      this.logDecision("O", "Corak ralat indeks dikesan berulang kali. Orchestrator mencadangkan campur tangan modul prasyarat Hukum Indeks.");
      this.notify("prerequisite_suggested", {
        prereqId: "ind",
        prereqName: OyenCurriculum.getTopic("ind").name,
        reason: "Ralat menunjukkan kelemahan asas dalam manipulasi kuasa dan indeks."
      });
      return;
    }

    if (ratio >= 0.85) {
      this.logDecision("O", "Prestasi diagnostik cemerlang (>85%). Pelajar melangkau fasa pengajaran asas terus ke Cabaran Peringkat Tinggi.");
      this.startChallengePhase();
      return;
    }

    this.logDecision("O", "Terdapat jurang kefahaman konsep. Mengaktifkan Ejen Pengajaran (Teaching Agent) dengan strategi bersesuaian.");
    this.startTeachingPhase();
  }

  /**
   * Node 6: Teaching Phase (Multimodal Instruction)
   */
  startTeachingPhase(forcedMethod = null) {
    this.state.phase = "teaching";
    const availableMethods = ["worked", "visual", "text", "practical"];

    let method = forcedMethod;
    if (!method) {
      method = availableMethods.find(m => !this.state.teachingMethodsTried.includes(m)) || "worked";
    }

    this.state.currentTeachingMethod = method;
    this.state.teachingMethodsTried.push(method);

    const topic = OyenCurriculum.getTopic(this.state.currentTopicId);
    let content = topic.teach[method];
    if (typeof content === "function") {
      content = content();
    }

    this.logDecision("T", `Memilih kaedah pengajaran “${method.toUpperCase()}”. Mengoptimumkan pemahaman kognitif pelajar.`);
    this.notify("teaching_ready", {
      method,
      content,
      topicName: topic.name
    });
  }

  retryTeachingWithDifferentMethod() {
    this.logDecision("O", "Pelajar masih keliru. Mengarahkan Ejen Pengajaran menukar kaedah penjelasan.");
    this.startTeachingPhase();
  }

  /**
   * Node 7: Challenge Phase
   */
  startChallengePhase() {
    this.state.phase = "challenge";
    this.state.stepInPhase = 0;
    this.state.challengeScores = [];
    this.logDecision("O", `Mengaktifkan Ejen Cabaran. Memulakan 3 pusingan misi SPM adaptif.`);
    this.nextQuestion();
  }

  /**
   * Node 8: Final Evaluation & Mastery Update
   */
  evaluateChallengeResults() {
    this.state.phase = "evaluation";
    this.state.round += 1;

    const totalPossible = this.state.challengeScores.reduce((acc, s) => acc + s.level, 0);
    const earned = this.state.challengeScores.reduce((acc, s) => acc + (s.ok ? s.level : 0), 0);
    const postRatio = totalPossible > 0 ? earned / totalPossible : 0;
    const isConsistent = this.state.challengeScores.slice(-2).every(s => s.ok);

    const topicId = this.state.currentTopicId;
    const oldMastery = this.state.mastery[topicId] || 0;
    const newMastery = +(oldMastery * 0.4 + postRatio * 0.6).toFixed(2);
    this.state.mastery[topicId] = Math.min(1.0, newMastery);

    let recommendation = "";
    if (postRatio >= 0.75 && isConsistent) {
      recommendation = "Konsep dikuasai dengan cemerlang dan konsisten! Oyen mencadangkan untuk meneruskan pengembaraan ke topik seterusnya.";
    } else if (postRatio < 0.5) {
      recommendation = "Prestasi memerlukan pengukuhan. Orchestrator mencadangkan ulang kaji dengan strategi pengajaran berbeza.";
    } else {
      recommendation = "Kemajuan baik! Sedikit lagi latihan tambahan untuk mencapai penguasaan 100%.";
    }

    this.logDecision("E", `Penilaian pusingan siap. Pra: ${(oldMastery * 100).toFixed(0)}% → Pasca: ${(postRatio * 100).toFixed(0)}%. Penguasaan baharu: ${(newMastery * 100).toFixed(0)}%.`);
    this.logDecision("O", recommendation);

    this.notify("evaluation_completed", {
      oldMastery,
      newMastery,
      postRatio,
      isConsistent,
      recommendation,
      errorMessages: this.state.errorMessages
    });
  }

  /**
   * Node 9: Heart Recovery Zone
   */
  triggerRecoveryMode() {
    this.state.phase = "recovery";
    this.state.stepInPhase = 0;
    this.logDecision("O", "Jantung habis! Mengaktifkan Zon Pemulihan Jantung Oyen.");
    
    // Pick an accessible recovery question
    const topic = OyenCurriculum.getTopic(this.state.currentTopicId);
    const qData = topic.gen(1); // Level 1 practice
    qData.isRecovery = true;
    this.state.currentQuestion = qData;

    this.notify("recovery_mode_started", {
      question: qData,
      message: OyenI18n.t("oyenQuotes.recoveryExercise")
    });
  }
}

if (typeof window !== "undefined") {
  window.OyenAgenticGraph = OyenAgenticGraph;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = OyenAgenticGraph;
}

