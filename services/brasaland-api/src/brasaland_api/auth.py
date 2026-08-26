"""
Módulo de autenticación JWT para Brasaland API.

Proporciona:
- Creación y verificación de tokens JWT (python-jose[cryptography])
- Hash y verificación de contraseñas (libpass[bcrypt])
- Dependencia get_current_user con OAuth2PasswordBearer
- Endpoints /auth/login y /auth/me
- CRUD completo de usuarios (/users)
- CRUD de perfiles (/profiles)
"""

import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.hash import bcrypt as bcrypt_hasher
from pydantic import BaseModel, EmailStr
from tinydb import TinyDB, Query

load_dotenv()

# ---------------------------------------------------------------------------
# Configuración desde variables de entorno
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("BRASALAND_JWT_SECRET", "brasaland-jwt-secret-dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("BRASALAND_JWT_EXPIRE_MINUTES", "480"))
DB_PATH = os.getenv("BRASALAND_DB_PATH", "brasaland_db.json")

# ---------------------------------------------------------------------------
# Enumeración de roles
# ---------------------------------------------------------------------------


class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    user = "user"


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------


class UserInDB(BaseModel):
    """Modelo de usuario almacenado en TinyDB."""
    id: str
    email: str
    hashed_password: str
    is_active: bool = True
    role: Role = Role.user
    created_at: str


class UserCreate(BaseModel):
    """Payload para crear un nuevo usuario. Acepta campos opcionales de perfil."""
    email: str
    password: str
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class UserUpdate(BaseModel):
    """Payload para actualizar credenciales de usuario."""
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[Role] = None


class UserResponse(BaseModel):
    """Respuesta pública de un usuario (sin password)."""
    id: str
    email: str
    is_active: bool
    role: Role
    created_at: str


class Profile(BaseModel):
    """Modelo de perfil vinculado 1:1 a User mediante user_id."""
    id: str
    user_id: str
    name: str = ""
    phone: str = ""
    address: str = ""



class ProfileUpdate(BaseModel):
    """Payload para actualizar perfil."""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class TokenResponse(BaseModel):
    """Respuesta de login exitoso."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str


# ---------------------------------------------------------------------------
# TinyDB setup
# ---------------------------------------------------------------------------

_db_instance: Optional[TinyDB] = None


def get_db() -> TinyDB:
    """Retorna la instancia singleton de TinyDB."""
    global _db_instance
    if _db_instance is None:
        _db_instance = TinyDB(DB_PATH)
    return _db_instance


def get_users_table():
    return get_db().table("users")


def get_profiles_table():
    return get_db().table("profiles")


# ---------------------------------------------------------------------------
# Password hashing con passlib[bcrypt]
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return bcrypt_hasher.using(rounds=12).hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt_hasher.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT: creación y verificación
# ---------------------------------------------------------------------------


def create_access_token(email: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": email,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "iss": "brasaland-api",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], issuer="brasaland-api")
        email: str | None = payload.get("sub")
        role: str | None = payload.get("role")

        if email is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido: faltan claims",
            )

        try:
            Role(role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token inválido: rol desconocido '{role}'",
            )

        return payload

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido o expirado: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# OAuth2PasswordBearer
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """
    Dependencia de FastAPI que extrae y valida el token JWT,
    recupera el usuario de TinyDB y lo retorna.
    Lanza 401 si algo falla.
    """
    payload = decode_access_token(token)
    email = payload.get("sub")

    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: email no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ---------------------------------------------------------------------------
# Servicios de usuario
# ---------------------------------------------------------------------------


def create_user_in_db(user_data: UserCreate) -> UserInDB:
    """Crea un usuario en TinyDB con password hasheado. Verifica email único."""
    users_table = get_users_table()
    UserQuery = Query()

    if users_table.get(UserQuery.email == user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El email '{user_data.email}' ya está registrado",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    doc_id = users_table.insert({
        "email": user_data.email,
        "hashed_password": hash_password(user_data.password),
        "is_active": True,
        "role": Role.user.value,
        "created_at": now_iso,
    })

    # Crear perfil vinculado si se proporcionaron datos opcionales
    create_profile_for_user(
        str(doc_id),
        name=user_data.name or "",
        phone=user_data.phone or "",
        address=user_data.address or "",
    )

    return UserInDB(
        id=str(doc_id),
        email=user_data.email,
        hashed_password="***redacted***",
        is_active=True,
        role=Role.user,
        created_at=now_iso,
    )


def get_user_by_email(email: str) -> UserInDB | None:
    users_table = get_users_table()
    UserQuery = Query()
    user_doc = users_table.get(UserQuery.email == email)

    if user_doc is None:
        return None

    return UserInDB(
        id=str(user_doc.doc_id),
        email=user_doc["email"],
        hashed_password=user_doc["hashed_password"],
        is_active=user_doc.get("is_active", True),
        role=Role(user_doc.get("role", Role.user.value)),
        created_at=user_doc.get("created_at", ""),
    )


def get_user_by_id(user_id: str) -> UserInDB | None:
    users_table = get_users_table()
    try:
        doc_id = int(user_id)
    except ValueError:
        return None

    user_doc = users_table.get(doc_id=doc_id)
    if user_doc is None:
        return None

    return UserInDB(
        id=str(doc_id),
        email=user_doc["email"],
        hashed_password=user_doc["hashed_password"],
        is_active=user_doc.get("is_active", True),
        role=Role(user_doc.get("role", Role.user.value)),
        created_at=user_doc.get("created_at", ""),
    )


def get_all_users() -> list[UserInDB]:
    users_table = get_users_table()
    users = []
    for item in users_table:
        users.append(UserInDB(
            id=str(item.doc_id),
            email=item["email"],
            hashed_password=item["hashed_password"],
            is_active=item.get("is_active", True),
            role=Role(item.get("role", Role.user.value)),
            created_at=item.get("created_at", ""),
        ))
    return users


def authenticate_user(email: str, password: str) -> UserInDB | None:
    """Autentica un usuario por email + password. Retorna el usuario o None."""
    user = get_user_by_email(email)
    if user is None:
        return None

    # Obtener el hash real desde TinyDB para verificar
    users_table = get_users_table()
    UserQuery = Query()
    user_doc = users_table.get(UserQuery.email == email)

    if not verify_password(password, user_doc["hashed_password"]):
        return None

    return user


def update_user_in_db(user_id: str, update_data: UserUpdate, current_user: UserInDB) -> UserInDB:
    """Actualiza un usuario. Solo el propio usuario o un admin."""
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if current_user.id != user_id and current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para actualizar este usuario",
        )

    if update_data.role is not None and current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un admin puede cambiar el rol",
        )

    users_table = get_users_table()
    doc_id = int(user_id)
    updates = {}

    if update_data.email is not None:
        UserQuery = Query()
        existing = users_table.get(UserQuery.email == update_data.email)
        if existing is not None and existing.doc_id != doc_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El email '{update_data.email}' ya está registrado",
            )
        updates["email"] = update_data.email

    if update_data.password is not None:
        updates["hashed_password"] = hash_password(update_data.password)

    if update_data.role is not None:
        updates["role"] = update_data.role.value

    if updates:
        users_table.update(updates, doc_ids=[doc_id])

    return get_user_by_id(user_id)


def delete_user_in_db(user_id: str, current_user: UserInDB) -> None:
    """Elimina un usuario y su perfil vinculado de TinyDB."""
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if current_user.id != user_id and current_user.role != Role.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este usuario",
        )

    users_table = get_users_table()
    profiles_table = get_profiles_table()

    # Eliminar perfil vinculado
    ProfileQuery = Query()
    profile_docs = profiles_table.search(ProfileQuery.user_id == user_id)
    for p_doc in profile_docs:
        profiles_table.remove(doc_ids=[p_doc.doc_id])

    # Eliminar usuario
    users_table.remove(doc_ids=[int(user_id)])


# ---------------------------------------------------------------------------
# Servicios de perfil
# ---------------------------------------------------------------------------


def create_profile_for_user(user_id: str, name: str = "", phone: str = "", address: str = "") -> Profile:
    """Crea un perfil para un usuario. Si ya existe, lo retorna."""
    profiles_table = get_profiles_table()
    ProfileQuery = Query()

    existing = profiles_table.get(ProfileQuery.user_id == user_id)
    if existing is not None:
        return Profile(
            id=str(existing.doc_id),
            user_id=existing["user_id"],
            name=existing.get("name", ""),
            phone=existing.get("phone", ""),
            address=existing.get("address", ""),
        )

    doc_id = profiles_table.insert({
        "user_id": user_id,
        "name": name,
        "phone": phone,
        "address": address,
    })

    return Profile(
        id=str(doc_id),
        user_id=user_id,
        name=name,
        phone=phone,
        address=address,
    )


def get_profile_by_user_id(user_id: str) -> Profile | None:
    profiles_table = get_profiles_table()
    ProfileQuery = Query()
    profile_doc = profiles_table.get(ProfileQuery.user_id == user_id)

    if profile_doc is None:
        return None

    return Profile(
        id=str(profile_doc.doc_id),
        user_id=profile_doc["user_id"],
        name=profile_doc.get("name", ""),
        phone=profile_doc.get("phone", ""),
        address=profile_doc.get("address", ""),
    )


def update_profile_in_db(user_id: str, update_data: ProfileUpdate) -> Profile:
    """Actualiza el perfil de un usuario. Crea uno si no existe."""
    profiles_table = get_profiles_table()
    ProfileQuery = Query()
    profile_doc = profiles_table.get(ProfileQuery.user_id == user_id)

    if profile_doc is None:
        return create_profile_for_user(
            user_id=user_id,
            name=update_data.name or "",
            phone=update_data.phone or "",
            address=update_data.address or "",
        )

    updates = {}
    if update_data.name is not None:
        updates["name"] = update_data.name
    if update_data.phone is not None:
        updates["phone"] = update_data.phone
    if update_data.address is not None:
        updates["address"] = update_data.address

    if updates:
        profiles_table.update(updates, doc_ids=[profile_doc.doc_id])

    return get_profile_by_user_id(user_id)


# ---------------------------------------------------------------------------
# Seed de usuarios por defecto
# ---------------------------------------------------------------------------

DEFAULT_SEED_USERS = [
    {"email": "admin@brasaland.com", "password": "brasaland-admin", "role": Role.admin, "name": "Admin Brasaland"},
    {"email": "manager@brasaland.com", "password": "brasaland-manager", "role": Role.manager, "name": "Manager Brasaland"},
    {"email": "user@brasaland.com", "password": "brasaland-user", "role": Role.user, "name": "Usuario Brasaland"},
]


def init_seed_users():
    """Inicializa los usuarios por defecto si la tabla está vacía."""
    users_table = get_users_table()
    if len(users_table) > 0:
        return

    for seed in DEFAULT_SEED_USERS:
        doc_id = users_table.insert({
            "email": seed["email"],
            "hashed_password": hash_password(seed["password"]),
            "is_active": True,
            "role": seed["role"].value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        create_profile_for_user(str(doc_id), name=seed.get("name", ""))


# ---------------------------------------------------------------------------
# Endpoints de autenticación
# ---------------------------------------------------------------------------

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description="Autentica un usuario con email y password. Devuelve un token JWT.",
)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """
    Login con OAuth2 Password flow.
    Envía email en el campo 'username' y password en 'password'.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    token = create_access_token(
        email=user.email,
        role=user.role.value,
        expires_delta=timedelta(seconds=expires_in),
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        role=user.role.value,
    )


@auth_router.get(
    "/me",
    summary="Obtener información del usuario autenticado",
)
async def whoami(current_user: UserInDB = Depends(get_current_user)) -> dict:
    """Devuelve el email, rol y perfil del usuario autenticado."""
    profile = get_profile_by_user_id(current_user.id)
    return {
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "profile": profile.model_dump() if profile else None,
    }


# ---------------------------------------------------------------------------
# Endpoints de usuarios (/users)
# ---------------------------------------------------------------------------

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate):
    """Registrar un nuevo usuario (público). Crea perfil vinculado si se envían datos opcionales."""
    user = create_user_in_db(payload)
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        role=user.role,
        created_at=user.created_at,
    )


@users_router.get("", response_model=list[UserResponse])
def list_users(current_user: UserInDB = Depends(get_current_user)):
    """Listar todos los usuarios (protegida)."""
    users = get_all_users()
    return [
        UserResponse(id=u.id, email=u.email, is_active=u.is_active, role=u.role, created_at=u.created_at)
        for u in users
    ]


@users_router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Obtener un usuario por ID (protegida)."""
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        role=user.role,
        created_at=user.created_at,
    )


@users_router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, payload: UserUpdate, current_user: UserInDB = Depends(get_current_user)):
    """Actualizar usuario. Solo el propio usuario o un admin. Solo admin cambia rol."""
    user = update_user_in_db(user_id, payload, current_user)
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        role=user.role,
        created_at=user.created_at,
    )


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, current_user: UserInDB = Depends(get_current_user)):
    """Eliminar un usuario y su perfil. Solo el propio usuario o un admin."""
    delete_user_in_db(user_id, current_user)


# ---------------------------------------------------------------------------
# Endpoints de perfiles (/profiles)
# ---------------------------------------------------------------------------

profiles_router = APIRouter(prefix="/profiles", tags=["profiles"])


@profiles_router.get("/me")
def get_my_profile(current_user: UserInDB = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado (protegida)."""
    profile = get_profile_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    return profile


@profiles_router.put("/me")
def update_my_profile(payload: ProfileUpdate, current_user: UserInDB = Depends(get_current_user)):
    """Actualiza el perfil del usuario autenticado. Solo el dueño puede modificarlo."""
    profile = update_profile_in_db(current_user.id, payload)
    return profile


# ---------------------------------------------------------------------------
# Compatibilidad: require_roles y role tokens (para rutas existentes)
# ---------------------------------------------------------------------------
# El sistema principal usa get_current_user + OAuth2. Pero las rutas existentes
# del monorepo usaban require_roles(...) con X-API-Role + X-API-Token.
# Mantenemos estos helpers para no romper 50+ endpoints existentes.
# Ahora require_roles se basa en get_current_user (JWT) y también acepta
# la verificación de X-API-Role + X-API-Token si no hay bearer token.

LEGACY_ROLE_TOKENS: dict[str, str] = {
    "admin": os.getenv("BRASALAND_ADMIN_TOKEN", "brasaland-admin-token"),
    "executive": os.getenv("BRASALAND_EXECUTIVE_TOKEN", "brasaland-executive-token"),
    "operations": os.getenv("BRASALAND_OPERATIONS_TOKEN", "brasaland-operations-token"),
    "finance": os.getenv("BRASALAND_FINANCE_TOKEN", "brasaland-finance-token"),
    # Nuevos roles del proyecto
    "manager": os.getenv("BRASALAND_MANAGER_TOKEN", "brasaland-manager-token"),
    "user": os.getenv("BRASALAND_USER_TOKEN", "brasaland-user-token"),
}


def _resolve_role_tokens() -> dict[str, str]:
    """Resuelve tokens por rol desde variables de entorno o defaults."""
    return dict(LEGACY_ROLE_TOKENS)


def require_roles(allowed_roles: set[str]):
    """
    Factory de dependencia que valida que el usuario tenga uno de los roles permitidos.

    Soporta dos modos:
    1. **JWT Bearer token** (recomendado) — extrae el token del header Authorization
       y lo valida contra TinyDB.
    2. **Legacy X-API-Role + X-API-Token** — para clientes que no usan JWT.

    Uso:
        @app.get("/ruta")
        def mi_endpoint(role: str = Depends(require_roles({"admin", "operations"}))):
            ...
    """
    async def role_validator(
        authorization: str | None = Header(default=None, alias="Authorization"),
        x_api_role: str | None = Header(default=None, alias="X-API-Role"),
        x_api_token: str | None = Header(default=None, alias="X-API-Token"),
    ) -> str:
        # 1. Intentar con JWT Bearer token
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            try:
                payload = decode_access_token(token)
                email = payload.get("sub")
                if email:
                    user = get_user_by_email(email)
                    if user and user.role.value in allowed_roles:
                        return user.role.value
            except HTTPException:
                pass  # Fall through to legacy check

        # 2. Fallback legacy: X-API-Role + X-API-Token
        if x_api_role is not None:
            role_tokens = _resolve_role_tokens()
            expected_token = role_tokens.get(x_api_role)
            if expected_token is not None and x_api_token == expected_token:
                if x_api_role in allowed_roles:
                    return x_api_role
                # Rol válido pero no permitido en este endpoint
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Se requiere uno de los roles: {', '.join(sorted(allowed_roles))}",
                )
            # Token inválido para el rol = 401 (no autenticado)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido para el rol especificado",
            )

        # Sin ningún header de autenticación = 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere autenticación",
        )

    return role_validator