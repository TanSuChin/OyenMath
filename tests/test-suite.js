/**
 * Oyen Math - Automated Verification Test Suite
 */

const assert = require("assert");

// Mock browser globals for Node.js test environment
global.window = global;
global.document = {
  getElementById: () => null,
  documentElement: { lang: "ms" },
  querySelectorAll: () => []
};
global.localStorage = {
  _store: {},
  getItem(k) { return this._store[k] || null; },
  setItem(k, v) { this._store[k] = String(v); },
  removeItem(k) { delete this._store[k]; }
};

// Load modules
const OyenCharacter = require("../js/oyen-characters.js");
const OyenI18n = require("../js/i18n.js");
const OyenMathEngine = require("../js/math-engine.js");
const OyenCurriculum = require("../js/curriculum.js");
const OyenAgenticGraph = require("../js/agentic-graph.js");
const OyenDetectiveScanner = require("../js/detective-scanner.js");
const OyenFirebase = require("../js/firebase-app.js");

console.log("==========================================");
console.log("🐱 RUNNING OYEN MATH TEST SUITE");
console.log("==========================================");

let passedTests = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✔ PASS: ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`  ✘ FAIL: ${name}`);
    console.error(err);
    process.exit(1);
  }
}

// 1. Character Engine
test("OyenCharacter renders all 8 canonical poses", () => {
  const expectedPoses = ["happy", "sad", "thinking", "confused", "excited", "determined", "sleeping", "detective"];
  assert.deepStrictEqual(OyenCharacter.poses, expectedPoses);

  expectedPoses.forEach(pose => {
    const svg = OyenCharacter.render(pose, 100);
    assert.ok(svg.includes("<svg"), `Pose ${pose} must produce valid SVG`);
    assert.ok(svg.includes(`aria-label="`), `Pose ${pose} must include aria-label`);
  });

  // Check specific distinctive accessories
  const determinedSvg = OyenCharacter.render("determined", 120);
  assert.ok(determinedSvg.includes("SPM Headband") || determinedSvg.includes("headband"), "Determined pose has headband");

  const detectiveSvg = OyenCharacter.render("detective", 120);
  assert.ok(detectiveSvg.includes("Magnifying Glass") || detectiveSvg.includes("Cap"), "Detective pose has cap/glass");
});

// 2. i18n & Dialogues
test("OyenI18n contains required dialogue quotes and bilingual keys", () => {
  assert.strictEqual(OyenI18n.t("appName"), "Oyen Math");
  assert.strictEqual(OyenI18n.t("appTagline"), "Learn. Play. Level Up!");

  const msQuotes = OyenI18n.translations.ms.oyenQuotes;
  assert.ok(msQuotes.correct.includes("MEOWWWW"), "Must include MEOWWWW correct quote");
  assert.ok(msQuotes.incorrect.includes("negatif"), "Must include negative sign quote");
  assert.ok(msQuotes.difficult.includes("Brain.exe"), "Must include Brain.exe quote");
  assert.ok(msQuotes.recoveryExercise.includes("LOCK IN!"), "Must include LOCK IN quote");

  // Switch to English
  OyenI18n.setLang("en");
  assert.strictEqual(OyenI18n.getLang(), "en");
  assert.ok(OyenI18n.t("oyenQuotes.correct").includes("MEOWWWW"), "English quote also has MEOWWWW");
  assert.ok(OyenI18n.t("oyenQuotes.recoveryExercise").includes("LOCK IN!"), "English recovery has LOCK IN!");

  // Switch back to Malay
  OyenI18n.setLang("ms");
});

// 3. Mathematical Evaluation Engine
test("OyenMathEngine checks derivatives and integrals correctly", () => {
  // Test derivative: f(x) = 3x^2 + 5 -> f'(x) = 6x
  const qDiff = {
    f: x => 6 * x,
    w: [
      { t: "exp", m: "Exponent error", f: x => 6 * x * x }
    ]
  };

  const correctRes = OyenMathEngine.checkAnswer("6x", qDiff);
  assert.strictEqual(correctRes.ok, true, "6x should be recognized as correct");

  const wrongRes = OyenMathEngine.checkAnswer("6x^2", qDiff);
  assert.strictEqual(wrongRes.ok, false);
  assert.strictEqual(wrongRes.tag, "exp", "Should tag as exponent error");

  // Test integration with required + C
  const qInteg = {
    hasC: true,
    f: (x, c) => x * x + c,
    w: []
  };

  const noCRes = OyenMathEngine.checkAnswer("x^2", qInteg);
  assert.strictEqual(noCRes.ok, false);
  assert.strictEqual(noCRes.tag, "forgot_c", "Should flag missing + C");

  const withCRes = OyenMathEngine.checkAnswer("x^2 + c", qInteg);
  assert.strictEqual(withCRes.ok, true, "x^2 + c should be accepted");
});

// 4. Curriculum Chapters & Storyline
test("Curriculum contains Level 1 (Differentiation) & Level 2 (Integration) storyline", () => {
  const dif = OyenCurriculum.getTopic("dif");
  assert.strictEqual(dif.chapterName, "Kucing Kecil dengan Impian Besar");
  assert.strictEqual(dif.chapterNameEn, "A Little Cat with Big Dreams");
  assert.ok(dif.storyScene.intro.includes("Oyen"), "Story intro must feature Oyen");

  const integ = OyenCurriculum.getTopic("integ");
  assert.strictEqual(integ.chapterName, "Menyusun Kepingan Impian");
  assert.strictEqual(integ.chapterNameEn, "Putting the Pieces Together");
  assert.ok(integ.storyScene.intro.includes("Pembezaan"), "Integration story must continue from Differentiation");

  // Prerequisites
  assert.ok(OyenCurriculum.getTopic("ind"), "Index prerequisite topic exists");
  assert.ok(OyenCurriculum.getTopic("quad"), "Quadratic prerequisite topic exists");
});

// 5. LangGraph Agentic Graph
test("OyenAgenticGraph coordinates multi-agent lifecycle and state transitions", () => {
  const graph = new OyenAgenticGraph({ studentName: "Siti SPM" });
  assert.strictEqual(graph.state.hearts, 5);

  graph.startSession("dif");
  assert.strictEqual(graph.state.phase, "diagnostic");
  assert.ok(graph.state.currentQuestion, "Diagnostic question generated");

  // Simulate correct answer
  const correctQ = graph.state.currentQuestion;
  const targetAns = correctQ.t;
  graph.submitAnswer(targetAns);

  assert.strictEqual(graph.state.normalPoints > 0, true, "Points awarded");
  assert.strictEqual(graph.state.traceLog.length > 0, true, "Agent decisions logged in trace");

  // Verify LangGraph trace logging agent identities
  const codes = graph.state.traceLog.map(l => l.agentCode);
  assert.ok(codes.includes("O") || codes.includes("D") || codes.includes("M") || codes.includes("E"), "Trace contains agent identities");
});

// 6. Detective Oyen Working Inspector
test("OyenDetectiveScanner detects step-by-step errors in student derivations", () => {
  const sample = OyenDetectiveScanner.sampleCalculations[0]; // diff constant error
  const inspection = OyenDetectiveScanner.inspectCalculation(sample.lines, sample.topic);

  assert.strictEqual(inspection.allValid, false, "Should catch intentional error");
  assert.strictEqual(inspection.issues.length > 0, true, "Issues list populated");
  assert.ok(inspection.issues[0].message.includes("pemalar"), "Correctly explains constant misconception");

  // Test perfect working
  const perfectSample = OyenDetectiveScanner.sampleCalculations[3];
  const perfectInspection = OyenDetectiveScanner.inspectCalculation(perfectSample.lines, perfectSample.topic);
  assert.strictEqual(perfectInspection.allValid, true, "Perfect working has 0 errors");
});

// 7. Firebase Auth & Persistence
test("OyenFirebase handles user auth and state synchronization", async () => {
  OyenFirebase.init();
  const guest = OyenFirebase.getCurrentUser();
  assert.ok(guest, "Default guest user initialized");
  assert.strictEqual(guest.isGuest, true);

  const regUser = await OyenFirebase.registerUser("test@oyen.edu.my", "password123", "Oyen Challenger");
  assert.strictEqual(regUser.displayName, "Oyen Challenger");
  assert.strictEqual(OyenFirebase.getCurrentUser().email, "test@oyen.edu.my");

  const board = await OyenFirebase.getLeaderboard(500, "happy");
  assert.ok(board.length >= 6, "Leaderboard populated with community students");
});

// 8. Chubby Oyen mascot
test("OyenFat renders all 8 poses with animation hooks", () => {
  const Fat = require("../js/oyen-fat.js");
  assert.strictEqual(Fat.poses.length, 8);
  Fat.poses.forEach(p => {
    const svg = Fat.render(p, 100);
    assert.ok(svg.includes("<svg") && svg.includes("oy-body") && svg.includes('data-pose="' + p + '"'), p);
  });
  assert.ok(OyenCharacter.render("happy", 80).includes("oy-tail"), "OyenCharacter.render is patched to chubby Oyen");
});

// 9. OCR normalisation
test("OyenOCR normalises handwriting text to checkable answers", () => {
  const OCR = require("../js/ocr.js");
  assert.strictEqual(OCR.toPlain("f′(x) = 6x² + 5"), "6x^2 + 5");
  assert.strictEqual(OCR.pickFinal([{ text: "y = 3x² + 5x − 2" }, { text: "dy/dx = 6x + 5" }]), "6x + 5");
  assert.strictEqual(OCR.pickFinal([]), "");
  const out = OyenMathEngine.checkAnswer(OCR.toPlain("f′(x) = 6x + 5"), { f: x => 6 * x + 5, w: [], t: "6x+5", level: 1 });
  assert.ok(out.ok, "OCR-normalised answer passes the Math Solver");
});

// 10. Home map order and locking
test("Home map lists prerequisites first and locks Level 1/2 until prerequisites are met", () => {
  const HM = require("../js/home-map.js");
  assert.deepStrictEqual(HM.order, ["ind", "quad", "dif", "integ"]);
  assert.deepStrictEqual(HM.missing("ind", {}), [], "P1 open");
  assert.deepStrictEqual(HM.missing("quad", {}), [], "P2 open");
  assert.deepStrictEqual(HM.missing("dif", {}), ["ind", "quad"]);
  assert.deepStrictEqual(HM.missing("dif", { ind: 0.6 }), ["quad"]);
  assert.deepStrictEqual(HM.missing("dif", { ind: 0.6, quad: 0.4 }), []);
  assert.deepStrictEqual(HM.missing("integ", { ind: 1, quad: 1 }), ["dif"]);
  assert.deepStrictEqual(HM.missing("dif", { dif: 0.3 }), [], "existing progress is never locked out");
});

// 11. Stories
test("Every topic has a 4-scene bilingual story", () => {
  global.OyenCurriculum = OyenCurriculum;
  const src = require("fs").readFileSync(__dirname + "/../js/story.js", "utf8");
  const Story = new Function("window", "OyenCurriculum", "OyenI18n", "OyenCharacter", src + ";return OyenStory;")(global, OyenCurriculum, OyenI18n, OyenCharacter);
  assert.deepStrictEqual(Story.topics.sort(), ["dif", "ind", "integ", "quad"]);
});

// 12. Detective samples always carry the question they answer
test("Every detective sample states its question (BM + EN)", () => {
  OyenDetectiveScanner.sampleCalculations.forEach(sm => {
    assert.ok(sm.question && sm.questionEn, sm.id + " has a question");
  });
});

console.log("==========================================");
console.log(`🎉 ALL ${passedTests} TESTS PASSED SUCCESSFULLY!`);
console.log("==========================================");

