"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { login } from "../../services/authApi";
import { saveAccessToken } from "../../services/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      saveAccessToken(await login(email.trim(), password));
      router.replace("/");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "No se pudo iniciar sesion.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <form onSubmit={onSubmit} className="auth-form">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--brand-2)]">Brasaland | Personas y Cultura</p>
        <h1>Iniciar sesion</h1>
        <label>Correo electronico<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>Contrasena<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {error ? <p className="feedback feedback-error" role="alert">{error}</p> : null}
        <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Ingresando..." : "Ingresar"}</button>
        <p className="auth-switch">No tienes una cuenta? <Link href="/register">Registrate</Link></p>
      </form>
    </main>
  );
}