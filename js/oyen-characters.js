/**
 * Oyen Math - Mascot Character Engine
 * Renders consistent, high-fidelity SVG illustrations for Oyen the Orange Cat.
 * 
 * Features:
 * - 8 canonical poses/expressions:
 *   1. happy (correct answers / celebrations)
 *   2. sad (incorrect answers / consolation)
 *   3. thinking (solving difficult math problems)
 *   4. confused (humorous 'brain.exe' reactions)
 *   5. excited (level completions / achievements)
 *   6. determined ('LOCK IN! 🐈' / encouragement)
 *   7. sleeping (loading / resting states)
 *   8. detective (examining handwritten calculation steps)
 */

const OyenCharacter = (() => {
  // Brand color palette constants
  const C = {
    fur: "#FF8C24",
    furLight: "#FFAA5C",
    furDark: "#D85B10",
    stripe: "#B84206",
    muzzle: "#FFF0DF",
    belly: "#FFF5E8",
    innerEar: "#FFA6B5",
    nose: "#FF6B8B",
    eye: "#1C2430",
    eyeIris: "#107050",
    eyeHighlight: "#FFFFFF",
    cheeks: "#FFB0BC",
    gold: "#FFD13B",
    goldDark: "#D99B00",
    headband: "#E11D48",
    cap: "#854D0E",
    capStripe: "#57300A"
  };

  /**
   * Common defs (gradients, filters)
   */
  const getDefs = (idPrefix) => `
    <defs>
      <linearGradient id="${idPrefix}_furGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="${C.furLight}"/>
        <stop offset="60%" stop-color="${C.fur}"/>
        <stop offset="100%" stop-color="${C.furDark}"/>
      </linearGradient>
      <linearGradient id="${idPrefix}_stripeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="${C.stripe}"/>
        <stop offset="100%" stop-color="${C.furDark}"/>
      </linearGradient>
      <linearGradient id="${idPrefix}_bellyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="#FFFFFF"/>
        <stop offset="100%" stop-color="${C.muzzle}"/>
      </linearGradient>
      <linearGradient id="${idPrefix}_goldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="#FFF38A"/>
        <stop offset="50%" stop-color="${C.gold}"/>
        <stop offset="100%" stop-color="${C.goldDark}"/>
      </linearGradient>
      <filter id="${idPrefix}_shadow" x="-10%" y="-10%" width="120%" height="120%">
        <feDropShadow dx="0" dy="4" stdDeviation="3" flood-color="#30251F" flood-opacity="0.15"/>
      </filter>
    </defs>
  `;

  /**
   * Base head & ears template
   */
  const renderEars = (prefix, tilt = 0, sad = false) => {
    if (sad) {
      // Drooping ears
      return `
        <!-- Left Ear (drooping) -->
        <path d="M 62,75 Q 40,85 30,105 Q 45,115 68,98 Z" fill="url(#${prefix}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <path d="M 58,80 Q 42,90 36,104 Q 48,110 64,96 Z" fill="${C.innerEar}"/>
        <!-- Right Ear (drooping) -->
        <path d="M 138,75 Q 160,85 170,105 Q 155,115 132,98 Z" fill="url(#${prefix}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <path d="M 142,80 Q 158,90 164,104 Q 152,110 136,96 Z" fill="${C.innerEar}"/>
      `;
    }
    // Normal upright perky ears
    const leftEar = `
      <path d="M 55,75 Q 40,30 68,22 Q 88,40 85,70 Z" fill="url(#${prefix}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
      <path d="M 59,70 Q 48,36 68,30 Q 80,44 78,68 Z" fill="${C.innerEar}"/>
    `;
    const rightEar = `
      <path d="M 145,75 Q 160,30 132,22 Q 112,40 115,70 Z" fill="url(#${prefix}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
      <path d="M 141,70 Q 152,36 132,30 Q 120,44 122,68 Z" fill="${C.innerEar}"/>
    `;
    return leftEar + rightEar;
  };

  /**
   * Striped tabby markings on forehead and cheeks
   */
  const renderTabbyStripes = (prefix) => `
    <!-- Forehead Stripes -->
    <path d="M 97,42 L 100,56 L 103,42 Z" fill="${C.stripe}"/>
    <path d="M 88,45 L 91,57 L 93,48 Z" fill="${C.stripe}"/>
    <path d="M 112,45 L 109,57 L 107,48 Z" fill="${C.stripe}"/>
    <!-- Left Cheek Stripes -->
    <path d="M 46,90 Q 56,92 62,90 Q 55,95 46,94 Z" fill="${C.stripe}"/>
    <path d="M 48,97 Q 56,99 60,98 Q 55,102 48,101 Z" fill="${C.stripe}"/>
    <!-- Right Cheek Stripes -->
    <path d="M 154,90 Q 144,92 138,90 Q 145,95 154,94 Z" fill="${C.stripe}"/>
    <path d="M 152,97 Q 144,99 140,98 Q 145,102 152,101 Z" fill="${C.stripe}"/>
  `;

  /**
   * Muzzle, nose and whiskers
   */
  const renderMuzzle = (prefix, mouthType = "smile") => {
    let mouthSvg = "";
    if (mouthType === "openSmile") {
      mouthSvg = `
        <path d="M 94,112 Q 100,124 106,112 Z" fill="#991B1B" stroke="${C.furDark}" stroke-width="1.5"/>
        <path d="M 96,117 Q 100,122 104,117 Z" fill="#F472B6"/>
      `;
    } else if (mouthType === "smile") {
      mouthSvg = `
        <path d="M 93,111 Q 97,116 100,111 Q 103,116 107,111" fill="none" stroke="${C.furDark}" stroke-width="2" stroke-linecap="round"/>
      `;
    } else if (mouthType === "sad") {
      mouthSvg = `
        <path d="M 95,115 Q 100,109 105,115" fill="none" stroke="${C.furDark}" stroke-width="2" stroke-linecap="round"/>
      `;
    } else if (mouthType === "confused") {
      mouthSvg = `
        <path d="M 93,113 Q 97,110 101,114 Q 105,117 108,112" fill="none" stroke="${C.furDark}" stroke-width="2" stroke-linecap="round"/>
      `;
    } else if (mouthType === "determined") {
      mouthSvg = `
        <path d="M 94,113 L 106,113" fill="none" stroke="${C.furDark}" stroke-width="2.5" stroke-linecap="round"/>
      `;
    } else if (mouthType === "sleeping") {
      mouthSvg = `
        <path d="M 96,112 Q 100,115 104,112" fill="none" stroke="${C.furDark}" stroke-width="1.8" stroke-linecap="round"/>
      `;
    }

    return `
      <!-- Muzzle -->
      <ellipse cx="94" cy="110" rx="9" ry="7" fill="${C.muzzle}"/>
      <ellipse cx="106" cy="110" rx="9" ry="7" fill="${C.muzzle}"/>
      <!-- Nose -->
      <polygon points="96,105 104,105 100,110" fill="${C.nose}" rx="2"/>
      <!-- Mouth -->
      ${mouthSvg}
      <!-- Blush Cheeks -->
      <ellipse cx="64" cy="104" rx="8" ry="4" fill="${C.cheeks}" opacity="0.6"/>
      <ellipse cx="136" cy="104" rx="8" ry="4" fill="${C.cheeks}" opacity="0.6"/>
      <!-- Whiskers Left -->
      <line x1="42" y1="106" x2="68" y2="108" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round" opacity="0.9"/>
      <line x1="40" y1="113" x2="68" y2="112" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round" opacity="0.9"/>
      <!-- Whiskers Right -->
      <line x1="158" y1="106" x2="132" y2="108" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round" opacity="0.9"/>
      <line x1="160" y1="113" x2="132" y2="112" stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round" opacity="0.9"/>
    `;
  };

  // Poses implementations
  const poses = {
    /**
     * 1. HAPPY OYEN - Arms up in celebration, big sparkling happy eyes, sparkles!
     */
    happy: (id) => `
      <svg viewBox="0 0 200 200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Happy Oyen">
        ${getDefs(id)}
        <!-- Sparkles -->
        <g fill="${C.gold}" opacity="0.9">
          <path d="M 28,38 L 31,48 L 41,51 L 31,54 L 28,64 L 25,54 L 15,51 L 25,48 Z"/>
          <path d="M 172,38 L 175,48 L 185,51 L 175,54 L 172,64 L 169,54 L 159,51 L 169,48 Z" transform="scale(0.85) translate(40,-10)"/>
          <circle cx="36" cy="74" r="3"/>
          <circle cx="168" cy="72" r="3"/>
        </g>
        <!-- Tail -->
        <path d="M 140,165 Q 185,160 178,120 Q 174,100 162,106 Q 168,125 145,150 Z" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <path d="M 175,115 Q 170,102 162,106 Q 166,118 174,122 Z" fill="${C.muzzle}"/>
        <!-- Body -->
        <ellipse cx="100" cy="155" rx="42" ry="32" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <!-- Belly -->
        <ellipse cx="100" cy="158" rx="26" ry="22" fill="url(#${id}_bellyGrad)"/>
        <!-- Paws Raised Up High -->
        <ellipse cx="58" cy="120" rx="12" ry="16" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(-30 58 120)"/>
        <circle cx="53" cy="112" r="4" fill="${C.innerEar}"/>
        <circle cx="61" cy="114" r="3" fill="${C.innerEar}"/>
        <ellipse cx="142" cy="120" rx="12" ry="16" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(30 142 120)"/>
        <circle cx="147" cy="112" r="4" fill="${C.innerEar}"/>
        <circle cx="139" cy="114" r="3" fill="${C.innerEar}"/>
        <!-- Ears -->
        ${renderEars(id)}
        <!-- Head -->
        <circle cx="100" cy="94" r="48" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        ${renderTabbyStripes(id)}
        <!-- Happy Eyes (curved crescent cheerful arcs) -->
        <path d="M 76,88 Q 84,78 92,88" fill="none" stroke="${C.furDark}" stroke-width="4.5" stroke-linecap="round"/>
        <path d="M 108,88 Q 116,78 124,88" fill="none" stroke="${C.furDark}" stroke-width="4.5" stroke-linecap="round"/>
        <!-- Muzzle & Open Smiling Mouth -->
        ${renderMuzzle(id, "openSmile")}
        <!-- Feet -->
        <ellipse cx="78" cy="182" rx="14" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <ellipse cx="122" cy="182" rx="14" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
      </svg>
    `,

    /**
     * 2. SAD OYEN - Drooping ears, teary eyes, comforting paw, comforting expression
     */
    sad: (id) => `
      <svg viewBox="0 0 200 200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Sad Oyen">
        ${getDefs(id)}
        <!-- Drooping Tail -->
        <path d="M 135,168 Q 170,180 165,192 Q 155,195 130,175 Z" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <!-- Body -->
        <ellipse cx="100" cy="155" rx="40" ry="30" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <ellipse cx="100" cy="158" rx="24" ry="20" fill="url(#${id}_bellyGrad)"/>
        <!-- Drooping Ears -->
        ${renderEars(id, 0, true)}
        <!-- Head -->
        <circle cx="100" cy="98" r="46" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        ${renderTabbyStripes(id)}
        <!-- Sad Brow & Big Watery Eyes -->
        <path d="M 74,78 Q 84,83 92,80" fill="none" stroke="${C.furDark}" stroke-width="2" stroke-linecap="round"/>
        <path d="M 126,78 Q 116,83 108,80" fill="none" stroke="${C.furDark}" stroke-width="2" stroke-linecap="round"/>
        <!-- Eyes with Tears -->
        <ellipse cx="83" cy="92" rx="9" ry="11" fill="${C.eye}"/>
        <circle cx="81" cy="89" r="4" fill="${C.eyeHighlight}"/>
        <circle cx="86" cy="95" r="2" fill="${C.eyeHighlight}"/>
        <!-- Little Tear Drop Left -->
        <path d="M 71,98 C 69,103 66,108 66,110 C 66,113 69,115 72,115 C 75,115 77,113 77,110 C 77,108 73,103 71,98 Z" fill="#60A5FA" opacity="0.85"/>
        <ellipse cx="117" cy="92" rx="9" ry="11" fill="${C.eye}"/>
        <circle cx="115" cy="89" r="4" fill="${C.eyeHighlight}"/>
        <circle cx="120" cy="95" r="2" fill="${C.eyeHighlight}"/>
        <!-- Muzzle with Sad Mouth -->
        ${renderMuzzle(id, "sad")}
        <!-- Paws Comforting -->
        <ellipse cx="88" cy="148" rx="10" ry="12" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <ellipse cx="112" cy="148" rx="10" ry="12" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <!-- Feet -->
        <ellipse cx="76" cy="180" rx="13" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <ellipse cx="124" cy="180" rx="13" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
      </svg>
    `,

    /**
     * 3. THINKING OYEN - Paw on chin, glancing up, floating math symbols
     */
    thinking: (id) => `
      <svg viewBox="0 0 200 200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Thinking Oyen">
        ${getDefs(id)}
        <!-- Floating Math Symbols -->
        <g font-family="monospace" font-weight="bold" fill="#F06A16" opacity="0.85" font-size="14">
          <text x="24" y="52">dy/dx</text>
          <text x="148" y="44">∫f(x)</text>
          <text x="22" y="105">x²</text>
          <text x="165" y="98">+ C</text>
        </g>
        <!-- Tail -->
        <path d="M 138,162 Q 170,150 165,125 Q 160,110 152,118 Q 155,138 135,152 Z" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <!-- Body -->
        <ellipse cx="100" cy="156" rx="41" ry="31" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <ellipse cx="98" cy="158" rx="25" ry="21" fill="url(#${id}_bellyGrad)"/>
        <!-- Ears -->
        ${renderEars(id)}
        <!-- Head -->
        <circle cx="100" cy="94" r="47" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        ${renderTabbyStripes(id)}
        <!-- Thinking Eyebrows -->
        <path d="M 72,76 Q 82,73 90,78" fill="none" stroke="${C.furDark}" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M 110,75 Q 118,72 128,74" fill="none" stroke="${C.furDark}" stroke-width="2.5" stroke-linecap="round"/>
        <!-- Eyes looking up and to the right -->
        <ellipse cx="81" cy="88" rx="9" ry="10" fill="${C.eye}"/>
        <circle cx="85" cy="84" r="4" fill="${C.eyeHighlight}"/>
        <ellipse cx="119" cy="88" rx="9" ry="10" fill="${C.eye}"/>
        <circle cx="123" cy="84" r="4" fill="${C.eyeHighlight}"/>
        <!-- Muzzle -->
        ${renderMuzzle(id, "smile")}
        <!-- Paw on Chin (Thinking Pose) -->
        <g transform="translate(90, 115)">
          <ellipse cx="15" cy="6" rx="10" ry="13" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(-40 15 6)"/>
          <circle cx="12" cy="1" r="3.5" fill="${C.innerEar}"/>
          <circle cx="18" cy="3" r="3" fill="${C.innerEar}"/>
        </g>
        <!-- Other paw resting -->
        <ellipse cx="64" cy="148" rx="10" ry="13" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <!-- Feet -->
        <ellipse cx="78" cy="182" rx="13" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <ellipse cx="122" cy="182" rx="13" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
      </svg>
    `,

    /**
     * 4. CONFUSED OYEN - Tilted head, question mark swirl, funny Gen Z meme face
     */
    confused: (id) => `
      <svg viewBox="0 0 200 200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Confused Oyen">
        ${getDefs(id)}
        <!-- Floating Question Mark and Sweatdrop -->
        <g fill="#D85B10" font-family="sans-serif" font-weight="900" font-size="28">
          <text x="145" y="48">?</text>
        </g>
        <path d="M 60,45 C 57,50 53,55 53,58 C 53,62 57,64 60,64 C 63,64 67,62 67,58 C 67,55 63,50 60,45 Z" fill="#60A5FA" opacity="0.8"/>
        <!-- Body -->
        <ellipse cx="100" cy="158" rx="41" ry="30" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <ellipse cx="100" cy="160" rx="25" ry="20" fill="url(#${id}_bellyGrad)"/>
        <!-- Tilted Head Group -->
        <g transform="rotate(12 100 100)">
          ${renderEars(id)}
          <circle cx="100" cy="94" r="47" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
          ${renderTabbyStripes(id)}
          <!-- Asymmetric funny confused eyebrows -->
          <path d="M 72,74 Q 80,78 90,75" fill="none" stroke="${C.furDark}" stroke-width="2.5" stroke-linecap="round"/>
          <path d="M 110,70 Q 118,64 128,68" fill="none" stroke="${C.furDark}" stroke-width="2.5" stroke-linecap="round"/>
          <!-- Confused Eyes (one wide, one spiral/slightly squinted) -->
          <!-- Left Eye: Spiral/swirl -->
          <circle cx="80" cy="88" r="10" fill="#FFFFFF" stroke="${C.furDark}" stroke-width="1.5"/>
          <path d="M 80,88 A 2,2 0 0,1 82,88 A 4,4 0 0,1 76,88 A 6,6 0 0,1 86,88" fill="none" stroke="${C.furDark}" stroke-width="2"/>
          <!-- Right Eye: Big Wide Pupil -->
          <ellipse cx="120" cy="87" rx="11" ry="11" fill="${C.eye}"/>
          <circle cx="118" cy="84" r="4" fill="${C.eyeHighlight}"/>
          <circle cx="123" cy="90" r="2" fill="${C.eyeHighlight}"/>
          <!-- Muzzle & Wavy Mouth -->
          ${renderMuzzle(id, "confused")}
        </g>
        <!-- Paws Scratching Head / Floating -->
        <ellipse cx="65" cy="140" rx="10" ry="14" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(15 65 140)"/>
        <ellipse cx="138" cy="132" rx="10" ry="14" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(-30 138 132)"/>
        <!-- Feet -->
        <ellipse cx="78" cy="182" rx="13" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <ellipse cx="122" cy="182" rx="13" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
      </svg>
    `,

    /**
     * 5. EXCITED OYEN - Holding golden fish trophy, jumping pose, confetti
     */
    excited: (id) => `
      <svg viewBox="0 0 200 200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Excited Oyen">
        ${getDefs(id)}
        <!-- Confetti -->
        <rect x="25" y="30" width="6" height="6" fill="#F43F5E" transform="rotate(25 28 33)"/>
        <rect x="165" y="25" width="7" height="7" fill="#3B82F6" transform="rotate(45 168 28)"/>
        <rect x="175" y="85" width="5" height="5" fill="#10B981" transform="rotate(15 177 87)"/>
        <rect x="20" y="85" width="6" height="6" fill="${C.gold}" transform="rotate(60 23 88)"/>
        <!-- Swishing Upward Tail -->
        <path d="M 140,150 Q 185,135 180,90 Q 170,75 160,85 Q 165,115 138,138 Z" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <path d="M 175,82 Q 168,76 160,85 Q 166,95 174,96 Z" fill="${C.muzzle}"/>
        <!-- Body jumping slightly higher -->
        <ellipse cx="100" cy="148" rx="42" ry="32" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <ellipse cx="100" cy="150" rx="26" ry="22" fill="url(#${id}_bellyGrad)"/>
        <!-- Ears -->
        ${renderEars(id)}
        <!-- Head -->
        <circle cx="100" cy="88" r="48" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        ${renderTabbyStripes(id)}
        <!-- Big Excited Anime Sparkle Eyes -->
        <ellipse cx="78" cy="83" rx="12" ry="13" fill="${C.eye}"/>
        <circle cx="75" cy="78" r="5" fill="${C.eyeHighlight}"/>
        <circle cx="82" cy="87" r="2.5" fill="${C.eyeHighlight}"/>
        <!-- Star in Eye -->
        <path d="M 78,82 L 80,85 L 83,86 L 80,87 L 78,90 L 76,87 L 73,86 L 76,85 Z" fill="${C.gold}"/>
        <ellipse cx="122" cy="83" rx="12" ry="13" fill="${C.eye}"/>
        <circle cx="119" cy="78" r="5" fill="${C.eyeHighlight}"/>
        <circle cx="126" cy="87" r="2.5" fill="${C.eyeHighlight}"/>
        <path d="M 122,82 L 124,85 L 127,86 L 124,87 L 122,90 L 120,87 L 117,86 L 120,85 Z" fill="${C.gold}"/>
        <!-- Wide Happy Open Mouth -->
        ${renderMuzzle(id, "openSmile")}
        <!-- Golden Fish Trophy Held High -->
        <g transform="translate(130, 95) rotate(-20)">
          <!-- Fish Body -->
          <ellipse cx="15" cy="10" rx="16" ry="10" fill="url(#${id}_goldGrad)" stroke="${C.goldDark}" stroke-width="1.5"/>
          <!-- Fish Tail -->
          <polygon points="28,10 38,3 35,10 38,17" fill="url(#${id}_goldGrad)" stroke="${C.goldDark}" stroke-width="1.5"/>
          <!-- Fish Eye & Fin -->
          <circle cx="6" cy="8" r="2" fill="${C.furDark}"/>
          <path d="M 14,8 Q 18,14 14,16" fill="none" stroke="${C.goldDark}" stroke-width="1.5"/>
        </g>
        <!-- Paws Holding Trophy / High -->
        <ellipse cx="64" cy="120" rx="11" ry="14" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(-25 64 120)"/>
        <ellipse cx="132" cy="116" rx="11" ry="14" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(25 132 116)"/>
        <!-- Feet (Jumping Spread) -->
        <ellipse cx="72" cy="178" rx="14" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(-15 72 178)"/>
        <ellipse cx="128" cy="178" rx="14" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(15 128 178)"/>
      </svg>
    `,

    /**
     * 6. DETERMINED OYEN - Red SPM headband with paw, focused confident look, "LOCK IN!"
     */
    determined: (id) => `
      <svg viewBox="0 0 200 200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Determined Oyen">
        ${getDefs(id)}
        <!-- Fire Aura Sparkles -->
        <g fill="#EF4444" opacity="0.8">
          <circle cx="28" cy="130" r="4"/>
          <circle cx="172" cy="130" r="4"/>
          <path d="M 32,80 L 35,90 L 42,93 L 35,96 L 32,106 L 29,96 L 22,93 L 29,90 Z" fill="${C.gold}"/>
        </g>
        <!-- Tail -->
        <path d="M 140,160 Q 180,150 175,115 Q 170,95 158,102 Q 165,122 138,144 Z" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <!-- Body -->
        <ellipse cx="100" cy="155" rx="42" ry="32" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <ellipse cx="100" cy="158" rx="26" ry="22" fill="url(#${id}_bellyGrad)"/>
        <!-- Ears -->
        ${renderEars(id)}
        <!-- Head -->
        <circle cx="100" cy="94" r="48" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        ${renderTabbyStripes(id)}
        <!-- Red Hachimaki (SPM Headband) -->
        <path d="M 54,68 Q 100,56 146,68 L 148,80 Q 100,68 52,80 Z" fill="${C.headband}" stroke="#9F1239" stroke-width="1.5"/>
        <!-- Headband Knot Tails Flying Left -->
        <path d="M 53,74 Q 30,70 20,85 Q 35,85 50,78 Z" fill="${C.headband}"/>
        <path d="M 52,76 Q 28,85 24,102 Q 38,94 51,80 Z" fill="${C.headband}"/>
        <!-- White Paw / 'A+' on Headband -->
        <circle cx="100" cy="69" r="4.5" fill="#FFFFFF"/>
        <circle cx="95" cy="66" r="1.8" fill="#FFFFFF"/>
        <circle cx="100" cy="63" r="1.8" fill="#FFFFFF"/>
        <circle cx="105" cy="66" r="1.8" fill="#FFFFFF"/>
        <!-- Sharp Determined Eyebrows -->
        <path d="M 72,82 L 92,86" stroke="${C.furDark}" stroke-width="3.5" stroke-linecap="round"/>
        <path d="M 128,82 L 108,86" stroke="${C.furDark}" stroke-width="3.5" stroke-linecap="round"/>
        <!-- Sharp Focused Eyes -->
        <path d="M 73,86 Q 84,84 91,92 Q 82,97 73,86 Z" fill="${C.eye}"/>
        <circle cx="83" cy="88" r="3" fill="${C.eyeHighlight}"/>
        <circle cx="85" cy="89" r="1" fill="${C.gold}"/>
        <path d="M 127,86 Q 116,84 109,92 Q 118,97 127,86 Z" fill="${C.eye}"/>
        <circle cx="117" cy="88" r="3" fill="${C.eyeHighlight}"/>
        <circle cx="115" cy="89" r="1" fill="${C.gold}"/>
        <!-- Determined Clenched Smile -->
        ${renderMuzzle(id, "determined")}
        <!-- Clenched Fist Paws (Ready for action) -->
        <circle cx="68" cy="142" r="12" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <circle cx="68" cy="142" r="6" fill="${C.innerEar}"/>
        <circle cx="132" cy="142" r="12" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <circle cx="132" cy="142" r="6" fill="${C.innerEar}"/>
        <!-- Feet Grounded -->
        <ellipse cx="78" cy="182" rx="14" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <ellipse cx="122" cy="182" rx="14" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
      </svg>
    `,

    /**
     * 7. SLEEPING OYEN - Curled on cushion, peaceful 'Zzz', loading screen
     */
    sleeping: (id) => `
      <svg viewBox="0 0 200 200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Sleeping Oyen">
        ${getDefs(id)}
        <!-- Floating Zzz -->
        <g fill="#9CA3AF" font-family="sans-serif" font-weight="bold">
          <text x="145" y="65" font-size="14">z</text>
          <text x="156" y="52" font-size="18">z</text>
          <text x="170" y="36" font-size="22" fill="${C.fur}">Z</text>
        </g>
        <!-- Soft Cushion -->
        <ellipse cx="100" cy="165" rx="72" ry="24" fill="#FFF0DF" stroke="#FDE68A" stroke-width="2"/>
        <ellipse cx="100" cy="165" rx="66" ry="20" fill="#FFF9F2"/>
        <!-- Curled Body -->
        <ellipse cx="100" cy="142" rx="46" ry="30" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <ellipse cx="100" cy="148" rx="28" ry="18" fill="url(#${id}_bellyGrad)"/>
        <!-- Curled Tail Wrapped Around -->
        <path d="M 60,150 Q 50,135 60,120 Q 85,115 130,128" fill="none" stroke="url(#${id}_furGrad)" stroke-width="16" stroke-linecap="round"/>
        <path d="M 60,150 Q 50,135 60,120 Q 85,115 130,128" fill="none" stroke="${C.furDark}" stroke-width="1" stroke-linecap="round"/>
        <!-- White Tail Tip -->
        <circle cx="126" cy="127" r="7" fill="${C.muzzle}"/>
        <!-- Sleeping Relaxed Ears -->
        <path d="M 62,88 Q 45,60 70,55 Q 85,72 82,90 Z" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <path d="M 65,85 Q 52,65 69,61 Q 78,74 76,86 Z" fill="${C.innerEar}"/>
        <path d="M 138,88 Q 155,60 130,55 Q 115,72 118,90 Z" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <path d="M 135,85 Q 148,65 131,61 Q 122,74 124,86 Z" fill="${C.innerEar}"/>
        <!-- Head resting down -->
        <circle cx="100" cy="104" r="42" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        ${renderTabbyStripes(id)}
        <!-- Closed Peaceful Curved Sleeping Eyes -->
        <path d="M 76,102 Q 84,108 92,102" fill="none" stroke="${C.furDark}" stroke-width="3" stroke-linecap="round"/>
        <path d="M 108,102 Q 116,108 124,102" fill="none" stroke="${C.furDark}" stroke-width="3" stroke-linecap="round"/>
        <!-- Muzzle with sweet breathing smile -->
        ${renderMuzzle(id, "sleeping")}
        <!-- Front Paws Tucked In -->
        <ellipse cx="88" cy="148" rx="8" ry="10" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <ellipse cx="112" cy="148" rx="8" ry="10" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
      </svg>
    `,

    /**
     * 8. DETECTIVE OYEN - Deerstalker detective hat, magnifying glass inspecting calculations
     */
    detective: (id) => `
      <svg viewBox="0 0 200 200" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Detective Oyen">
        ${getDefs(id)}
        <!-- Inspecting Math Line Target -->
        <rect x="18" y="145" width="60" height="40" rx="6" fill="#FFFFFF" stroke="#E2E8F0" stroke-width="1.5"/>
        <line x1="24" y1="155" x2="68" y2="155" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/>
        <line x1="24" y1="165" x2="60" y2="165" stroke="#F06A16" stroke-width="2" stroke-linecap="round"/>
        <line x1="24" y1="175" x2="52" y2="175" stroke="#94A3B8" stroke-width="2" stroke-linecap="round"/>
        <!-- Tail -->
        <path d="M 140,165 Q 175,160 170,128 Q 166,110 155,116 Q 160,135 138,150 Z" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <!-- Body -->
        <ellipse cx="106" cy="156" rx="41" ry="31" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        <ellipse cx="106" cy="158" rx="25" ry="21" fill="url(#${id}_bellyGrad)"/>
        <!-- Ears -->
        ${renderEars(id)}
        <!-- Head -->
        <circle cx="106" cy="96" r="46" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="2"/>
        ${renderTabbyStripes(id)}
        <!-- Detective Deerstalker Cap -->
        <ellipse cx="106" cy="62" rx="42" ry="20" fill="${C.cap}" stroke="${C.capStripe}" stroke-width="2"/>
        <!-- Front & Back Visor of Cap -->
        <path d="M 64,68 Q 106,56 148,68 Q 106,78 64,68 Z" fill="#6B3E0A"/>
        <path d="M 88,44 Q 106,38 124,44 L 122,50 Q 106,44 90,50 Z" fill="#57300A"/>
        <!-- Cap Ear Flap Tie Ribbon -->
        <path d="M 103,42 Q 106,34 109,42 Z" fill="#FF8C24"/>
        <!-- Sharp Focused Inquisitive Eyes -->
        <!-- Right eye normal curious -->
        <ellipse cx="124" cy="94" rx="9" ry="10" fill="${C.eye}"/>
        <circle cx="122" cy="91" r="3.5" fill="${C.eyeHighlight}"/>
        <!-- Left eye magnified by looking down towards glass -->
        <ellipse cx="88" cy="94" rx="10" ry="11" fill="${C.eye}"/>
        <circle cx="86" cy="91" r="4" fill="${C.eyeHighlight}"/>
        <!-- Focused Eyebrows -->
        <path d="M 78,82 Q 88,85 96,82" fill="none" stroke="${C.furDark}" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M 116,82 Q 124,80 132,84" fill="none" stroke="${C.furDark}" stroke-width="2.5" stroke-linecap="round"/>
        <!-- Muzzle -->
        ${renderMuzzle(id, "smile")}
        <!-- Paw holding Magnifying Glass -->
        <g transform="translate(38, 110)">
          <!-- Glass Handle -->
          <line x1="42" y1="36" x2="22" y2="58" stroke="#78350F" stroke-width="6" stroke-linecap="round"/>
          <line x1="42" y1="36" x2="22" y2="58" stroke="#D97706" stroke-width="2" stroke-linecap="round"/>
          <!-- Glass Rim -->
          <circle cx="48" cy="30" r="22" fill="#E0F2FE" fill-opacity="0.35" stroke="#3B82F6" stroke-width="4"/>
          <!-- Lens Glare -->
          <path d="M 36,22 Q 48,14 60,24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" opacity="0.8"/>
          <!-- Paw Clasping Handle -->
          <ellipse cx="32" cy="48" rx="8" ry="10" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5" transform="rotate(-30 32 48)"/>
          <circle cx="28" cy="44" r="3" fill="${C.innerEar}"/>
        </g>
        <!-- Other paw resting on table -->
        <ellipse cx="138" cy="145" rx="10" ry="12" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <!-- Feet -->
        <ellipse cx="86" cy="182" rx="13" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
        <ellipse cx="128" cy="182" rx="13" ry="8" fill="url(#${id}_furGrad)" stroke="${C.furDark}" stroke-width="1.5"/>
      </svg>
    `
  };

  /**
   * Public renderer
   * @param {string} pose - One of: happy, sad, thinking, confused, excited, determined, sleeping, detective
   * @param {number|string} size - CSS size or numeric px (default 120)
   * @param {object} options - { className, extraStyles, id }
   */
  const render = (pose = "happy", size = 120, options = {}) => {
    const validPose = poses[pose] ? pose : "happy";
    const uniqueId = (options.id || "oyen_" + validPose + "_" + Math.random().toString(36).substring(2, 7)).replace(/[^a-zA-Z0-9_]/g, "_");
    const svgContent = poses[validPose](uniqueId);

    const styleStr = typeof size === "number" ? `width:${size}px;height:${size}px;` : `width:${size};height:${size};`;
    const extraStyle = options.extraStyles ? options.extraStyles : "";
    const cls = options.className ? `class="oyen-avatar oyen-${validPose} ${options.className}"` : `class="oyen-avatar oyen-${validPose}"`;

    return `<div ${cls} style="display:inline-block;${styleStr}${extraStyle}" data-pose="${validPose}">${svgContent}</div>`;
  };

  /**
   * Helper to set pose inside a container element
   */
  const setPose = (elementOrId, pose = "happy", size = null) => {
    const el = typeof elementOrId === "string" ? document.getElementById(elementOrId) : elementOrId;
    if (!el) return;
    const currentSize = size || el.dataset.size || 120;
    el.innerHTML = render(pose, currentSize);
    el.dataset.currentPose = pose;
  };

  return {
    render,
    setPose,
    poses: Object.keys(poses),
    colors: C
  };
})();

// Attach to window if in browser environment
if (typeof window !== "undefined") {
  window.OyenCharacter = OyenCharacter;
}

// Export for Node/CommonJS if needed
if (typeof module !== "undefined" && module.exports) {
  module.exports = OyenCharacter;
}

