(function () {
  "use strict";

  if (window.DOMPurify) {
    window.DOMPurify.addHook("uponSanitizeAttribute", (_node, data) => {
      if (data.attrName === "style") {
        const height = data.attrValue.match(/^height:\s*(\d+(?:\.\d+)?)%;?$/);
        data.keepAttr = Boolean(height && Number(height[1]) <= 100);
      }
    });
  }

  function getToken() {
    try {
      return window.localStorage.getItem("brasaland_access_token")
        || window.localStorage.getItem("brasaland_token") || "";
    } catch {
      return "";
    }
  }

  function trustedApi(apiBase) {
    const target = new URL(apiBase, window.location.href);
    const localHosts = ["localhost", "127.0.0.1", "[::1]"];
    const local = localHosts.includes(window.location.hostname) && localHosts.includes(target.hostname);
    const previewHost = window.location.hostname.replace(/-\d+(\.(?:app\.)?github\.dev)$/, "-8000$1");
    const preview = previewHost !== window.location.hostname && target.hostname === previewHost;
    const configured = typeof window.BRASALAND_API_BASE === "string"
      && target.origin === new URL(window.BRASALAND_API_BASE, window.location.href).origin;
    const sameOrigin = target.origin === window.location.origin;
    if ((!local && target.protocol !== "https:") || (!local && !preview && !configured && !sameOrigin)) {
      throw new Error("Destino de API no autorizado");
    }
    return target;
  }

  function authHeaders(apiBase, supplied = {}) {
    trustedApi(apiBase);
    const headers = new Headers(supplied);
    headers.delete("X-API-Role");
    headers.delete("X-API-Token");
    headers.delete("Authorization");
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return Object.fromEntries(headers);
  }

  function sanitizeHTML(markup) {
    if (!window.DOMPurify) throw new Error("Sanitizador no disponible");
    return window.DOMPurify.sanitize(markup, {
      USE_PROFILES: { html: true },
      FORBID_TAGS: ["style", "form", "input", "iframe", "object", "embed"],
      FORBID_ATTR: ["srcdoc"],
    });
  }

  window.BrasalandSecurity = Object.freeze({ getToken, trustedApi, authHeaders, sanitizeHTML });
})();