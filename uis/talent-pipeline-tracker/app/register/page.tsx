"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { saveAccessToken } from "../../services/auth";
import { login, register } from "../../services/authApi";

type FormValues = { email: string; password: string; name: string; phone: string; address: string };
const initialForm: FormValues = { email: "", password: "", name: "", phone: "", address: "" };

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState(initialForm);
  const [errors, setErrors] = useState<Partial<FormValues>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const setField = (field: keyof FormValues, value: string) => setForm((current) => ({ ...current, [field]: value }));

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors: Partial<FormValues> = {};
    if (!form.email.trim()) nextErrors.email = "El correo es obligatorio.";
    if (form.password.length < 8) nextErrors.password = "La contrasena debe tener al menos 8 caracteres.";
    if (Object.keys(nextErrors).length) { setErrors(nextErrors); return; }

    setErrors({});
    setIsSubmitting(true);
    try {
      await register({
        email: form.email.trim(), password: form.password, name: form.name.trim() || undefined,
        phone: form.phone.trim() || undefined, address: form.address.trim() || undefined,
      });
      saveAccessToken(await login(form.email.trim(), form.password));
      router.replace("/");
    } catch (requestError) {
      setErrors({ email: requestError instanceof Error ? requestError.message : "No se pudo crear la cuenta." });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="auth-page">
      <form onSubmit={onSubmit} className="auth-form">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-[var(--brand-2)]">Brasaland | Personas y Cultura</p>
        <h1>Crear cuenta</h1>
        <label>Correo electronico<input required type="email" autoComplete="email" value={form.email} onChange={(event) => setField("email", event.target.value)} />{errors.email ? <span role="alert">{errors.email}</span> : null}</label>
        <label>Contrasena<input required minLength={8} type="password" autoComplete="new-password" value={form.password} onChange={(event) => setField("password", event.target.value)} />{errors.password ? <span role="alert">{errors.password}</span> : null}</label>
        <label>Nombre<input autoComplete="name" value={form.name} onChange={(event) => setField("name", event.target.value)} /></label>
        <label>Telefono<input autoComplete="tel" value={form.phone} onChange={(event) => setField("phone", event.target.value)} /></label>
        <label>Direccion<input autoComplete="street-address" value={form.address} onChange={(event) => setField("address", event.target.value)} /></label>
        <button type="submit" disabled={isSubmitting}>{isSubmitting ? "Creando cuenta..." : "Crear cuenta"}</button>
        <p className="auth-switch">Ya tienes cuenta? <Link href="/login">Inicia sesion</Link></p>
      </form>
    </main>
  );
}