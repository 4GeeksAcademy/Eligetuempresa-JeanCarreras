"""
Módulo de autenticación JWT para Brasaland API.

Proporciona:
- Creación y verificación de tokens JWT (python-jose[cryptography])
- Hash y verificación de contraseñas (libpass[bcrypt])
- Dependencias de FastAPI para proteger endpoints
- Endpoint de login (/api/v1/auth/login)
"""

from datetime import datetime, timedelta, timezone
import os
from typing import Literal

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("BRASALAND_JWT_SECRET", "brasaland-jwt-secret-dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("BRASALAND_JWT_EXPIRE_MINUTES", "480"))  # 8 horas

# Roles del sistema
VALID_ROLES = frozenset({"admin", "executive", "operations", "finance"})

# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInDB(BaseModel):
    id: str
    username: str
    role: str
    hashed_password: str
    is_active: bool = True
    full_name: str = ""


class TokenData(BaseModel):
    username: str | None = None
    role: str | None = None


# ---------------------------------------------------------------------------
# Password hashing con passlib[bcrypt]
# ---------------------------------------------------------------------------

PWD_CONTEXT = bcrypt.using(rounds=12)


def hash_password(password: str) -> str:
    """Hashea una contraseña con bcrypt (12 rounds)."""
    return PWD_CONTEXT.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    return bcrypt.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT: creación y verificación
# ---------------------------------------------------------------------------


def create_access_token(
    username: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Crea un token JWT con la identidad y rol del usuario."""
    if role not in VALID_ROLES:
        raise ValueError(f"Rol inválido: {role}. Válidos: {', '.join(sorted(VALID_ROLES))}")

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    payload = {
        "sub": username,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "iss": "brasaland-api",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> TokenData:
    """Decodifica y valida un token JWT. Lanza HTTPException si es inválido."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], issuer="brasaland-api")
        username: str | None = payload.get("sub")
        role: str | None = payload.get("role")

        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Token inválido: faltan claims")

        if role not in VALID_ROLES:
            raise HTTPException(status_code=401, detail=f"Token inválido: rol desconocido '{role}'")

        return TokenData(username=username, role=role)

    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Token inválido o expirado: {exc}") from exc


# ---------------------------------------------------------------------------
# Usuarios por defecto (seed)
# ---------------------------------------------------------------------------

DEFAULT_USERS: list[dict[str, str]] = [
    {
        "id": "usr-admin-001",
        "username": "admin",
        "password": "brasaland-admin",
        "role": "admin",
        "full_name": "Administrador Brasaland",
    },
    {
        "id": "usr-exec-001",
        "username": "mariana",
        "password": "brasaland-exec",
        "role": "executive",
        "full_name": "Mariana Restrepo",
    },
    {
        "id": "usr-ops-001",
        "username": "felipe",
        "password": "brasaland-ops",
        "role": "operations",
        "full_name": "Felipe Guerrero",
    },
    {
        "id": "usr-fin-001",
        "username": "lucia",
        "password": "brasaland-fin",
        "role": "finance",
        "full_name": "Lucia Fernandez",
    },
]

# Cache en memoria de usuarios (se carga al iniciar)
_users_cache: dict[str, UserInDB] = {}


def init_users(db_users: list[dict] | None = None) -> list[UserInDB]:
    """Inicializa el cache de usuarios y devuelve la lista de usuarios creados."""
    global _users_cache
    _users_cache = {}
    users_created: list[UserInDB] = []

    source = db_users or DEFAULT_USERS

    for u in source:
        user = UserInDB(
            id=u["id"],
            username=u["username"],
            role=u["role"],
            hashed_password=hash_password(u["password"]),
            full_name=u.get("full_name", ""),
        )
        _users_cache[user.username] = user
        users_created.append(user)

    return users_created


def get_user_by_username(username: str) -> UserInDB | None:
    """Busca un usuario por nombre de usuario en el cache."""
    return _users_cache.get(username)


def authenticate_user(username: str, password: str) -> UserInDB | None:
    """Autentica un usuario por username + password. Retorna el usuario o None."""
    user = get_user_by_username(username)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ---------------------------------------------------------------------------
# Dependencias FastAPI
# ---------------------------------------------------------------------------

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_jwt(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_token: str | None = Header(default=None),
    x_api_role: str | None = Header(default=None),
) -> TokenData:
    """
    Dependencia de FastAPI que extrae el usuario autenticado.

    Soporta dos modos:
    1. **JWT Bearer Token** (preferido): `Authorization: Bearer <token>`
    2. **Legacy token por rol** (backwards-compatible): `X-API-Token + X-API-Role`
    """
    # --- Modo 1: JWT Bearer ---
    if credentials is not None:
        return decode_access_token(credentials.credentials)

    # --- Modo 2: Legacy role tokens ---
    if x_api_token is not None and x_api_role is not None:
        if x_api_role not in VALID_ROLES:
            raise HTTPException(status_code=403, detail="Role no válido")

        role_tokens = _resolve_role_tokens()
        expected_token = role_tokens.get(x_api_role)
        if expected_token is None or x_api_token != expected_token:
            raise HTTPException(status_code=401, detail="Token de rol inválido")

        return TokenData(username=f"legacy-{x_api_role}", role=x_api_role)

    raise HTTPException(
        status_code=401,
        detail="Autenticación requerida. Usa Authorization: Bearer <token> o X-API-Token + X-API-Role",
    )


def _resolve_role_tokens() -> dict[str, str]:
    """Resuelve tokens de rol desde variables de entorno o defaults."""
    return {
        "admin": os.getenv("BRASALAND_ADMIN_TOKEN", "brasaland-admin-token"),
        "executive": os.getenv("BRASALAND_EXECUTIVE_TOKEN", "brasaland-executive-token"),
        "operations": os.getenv("BRASALAND_OPERATIONS_TOKEN", "brasaland-operations-token"),
        "finance": os.getenv("BRASALAND_FINANCE_TOKEN", "brasaland-finance-token"),
    }


def require_roles(allowed_roles: set[str]):
    """
    Factory de dependencia que valida que el usuario tenga uno de los roles permitidos.

    Uso:
        @app.get("/ruta")
        def mi_endpoint(role: str = Depends(require_roles({"admin", "operations"}))):
            ...
    """
    async def role_validator(
        current_user: TokenData = Depends(get_current_user_jwt),
    ) -> str:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Se requiere uno de los roles: {', '.join(sorted(allowed_roles))}",
            )
        return current_user.role

    return role_validator


# ---------------------------------------------------------------------------
# Endpoints de autenticación
# ---------------------------------------------------------------------------

# Para evitar import circular, los endpoints se registran desde main.py
# usando app.include_router o directamente. Exportamos un router.

from fastapi import APIRouter

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión y obtener token JWT",
    description="Autentica un usuario con username y password. Devuelve un token JWT válido para usar en el header Authorization: Bearer <token>.",
)
def login(payload: LoginRequest) -> TokenResponse:
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    token = create_access_token(
        username=user.username,
        role=user.role,
        expires_delta=timedelta(seconds=expires_in),
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        role=user.role,
    )


@auth_router.get(
    "/me",
    response_model=dict,
    summary="Obtener información del usuario autenticado",
)
async def whoami(current_user: TokenData = Depends(get_current_user_jwt)) -> dict:
    return {
        "username": current_user.username,
        "role": current_user.role,
        "authenticated": True,
    }