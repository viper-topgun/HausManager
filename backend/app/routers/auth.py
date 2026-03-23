"""
Authentication & User Management router.

Users are stored in MongoDB collection 'users'.
Passwords are hashed with bcrypt via passlib.
Tokens are signed JWT (HS256).

Roles:  "admin"  – can manage users
        "viewer" – read-only access (can use the app but cannot manage users)

On first startup with an empty users collection an admin seed account is created:
  username: admin   password: admin123
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Password + JWT helpers
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _hash(password: str) -> str:
    return pwd_context.hash(password)


def _verify(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


async def _get_user(db, username: str):
    return await db.users.find_one({"username": username})


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Ungültige oder abgelaufene Anmeldedaten",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    db = get_db()
    user = await _get_user(db, username)
    if user is None:
        raise credentials_exc
    return user


async def require_admin(current_user=Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen das.")
    return current_user


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"  # "admin" | "viewer"
    display_name: str = ""


class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    display_name: Optional[str] = None


class UserOut(BaseModel):
    username: str
    role: str
    display_name: str
    created_at: Optional[str] = None


def _to_out(u: dict) -> UserOut:
    return UserOut(
        username=u["username"],
        role=u.get("role", "viewer"),
        display_name=u.get("display_name", ""),
        created_at=u.get("created_at"),
    )


# ---------------------------------------------------------------------------
# Seed: ensure at least one admin exists
# ---------------------------------------------------------------------------

async def seed_admin():
    db = get_db()
    count = await db.users.count_documents({})
    if count == 0:
        await db.users.insert_one({
            "username": "admin",
            "hashed_password": _hash("admin123"),
            "role": "admin",
            "display_name": "Administrator",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        print("[auth] Default admin user created (admin / admin123) – change password!")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_db()
    user = await _get_user(db, form_data.username)
    if not user or not _verify(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzername oder Passwort falsch",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = _create_token({"sub": user["username"], "role": user.get("role", "viewer")})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user["username"],
        role=user.get("role", "viewer"),
    )


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return _to_out(current_user)


# --- User management (admin only) ---

@router.get("/users", response_model=list[UserOut])
async def list_users(_admin=Depends(require_admin)):
    db = get_db()
    users = await db.users.find({}, {"hashed_password": 0}).to_list(None)
    return [_to_out(u) for u in users]


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, _admin=Depends(require_admin)):
    db = get_db()
    if await db.users.find_one({"username": body.username}):
        raise HTTPException(400, detail=f"Benutzer '{body.username}' existiert bereits")
    if body.role not in ("admin", "viewer"):
        raise HTTPException(400, detail="Rolle muss 'admin' oder 'viewer' sein")
    doc = {
        "username": body.username,
        "hashed_password": _hash(body.password),
        "role": body.role,
        "display_name": body.display_name or body.username,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return _to_out(doc)


@router.put("/users/{username}", response_model=UserOut)
async def update_user(username: str, body: UserUpdate, current_user=Depends(get_current_user)):
    # Admins can update anyone; non-admins can only change their own password
    is_admin = current_user.get("role") == "admin"
    is_self = current_user["username"] == username
    if not is_admin and not is_self:
        raise HTTPException(403, detail="Keine Berechtigung")
    if not is_admin and body.role is not None:
        raise HTTPException(403, detail="Nur Administratoren dürfen Rollen ändern")

    db = get_db()
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(404, detail="Benutzer nicht gefunden")

    update: dict = {}
    if body.password:
        update["hashed_password"] = _hash(body.password)
    if body.role and is_admin:
        if body.role not in ("admin", "viewer"):
            raise HTTPException(400, detail="Rolle muss 'admin' oder 'viewer' sein")
        update["role"] = body.role
    if body.display_name is not None:
        update["display_name"] = body.display_name

    if update:
        await db.users.update_one({"username": username}, {"$set": update})

    updated = await db.users.find_one({"username": username})
    return _to_out(updated)


@router.delete("/users/{username}", status_code=204)
async def delete_user(username: str, admin=Depends(require_admin)):
    if username == admin["username"]:
        raise HTTPException(400, detail="Sie können sich nicht selbst löschen")
    db = get_db()
    result = await db.users.delete_one({"username": username})
    if result.deleted_count == 0:
        raise HTTPException(404, detail="Benutzer nicht gefunden")
