/**
 * Oyen Math - Internationalization (i18n) Engine
 * Full bilingual support (Bahasa Melayu / English) for Malaysian SPM students.
 */

const OyenI18n = (() => {
  let currentLang = "ms"; // Default to Bahasa Melayu for SPM

  const translations = {
    ms: {
      appName: "Oyen Math",
      appTagline: "Learn. Play. Level Up!",
      appSubtitle: "Platform Pembelajaran Gamifikasi AI Ejen untuk Matematik Tambahan SPM",
      systemTitle: "Oyen Math – Platform Pembelajaran Diperkasa Ejen AI SPM",
      
      // Navigation
      navAdventure: "Peta Pengembaraan",
      navPractice: "Zon Latihan",
      navDetective: "Penyiasat Oyen (Jalan Kerja)",
      navRecovery: "Zon Pemulihan Jantung",
      navLeaderboard: "Papan Pendahulu",
      navAchievements: "Pencapaian",
      navBrain: "Otak Ejen AI",
      navLogin: "Log Masuk",
      navLogout: "Log Keluar",
      navGuest: "Mod Tetamu",

      // Gamification Stats
      heartsLabel: "Jantung",
      pointsLabel: "Mata Normal",
      recoveryPointsLabel: "Mata Pemulihan",
      fishCoinsLabel: "Ikan Emas",
      levelLabel: "Tahap",
      masteryLabel: "Penguasaan",

      // Character & Dialogue Quotes
      oyenQuotes: {
        correct: "MEOWWWW! Jawapan tepat! Oyen bangga dengan kamu! 🐱",
        incorrect: "Kejap... tanda negatif tu sesat dari mana? Oyen risau ni. 💀",
        difficult: "Brain.exe Oyen telah berhenti berfungsi. Bagi Oyen seminit...",
        lowHearts: "ALAMAK! Oyen dah kehabisan tenaga! Jom kita buat latihan pemulihan bersama-sama!",
        levelCompleted: "KITA BERJAYA! Oyen kini selangkah lebih dekat dengan impian besarnya!",
        recoveryExercise: "Satu lagi jawapan betul dan Oyen dapat semula jantungnya. LOCK IN! 🐈",
        welcomeBack: "Meow! Selamat kembali kawan! Jom kita takluk AddMath hari ini!",
        detectiveScanning: "Siasatan bermula... Oyen sedang meneliti setiap baris tulisan tangan kamu dengan cermat!",
        chainRuleTip: "Ingat Petua Rantai: bezakan bahagian luar dahulu, kemudian darab dengan bezakan bahagian dalam!"
      },

      // Agent Roles
      agentRoles: {
        orchestrator: "Orchestrator Pembelajaran",
        diagnostic: "Ejen Diagnostik",
        teaching: "Ejen Pengajaran",
        challenge: "Ejen Cabaran",
        evaluation: "Ejen Penilaian",
        solver: "Alat: Penyelesai Matematik"
      },

      // Agent Dialogue Prefixes
      agentDesc: {
        orchestrator: "Menyelaras laluan pembelajaran adaptif & campur tangan Oyen.",
        diagnostic: "Mengenal pasti salah faham konsep & jurang prasyarat.",
        teaching: "Menyampaikan pengajaran multimodal (teks, langkah, graf, analogi).",
        challenge: "Menghasilkan misi cabaran mengikut tahap penguasaan.",
        evaluation: "Menyemak jawapan & meneliti langkah jalan kerja pelajar.",
        solver: "Mengesahkan ungkapan beraljabar & kalkulus secara berangka."
      },

      // Chapters & Curriculum
      chapters: {
        level1Title: "Tahap 1: Pembezaan",
        level1Subtitle: "Bab: Kucing Kecil dengan Impian Besar",
        level1Desc: "Oyen memulakan persekolahan di sebuah sekolah kampung. Dia ingin membantu keluarganya keluar daripada kesusahan hidup. Di sekolah, dia bertemu topik Pembezaan dan belajar memahami kadar perubahan, kecerunan, serta nilai maksimum dan minimum.",
        
        level2Title: "Tahap 2: Pengamiran",
        level2Subtitle: "Bab: Menyusun Kepingan Impian",
        level2Desc: "Setelah menguasai Pembezaan, Oyen semakin yakin! Dia ingin merancang pembinaan tempat perlindungan kucing yang selesa dengan kolam ikan, tetapi perlu mengira jumlah luas terkumpul dan kuantiti berkait. Dia menemui Pengamiran!",

        prereqIndexTitle: "Prasyarat: Hukum Indeks",
        prereqIndexDesc: "Asas penting sebelum membezakan kuasa negatif dan pecahan.",
        prereqQuadTitle: "Prasyarat: Fungsi Kuadratik",
        prereqQuadDesc: "Memahami verteks dan bentuk parabola graf."
      },

      // Modes & Actions
      btnStart: "Mula Belajar",
      btnCheck: "Semak Jawapan",
      btnNext: "Seterusnya",
      btnUnderstood: "Saya Faham → Ke Cabaran",
      btnStillConfused: "Masih keliru, cuba kaedah lain",
      btnRetry: "Cuba Lagi",
      btnLockIn: "LOCK IN! 🐈",
      btnAcceptPrereq: "Terima Cadangan Prasyarat",
      btnSkipPrereq: "Teruskan Topik Semasa",
      btnBackMap: "Kembali ke Peta",
      btnUploadWork: "Muat Naik Gambar Jalan Kerja",
      btnClearCanvas: "Padam Kanvas",
      btnAnalyzeWork: "Siasat Jalan Kerja dengan Detektif Oyen",

      // Teaching Methods
      teachMethods: {
        text: "Penerangan Konsep & Tip SPM",
        worked: "Contoh Langkah Demi Langkah",
        visual: "Visual Interaktif & Plot Graf",
        practical: "Analogi Kucing & Kehidupan Harian"
      },

      // Detective Scanner
      detectiveTitle: "Penyiasat Oyen: Imbasan Jalan Kerja",
      detectiveSubtitle: "Muat naik atau tulis langkah kerja anda. Detektif Oyen akan mengesan baris yang mengandungi kesilapan!",
      detectiveNoMistake: "Bagus sekali! Semua baris jalan kerja anda tepat dan konsisten!",
      detectiveMistakeFound: "Detektif Oyen menemui kesilapan pada baris:",

      // Auth & User Profile
      authModalTitle: "Selamat Datang ke Oyen Math!",
      authSubtitle: "Daftar akaun untuk menyimpan kemajuan, jantung, dan ikan emas anda di awan.",
      lblEmail: "E-mel",
      lblPassword: "Kata Laluan",
      lblName: "Nama Pelajar / Panggilan",
      btnLoginAction: "Log Masuk",
      btnRegisterAction: "Daftar Akaun Baharu",
      btnGuestAction: "Teruskan Sebagai Tetamu (Simpan Tempatan)",
      authGuestNote: "Kemajuan tetamu disimpan dalam pelayar ini."
    },

    en: {
      appName: "Oyen Math",
      appTagline: "Learn. Play. Level Up!",
      appSubtitle: "Agentic AI-Powered Gamified Learning Platform for SPM Additional Mathematics",
      systemTitle: "Oyen Math – Agentic AI Learning Platform for SPM Additional Math",

      // Navigation
      navAdventure: "Adventure Map",
      navPractice: "Practice Zone",
      navDetective: "Detective Oyen (Working)",
      navRecovery: "Heart Recovery Zone",
      navLeaderboard: "Leaderboard",
      navAchievements: "Achievements",
      navBrain: "AI Agent Brain",
      navLogin: "Sign In",
      navLogout: "Sign Out",
      navGuest: "Guest Mode",

      // Gamification Stats
      heartsLabel: "Hearts",
      pointsLabel: "Normal Points",
      recoveryPointsLabel: "Recovery Points",
      fishCoinsLabel: "Fish Coins",
      levelLabel: "Level",
      masteryLabel: "Mastery",

      // Character & Dialogue Quotes
      oyenQuotes: {
        correct: "MEOWWWW! You got it right! Oyen is proud of you! 🐱",
        incorrect: "Wait... where did that negative sign come from? Oyen is concerned. 💀",
        difficult: "Brain.exe has stopped working. Give Oyen a second...",
        lowHearts: "OH NOOO! Oyen is running out of energy! Let's do some extra practice together!",
        levelCompleted: "WE DID IT! Oyen is officially one step closer to his dream!",
        recoveryExercise: "One more correct answer and Oyen gets his heart back. LOCK IN! 🐈",
        welcomeBack: "Meow! Welcome back, friend! Let's conquer AddMath today!",
        detectiveScanning: "Investigation in progress... Detective Oyen is closely examining every line of your handwritten working!",
        chainRuleTip: "Remember the Chain Rule: differentiate the outer bracket first, then multiply by the derivative of the inside!"
      },

      // Agent Roles
      agentRoles: {
        orchestrator: "Learning Orchestrator",
        diagnostic: "Diagnostic Agent",
        teaching: "Teaching Agent",
        challenge: "Challenge Agent",
        evaluation: "Evaluation Agent",
        solver: "Tool: Math Solver"
      },

      // Agent Dialogue Prefixes
      agentDesc: {
        orchestrator: "Coordinates adaptive learning routes and Oyen's interventions.",
        diagnostic: "Identifies conceptual misconceptions and prerequisite gaps.",
        teaching: "Delivers multimodal instruction (text, worked examples, graphs, analogies).",
        challenge: "Generates mission challenges tailored to student mastery level.",
        evaluation: "Validates numerical answers and diagnoses handwritten steps.",
        solver: "Verifies algebraic and calculus expressions numerically."
      },

      // Chapters & Curriculum
      chapters: {
        level1Title: "Level 1: Differentiation",
        level1Subtitle: "Chapter: A Little Cat with Big Dreams",
        level1Desc: "Oyen is a young orange cat growing up in a humble, financially struggling family. He dreams of making life better for his family. At school, he encounters Differentiation and learns to understand rates of change, gradients, and maximum/minimum values.",
        
        level2Title: "Level 2: Integration",
        level2Subtitle: "Chapter: Putting the Pieces Together",
        level2Desc: "After mastering Differentiation, Oyen grows confident! He plans to design a cozy dream shelter with a salmon pond, but must calculate accumulated totals, curves, and areas. He discovers Integration — reversing the derivative!",

        prereqIndexTitle: "Prerequisite: Laws of Indices",
        prereqIndexDesc: "Crucial foundation for differentiating fractional and negative powers.",
        prereqQuadTitle: "Prerequisite: Quadratic Functions",
        prereqQuadDesc: "Understanding vertex points and parabolic curves."
      },

      // Modes & Actions
      btnStart: "Start Learning",
      btnCheck: "Check Answer",
      btnNext: "Next",
      btnUnderstood: "I Understand → Go to Challenge",
      btnStillConfused: "Still confused, try another method",
      btnRetry: "Try Again",
      btnLockIn: "LOCK IN! 🐈",
      btnAcceptPrereq: "Accept Prerequisite Recommendation",
      btnSkipPrereq: "Continue Current Topic",
      btnBackMap: "Back to Map",
      btnUploadWork: "Upload Working Photo",
      btnClearCanvas: "Clear Canvas",
      btnAnalyzeWork: "Investigate with Detective Oyen",

      // Teaching Methods
      teachMethods: {
        text: "Concept Explanation & SPM Tips",
        worked: "Step-by-Step Worked Example",
        visual: "Interactive Visual & Graph Plotter",
        practical: "Cat & Real-Life Analogy"
      },

      // Detective Scanner
      detectiveTitle: "Detective Oyen: Working Step Inspector",
      detectiveSubtitle: "Upload or write your handwritten solution steps. Detective Oyen will pinpoint the exact line where an error occurred!",
      detectiveNoMistake: "Outstanding! All lines of your working are mathematically sound and correct!",
      detectiveMistakeFound: "Detective Oyen detected an issue on line:",

      // Auth & User Profile
      authModalTitle: "Welcome to Oyen Math!",
      authSubtitle: "Sign in or register to sync your learning journey, hearts, and fish coins to the cloud.",
      lblEmail: "Email",
      lblPassword: "Password",
      lblName: "Student Name / Nickname",
      btnLoginAction: "Sign In",
      btnRegisterAction: "Create New Account",
      btnGuestAction: "Continue as Guest (Local Storage)",
      authGuestNote: "Guest progress is saved locally in this browser."
    }
  };

  const getLang = () => currentLang;

  const setLang = (lang) => {
    if (translations[lang]) {
      currentLang = lang;
      document.documentElement.lang = lang;
      if (typeof window !== "undefined" && window.dispatchEvent) {
        window.dispatchEvent(new CustomEvent("oyen_language_changed", { detail: { lang } }));
      }
    }
  };

  const t = (key) => {
    const keys = key.split(".");
    let val = translations[currentLang];
    for (const k of keys) {
      if (val && typeof val === "object" && k in val) {
        val = val[k];
      } else {
        // Fallback to ms or key
        return key;
      }
    }
    return val;
  };

  return {
    getLang,
    setLang,
    t,
    translations
  };
})();

if (typeof window !== "undefined") {
  window.OyenI18n = OyenI18n;
  window.t = OyenI18n.t;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = OyenI18n;
}

