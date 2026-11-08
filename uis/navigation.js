(function () {
  "use strict";

  const root = new URL("./", document.currentScript.src);
  const current = new URL(window.location.href);
  const integrated = root.pathname.startsWith("/platform/");
  const previewHost = current.hostname.replace(/-\d+(\.(?:app\.)?github\.dev)$/, "-8000$1");
  const defaultApi = integrated ? `${current.origin}/backend`
    : ["localhost", "127.0.0.1"].includes(current.hostname) ? `${current.protocol}//${current.hostname}:8000`
    : `${current.protocol}//${previewHost}`;
  window.BRASALAND_API_BASE = window.BRASALAND_API_BASE || defaultApi;
  window.NEXT_PUBLIC_TELEMETRY_ENDPOINT = `${window.BRASALAND_API_BASE}/telemetry/events`;
  let session = "";
  try {
    session = window.localStorage.getItem("brasaland_access_token") || window.localStorage.getItem("brasaland_token") || "";
    if (session) {
      window.localStorage.setItem("brasaland_token", session);
      window.localStorage.setItem("brasaland_access_token", session);
    }
  } catch {}
  const publicPage = current.pathname.startsWith(new URL("auth/", root).pathname)
    || current.pathname.startsWith(new URL("public-website/", root).pathname);
  const loginTarget = new URL("auth/", root);
  loginTarget.searchParams.set("next", current.pathname + current.search);
  loginTarget.searchParams.set("apiBase", window.BRASALAND_API_BASE);
  if (!session && !publicPage) {
    window.location.replace(loginTarget.href);
    return;
  }
  if (session && !publicPage) {
    fetch(`${window.BRASALAND_API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${session}` } })
      .then((response) => {
        if (response.status === 401) {
          window.localStorage.removeItem("brasaland_token");
          window.localStorage.removeItem("brasaland_access_token");
          window.location.replace(loginTarget.href);
        }
      }).catch(() => {});
  }
  const talent = new URL(current.origin);
  if (integrated) {
    talent.pathname = "/";
  } else if (["localhost", "127.0.0.1"].includes(talent.hostname)) {
    talent.port = "3000";
  } else if (/-\d+\.(?:app\.)?github\.dev$/.test(talent.hostname)) {
    talent.hostname = talent.hostname.replace(/-\d+(\.(?:app\.)?github\.dev)$/, "-3000$1");
  } else {
    talent.pathname = "/talent/";
  }
  const entries = [
    ["Inicio", "backoffice/"],
    ["Direccion", "executive-dashboard/"],
    ["Informes", "backoffice/reporting/"],
    ["Recepcion RFP", "backoffice/rfp-intake/"],
    ["Conocimiento", "knowledge-assistant/"],
    ["Fidelizacion", "marketing-loyalty-app/"],
    ["Talento", talent.href],
    ["Utilidades", new URL("/data-utils", talent).href],
    ["Sitio publico", "public-website/"],
    ["Mi cuenta", "auth/"],
  ];
  if (session) entries.splice(entries.length - 1, 0, ["Cambiar contrasena", "auth/account/change-password.html"]);
  const nav = document.createElement("nav");
  nav.setAttribute("aria-label", "Brasaland Digital");
  nav.style.cssText = "display:flex;flex-wrap:wrap;gap:8px 16px;padding:16px 24px;background:#fff;color:#172820;border-bottom:1px solid #ccd6d0;font:500 14px 'Space Grotesk',sans-serif;position:relative;z-index:10";
  for (const [label, path] of entries) {
    const link = document.createElement("a");
    const target = new URL(path, root);
    const apiBase = current.searchParams.get("apiBase") || window.BRASALAND_API_BASE;
    if (apiBase && target.origin === current.origin) target.searchParams.set("apiBase", apiBase);
    if (path === "auth/" && !current.pathname.startsWith(new URL("auth/", root).pathname)) {
      target.searchParams.set("next", current.pathname + current.search);
    }
    link.href = target.href;
    link.textContent = label;
    link.style.cssText = "color:inherit;padding:6px 0;text-decoration:underline;text-underline-offset:4px";
    if (target.origin === current.origin && target.pathname === current.pathname) {
      link.setAttribute("aria-current", "page");
      link.style.fontWeight = "700";
    }
    nav.append(link);
  }
  const logout = document.createElement("button");
  logout.type = "button";
  logout.textContent = "Cerrar sesion";
  logout.style.cssText = "background:transparent;border:0;color:inherit;font:inherit;cursor:pointer;padding:6px 0";
  logout.addEventListener("click", () => {
    window.localStorage.removeItem("brasaland_token");
    window.localStorage.removeItem("brasaland_access_token");
    window.location.assign(new URL("auth/", root).href);
  });
  if (session) nav.append(logout);
  document.body.prepend(nav);
})();