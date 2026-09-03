const API_BASE = new URLSearchParams(location.search).get("apiBase") || "http://localhost:8000";
const params = new URLSearchParams(location.search);
const viewName = params.get("view") || (location.pathname.includes("forgot") ? "forgot" : location.pathname.includes("reset") ? "reset" : location.pathname.includes("change-password") ? "change" : "login");

document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${viewName}`));
document.querySelector(".back").style.display = viewName === "login" ? "none" : "block";

async function post(path, payload, form) {
  const response = await fetch(`${API_BASE}${path}`, { method: "POST", headers: { "Content-Type": "application/json", ...(localStorage.getItem("brasaland_token") ? { Authorization: `Bearer ${localStorage.getItem("brasaland_token")}` } : {}) }, body: JSON.stringify(payload) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "No se pudo completar la solicitud.");
  return data;
}

function feedback(form, message, error = false) {
  const element = form.querySelector("[data-feedback]");
  element.textContent = message;
  element.classList.toggle("error", error);
}

const forms = { login: document.querySelector('[data-form="login"]'), forgot: document.querySelector('[data-form="forgot"]'), reset: document.querySelector('[data-form="reset"]'), change: document.querySelector('[data-form="change"]') };
forms.login?.addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form)); try { const result = await post("/auth/login", data, form); localStorage.setItem("brasaland_token", result.access_token); feedback(form, "Acceso correcto."); } catch (error) { feedback(form, error.message, true); } });
forms.forgot?.addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const button = form.querySelector("button"); button.disabled = true; try { await post("/auth/forgot-password", Object.fromEntries(new FormData(form)), form); feedback(form, "Si esa dirección está registrada, recibirás un enlace en breve"); } catch (error) { feedback(form, "Si esa dirección está registrada, recibirás un enlace en breve"); } });
forms.reset?.addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form)); if (data.password !== data.confirmation) return feedback(form, "Las contraseñas no coinciden.", true); try { await post("/auth/reset-password", { token: params.get("token"), new_password: data.password }, form); location.href = "login/?reset=success"; } catch (error) { feedback(form, `${error.message} Solicita un enlace nuevo.`, true); } });
forms.change?.addEventListener("submit", async (event) => { event.preventDefault(); const form = event.currentTarget; const data = Object.fromEntries(new FormData(form)); if (data.password !== data.confirmation) return feedback(form, "Las contraseñas no coinciden.", true); try { await post("/auth/change-password", { current_password: data.current_password, new_password: data.password }, form); feedback(form, "Contraseña actualizada correctamente."); form.reset(); } catch (error) { feedback(form, error.message, true); } });
if (params.get("reset") === "success") feedback(forms.login, "Contraseña actualizada. Ya puedes iniciar sesión.");
