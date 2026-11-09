/**
 * Oyen Math - Curriculum & Storyline Engine
 * 
 * Chapter 1 (Level 1): "A Little Cat with Big Dreams" (Differentiation)
 * Chapter 2 (Level 2): "Putting the Pieces Together" (Integration - Direct continuation)
 * Prerequisites: Indices (Indeks) & Quadratic Functions (Fungsi Kuadratik)
 */

const OyenCurriculum = (() => {
  const R = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
  const pw = Math.pow;
  const poly = OyenMathEngine.poly;

  const topics = {
    // ==========================================
    // PREREQUISITE: INDICES
    // ==========================================
    ind: {
      id: "ind",
      name: "Hukum Indeks (Prasyarat)",
      nameEn: "Laws of Indices (Prerequisite)",
      tag: "Asas Penting Pembezaan",
      tagEn: "Essential Calculus Prerequisite",
      chapterName: "Peti Rahsia Dapur Oyen",
      chapterNameEn: "Oyen's Kitchen Vault",
      mission: "🔐 Misi Peti Makanan: Oyen terjumpa peti makanan lama yang dikunci dengan kod indeks! Tolong Oyen buka kod sebelum perutnya berbunyi lapar!",
      missionEn: "🔐 Kitchen Vault Mission: Oyen found an old pantry vault locked with an index code! Help Oyen crack the code before his tummy rumbles!",
      storyScene: {
        intro: "Di rumah papan usang keluarganya, Oyen cuba mencari makanan lebih untuk ibu dan adik-adiknya. Di sudut dapur, ada satu peti simpanan terkunci yang ditinggalkan ayahnya dengan nota: 'Gunakan hukum indeks untuk membukanya'.",
        introEn: "In his family's humble wooden home, Oyen looks for extra food for his mother and siblings. In the pantry corner stands an old locked vault with a note: 'Use the laws of indices to open it'."
      },
      gen(level) {
        let a = R(3, 6);
        let b = R(2, 5);
        if (level === 1) {
          return {
            q: `Diberi x<sup>${a}</sup> × x<sup>${b}</sup> = x<sup>m</sup>. Cari nilai m.`,
            qEn: `Given x<sup>${a}</sup> × x<sup>${b}</sup> = x<sup>m</sup>. Find m.`,
            f: () => a + b,
            t: `${a + b}`,
            w: [
              { t: "mul", m: "Anda mendarab indeks. Apabila mendarab asas yang sama, indeks mestilah <b>DITAMBAH</b> (a + b).", f: () => a * b }
            ]
          };
        }
        if (level === 2) {
          return {
            q: `Diberi (x<sup>${a}</sup>)<sup>${b}</sup> = x<sup>m</sup>. Cari nilai m.`,
            qEn: `Given (x<sup>${a}</sup>)<sup>${b}</sup> = x<sup>m</sup>. Find m.`,
            f: () => a * b,
            t: `${a * b}`,
            w: [
              { t: "add", m: "Bagi kuasa bagi kuasa (x<sup>a</sup>)<sup>b</sup>, indeks mestilah <b>DIDARAB</b> (a × b), bukan ditambah.", f: () => a + b }
            ]
          };
        }
        a = R(6, 9);
        b = R(2, 4);
        return {
          q: `Diberi x<sup>${a}</sup> ÷ x<sup>${b}</sup> = x<sup>m</sup>. Cari nilai m.`,
          qEn: `Given x<sup>${a}</sup> ÷ x<sup>${b}</sup> = x<sup>m</sup>. Find m.`,
          f: () => a - b,
          t: `${a - b}`,
          w: [
            { t: "div", m: "Apabila membahagi asas sama, indeks mestilah <b>DITOLAK</b> (a − b), bukan dibahagi.", f: () => a / b }
          ]
        };
      },
      teach: {
        text: `
          <h4>Hukum Asas Indeks (Dual Language)</h4>
          <p>Apabila asas algebra adalah sama:</p>
          <ul>
            <li><b>Pendaraban:</b> x<sup>a</sup> × x<sup>b</sup> = x<sup>a + b</sup> (Indeks ditambah)</li>
            <li><b>Pembahagian:</b> x<sup>a</sup> ÷ x<sup>b</sup> = x<sup>a − b</sup> (Indeks ditolak)</li>
            <li><b>Kuasa bagi kuasa:</b> (x<sup>a</sup>)<sup>b</sup> = x<sup>a × b</sup> (Indeks didarab)</li>
            <li><b>Kuasa negatif:</b> x<sup>−n</sup> = 1 / x<sup>n</sup> (Penting bila membezakan sebutan pecahan!)</li>
          </ul>
        `,
        worked: `
          <h4>Contoh Langkah Demi Langkah</h4>
          <p><b>Contoh 1:</b> Permudahkan x<sup>4</sup> × x<sup>3</sup></p>
          <p>Penyelesaian: 4 + 3 = <b>7</b> → Jawapan: x<sup>7</sup></p>
          <p><b>Contoh 2:</b> Permudahkan (x<sup>3</sup>)<sup>4</sup></p>
          <p>Penyelesaian: 3 × 4 = <b>12</b> → Jawapan: x<sup>12</sup></p>
          <p><b>Contoh 3:</b> Permudahkan x<sup>7</sup> ÷ x<sup>2</sup></p>
          <p>Penyelesaian: 7 − 2 = <b>5</b> → Jawapan: x<sup>5</sup></p>
        `,
        visual: () => `
          <h4>Visualisasi Blok Ikan Oyen</h4>
          <p>x<sup>3</sup> = <b>x · x · x</b> (3 ekor ikan) dan x<sup>2</sup> = <b>x · x</b> (2 ekor ikan).</p>
          <p>Bila digabungkan bersama: (x·x·x) × (x·x) = <b>x·x·x·x·x = x<sup>5</sup></b>.</p>
          <p>Indeks mewakili <i>bilangan faktor pendaraban</i>, maka kita hanya menjumlahkan bilangannya!</p>
        `,
        practical: `
          <h4>Analogi Makanan Kucing</h4>
          <p>Bayangkan Oyen ada 3 tin makanan setiap hari selama 4 minggu berturut-turut. Jumlahnya ialah (3)<sup>4</sup> kumpulan berulang = 3 × 4 = 12 blok makanan. Jangan sesekali tambah jika ada tanda kurungan bertingkat!</p>
        `
      }
    },

    // ==========================================
    // LEVEL 1: DIFFERENTIATION
    // "A Little Cat with Big Dreams"
    // ==========================================
    dif: {
      id: "dif",
      name: "Tahap 1: Pembezaan (Differentiation)",
      nameEn: "Level 1: Differentiation",
      tag: "Bab 2 Tingkatan 5 SPM",
      tagEn: "Form 5 SPM Chapter 2",
      chapterName: "Kucing Kecil dengan Impian Besar",
      chapterNameEn: "A Little Cat with Big Dreams",
      storyScene: {
        intro: "Oyen duduk di meja belakang kelas 5 Sains 1. Walaupun beg sekolahnya bertampal dan kasutnya lusuh, matanya bersinar mendengar Cikgu Amin mengajar Pembezaan di papan hitam. Cikgu kata: 'Pembezaan ialah ilmu tentang kadar perubahan — bagaimana langkah kecil hari ini mengubah masa depan esok!' Oyen bertekad: 'Kalau aku kuasai ilmu ini, aku boleh ubah nasib keluargaku!'",
        introEn: "Oyen sits at the back row of 5 Science 1. Even with a patched backpack and worn shoes, his eyes sparkle watching Cikgu Amin write Differentiation on the blackboard. Cikgu says: 'Differentiation is the science of change — how small actions today transform tomorrow!' Oyen thinks: 'If I master this, I can transform my family's future!'"
      },
      mission: "🎢 Misi Landasan Roller Coaster Oyen: Kira kecuraman f'(x) landasan pada setiap titik supaya Oyen dan keretanya meluncur laju tanpa tergelincir!",
      missionEn: "🎢 Oyen's Roller Coaster Mission: Calculate the slope f'(x) at critical points so Oyen slides safely at maximum speed!",
      gen(level) {
        const a = R(2, 5);
        let n = R(2, 4);
        const b = R(2, 8) * (R(0, 1) ? 1 : -1);
        const c = R(1, 9) * (R(0, 1) ? 1 : -1);
        const k = R(1, 3);

        if (level === 1) {
          n = R(2, 3);
          const qText = `Diberi f(x) = ${poly([[a, n], [c, 0]])}. Cari terbitan pertama f′(x).`;
          const qEn = `Given f(x) = ${poly([[a, n], [c, 0]])}. Find the first derivative f′(x).`;
          return {
            q: qText,
            qEn: qEn,
            f: x => a * n * pw(x, n - 1),
            t: poly([[a * n, n - 1]], true),
            w: [
              { t: "exp", m: "Indeks tidak ditolak 1! Petua kuasa: ax<sup>n</sup> menjadi a·n·x<sup>n−1</sup>. Oyen risau ni! 💀", f: x => a * n * pw(x, n) },
              { t: "coef", m: "Anda lupa mendarabkan pekali dengan indeks asal (n).", f: x => a * pw(x, n - 1) },
              { t: "const", m: "Pemalar tanpa pemboleh ubah x dibezakan menjadi <b>0</b>, bukan kekal!", f: x => a * n * pw(x, n - 1) + c }
            ]
          };
        }

        if (level === 2) {
          const qText = `Diberi f(x) = ${poly([[a, n], [b, 1], [c, 0]])}. Cari f′(x).`;
          const qEn = `Given f(x) = ${poly([[a, n], [b, 1], [c, 0]])}. Find f′(x).`;
          return {
            q: qText,
            qEn: qEn,
            f: x => a * n * pw(x, n - 1) + b,
            t: poly([[a * n, n - 1], [b, 0]], true),
            w: [
              { t: "exp", m: "Indeks x tidak dikurangkan 1. Contoh: 3x² dibezakan menjadi 6x, bukan 6x².", f: x => a * n * pw(x, n) + b },
              { t: "dropb", m: "Sebutan linear bx dibezakan menjadi <b>b</b>, bukan dibuang terus!", f: x => a * n * pw(x, n - 1) },
              { t: "const", m: "Pemalar nombor tunggal dibezakan menjadi 0.", f: x => a * n * pw(x, n - 1) + b + c }
            ]
          };
        }

        // Level 3: Gradient at a specific point f'(k)
        const slope = a * n * pw(k, n - 1) + b;
        const qText = `Diberi lengkung f(x) = ${poly([[a, n], [b, 1], [c, 0]])}. Cari kecerunan tangen pada titik x = ${k}, iaitu f′(${k}).`;
        const qEn = `Given the curve f(x) = ${poly([[a, n], [b, 1], [c, 0]])}. Find the gradient of the tangent at x = ${k}, which is f′(${k}).`;
        return {
          q: qText,
          qEn: qEn,
          f: () => slope,
          t: `${slope}`,
          w: [
            { t: "sub_orig", m: "Anda menggantikan nilai x ke dalam f(x), bukan f′(x)! Bezakan dahulu fungsi itu, kemudian baru gantikan x = " + k + ".", f: () => a * pw(k, n) + b * k + c },
            { t: "exp", m: "Indeks tidak ditolak 1 semasa membezakan fungsi.", f: () => a * n * pw(k, n) + b }
          ]
        };
      },
      teach: {
        text: `
          <h4>Petua Kuasa Pembezaan (Power Rule)</h4>
          <p>Jika <b>f(x) = ax<sup>n</sup></b>, maka terbitan pertamanya ialah:</p>
          <div style="background:#FFF0DF;padding:12px;border-radius:8px;font-size:18px;font-weight:bold;color:#D85B10;text-align:center;">
            f′(x) = a · n · x<sup>n − 1</sup>
          </div>
          <p><b>3 Langkah Emas Oyen:</b></p>
          <ol>
            <li>Darabkan pekali <i>a</i> dengan kuasa asal <i>n</i>.</li>
            <li>Kurangkan kuasa <i>x</i> sebanyak 1 (n − 1).</li>
            <li>Sebutan linear <i>bx → b</i>, dan sebutan pemalar <i>c → 0</i>.</li>
          </ol>
        `,
        worked: `
          <h4>Contoh Langkah Demi Langkah SPM</h4>
          <p>Cari terbitan pertama bagi: <b>f(x) = 4x<sup>3</sup> + 5x − 7</b></p>
          <p><b>Langkah 1:</b> Bezakan sebutan pertama 4x<sup>3</sup>:<br>
          4 × 3 · x<sup>3−1</sup> = <b>12x<sup>2</sup></b></p>
          <p><b>Langkah 2:</b> Bezakan sebutan linear 5x:<br>
          Kuasa x ialah 1 → 5 × 1 · x<sup>0</sup> = <b>5</b></p>
          <p><b>Langkah 3:</b> Bezakan pemalar −7:<br>
          Pemalar tidak berubah dengan x → <b>0</b></p>
          <p><b>Jawapan Akhir:</b> f′(x) = <b>12x<sup>2</sup> + 5</b></p>
        `,
        visual: () => {
          return OyenMathEngine.plotCurve({
            fn: x => x * x,
            xMin: -2,
            xMax: 3,
            yMin: -1,
            yMax: 9,
            tangentAt: 1.5,
            tangentSlope: 3.0,
            title: "Graf y = x² dan Garis Tangen pada x = 1.5 (Kecerunan m = 2x = 3)"
          });
        },
        practical: `
          <h4>Analogi Kereta Lumba Oyen</h4>
          <p>Bayangkan Oyen menaiki roller coaster mini di taman permainan. <b>f(x)</b> ialah ketinggian Oyen dari tanah. <b>f′(x)</b> ialah kecuraman landasan di titik tersebut. Jika landasan mendatar (f'(x) = 0), Oyen berada di puncak paling tinggi atau paling rendah!</p>
        `
      }
    },

    // ==========================================
    // LEVEL 2: INTEGRATION
    // "Putting the Pieces Together" (Direct Continuation)
    // ==========================================
    integ: {
      id: "integ",
      name: "Tahap 2: Pengamiran (Integration)",
      nameEn: "Level 2: Integration",
      tag: "Bab 3 Tingkatan 5 SPM",
      tagEn: "Form 5 SPM Chapter 3",
      chapterName: "Menyusun Kepingan Impian",
      chapterNameEn: "Putting the Pieces Together",
      storyScene: {
        intro: "Dengan berkat penguasaan Pembezaan, Oyen berjaya memenangi hadiah kecil kuiz matematik sekolah! Dia mula mereka bentuk tempat perlindungan untuk keluarganya dengan kolam ikan. Tetapi untuk mengira kuantiti jubin terkumpul dan luas kolam berlengkung itu, dia perlu menyatukan semua kepingan kecil. Cikgu Amin tersenyum: 'Oyen, songsangan bagi pembezaan ialah Pengamiran. Kamu sudah tahu kadar perubahan, sekarang masa untuk mengira jumlah terkumpul!'",
        introEn: "Armed with his mastery of Differentiation, Oyen wins a school math prize! He starts sketching plans for a warm shelter with a fish pond. But to calculate total accumulated tiles and curved pond areas, he must assemble tiny pieces. Cikgu Amin smiles: 'Oyen, the reverse of differentiation is Integration. You know the rates of change; now calculate the accumulated whole!'"
      },
      mission: "🐟 Misi Kolam Ikan Oyen: Kira luas permukaan air dan kamiran tak tentu bagi membentuk kolam salmon impian Oyen!",
      missionEn: "🐟 Oyen's Salmon Pond Mission: Calculate the definite area and indefinite integral to build Oyen's dream fish sanctuary!",
      gen(level) {
        const a = R(2, 4) * 2; // Even number so a/2 is integer
        const b = R(2, 6);
        const k = R(1, 3);

        if (level === 1) {
          // Indefinite integral of a*x
          const qText = `Cari kamiran tak tentu: ∫ (${a}x) dx. (Gunakan + c dalam jawapan anda!)`;
          const qEn = `Find the indefinite integral: ∫ (${a}x) dx. (Include + c in your answer!)`;
          const coeff = a / 2;
          return {
            q: qText,
            qEn: qEn,
            hasC: true,
            f: (x, c) => coeff * x * x + c,
            t: `${coeff}x^2 + c`,
            w: [
              { t: "no_c", m: "Ingat pemalar pengamiran! Tambahkan <b>+ c</b> pada hujung jawapan anda.", f: (x) => coeff * x * x },
              { t: "div_power", m: "Kuasa ditambah 1 (x²), tetapi jangan lupa bahagi dengan kuasa baharu itu (2)!", f: (x, c) => a * x * x + c },
              { t: "diff_instead", m: "Anda membezakan fungsi! Pengamiran ialah songsangan: tambahkan 1 pada kuasa, bukan tolak.", f: () => a }
            ]
          };
        }

        if (level === 2) {
          // Indefinite integral of a polynomial: a*x + b
          const qText = `Cari kamiran tak tentu: ∫ (${a}x + ${b}) dx. (Sertakan + c)`;
          const qEn = `Find the indefinite integral: ∫ (${a}x + ${b}) dx. (Include + c)`;
          const coeff = a / 2;
          return {
            q: qText,
            qEn: qEn,
            hasC: true,
            f: (x, c) => coeff * x * x + b * x + c,
            t: `${coeff}x^2 + ${b}x + c`,
            w: [
              { t: "drop_bx", m: "Pemalar ${b} bila dikamir menjadi <b>${b}x</b>, bukan kekal ${b}!", f: (x, c) => coeff * x * x + b + c },
              { t: "no_c", m: "Jangan lupa <b>+ c</b> pada jawapan kamiran tak tentu!", f: (x) => coeff * x * x + b * x }
            ]
          };
        }

        // Level 3: Definite integral ∫_0^k (3x^2) dx = k^3
        const upper = R(2, 4);
        const targetVal = pw(upper, 3);
        const qText = `Hitung nilai kamiran tentu: ∫<sub>0</sub><sup>${upper}</sup> (3x<sup>2</sup>) dx.`;
        const qEn = `Evaluate the definite integral: ∫<sub>0</sub><sup>${upper}</sup> (3x<sup>2</sup>) dx.`;
        return {
          q: qText,
          qEn: qEn,
          hasC: false,
          f: () => targetVal,
          t: `${targetVal}`,
          w: [
            { t: "forgot_integrate", m: "Gantikan had selepas mengamir: ∫ 3x² dx = x³. Kemudian hitung [${upper}³ − 0³].", f: () => 3 * pw(upper, 2) },
            { t: "arithmetic", m: "Semak semula pengiraan kuasa tiga anda: ${upper} × ${upper} × ${upper}.", f: () => upper * 3 }
          ]
        };
      },
      teach: {
        text: `
          <h4>Petua Asas Pengamiran (Integration Rule)</h4>
          <p>Pengamiran ialah operasi <b>songsang</b> bagi pembezaan:</p>
          <div style="background:#FFF0DF;padding:12px;border-radius:8px;font-size:18px;font-weight:bold;color:#D85B10;text-align:center;">
            ∫ ax<sup>n</sup> dx = [ a · x<sup>n + 1</sup> / (n + 1) ] + C
          </div>
          <p><b>Langkah Penting Oyen:</b></p>
          <ul>
            <li><b>Tambah</b> kuasa x sebanyak 1 (n + 1).</li>
            <li><b>Bahagi</b> dengan nombor kuasa baharu itu.</li>
            <li>Pemalar <i>b → bx</i>.</li>
            <li><b>WAJIB + C:</b> Jangan tertinggal pemalar pengamiran <i>+ C</i> untuk kamiran tak tentu!</li>
          </ul>
        `,
        worked: `
          <h4>Contoh Langkah Demi Langkah SPM</h4>
          <p><b>Contoh 1:</b> Selesaikan ∫ (6x<sup>2</sup> + 4x − 3) dx</p>
          <p><b>Langkah 1:</b> Kamirkan 6x<sup>2</sup> → 6x<sup>2+1</sup> / (2+1) = 6x<sup>3</sup> / 3 = <b>2x<sup>3</sup></b></p>
          <p><b>Langkah 2:</b> Kamirkan 4x → 4x<sup>1+1</sup> / (1+1) = 4x<sup>2</sup> / 2 = <b>2x<sup>2</sup></b></p>
          <p><b>Langkah 3:</b> Kamirkan pemalar −3 → <b>−3x</b></p>
          <p><b>Langkah 4:</b> Tambah pemalar <b>+ C</b></p>
          <p><b>Jawapan:</b> 2x<sup>3</sup> + 2x<sup>2</sup> − 3x + C</p>
        `,
        visual: () => {
          return OyenMathEngine.plotCurve({
            fn: x => 0.5 * x * x + 1,
            xMin: -1,
            xMax: 4,
            yMin: -1,
            yMax: 8,
            integralFrom: 0,
            integralTo: 3,
            title: "Luas di Bawah Lengkung y = 0.5x² + 1 dari x = 0 hingga x = 3"
          });
        },
        practical: `
          <h4>Analogi Kolam Ikan Oyen</h4>
          <p>Jika pembezaan memberitahu kita kelajuan air paip mengalir setiap saat, pengamiran pula mengira <b>jumlah keseluruhan air</b> yang telah terkumpul di dalam kolam ikan Oyen sepanjang masa! Kamiran tentu ialah luas sebenar kolam itu.</p>
        `
      }
    },

    // ==========================================
    // PREREQUISITE: QUADRATIC FUNCTIONS
    // ==========================================
    quad: {
      id: "quad",
      name: "Fungsi Kuadratik (Prasyarat)",
      nameEn: "Quadratic Functions (Prerequisite)",
      tag: "Asas Bentuk Graf Parabola",
      tagEn: "Parabolic Curve Foundations",
      chapterName: "Bumbung Rumah Impian",
      chapterNameEn: "The Roof of Oyen's Dream Shelter",
      mission: "🌉 Misi Bumbung Lengkung: Bumbung tempat berteduh Oyen berbentuk parabola kuadratik. Cari titik puncaknya supaya air hujan mengalir keluar!",
      missionEn: "🌉 Curved Roof Mission: The shelter roof is parabolic. Find its vertex so rainwater drains away safely!",
      gen(level) {
        const a = [1, 2, -1, -2][R(0, 3)];
        const b = (R(1, 4) * 2) * (a > 0 ? -1 : 1);
        const c = R(-5, 5);
        const h = -b / (2 * a);
        const kVal = a * h * h + b * h + c;
        const expr = poly([[a, 2], [b, 1], [c, 0]]);

        if (level === 1) {
          return {
            q: `Diberi fungsi f(x) = ${expr}. Cari persamaan paksi simetri x = ?`,
            qEn: `Given f(x) = ${expr}. Find the axis of symmetry x = ?`,
            f: () => h,
            t: `${h}`,
            w: [
              { t: "sign", m: "Semak formula: paksi simetri ialah x = <b>−b / (2a)</b>. Perhatikan tanda negatif!", f: () => b / (2 * a) }
            ]
          };
        }

        if (level === 2) {
          return {
            q: `Diberi f(x) = ${expr}. Cari nilai ${a > 0 ? "minimum" : "maksimum"} bagi fungsi tersebut.`,
            qEn: `Given f(x) = ${expr}. Find the ${a > 0 ? "minimum" : "maximum"} value of the function.`,
            f: () => kVal,
            t: `${kVal}`,
            w: [
              { t: "x_instead_of_y", m: "Itu nilai x bagi paksi simetri. Gantikan nilai x itu ke dalam f(x) untuk mencari nilai minimum/maksimum fungsi!", f: () => h }
            ]
          };
        }

        const disc = b * b - 4 * a * c;
        return {
          q: `Kira nilai pembezalayan (discriminant) b² − 4ac bagi f(x) = ${expr}.`,
          qEn: `Calculate the discriminant b² − 4ac for f(x) = ${expr}.`,
          f: () => disc,
          t: `${disc}`,
          w: [
            { t: "sign_disc", m: "Formula pembezalayan ialah b² <b>−</b> 4ac. Berhati-hati semasa mendarab tanda negatif.", f: () => b * b + 4 * a * c }
          ]
        };
      },
      teach: {
        text: `
          <h4>Ciri-Ciri Utama Fungsi Kuadratik</h4>
          <p>f(x) = ax<sup>2</sup> + bx + c</p>
          <ul>
            <li><b>Paksi Simetri:</b> x = −b / (2a)</li>
            <li><b>Bentuk Graf:</b> Jika a > 0 bentuk 'senyum' (minimum ∪), jika a < 0 bentuk 'masam' (maksimum ∩).</li>
            <li><b>Titik Puncak (Verteks):</b> Koordinat (h, k) di mana h = −b/(2a) dan k = f(h).</li>
            <li><b>Pembezalayan:</b> b<sup>2</sup> − 4ac (Menentukan bilangan punca nyata).</li>
          </ul>
        `,
        worked: `
          <h4>Contoh Pengiraan Verteks</h4>
          <p>Diberi f(x) = x<sup>2</sup> − 6x + 5</p>
          <p>a = 1, b = −6, c = 5</p>
          <p>Paksi simetri: x = −(−6) / (2 × 1) = 6 / 2 = <b>3</b></p>
          <p>Nilai minimum: f(3) = (3)<sup>2</sup> − 6(3) + 5 = 9 − 18 + 5 = <b>−4</b></p>
          <p>Maka titik verteks ialah <b>(3, −4)</b>.</p>
        `,
        visual: () => {
          return OyenMathEngine.plotCurve({
            fn: x => x * x - 4 * x + 3,
            xMin: -1,
            xMax: 5,
            yMin: -3,
            yMax: 9,
            title: "Graf Kuadratik y = x² − 4x + 3 dengan Verteks pada (2, −1)"
          });
        },
        practical: `
          <h4>Analogi Bumbung Parabola Oyen</h4>
          <p>Bumbung melengkung tempat perlindungan Oyen membolehkan air hujan turun dengan seimbang ke kiri dan kanan dari titik puncak simetri x = −b/(2a). Jika simetri salah, air akan bertakung!</p>
        `
      }
    }
  };

  return {
    topics,
    getTopic: (id) => topics[id] || topics.dif
  };
})();

if (typeof window !== "undefined") {
  window.OyenCurriculum = OyenCurriculum;
}
if (typeof module !== "undefined" && module.exports) {
  module.exports = OyenCurriculum;
}
