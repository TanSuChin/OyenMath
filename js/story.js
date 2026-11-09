/**
 * Oyen Math - Animated storyline cutscenes (SVG/CSS + typewriter captions).
 * Each topic = a short chapter of Oyen's life. Scene: sky, parallax clouds, props, falling FX, chubby Oyen.
 */
const OyenStory = (() => {
  // props: [emoji, left%, bottom%, size, anim]   fx: fish | math | star | bfly | rain
  const S = {
    ind: [
      { bg: "warm", pose: "sleeping", mv: "stay", props: [["🏚️", 6, 24, 90, "sw"], ["🕸️", 72, 44, 50, "sw"]], fx: "", c: ["Prolog: sebelum Oyen jadi hebat, dia hanya kucing kecil yang tidur atas kotak kasut. Rumah papan bocor, tapi mimpi dia besar. 💤", "Prologue: before Oyen is great, he is a small cat sleeping in a shoebox. The wooden house leaks, but his dreams are big. 💤"] },
      { bg: "warm", pose: "thinking", mv: "stay", props: [["🔒", 66, 28, 80, "fl"], ["📝", 18, 30, 56, "sw"]], fx: "", c: ["Di dapur ada peti lama berkunci dan nota ayah: 'Guna hukum indeks untuk buka'. Oyen garu kepala... 'Indeks? Bunyi macam nama makanan.'", "In the kitchen sits an old locked vault and a note from Dad: 'Use the laws of indices.' Oyen scratches his head... 'Indices? Sounds like a snack.'"] },
      { bg: "day", pose: "determined", mv: "bounce", props: [["📚", 14, 24, 70, "st"], ["🔒", 70, 28, 70, "fl"]], fx: "math", c: ["Oyen ikat tali kepala dan belajar: darab tambah indeks, bahagi tolak indeks, kuasa bagi kuasa darab indeks. 'Senang je rupanya!' 🐈", "Oyen ties on his headband and studies: multiply adds indices, divide subtracts, power of a power multiplies. 'That is easy!' 🐈"] },
      { bg: "dawn", pose: "excited", mv: "bounce", props: [["🧰", 68, 26, 80, "fl"], ["🐟", 20, 40, 44, "fl"]], fx: "fish", c: ["KLIK! Peti terbuka! Ada ikan kering dan pesanan: 'Asas yang kukuh membawa kamu jauh.' Oyen menari sampai terjatuh. 🐟", "CLICK! The vault opens! Dried fish and a note: 'Strong foundations take you far.' Oyen dances until he falls over. 🐟"] }
    ],
    quad: [
      { bg: "day", pose: "sad", mv: "stay", props: [["🏠", 62, 26, 110, "sw"], ["🌧️", 66, 66, 50, "fl"]], fx: "rain", c: ["Hujan lebat! Bumbung rumah bocor dan lantai basah. Oyen tadah air guna mangkuk sambil menggigil. 🌧️", "Heavy rain! The roof leaks and the floor is soaked. Oyen catches drips with a bowl, shivering. 🌧️"] },
      { bg: "warm", pose: "thinking", mv: "stay", props: [["📐", 66, 32, 90, "sw"], ["📈", 16, 34, 60, "fl"]], fx: "", c: ["Cikgu Amin lukis lengkung di papan hitam: 'Bumbung melengkung ialah fungsi kuadratik. Titik tertinggi ialah verteks!' Oyen: 'Verteks... bunyi macam nama ikan.'", "Cikgu Amin draws a curve on the board: 'A curved roof is a quadratic function. The highest point is the vertex!' Oyen: 'Vertex... sounds like a fish.'"] },
      { bg: "night", pose: "determined", mv: "bounce", props: [["🕯️", 18, 26, 60, "fl"], ["📚", 70, 26, 70, "st"]], fx: "math", c: ["Malam itu Oyen kira x = −b/2a sampai tertidur atas buku. 'Satu lagi soalan... zzz...' Esoknya dia kira semula, kali ini betul! ✏️", "That night Oyen computes x = −b/2a until he dozes off on the book. 'One more question... zzz...' Next day he recomputes, correct this time! ✏️"] },
      { bg: "dawn", pose: "happy", mv: "bounce", props: [["🏡", 66, 24, 110, "sw"]], fx: "star", c: ["Dengan verteks yang tepat, bumbung siap dan kering! Oyen berguling-guling di lantai. Kini dia bersedia untuk Tahap 1: Pembezaan! ☀️", "With the exact vertex the roof is done and dry! Oyen rolls on the floor. Now he is ready for Level 1: Differentiation! ☀️"] }
    ],
    dif: [
      { bg: "dawn", pose: "sad", mv: "stay", props: [["🏚️", 8, 24, 100, "sw"], ["🥣", 68, 20, 56, "st"]], fx: "", c: ["Pagi di rumah papan usang. Perut Oyen berbunyi krruuu... Mangkuk ikan kosong, tapi ekornya masih terkibas. 'Hari ini aku mesti belajar betul-betul!'", "Morning in the old wooden house. Oyen's tummy goes grrruuu... The fish bowl is empty, yet his tail still wags. 'Today I will really study!'"] },
      { bg: "day", pose: "happy", mv: "walk", props: [["🌳", 10, 24, 80, "sw"], ["🏫", 72, 24, 100, "st"]], fx: "bfly", c: ["Jalan ke sekolah, beg bertampal terlantun-lantun. Eh, rama-rama! Oyen terkejar sampai hampir terlepas loceng. 🦋", "Walking to school, his patched bag bouncing. Oh, a butterfly! Oyen chases it and nearly misses the bell. 🦋"] },
      { bg: "warm", pose: "sleeping", mv: "stay", props: [["📋", 60, 34, 110, "st"], ["👨‍🏫", 80, 24, 64, "sw"]], fx: "math", c: ["Cikgu Amin menulis dy/dx di papan hitam. Zzz... Oyen tertidur. 'Oyen! Apa itu kadar perubahan?' Oyen terjaga: 'Brain.exe has stopped working...' 💀", "Cikgu Amin writes dy/dx on the board. Zzz... Oyen is asleep. 'Oyen! What is a rate of change?' He wakes: 'Brain.exe has stopped working...' 💀"] },
      { bg: "night", pose: "determined", mv: "bounce", props: [["🌙", 74, 60, 60, "fl"], ["📚", 14, 24, 70, "st"]], fx: "star", c: ["Malam itu Oyen ikat tali kepala A+. 'Kalau aku kuasai Pembezaan, aku boleh ubah nasib keluargaku!' LOCK IN! 🐈", "That night Oyen ties on his A+ headband. 'If I master Differentiation, I can change my family's fate!' LOCK IN! 🐈"] }
    ],
    integ: [
      { bg: "day", pose: "excited", mv: "bounce", props: [["🏆", 68, 28, 80, "fl"], ["🎈", 16, 50, 50, "fl"]], fx: "star", c: ["Berkat Pembezaan, Oyen menang hadiah kuiz sekolah! Ibu menangis gembira dan adik-adik bertepuk tangan. 🏆", "Thanks to Differentiation, Oyen wins the school quiz! Mum cries happy tears and his siblings cheer. 🏆"] },
      { bg: "night", pose: "thinking", mv: "stay", props: [["📐", 66, 32, 90, "sw"], ["🕯️", 18, 26, 60, "fl"]], fx: "", c: ["Malam-malam Oyen melukis pelan rumah baharu dengan kolam ikan. Tapi berapa banyak jubin? Berapa luas kolam yang melengkung itu?", "Late at night Oyen sketches a new home with a fish pond. But how many tiles? What is the area of that curved pond?"] },
      { bg: "day", pose: "confused", mv: "stay", props: [["🐟", 20, 24, 50, "fl"], ["🐟", 40, 30, 40, "fl"], ["🐟", 70, 26, 56, "fl"]], fx: "math", c: ["Cikgu Amin senyum: 'Songsangan bagi pembezaan ialah Pengamiran. Kumpul kepingan kecil jadi jumlah besar.' Oyen: 'Macam kumpul ikan sikit-sikit?' 🐟", "Cikgu Amin smiles: 'The reverse of differentiation is Integration. Add tiny pieces into a big total.' Oyen: 'Like collecting fish bit by bit?' 🐟"] },
      { bg: "dawn", pose: "determined", mv: "bounce", props: [["🏡", 70, 24, 110, "sw"]], fx: "star", c: ["Satu ∫ demi satu ∫, rumah impian Oyen mula terbina. Cerita ini bersambung terus daripada Bab 1. Jom! 🏡", "One ∫ at a time, Oyen's dream home starts to rise. This story flows straight on from Chapter 1. Let's go! 🏡"] }
    ]
  };
  const FX = { fish: ["🐟"], math: ["∫", "x²", "dy/dx", "π", "Σ"], star: ["⭐", "✨"], bfly: ["🦋"], rain: ["💧"] };
  let timer, typer, cur;

  function stop() { clearTimeout(timer); clearInterval(typer); const o = document.getElementById("oyenStory"); if (o) o.remove(); }

  function scene(i) {
    clearTimeout(timer); clearInterval(typer);
    const sc = cur.scenes[i], lang = OyenI18n.getLang() === "en" ? 1 : 0, ov = document.getElementById("oyenStory");
    const fx = (FX[sc.fx] || []).length ? Array.from({ length: 14 }, (_, k) => `<span class="st-fx st-${sc.fx}" style="left:${(k * 7 + 3) % 96}%;animation-delay:${(k * .37).toFixed(2)}s;animation-duration:${4 + k % 4}s">${FX[sc.fx][k % FX[sc.fx].length]}</span>`).join("") : "";
    ov.innerHTML = `<div class="st-stage st-${sc.bg}">
      <div class="st-cloud" style="top:10%"></div><div class="st-cloud c2" style="top:24%"></div>
      ${sc.props.map(p => `<span class="st-prop ${p[4]}" style="left:${p[1]}%;bottom:${p[2]}%;font-size:${p[3]}px">${p[0]}</span>`).join("")}
      ${fx}<div class="st-ground"></div><div class="st-oyen mv-${sc.mv}">${OyenCharacter.render(sc.pose, 150)}</div></div>
      <div class="st-cap"><div class="st-name">🐱 Oyen · ${cur.title}</div><p id="stTxt"></p>
      <div class="st-ctl"><span>${cur.scenes.map((_, k) => `<i class="${k === i ? "on" : ""}"></i>`).join("")}</span>
      <button class="btn btn-alt btn-sm" id="stSkip">${lang ? "Skip" : "Langkau"}</button><button class="btn btn-primary btn-sm" id="stNext">${i === cur.scenes.length - 1 ? (lang ? "Start! 🐾" : "Mula! 🐾") : (lang ? "Next ▶" : "Seterusnya ▶")}</button></div></div>`;
    const txt = sc.c[lang]; let n = 0; const el = document.getElementById("stTxt");
    const next = () => { if (i + 1 < cur.scenes.length) scene(i + 1); else finish(); };
    const done = () => { clearInterval(typer); el.textContent = txt; n = txt.length; timer = setTimeout(next, 3500); };
    typer = setInterval(() => { el.textContent = txt.slice(0, ++n); if (n >= txt.length) done(); }, 26);
    document.getElementById("stNext").onclick = () => (n < txt.length ? done() : next());
    document.getElementById("stSkip").onclick = () => finish();
  }
  function finish() { const cb = cur.cb; stop(); if (cb) cb(); }

  function play(topicId, cb) {
    const sc = S[topicId]; if (!sc) { if (cb) cb(); return; }
    stop();
    const t = OyenCurriculum.getTopic(topicId), lang = OyenI18n.getLang() === "en";
    cur = { scenes: sc, cb, title: lang ? t.chapterNameEn : t.chapterName };
    const ov = document.createElement("div"); ov.id = "oyenStory"; ov.className = "story-ov"; document.body.appendChild(ov);
    scene(0);
  }
  const seen = id => { try { return JSON.parse(localStorage.getItem("oyen_story_seen") || "{}")[id]; } catch (e) { return false; } };
  const mark = id => { try { const o = JSON.parse(localStorage.getItem("oyen_story_seen") || "{}"); o[id] = 1; localStorage.setItem("oyen_story_seen", JSON.stringify(o)); } catch (e) {} };
  return { play, seen, mark, topics: Object.keys(S) };
})();
if (typeof window !== "undefined") window.OyenStory = OyenStory;
