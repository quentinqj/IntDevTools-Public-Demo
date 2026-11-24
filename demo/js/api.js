/* =====================================================================
   IntDevTools Public Demo v2 · API 客户端
   - 默认同源调用后端（npm run 后由 Flask 提供 /api 与静态页）
   - 支持 ?api=http://127.0.0.1:8000 或 localStorage.idt_api_base 覆盖
   - 所有失败都抛错并携带可读信息（前端不做假确认）
   ===================================================================== */
(function () {
  "use strict";

  function detectBase() {
    var fromQuery = new URLSearchParams(location.search).get("api");
    if (fromQuery) return fromQuery.replace(/\/+$/, "");
    var stored = null;
    try { stored = localStorage.getItem("idt_api_base"); } catch (e) {}
    if (stored) return stored.replace(/\/+$/, "");
    if (location.protocol === "file:") return "http://127.0.0.1:8000";
    return ""; // 同源
  }

  var base = detectBase();

  async function request(path, opts) {
    opts = opts || {};
    var url = base + path;
    var resp;
    try {
      resp = await fetch(url, {
        method: opts.method || "GET",
        headers: opts.body ? { "Content-Type": "application/json" } : {},
        body: opts.body ? JSON.stringify(opts.body) : undefined,
      });
    } catch (e) {
      throw new Error("无法连接后端（" + url + "）。请先运行 backend/start.bat 或 start.sh。");
    }
    var payload = null;
    try { payload = await resp.json(); } catch (e) {}
    if (!payload || payload.code !== 0) {
      var msg = (payload && payload.message) || ("HTTP " + resp.status);
      throw new Error(msg);
    }
    return payload.data;
  }

  window.IDT_API = {
    base: base,
    get: function (path) { return request(path); },
    post: function (path, body) { return request(path, { method: "POST", body: body }); },
  };
})();
