/**
 * Oyen Math - Answer-Sheet OCR Agent (Detective Oyen)
 * 1) Preferred: POST image to local server /api/ocr (Claude vision reads handwriting + flags errors)
 * 2) Fallback: Tesseract.js in the browser (printed text OK, handwriting is weak)
 * The extracted final answer is then verified by the deterministic Math Solver via the agent graph.
 */
const OyenOCR = (() => {
  const SUP = { "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9" };

  function toPlain(s) {
    return String(s || "")
      .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]+/g, m => "^" + [...m].map(c => SUP[c]).join(""))
      .replace(/[−–—]/g, "-").replace(/[×·]/g, "*").replace(/÷/g, "/")
      .replace(/f\s*[′'’]?\s*\(x\)\s*=|dy\s*\/\s*dx\s*=|∫|dx\s*$/gi, "")
      .replace(/^\s*(langkah|step)\s*\d+\s*[:.)]/i, "")
      .replace(/^\s*=\s*/, "").trim();
  }

  function pickFinal(lines) {
    const texts = lines.map(l => (l.text || l)).filter(t => String(t).trim());
    if (!texts.length) return "";
    const last = String(texts[texts.length - 1]);
    const afterEq = last.includes("=") ? last.split("=").pop() : last;
    return toPlain(afterEq).replace(/\s+/g, " ");
  }

  /** Grayscale + contrast stretch (2%-98% percentile) to make pencil/pen on paper clearer for OCR. */
  function enhance(g, w, h) {
    const im = g.getImageData(0, 0, w, h), d = im.data, hist = new Array(256).fill(0);
    for (let i = 0; i < d.length; i += 4) { const v = (d[i] * 0.299 + d[i + 1] * 0.587 + d[i + 2] * 0.114) | 0; d[i] = d[i + 1] = d[i + 2] = v; hist[v]++; }
    const n = w * h; let a = 0, lo = 0, hi = 255;
    for (let v = 0; v < 256; v++) { a += hist[v]; if (a >= n * 0.02) { lo = v; break; } }
    a = 0; for (let v = 255; v >= 0; v--) { a += hist[v]; if (a >= n * 0.02) { hi = v; break; } }
    const k = hi > lo + 20 ? 255 / (hi - lo) : 1;
    for (let i = 0; i < d.length; i += 4) { const v = Math.max(0, Math.min(255, (d[i] - lo) * k)); d[i] = d[i + 1] = d[i + 2] = v; }
    g.putImageData(im, 0, 0);
  }

  function downscale(file, maxW = 1400) {
    return new Promise((res, rej) => {
      const fr = new FileReader();
      fr.onerror = () => rej(new Error("Gagal membaca fail"));
      fr.onload = () => {
        const img = new Image();
        img.onerror = () => rej(new Error("Imej tidak sah"));
        img.onload = () => {
          const k = Math.min(1, maxW / img.width), c = document.createElement("canvas");
          c.width = Math.round(img.width * k); c.height = Math.round(img.height * k);
          const g = c.getContext("2d");
          g.drawImage(img, 0, 0, c.width, c.height);
          try { enhance(g, c.width, c.height); } catch (e) { /* keep original colours */ }
          res(c.toDataURL("image/jpeg", 0.9));
        };
        img.src = fr.result;
      };
      fr.readAsDataURL(file);
    });
  }

  async function viaServer(dataUrl, question) {
    const r = await fetch("/api/ocr", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ image: dataUrl, question }) });
    const j = await r.json();
    if (!r.ok || j.error) throw new Error(j.error || "server " + r.status);
    return j;
  }

  async function viaTesseract(dataUrl) {
    if (typeof Tesseract === "undefined") {
      await new Promise((ok, no) => {
        const s = document.createElement("script");
        s.src = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js";
        s.onload = ok; s.onerror = () => no(new Error("Tesseract.js tidak dapat dimuatkan (semak sambungan internet)"));
        document.head.appendChild(s);
      });
    }
    const { data } = await Tesseract.recognize(dataUrl, "eng");
    const lines = data.text.split("\n").map(t => t.trim()).filter(Boolean).map(text => ({ text, valid: null }));
    return { lines, finalAnswer: pickFinal(lines), engine: "tesseract" };
  }

  async function readDataURL(dataUrl, question = "") {
    let out, note = "";
    try { out = await viaServer(dataUrl, question); }
    catch (e) {
      note = "Pelayan OCR tidak tersedia (" + e.message + "). Menggunakan mod asas Tesseract.";
      try { out = await viaTesseract(dataUrl); }
      catch (e2) { return { lines: [], finalAnswer: "", engine: "none", error: e2.message, note }; }
    }
    out.lines = (out.lines || []).map(l => typeof l === "string" ? { text: l, valid: null } : l);
    out.finalAnswer = toPlain(out.finalAnswer || pickFinal(out.lines));
    out.note = note;
    return out;
  }

  const read = async (file, question) => readDataURL(await downscale(file), question);

  function scanningHTML(file) {
    const url = file ? URL.createObjectURL(file) : "";
    return `<div class="ocr-scan">${url ? `<img src="${url}" alt="kertas jawapan">` : '<div class="ocr-blank">📝</div>'}<div class="ocr-beam"></div>
      <div class="ocr-det">${OyenCharacter.render("detective", 84)}<span>Detektif Oyen sedang membaca tulisan kamu... 🔍</span></div></div>
      <div class="ocr-tip">💡 Tip: kertas rata, cahaya terang, tulis jelas, satu soalan setiap gambar.</div>`;
  }

  function resultHTML(r, opts = {}) {
    if (r.error) return `<div class="ocr-res bad">😿 ${r.error}<br><small>${r.note || ""}</small></div>`;
    if (!r.lines.length) return `<div class="ocr-res bad">😿 Oyen tidak dapat membaca apa-apa. Cuba gambar yang lebih jelas dan terang.</div>`;
    const rows = r.lines.map((l, i) => `<div class="ocr-line ${l.valid === false ? "err" : l.valid === true ? "good" : ""}">
      <span class="ocr-n">${i + 1}</span><div><b>${String(l.text).replace(/</g, "&lt;")}</b>${l.error ? `<div class="ocr-why">⚠️ ${l.error}</div>` : ""}</div></div>`).join("");
    const eng = r.engine === "tesseract" ? "Tesseract (asas, kurang tepat untuk tulisan tangan)" : "Claude Vision";
    const q = opts.question ? `<div class="ocr-q">📌 ${opts.question}</div>` : "";
    return `<div class="ocr-res">${q}${opts.verdict || ""}<div class="ocr-head">${OyenCharacter.render("detective", 56)}<div><b>Laporan Detektif Oyen</b><small>Enjin OCR: ${eng}</small></div></div>
      ${r.note ? `<div class="ocr-note">${r.note}</div>` : ""}${rows}
      <label class="ocr-fl">Jawapan akhir yang dibaca (boleh dibetulkan):</label>
      <input id="ocrFinal" class="math-input" value="${String(r.finalAnswer || "").replace(/"/g, "&quot;")}" />
      ${opts.submit ? `<button class="btn btn-primary" onclick="OyenApp.submitScanned()">✅ Hantar jawapan ini kepada Ejen</button>` : ""}
      <button class="btn btn-alt btn-sm" onclick="document.getElementById('${opts.retryId || "answerSheetFile"}').click()">🔄 Imbas semula</button></div>`;
  }

  return { read, readDataURL, toPlain, pickFinal, scanningHTML, resultHTML };
})();
if (typeof window !== "undefined") window.OyenOCR = OyenOCR;
if (typeof module !== "undefined" && module.exports) module.exports = OyenOCR;
