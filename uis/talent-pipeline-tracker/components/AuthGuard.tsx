"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  AUTH_UNAUTHORIZED_EVENT,
  clearSession,
  getAccessToken,
} from "../services/auth";
import { getCurrentProfile } from "../services/authApi";

const PUBLIC_PATHS = new Set(["/login", "/register"]);

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [isSessionValid, setIsSessionValid] = useState(false);
  const isPublicPath = PUBLIC_PATHS.has(pathname);

  useEffect(() => {
    let isCurrent = true;
    const redirectToLogin = () => {
      clearSession();
      router.replace("/login");
    };

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, redirectToLogin);
    if (isPublicPath) {
      return () => window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, redirectToLogin);
    }

    if (!getAccessToken()) {
      redirectToLogin();
    } else {
      getCurrentProfile()
        .then(() => {
          if (isCurrent) {
            setIsSessionValid(true);
          }
        })
        .catch(redirectToLogin);
    }

    return () => {
      isCurrent = false;
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, redirectToLogin);
    };
  }, [isPublicPath, pathname, router]);

  return (
    <>
      <nav className="session-nav" aria-label="Brasaland Digital">
        <a href="/platform/backoffice/">Inicio</a>
        <a href="/platform/executive-dashboard/">Direccion</a>
        <a href="/platform/backoffice/reporting/">Informes</a>
        <a href="/platform/backoffice/rfp-intake/">Recepcion RFP</a>
        <a href="/platform/knowledge-assistant/">Conocimiento</a>
        <a href="/platform/marketing-loyalty-app/">Fidelizacion</a>
        <Link href="/">Talento</Link>
        <Link href="/data-utils">Utilidades</Link>
        <a href="/platform/public-website/">Sitio publico</a>
        {!isPublicPath && isSessionValid ? <>
          <Link href="/account/profile">Mi perfil</Link>
          <a href="/platform/auth/account/change-password.html">Cambiar contrasena</a>
          <button type="button" onClick={() => { clearSession(); router.replace("/login"); }}>Cerrar sesion</button>
        </> : <Link href="/login">Mi cuenta</Link>}
      </nav>
      {isPublicPath || isSessionValid ? children : <p role="status">Validando sesion...</p>}
    </>
  );
}