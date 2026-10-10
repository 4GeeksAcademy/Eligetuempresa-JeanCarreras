(() => {
  const SCHEMA_VERSION = "1.0.0";
  const APP_VERSION = "0.1.0";
  const BATCH_SIZE = 20;
  const FLUSH_INTERVAL_MS = 10000;
  const MAX_RETRIES = 3;
  const queue = [];
  let sessionId = getSessionId();
  let isFlushing = false;

  function createId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }

    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
      const random = Math.random() * 16 | 0;
      return (character === "x" ? random : (random & 0x3 | 0x8)).toString(16);
    });
  }

  function getSessionId() {
    try {
      const existingId = window.sessionStorage.getItem("brasaland_telemetry_session_id");
      if (existingId) {
        return existingId;
      }
      const newId = createId();
      window.sessionStorage.setItem("brasaland_telemetry_session_id", newId);
      return newId;
    } catch (_error) {
      return createId();
    }
  }

  function resolveEndpoint() {
    const configuredEndpoint = window.NEXT_PUBLIC_TELEMETRY_ENDPOINT;
    if (typeof configuredEndpoint === "string" && configuredEndpoint.trim()) {
      return configuredEndpoint.trim();
    }

    let apiBase = typeof window.BRASALAND_API_BASE === "string"
      ? window.BRASALAND_API_BASE.trim().replace(/\/$/, "")
      : "";
    const hostname = window.location.hostname;
    if (!apiBase && (hostname === "localhost" || hostname === "127.0.0.1")) {
      apiBase = `${window.location.protocol}//${hostname}:8000`;
    }
    if (!apiBase) {
      const hostMatch = hostname.match(/^(.*)-\d+(\.(?:app\.)?github\.dev)$/);
      if (hostMatch) {
        apiBase = `${window.location.protocol}//${hostMatch[1]}-8000${hostMatch[2]}`;
      }
    }
    return apiBase ? `${apiBase}/telemetry/events` : "";
  }

  const endpoint = resolveEndpoint();

  function track(eventType, properties) {
    if (eventType === "auth_login_succeeded") {
      sessionId = createId();
      try {
        window.sessionStorage.setItem("brasaland_telemetry_session_id", sessionId);
      } catch (_error) {
        // Keep the in-memory session when storage is blocked.
      }
    }

    queue.push({
      eventId: createId(),
      timestamp: new Date().toISOString(),
      sessionId,
      userId: null,
      event_type: eventType,
      schemaVersion: SCHEMA_VERSION,
      requestId: createId(),
      properties: properties || {},
    });

    if (queue.length >= BATCH_SIZE) {
      void flush();
    }
  }

  function wait(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  async function sendBatch(events) {
    for (let attempt = 0; attempt <= MAX_RETRIES; attempt += 1) {
      try {
        const response = await window.fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ events }),
          keepalive: true,
        });
        if (!response.ok) {
          throw new Error("Telemetry endpoint rejected the batch");
        }
        return true;
      } catch (_error) {
        if (attempt === MAX_RETRIES) {
          return false;
        }
        await wait(500 * (2 ** attempt));
      }
    }
    return false;
  }

  async function flush() {
    if (isFlushing || !endpoint || queue.length === 0) {
      return;
    }

    isFlushing = true;
    try {
      while (queue.length > 0) {
        const events = queue.splice(0, BATCH_SIZE);
        await sendBatch(events);
      }
    } finally {
      isFlushing = false;
    }
  }

  function flushWithBeacon() {
    if (!endpoint || queue.length === 0 || typeof navigator.sendBeacon !== "function") {
      return;
    }

    const events = queue.slice(0, BATCH_SIZE);
    const payload = new Blob([JSON.stringify({ events })], { type: "application/json" });
    if (navigator.sendBeacon(endpoint, payload)) {
      queue.splice(0, events.length);
    }
  }

  function clientPlatform() {
    return window.matchMedia("(max-width: 767px)").matches ? "mobile" : "desktop";
  }

  window.BrasalandTelemetry = Object.freeze({ track });
  window.setInterval(() => void flush(), FLUSH_INTERVAL_MS);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      flushWithBeacon();
    }
  });

  window.addEventListener("load", () => {
    const navigation = window.performance.getEntriesByType("navigation")[0];
    const duration = navigation ? navigation.loadEventEnd || navigation.duration : window.performance.now();
    track("frontend_page_load_recorded", {
      page_id: window.location.pathname.includes("/auth/") ? "auth" : "executive_dashboard",
      duration_ms: Math.max(0, duration),
      client_platform: clientPlatform(),
      app_version: APP_VERSION,
    });
  }, { once: true });

  window.addEventListener("error", (event) => {
    const errorClass = String(event.error?.name || "Error").replace(/[^A-Za-z0-9_.-]/g, "").slice(0, 64) || "Error";
    const pageId = window.location.pathname.includes("/auth/") ? "auth" : "executive_dashboard";
    track("frontend_error_captured", {
      error_fingerprint: `${errorClass.toLowerCase()}:window_error`,
      error_class: errorClass,
      page_id: pageId,
      app_version: APP_VERSION,
      fatal: Boolean(event.error),
      source_area: "window",
    });
  });

  window.addEventListener("unhandledrejection", () => {
    const pageId = window.location.pathname.includes("/auth/") ? "auth" : "executive_dashboard";
    track("frontend_error_captured", {
      error_fingerprint: "unhandledrejection:promise",
      error_class: "UnhandledRejection",
      page_id: pageId,
      app_version: APP_VERSION,
      fatal: false,
      source_area: "promise",
    });
  });
})();