/**
 * Oyen Math - Chubby Oyen (v2 mascot). A round, fat, cute orange tabby.
 * Overrides OyenCharacter.render so every screen uses the same character.
 */
const OyenFat = (() => {
  const K = "#30251F", O = "#FF8C24", D = "#D9580B", CR = "#FFF0DF", PK = "#FF7A93";
  const S = `stroke="${K}" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"`;
  const eyes = (dx = 0, dy = 0) => `<g class="oy-blink"><ellipse cx="81" cy="92" rx="10" ry="12" fill="${K}"/><ellipse cx="119" cy="92" rx="10" ry="12" fill="${K}"/><circle cx="${84 + dx}" cy="${87 + dy}" r="4.2" fill="#fff"/><circle cx="${122 + dx}" cy="${87 + dy}" r="4.2" fill="#fff"/><circle cx="${78 + dx}" cy="${96 + dy}" r="2" fill="#fff"/><circle cx="${116 + dx}" cy="${96 + dy}" r="2" fill="#fff"/></g>`;
  const arm = (x, r) => `<ellipse cx="${x}" cy="140" rx="12" ry="18" fill="${O}" stroke="${D}" stroke-width="2" transform="rotate(${r} ${x} 140)"/>`;
  const mouth = {
    smile: `<path d="M88 114q12 12 24 0" ${S}/>`,
    open: `<path d="M87 112q13 26 26 0z" fill="#B3321B" stroke="${K}" stroke-width="3" stroke-linejoin="round"/><ellipse cx="100" cy="120" rx="6" ry="4" fill="${PK}"/>`,
    frown: `<path d="M90 120q10-10 20 0" ${S}/>`,
    flat: `<path d="M92 116h16" ${S}/>`,
    wavy: `<path d="M88 116q6-7 12 0t12 0" ${S}/>`,
    grin: `<path d="M86 112q14 16 28 0z" fill="#fff" stroke="${K}" stroke-width="3" stroke-linejoin="round"/>`,
    tiny: `<path d="M94 114q6 5 12 0" ${S}/>`
  };
  const P = {
    happy:   { e: `<path d="M70 92q11-15 22 0M108 92q11-15 22 0" ${S}/>`, m: "smile", a: [-38, 38], x: `<text x="22" y="46" font-size="22" class="oy-twinkle">✨</text><text x="158" y="56" font-size="18" class="oy-twinkle">✨</text>` },
    excited: { e: eyes(), m: "open", a: [-55, 55], x: `<text x="24" y="44" font-size="22" class="oy-twinkle">⭐</text><text x="160" y="40" font-size="22" class="oy-twinkle">🎉</text><text x="150" y="186" font-size="26">🐟</text>`, c: "oy-jump" },
    sad:     { e: eyes(0, 2) + `<path d="M66 72l24 8M134 72l-24 8" ${S}/><ellipse cx="68" cy="112" rx="3.5" ry="6" fill="#5BC0EB"/>`, m: "frown", a: [8, -8], x: "" },
    thinking:{ e: eyes(2, -4), m: "flat", a: [8, -35], x: `<text x="140" y="40" font-size="26">💭</text><text x="147" y="31" font-size="9" fill="${K}" font-weight="700">dy/dx</text>` },
    confused:{ e: `<g class="oy-blink"><circle cx="81" cy="92" r="11" fill="#fff" stroke="${K}" stroke-width="3"/><circle cx="119" cy="92" r="11" fill="#fff" stroke="${K}" stroke-width="3"/><path d="M81 92m-5 0a5 5 0 1 1 5 5M119 92m-5 0a5 5 0 1 1 5 5" ${S}/></g>`, m: "wavy", a: [8, -8], x: `<text x="146" y="52" font-size="22" class="oy-twinkle">❓</text><text x="150" y="86" font-size="18">💧</text>` },
    determined:{ e: eyes() + `<path d="M64 76l26 8M136 76l-26 8" ${S}/>`, m: "grin", a: [-30, 30], x: `<path d="M44 66q56-30 112 0" stroke="#E53935" stroke-width="10" fill="none" stroke-linecap="round"/><circle cx="100" cy="47" r="10" fill="#fff"/><text x="93" y="52" font-size="12">🐾</text><path d="M152 66l24 10M150 72l22 20" stroke="#E53935" stroke-width="6" stroke-linecap="round"/>` },
    sleeping:{ e: `<path d="M70 92q11 10 22 0M108 92q11 10 22 0" ${S}/>`, m: "tiny", a: [8, -8], x: `<text x="150" y="50" font-size="20" fill="${K}" class="oy-z">Z</text><text x="164" y="34" font-size="15" fill="${K}" class="oy-z" style="animation-delay:.6s">z</text>`, c: "oy-sleepy" },
    detective:{ e: eyes(-2, 0), m: "flat", a: [8, -10], x: `<path d="M48 64q52-46 104 0z" fill="#8B5E3C" stroke="#5E3B1F" stroke-width="3"/><path d="M44 66q56 8 112 0" stroke="#5E3B1F" stroke-width="6" fill="none" stroke-linecap="round"/><circle cx="100" cy="30" r="5" fill="#5E3B1F"/><circle cx="148" cy="128" r="17" fill="#d8efff" fill-opacity=".55" stroke="#6b4a2b" stroke-width="5"/><path d="M160 141l22 26" stroke="#6b4a2b" stroke-width="8" stroke-linecap="round"/>` }
  };
  const svg = (p) => {
    const d = P[p];
    return `<svg viewBox="0 0 200 200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Oyen ${p}">
<g class="oy-tail"><path d="M150 152q44-8 32-50q-4-14-16-5" stroke="${O}" stroke-width="20" fill="none" stroke-linecap="round"/><path d="M172 124l10 4M176 108l10 2" stroke="${D}" stroke-width="5" stroke-linecap="round"/></g>
<g class="oy-body"><ellipse cx="100" cy="142" rx="66" ry="50" fill="${O}"/><ellipse cx="100" cy="152" rx="42" ry="34" fill="${CR}"/>
<path d="M40 128q10 4 17 0M44 148q10 4 17 0M160 128q-10 4-17 0M156 148q-10 4-17 0" stroke="${D}" stroke-width="5" stroke-linecap="round" fill="none"/>
<ellipse cx="68" cy="188" rx="19" ry="11" fill="${CR}" stroke="${D}" stroke-width="2"/><ellipse cx="132" cy="188" rx="19" ry="11" fill="${CR}" stroke="${D}" stroke-width="2"/>
${arm(48, d.a[0])}${arm(152, d.a[1])}
<polygon points="46,62 52,14 88,44" fill="${O}"/><polygon points="154,62 148,14 112,44" fill="${O}"/><polygon points="56,52 58,28 76,44" fill="${PK}" opacity=".7"/><polygon points="144,52 142,28 124,44" fill="${PK}" opacity=".7"/>
<ellipse cx="100" cy="88" rx="60" ry="50" fill="${O}"/><circle cx="45" cy="106" r="15" fill="${O}"/><circle cx="155" cy="106" r="15" fill="${O}"/>
<path d="M100 40v14M85 42l3 13M115 42l-3 13M42 92l10 3M158 92l-10 3" stroke="${D}" stroke-width="5" stroke-linecap="round"/>
<ellipse cx="100" cy="108" rx="25" ry="16" fill="${CR}"/><ellipse cx="62" cy="108" rx="9" ry="6" fill="${PK}" opacity=".5"/><ellipse cx="138" cy="108" rx="9" ry="6" fill="${PK}" opacity=".5"/>
<ellipse cx="100" cy="100" rx="6.5" ry="4.5" fill="${PK}"/>${mouth[d.m]}
<path d="M54 106l-24-5M54 113l-24 5M146 106l24-5M146 113l24 5" stroke="${K}" stroke-width="2" opacity=".45" stroke-linecap="round"/>
${d.e}${d.x}</g></svg>`;
  };
  const render = (pose = "happy", size = 120, options = {}) => {
    const p = P[pose] ? pose : "happy";
    const st = typeof size === "number" ? `${size}px` : size;
    const cls = ["oyen-avatar", "oyen-" + p, P[p].c || "", options.className || ""].join(" ").trim();
    return `<div class="${cls}" style="display:inline-block;width:${st};height:${st};${options.extraStyles || ""}" data-pose="${p}">${svg(p)}</div>`;
  };
  return { render, poses: Object.keys(P) };
})();

if (typeof OyenCharacter !== "undefined") {
  OyenCharacter.render = OyenFat.render;
  OyenCharacter.setPose = (el, pose = "happy", size = null) => {
    el = typeof el === "string" ? document.getElementById(el) : el;
    if (!el) return;
    el.innerHTML = OyenFat.render(pose, size || 120);
    el.dataset.currentPose = pose;
  };
}
if (typeof window !== "undefined") window.OyenFat = OyenFat;
if (typeof module !== "undefined" && module.exports) module.exports = OyenFat;
