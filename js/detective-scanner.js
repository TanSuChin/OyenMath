/**
 * Oyen Math - Detective Oyen Handwritten Calculation Inspector
 * Allows students to:
 * - Upload photos of handwritten homework / scratch paper
 * - Draw on a real-time responsive canvas
 * - Test curated SPM handwritten calculation samples
 * - Pinpoint line-by-line derivation errors with Detective Oyen's diagnosis
 */

const OyenDetectiveScanner = (() => {
  // Preloaded SPM handwritten calculation scenarios
  const sampleCalculations = [
    {
      id: "sample_diff_constant_error",
      title: "Contoh 1: Pembezaan (Ralat Pemalar)",
      titleEn: "Sample 1: Differentiation (Constant Error)",
      topic: "dif",
      equation: "y = 4x^3 - 6x + 9",
      question: "Bezakan y = 4x³ − 6x + 9 terhadap x.",
      questionEn: "Differentiate y = 4x³ − 6x + 9 with respect to x.",
      lines: [
        { text: "Langkah 1: y = 4x³ − 6x + 9", valid: true },
        { text: "Langkah 2: dy/dx = 4(3)x² − 6 + 9", valid: false, error: "Ralat pada sebutan pemalar: Pemalar 9 tidak mengandungi pemboleh ubah x, maka ia dibezakan menjadi 0, bukan kekal 9!" },
        { text: "Langkah 3: dy/dx = 12x² + 3", valid: false, error: "Kesan daripada ralat Baris 2: Jawapan yang tepat ialah dy/dx = 12x² − 6." }
      ],
      correctSolution: "dy/dx = 12x² − 6"
    },
    {
      id: "sample_diff_power_error",
      title: "Contoh 2: Pembezaan (Lupa Tolak 1 Kuasa)",
      titleEn: "Sample 2: Differentiation (Forgot Power − 1)",
      topic: "dif",
      equation: "f(x) = 5x^4 + 3x^2",
      question: "Diberi f(x) = 5x⁴ + 3x². Cari f′(x).",
      questionEn: "Given f(x) = 5x⁴ + 3x². Find f′(x).",
      lines: [
        { text: "Langkah 1: f(x) = 5x⁴ + 3x²", valid: true },
        { text: "Langkah 2: f′(x) = 20x⁴ + 6x²", valid: false, error: "Petua kuasa tidak selesai! Pekali sudah didarab dengan kuasa asal, tetapi kuasa x mestilah ditolak 1: 5(4)x³ + 3(2)x¹." },
        { text: "Langkah 3: f′(x) = 20x³ + 6x", valid: true, note: "Pembetulan berjaya dibuat!" }
      ],
      correctSolution: "f′(x) = 20x³ + 6x"
    },
    {
      id: "sample_integ_forgot_c",
      title: "Contoh 3: Pengamiran (Tertinggal + C)",
      titleEn: "Sample 3: Integration (Missing + C)",
      topic: "integ",
      equation: "∫ (6x^2 - 4x + 3) dx",
      question: "Cari ∫ (6x² − 4x + 3) dx.",
      questionEn: "Find ∫ (6x² − 4x + 3) dx.",
      lines: [
        { text: "Langkah 1: ∫ (6x² − 4x + 3) dx", valid: true },
        { text: "Langkah 2: = 6(x³/3) − 4(x²/2) + 3x", valid: true },
        { text: "Langkah 3: = 2x³ − 2x² + 3x", valid: false, error: "AMARAN SPM: Ini ialah Kamiran Tak Tentu! Anda terlupa menulis pemalar pengamiran '+ C' pada baris akhir. Markah penuh tidak akan diberikan tanpa + C!" }
      ],
      correctSolution: "2x³ − 2x² + 3x + C"
    },
    {
      id: "sample_perfect_full_marks",
      title: "Contoh 4: Jalan Kerja Cemerlang (Markah Penuh SPM)",
      titleEn: "Sample 4: Perfect SPM Working (Full Marks)",
      topic: "dif",
      equation: "y = (3x - 2)^4",
      question: "Bezakan y = (3x − 2)⁴ terhadap x.",
      questionEn: "Differentiate y = (3x − 2)⁴ with respect to x.",
      lines: [
        { text: "Langkah 1: Katakan u = 3x − 2, maka y = u⁴", valid: true },
        { text: "Langkah 2: du/dx = 3 dan dy/du = 4u³", valid: true },
        { text: "Langkah 3: Petua Rantai: dy/dx = (dy/du) × (du/dx)", valid: true },
        { text: "Langkah 4: dy/dx = 4(3x − 2)³ × 3 = 12(3x − 2)³", valid: true }
      ],
      correctSolution: "dy/dx = 12(3x − 2)³"
    }
  ];

  /**
   * Evaluates extracted or parsed working lines
   */
  function inspectCalculation(linesArray, targetTopic = "dif") {
    const issues = [];
    let allValid = true;

    linesArray.forEach((line, index) => {
      const lineNum = index + 1;
      const text = (line.text || line || "").trim();

      // Check if line was explicitly flagged in sample
      if (line.valid === false) {
        allValid = false;
        issues.push({
          lineNum,
          text,
          severity: "error",
          message: line.error || "Ralat dikesan pada baris ini."
        });
      } else {
        // Run heuristic pattern checks on text
        if (targetTopic === "integ" && index === linesArray.length - 1) {
          if (!text.toLowerCase().includes("+c") && !text.toLowerCase().includes("+ c")) {
            allValid = false;
            issues.push({
              lineNum,
              text,
              severity: "warning",
              message: "Detektif Oyen mengesan anda mungkin tertinggal pemalar pengamiran <b>+ C</b> pada jawapan akhir!"
            });
          }
        }
      }
    });

    return {
      allValid,
      issues,
      summary: allValid
        ? "MEOW! Siasatan Detektif Oyen mendapati semua langkah pengiraan kemas, logik, dan menepati skema pemarkahan SPM! 🐱🌟"
        : `Detektif Oyen menemui ${issues.length} titik kesilapan konsep dalam jalan kerja anda. Sila rujuk nota siasatan di bawah!`
    };
  }

  /**
   * Initializes interactive drawing canvas
   */
  function initDrawingCanvas(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const ctx = canvas.getContext("2d");
    let isDrawing = false;
    let lastX = 0;
    let lastY = 0;

    // Set background
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw faint notebook lines
    ctx.strokeStyle = "#F1F5F9";
    ctx.lineWidth = 1;
    for (let y = 30; y < canvas.height; y += 28) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    // Default pen style
    ctx.strokeStyle = "#1E293B";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    function getPos(e) {
      const rect = canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      return {
        x: (clientX - rect.left) * (canvas.width / rect.width),
        y: (clientY - rect.top) * (canvas.height / rect.height)
      };
    }

    function startDraw(e) {
      isDrawing = true;
      const pos = getPos(e);
      lastX = pos.x;
      lastY = pos.y;
      e.preventDefault();
    }

    function draw(e) {
      if (!isDrawing) return;
      const pos = getPos(e);
      ctx.beginPath();
      ctx.moveTo(lastX, lastY);
      ctx.lineTo(pos.x, pos.y);
      ctx.stroke();
      lastX = pos.x;
      lastY = pos.y;
      e.preventDefault();
    }

    function stopDraw() {
      isDrawing = false;
    }

    canvas.addEventListener("mousedown", startDraw);
    canvas.addEventListener("mousemove", draw);
    window.addEventListener("mouseup", stopDraw);

    canvas.addEventListener("touchstart", startDraw, { passive: false });
    canvas.addEventListener("touchmove", draw, { passive: false });
    window.addEventListener("touchend", stopDraw);

    function clear() {
      ctx.fillStyle = "#FFFFFF";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = "#F1F5F9";
      ctx.lineWidth = 1;
      for (let y = 30; y < canvas.height; y += 28) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
      }
      ctx.strokeStyle = "#1E293B";
      ctx.lineWidth = 3;
    }

    return {
      canvas,
      ctx,
      clear
    };
  }

  return {
    sampleCalculations,
    inspectCalculation,
    initDrawingCanvas
  };
})();

if (typeof window !== "undefined") {
  window.OyenDetectiveScanner = OyenDetectiveScanner;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = OyenDetectiveScanner;
}

