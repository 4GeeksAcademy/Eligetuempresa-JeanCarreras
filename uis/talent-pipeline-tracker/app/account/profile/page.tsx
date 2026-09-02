"use client";

import { useEffect, useState } from "react";
import { getCurrentProfile, updateCurrentProfile } from "../../../services/authApi";
import type { UserProfile } from "../../../services/auth";

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    getCurrentProfile().then(setProfile).catch((requestError) => {
      setError(requestError instanceof Error ? requestError.message : "No se pudo cargar el perfil.");
    });
  }, []);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!profile) return;
    setError(""); setMessage(""); setIsSaving(true);
    try {
      const formData = new FormData(event.currentTarget);
      const updated = await updateCurrentProfile({
        name: String(formData.get("name") ?? "").trim() || null,
        phone: String(formData.get("phone") ?? "").trim() || null,
        address: String(formData.get("address") ?? "").trim() || null,
      });
      setProfile(updated); setMessage("Perfil actualizado correctamente.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo actualizar el perfil.");
    } finally { setIsSaving(false); }
  };

  return <main className="auth-page"><section className="auth-form">
    <p className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--brand-2)]">Cuenta</p><h1>Mi perfil</h1>
    {!profile && !error ? <p className="feedback feedback-info">Cargando perfil...</p> : null}
    {error ? <p className="feedback feedback-error" role="alert">{error}</p> : null}
    {profile ? <form onSubmit={onSubmit}>
      <label>Correo electronico<input value={profile.email} disabled /></label>
      <label>Nombre<input name="name" defaultValue={profile.name ?? ""} /></label>
      <label>Telefono<input name="phone" defaultValue={profile.phone ?? ""} /></label>
      <label>Direccion<input name="address" defaultValue={profile.address ?? ""} /></label>
      {message ? <p className="feedback feedback-success">{message}</p> : null}
      <button type="submit" disabled={isSaving}>{isSaving ? "Guardando..." : "Guardar cambios"}</button>
    </form> : null}
  </section></main>;
}