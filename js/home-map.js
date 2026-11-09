/**
 * Oyen Math - Home: a zig-zag column of topic circles. Tap one and its sub-topic circles pop out below.
 */
const OyenHomeMap = (() => {
  // Order matters: prerequisites FIRST, then Level 1 and Level 2 (matches the learning path).
  const T = [
    { id: "ind", ic: "🧱", tag: "P1", sec: ["🧱 Prasyarat · mula di sini", "🧱 Prerequisites · start here"], sub: [["Darab Indeks", "Multiply Indices"], ["Kuasa bagi Kuasa", "Power of Power"], ["Bahagi Indeks", "Divide Indices"]] },
    { id: "quad", ic: "🏠", tag: "P2", sub: [["Paksi Simetri", "Axis of Symmetry"], ["Nilai Min / Maks", "Min / Max Value"], ["Diskriminan", "Discriminant"]] },
    { id: "dif", ic: "📈", tag: "1", sec: ["🎯 Pengembaraan Utama · Tahap 1", "🎯 Main Adventure · Level 1"], sub: [["Petua Kuasa", "Power Rule"], ["Polinomial", "Polynomials"], ["Kecerunan Tangen", "Tangent Slope"]] },
    { id: "integ", ic: "🧩", tag: "2", sec: ["🎯 Tahap 2 · sambungan cerita", "🎯 Level 2 · story continues"], sub: [["Kamiran ax", "Integral ax"], ["Pemalar + C", "Constant + C"], ["Kamiran Tentu", "Definite Area"]] }
  ];
  const NEED = 0.4;
  const RULES = { dif: ["ind", "quad"], integ: ["dif"] };
  const NAMES = { ind: ["Indeks", "Indices"], quad: ["Fungsi Kuadratik", "Quadratic Functions"], dif: ["Pembezaan", "Differentiation"], integ: ["Pengamiran", "Integration"] };
  /** Topics that must still reach NEED mastery before `id` opens. Students who already have progress in `id` are never locked out. */
  const missing = (id, m) => ((m[id] || 0) > 0 ? [] : (RULES[id] || []).filter(k => (m[k] || 0) < NEED));
  let open = null, root = null, ctx = null;

  function render(container, c) {
    root = container; ctx = c;
    const en = c.lang === "en", m = c.mastery || {};
    const rows = T.map((t, i) => {
      const top = OyenCurriculum.getTopic(t.id), pct = Math.round((m[t.id] || 0) * 100);
      const miss = missing(t.id, m), locked = miss.length > 0;
      const need = locked ? `<small class="hm-need">🔒 ${en ? "Reach" : "Capai"} ${NEED * 100}% ${en ? "in" : "dalam"}: ${miss.map(k => NAMES[k][en ? 1 : 0]).join(", ")}</small>` : "";
      const side = ["l", "r", "l", "r"][i % 4];
      const subs = open === t.id ? `<div class="hm-subs">
        <button class="hm-sub story" style="animation-delay:0s" onclick="OyenHomeMap.story('${t.id}')"><span>🎬</span><small>${en ? "Story" : "Kisah"}</small></button>
        ${t.sub.map((s, k) => `<button class="hm-sub ${(m[t.id] || 0) >= k / 3 + 0.01 ? "done" : ""}" style="animation-delay:${(k + 1) * .12}s" onclick="OyenHomeMap.go('${t.id}',${k + 1})"><span>${k + 1}</span><small>${s[en ? 1 : 0]}</small></button>`).join("")}</div>` : "";
      return `${t.sec ? `<div class="hm-sec">${t.sec[en ? 1 : 0]}</div>` : ""}<div class="hm-row ${side}"><button class="hm-circle ${locked ? "locked" : ""} ${open === t.id ? "open" : ""} ${i === 0 && !open ? "pulse" : ""}" style="--m:${pct}" onclick="OyenHomeMap.toggle('${t.id}')">
          <span class="hm-in"><span class="hm-ic">${locked ? "🔒" : t.ic}</span><span class="hm-n">${t.tag}</span></span></button>
        <div class="hm-lab"><b>${en ? top.nameEn : top.name}</b><small>🐾 ${en ? top.chapterNameEn : top.chapterName}</small><small>${pct}%</small>${need}</div></div>${subs}
        ${i < T.length - 1 ? '<div class="hm-trail">🐾<i>🐾</i><b>🐾</b></div>' : ""}`;
    }).join("");
    container.innerHTML = `<div class="hm"><div class="hm-hero">${OyenCharacter.render("happy", 120)}<div class="hm-bub"><b>${en ? "Meow! Start with circle P1!" : "Meow! Mula dengan bulatan P1!"}</b><small>Learn. Play. Level Up!</small></div></div>
      <div class="hm-col">${rows}</div><div id="hmToast" class="hm-toast"></div></div>`;
  }
  const toggle = id => {
    const t = T.find(x => x.id === id), m = ctx.mastery || {}, miss = missing(id, m);
    if (miss.length) {
      const en = ctx.lang === "en", el = document.getElementById("hmToast"), names = miss.map(k => NAMES[k][en ? 1 : 0]).join(", ");
      el.textContent = en ? `🔒 Oyen says: reach ${NEED * 100}% in ${names} first!` : `🔒 Oyen kata: capai ${NEED * 100}% dalam ${names} dahulu!`;
      el.classList.remove("show"); void el.offsetWidth; el.classList.add("show"); return;
    }
    open = open === id ? null : id; render(root, ctx);
  };
  const go = (id, lvl) => OyenStory.seen(id) ? ctx.start(id, lvl) : OyenStory.play(id, () => { OyenStory.mark(id); ctx.start(id, lvl); });
  const story = id => OyenStory.play(id, () => OyenStory.mark(id));
  return { render, toggle, go, story, T, missing, RULES };
})();
if (typeof window !== "undefined") window.OyenHomeMap = OyenHomeMap;
if (typeof module !== "undefined" && module.exports) module.exports = { OyenHomeMap, order: OyenHomeMap.T.map(t => t.id), missing: OyenHomeMap.missing, RULES: OyenHomeMap.RULES };
