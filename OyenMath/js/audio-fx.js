/**
 * Oyen Math - Web Audio Procedural Sound Synthesizer
 * Generates cute cat meows, success chimes, and alert tones with zero external files.
 */

const OyenAudio = (() => {
  let ctx = null;
  let enabled = true;

  function getContext() {
    if (!ctx && typeof window !== "undefined") {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        ctx = new AudioCtx();
      }
    }
    if (ctx && ctx.state === "suspended") {
      ctx.resume();
    }
    return ctx;
  }

  function toggle() {
    enabled = !enabled;
    return enabled;
  }

  function isEnabled() {
    return enabled;
  }

  /**
   * Play a cute friendly meow sound
   */
  function playMeow() {
    if (!enabled) return;
    const ac = getContext();
    if (!ac) return;

    const osc = ac.createOscillator();
    const gain = ac.createGain();

    osc.type = "sine";
    const now = ac.currentTime;

    // Pitch envelope of a friendly kitten meow: rise then gentle fall
    osc.frequency.setValueAtTime(450, now);
    osc.frequency.exponentialRampToValueAtTime(780, now + 0.12);
    osc.frequency.exponentialRampToValueAtTime(520, now + 0.35);

    // Volume envelope
    gain.gain.setValueAtTime(0.01, now);
    gain.gain.linearRampToValueAtTime(0.2, now + 0.08);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

    osc.connect(gain);
    gain.connect(ac.destination);

    osc.start(now);
    osc.stop(now + 0.45);
  }

  /**
   * Play success chime
   */
  function playSuccess() {
    if (!enabled) return;
    const ac = getContext();
    if (!ac) return;

    const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
    notes.forEach((freq, i) => {
      const osc = ac.createOscillator();
      const gain = ac.createGain();
      osc.type = "triangle";
      const now = ac.currentTime + i * 0.08;

      osc.frequency.setValueAtTime(freq, now);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

      osc.connect(gain);
      gain.connect(ac.destination);

      osc.start(now);
      osc.stop(now + 0.4);
    });
  }

  /**
   * Play incorrect / warning tone
   */
  function playWrong() {
    if (!enabled) return;
    const ac = getContext();
    if (!ac) return;

    const osc = ac.createOscillator();
    const gain = ac.createGain();

    osc.type = "sawtooth";
    const now = ac.currentTime;

    osc.frequency.setValueAtTime(220, now);
    osc.frequency.linearRampToValueAtTime(140, now + 0.25);

    gain.gain.setValueAtTime(0.12, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

    osc.connect(gain);
    gain.connect(ac.destination);

    osc.start(now);
    osc.stop(now + 0.35);
  }

  /**
   * Play heart recovery chime
   */
  function playRecovery() {
    if (!enabled) return;
    const ac = getContext();
    if (!ac) return;

    const notes = [440, 554.37, 659.25, 880];
    notes.forEach((freq, i) => {
      const osc = ac.createOscillator();
      const gain = ac.createGain();
      osc.type = "sine";
      const now = ac.currentTime + i * 0.1;

      osc.frequency.setValueAtTime(freq, now);
      gain.gain.setValueAtTime(0.18, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);

      osc.connect(gain);
      gain.connect(ac.destination);

      osc.start(now);
      osc.stop(now + 0.55);
    });
  }

  return {
    playMeow,
    playSuccess,
    playWrong,
    playRecovery,
    toggle,
    isEnabled
  };
})();

if (typeof window !== "undefined") {
  window.OyenAudio = OyenAudio;
}

