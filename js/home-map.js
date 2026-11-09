/**
 * Oyen Math - Home: a zig-zag column of topic circles. Tap one and its sub-topic circles pop out below.
 */
const OyenHomeMap = (() => {
  const T = [
    { id: "dif", ic: "📈", sub: [["Petua Kuasa", "Power Rule"], ["Polinomial", "Polynomials"], ["Kecerunan Tangen", "Tangent Slope"]] },
    { id: "integ", ic: "🧩", lock: ["dif", 0.4], sub: [["Kamiran ax", "Integral ax"], ["Pemalar + C", "Constant + C"], ["Kamiran Tentu", "Definite Area"]] },
    { id: "ind", ic: "🧱", sub: [["Darab Indeks", "Multiply Indices"], ["Kuasa bagi Kuasa", "Power of Power"], ["Bahagi Indeks", "Divide Indices"]] },
    { id: "quad", ic: "🏠", sub: [["Paksi Simetri", "Axis of Symmetry"], ["Nilai Min / Maks", "Min / Max Value"], ["Diskriminan", "Discriminant"]] }
  ];
  let open = null, root = null, ctx = null;

  function render(container, c) {
    root = container; ctx = c;
    const en = c.lang === "en", m = c.mastery || {};
    const rows = T.map((t, i) => {
      const top = OyenCurriculum.getTopic(t.id), pct = Math.round((m[t.id] || 0) * 100);
      const locked = t.lock && (m[t.lock[0]] || 0) < t.lock[1];
      const side = ["l", "r", "l", "r"][i % 4];
      const subs = open === t.id ? `<div class="hm-subs">
        <button class="hm-sub story" style="animation-delay:0s" onclick="OyenHomeMap.story('${t.id}')"><span>🎬</span><small>${en ? "Story" : "Kisah"}</small></button>
        ${t.sub.map((s, k) => `<button class="hm-sub ${(m[t.id] || 0) >= k / 3 + 0.01 ? "done" : ""}" style="animation-delay:${(k + 1) * .12}s" onclick="OyenHomeMap.go('${t.id}',${k + 1})"><span>${k + 1}</span><small>${s[en ? 1 : 0]}</small></button>`).join("")}</div>` : "";
      return `<div class="hm-row ${side}"><button class="hm-circle ${locked ? "locked" : ""} ${open === t.id ? "open" : ""} ${i === 0 && !open ? "pulse" : ""}" style="--m:${pct}" onclick="OyenHomeMap.toggle('${t.id}')">
          <span class="hm-in"><span class="hm-ic">${locked ? "🔒" : t.ic}</span><span class="hm-n">${i + 1}</span></span></button>
        <div class="hm-lab"><b>${en ? top.nameEn : top.name}</b><small>🐾 ${en ? top.chapterNameEn : top.chapterName}</small><small>${pct}%</small></div></div>${subs}
        ${i < T.length - 1 ? '<div class="hm-trail">🐾<i>🐾</i><b>🐾</b></div>' : ""}`;
    }).join("");
    container.innerHTML = `<div class="hm"><div class="hm-hero">${OyenCharacter.render("happy", 120)}<div class="hm-bub"><b>${en ? "Meow! Tap circle 1 to begin!" : "Meow! Ketuk bulatan 1 untuk mula!"}</b><small>Learn. Play. Level Up!</small></div></div>
      <div class="hm-col">${rows}</div><div id="hmToast" class="hm-toast"></div></div>`;
  }
  const toggle = id => {
    const t = T.find(x => x.id === id), m = ctx.mastery || {};
    if (t.lock && (m[t.lock[0]] || 0) < t.lock[1]) {
      const en = ctx.lang === "en", el = document.getElementById("hmToast");
      el.textContent = en ? "🔒 Oyen says: finish Differentiation first!" : "🔒 Oyen kata: habiskan Pembezaan dahulu!";
      el.classList.remove("show"); void el.offsetWidth; el.classList.add("show"); return;
    }
    open = open === id ? null : id; render(root, ctx);
  };
  const go = (id, lvl) => OyenStory.seen(id) ? ctx.start(id, lvl) : OyenStory.play(id, () => { OyenStory.mark(id); ctx.start(id, lvl); });
  const story = id => OyenStory.play(id, () => OyenStory.mark(id));
  return { render, toggle, go, story };
})();
if (typeof window !== "undefined") window.OyenHomeMap = OyenHomeMap;
