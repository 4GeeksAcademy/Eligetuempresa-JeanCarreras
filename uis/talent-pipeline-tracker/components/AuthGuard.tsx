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

  if (!isPublicPath && !isSessionValid) {
    return null;
  }

  if (isPublicPath) {
    return children;
  }

  return (
    <>
      <nav className="session-nav" aria-label="Sesion">
        <Link href="/account/profile">Mi perfil</Link>
        <button type="button" onClick={() => { clearSession(); router.replace("/login"); }}>
          Cerrar sesion
        </button>
      </nav>
      {children}
    </>
  );
}