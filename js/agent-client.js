/** Oyen Math - client for the Python LangGraph agent service (POST /api/agent). */
const OyenAgentAPI = (() => {
  async function coach(payload) {
    try {
      const r = await fetch("/api/agent", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const j = await r.json();
      return r.ok && !j.error ? j : { error: j.error || "server " + r.status };
    } catch (e) {
      return { error: e.message };
    }
  }
  return { coach };
})();
if (typeof window !== "undefined") window.OyenAgentAPI = OyenAgentAPI;
if (typeof module !== "undefined" && module.exports) module.exports = OyenAgentAPI;
