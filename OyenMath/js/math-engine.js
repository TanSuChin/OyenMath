/**
 * Oyen Math - Mathematical Evaluation Engine
 * Numerical and symbolic validator for SPM Additional Mathematics
 * Supports:
 * - Differentiation (Power Rule, Chain Rule, Tangents)
 * - Integration (Indefinite Integrals with +C, Definite Integrals, Shaded Areas)
 * - Diagnostic error pattern matching (exponent drop, sign errors, +C omission)
 * - SVG dynamic curve, tangent, and area plotting
 */

const OyenMathEngine = (() => {
  const pw = Math.pow;

  /**
   * Evaluates student mathematical expression string for given x and optional c
   */
  function evaluateExpr(rawStr, xVal = 1, cVal = 0) {
    if (!rawStr || typeof rawStr !== "string") return NaN;

    let s = rawStr.toLowerCase().trim();
    // Convert HTML superscripts and unicode exponents
    s = s.replace(/<sup>(.*?)<\/sup>/gi, "^($1)")
         .replace(/²/g, "^2")
         .replace(/³/g, "^3")
         .replace(/⁴/g, "^4");

    // Normalize symbols
    s = s.replace(/\s+/g, "")
         .replace(/−/g, "-")
         .replace(/[×·]/g, "*")
         .replace(/÷/g, "/");

    // Replace constant of integration 'c' with the numerical cVal if present
    s = s.replace(/(^|[+\-*\/])c(?=[+\-*\/]|$)/g, `$1(${cVal})`);

    // Verify allowed characters
    if (!/^[0-9x+\-*\/^().]+$/.test(s)) {
      if (/^-?\d+(\.\d+)?(\/\d+(\.\d+)?)?$/.test(s)) {
        try {
          return Function("return " + s)();
        } catch (e) {
          return NaN;
        }
      }
      return NaN;
    }

    // Convert power ^ to **
    s = s.replace(/\^/g, "**");

    // Add implicit multiplications: 3x -> 3*x, (x+1)(x-2) -> (x+1)*(x-2), 2(x) -> 2*(x)
    s = s.replace(/(\d|\))(?=[x(])/g, "$1*");
    s = s.replace(/(x)(?=\d)/g, "$1*");

    // Convert pow calls for reliable JS evaluation
    s = s.replace(/(x|\d+\.?\d*|\([^()]*\))\*\*(-?\d+\.?\d*|\([^()]*\))/g, "pow($1,$2)");

    try {
      const res = Function("x", "pow", "return " + s)(xVal, pw);
      return typeof res === "number" && !isNaN(res) && isFinite(res) ? res : NaN;
    } catch (e) {
      return NaN;
    }
  }

  /**
   * Compares student input against target function and known misconception functions
   * @param {string} inputStr - Student answer string
   * @param {object} questionDef - { f: fn(x,c), w: [{t, m, f: fn(x,c)}], hasC: bool }
   */
  function checkAnswer(inputStr, questionDef) {
    if (!inputStr || !inputStr.trim()) {
      return { ok: false, bad: true, msg: "Sila masukkan jawapan anda. / Please enter your answer." };
    }

    const cleaned = inputStr.trim().toLowerCase();

    // Special check for integration requiring '+ C'
    if (questionDef.hasC) {
      if (!cleaned.includes("+c") && !cleaned.includes("+ c")) {
        return {
          ok: false,
          tag: "forgot_c",
          msg: "ALAMAK! Anda terlupa pemalar pengamiran <b>+ C</b>! Dalam kamiran tak tentu, pemalar + C adalah wajib! 🐱"
        };
      }
    }

    // Test vector of varied real values (including positive, negative, and fraction)
    const testPoints = [
      { x: 1, c: 2 },
      { x: 2, c: -1 },
      { x: -1, c: 3 },
      { x: 0.5, c: 0 },
      { x: 3, c: 1.5 }
    ];

    const studentVals = testPoints.map(p => evaluateExpr(cleaned, p.x, p.c));

    // If input couldn't be parsed
    if (studentVals.some(v => isNaN(v))) {
      return {
        ok: false,
        bad: true,
        msg: "Format jawapan tidak dapat dibaca. Gunakan format seperti <b>6x^2 + 5</b> atau <b>3/2</b> atau <b>2x^3 + c</b>."
      };
    }

    // Check equality against correct target function f
    const matchesTarget = (fn) => {
      return testPoints.every((p, idx) => {
        const expected = typeof fn === "function" ? fn(p.x, p.c) : fn;
        return Math.abs(expected - studentVals[idx]) < 1e-5;
      });
    };

    if (matchesTarget(questionDef.f)) {
      return { ok: true };
    }

    // Check against known misconception distractor patterns (w)
    if (Array.isArray(questionDef.w)) {
      for (const distractor of questionDef.w) {
        if (matchesTarget(distractor.f)) {
          return {
            ok: false,
            tag: distractor.t,
            msg: distractor.m
          };
        }
      }
    }

    return {
      ok: false,
      tag: "general_error",
      msg: "Jawapan belum tepat. Cuba semak semula pengiraan anda!"
    };
  }

  /**
   * Helper to format a polynomial term: c * x^p
   */
  function term(coeff, power, plain = false) {
    if (coeff === 0) return "";
    const abs = Math.abs(coeff);
    const coeffStr = (abs === 1 && power > 0) ? "" : abs;
    let varStr = "";
    if (power === 1) {
      varStr = "x";
    } else if (power > 1) {
      varStr = plain ? `x^${power}` : `x<sup>${power}</sup>`;
    }
    return (coeff < 0 ? " − " : " + ") + coeffStr + varStr;
  }

  /**
   * Helper to format full polynomial array: [[coeff, power], ...]
   */
  function poly(terms, plain = false) {
    const formatted = terms.map(([c, p]) => term(c, p, plain)).join("");
    return formatted.replace(/^ \+ /, "").replace(/^ − /, "−");
  }

  /**
   * Dynamic SVG Graph Plotter for Differentiation & Integration visual explanations
   */
  function plotCurve(config) {
    const {
      fn,               // mathematical function y = fn(x)
      xMin = -2,
      xMax = 4,
      yMin = -4,
      yMax = 12,
      width = 360,
      height = 220,
      tangentAt = null, // x-value for tangent line
      tangentSlope = null,
      integralFrom = null, // [a, b] for shaded area
      integralTo = null,
      title = ""
    } = config;

    const toX = (x) => ((x - xMin) / (xMax - xMin)) * width;
    const toY = (y) => height - ((y - yMin) / (yMax - yMin)) * height;

    // Generate curve path
    const steps = 90;
    let pathD = "";
    for (let i = 0; i <= steps; i++) {
      const x = xMin + ((xMax - xMin) * i) / steps;
      let y = fn(x);
      // Clamp for rendering sanity
      y = Math.max(yMin - 5, Math.min(yMax + 5, y));
      const px = toX(x).toFixed(1);
      const py = toY(y).toFixed(1);
      pathD += (i === 0 ? "M" : "L") + `${px} ${py} `;
    }

    // Optional Shaded Area for Integration
    let shadedAreaSvg = "";
    if (integralFrom !== null && integralTo !== null) {
      const a = Math.max(xMin, integralFrom);
      const b = Math.min(xMax, integralTo);
      const areaSteps = 50;
      let areaD = `M ${toX(a)} ${toY(0)} `;
      for (let i = 0; i <= areaSteps; i++) {
        const x = a + ((b - a) * i) / areaSteps;
        const y = fn(x);
        areaD += `L ${toX(x).toFixed(1)} ${toY(y).toFixed(1)} `;
      }
      areaD += `L ${toX(b)} ${toY(0)} Z`;
      shadedAreaSvg = `
        <path d="${areaD}" fill="#FF8C24" fill-opacity="0.3" stroke="#F06A16" stroke-width="1.5" stroke-dasharray="3"/>
        <line x1="${toX(a)}" y1="${toY(0)}" x2="${toX(a)}" y2="${toY(fn(a))}" stroke="#D85B10" stroke-width="1.5" stroke-dasharray="2"/>
        <line x1="${toX(b)}" y1="${toY(0)}" x2="${toX(b)}" y2="${toY(fn(b))}" stroke="#D85B10" stroke-width="1.5" stroke-dasharray="2"/>
        <text x="${toX((a + b) / 2)}" y="${toY(Math.max(0.5, fn((a + b) / 2) / 2))}" fill="#D85B10" font-size="12" font-weight="bold" text-anchor="middle">Luas / Area</text>
      `;
    }

    // Optional Tangent Line for Differentiation
    let tangentSvg = "";
    if (tangentAt !== null && tangentSlope !== null) {
      const x0 = tangentAt;
      const y0 = fn(x0);
      const dx = 1.2;
      const x1 = x0 - dx;
      const y1 = y0 - dx * tangentSlope;
      const x2 = x0 + dx;
      const y2 = y0 + dx * tangentSlope;
      tangentSvg = `
        <!-- Tangent Line -->
        <line x1="${toX(x1)}" y1="${toY(y1)}" x2="${toX(x2)}" y2="${toY(y2)}" stroke="#E11D48" stroke-width="2.5"/>
        <!-- Contact Point -->
        <circle cx="${toX(x0)}" cy="${toY(y0)}" r="5" fill="#E11D48" stroke="#FFFFFF" stroke-width="2"/>
        <!-- Tangent Slope Badge -->
        <rect x="${toX(x0) + 10}" y="${toY(y0) - 24}" width="80" height="20" rx="4" fill="#E11D48"/>
        <text x="${toX(x0) + 50}" y="${toY(y0) - 10}" fill="#FFFFFF" font-size="11" font-weight="bold" text-anchor="middle">m = ${tangentSlope}</text>
      `;
    }

    return `
      <div class="oyen-plot-wrapper" style="margin:12px 0;text-align:center;">
        ${title ? `<div style="font-size:12px;font-weight:600;color:#6b7280;margin-bottom:4px;">${title}</div>` : ""}
        <svg viewBox="0 0 ${width} ${height}" style="width:100%;max-width:${width}px;background:#FFF9F2;border:1px solid #FFE4CC;border-radius:12px;box-shadow:0 2px 8px rgba(255,140,36,0.08);">
          <!-- Coordinate Axes -->
          <line x1="0" y1="${toY(0)}" x2="${width}" y2="${toY(0)}" stroke="#94A3B8" stroke-width="1.5"/>
          <line x1="${toX(0)}" y1="0" x2="${toX(0)}" y2="${height}" stroke="#94A3B8" stroke-width="1.5"/>
          
          <!-- Axis Labels -->
          <text x="${width - 15}" y="${toY(0) - 6}" fill="#64748B" font-size="11" font-weight="bold">x</text>
          <text x="${toX(0) + 8}" y="15" fill="#64748B" font-size="11" font-weight="bold">y</text>
          
          ${shadedAreaSvg}
          
          <!-- The Curve -->
          <path d="${pathD}" fill="none" stroke="#FF8C24" stroke-width="3" stroke-linecap="round"/>
          
          ${tangentSvg}
        </svg>
      </div>
    `;
  }

  return {
    evaluateExpr,
    checkAnswer,
    term,
    poly,
    plotCurve
  };
})();

if (typeof window !== "undefined") {
  window.OyenMathEngine = OyenMathEngine;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = OyenMathEngine;
}
