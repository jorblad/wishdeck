"""Authentication: local (JWT cookie) + generic OIDC (mixed mode, JIT provisioning)."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.config import get_settings, effective_value
from app.core.security import (
    cookie_props,
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_session
from app.models.core import AuthProvider, User, UserRole
from app.schemas import (
    CreateUserRequest,
    LoginRequest,
    OIDCLoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateUserRequest,
    UserOut,
)

logger = logging.getLogger("wishdeck.auth")
router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(**cookie_props(), value=token)


# --------------------------------------------------------------------------
# Local auth
# --------------------------------------------------------------------------
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> User:
    if not await effective_value("ENABLE_REGISTRATION", session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration disabled")

    exists = (await session.execute(
        select(User).where(User.email == payload.email)
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        username=payload.username or payload.email.split("@")[0],
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        auth_provider=AuthProvider.LOCAL,
        role=UserRole.ADMIN if not (await session.execute(select(User))).scalars().first() else UserRole.USER,
    )
    session.add(user)
    await session.flush()
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user = (await session.execute(
        select(User).where(User.email == payload.username)
    )).scalar_one_or_none()
    if not user or user.auth_provider != AuthProvider.LOCAL or not verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = create_access_token(user.id, {"role": user.role.value})
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout(response: Response) -> Response:
    response.delete_cookie("access_token", path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


# --------------------------------------------------------------------------
# OIDC (generic OpenID Connect, mixed mode)
# --------------------------------------------------------------------------
@router.get("/oidc/config")
async def oidc_config(session: AsyncSession = Depends(get_session)) -> dict:
    enabled = await effective_value("OIDC_ENABLED", session)
    return {
        "enabled": bool(enabled),
        "name": await effective_value("OIDC_NAME", session),
        "issuer_url": await effective_value("OIDC_ISSUER_URL", session),
        "client_id": await effective_value("OIDC_CLIENT_ID", session),
        "scopes": await effective_value("OIDC_SCOPES", session) or "openid email profile",
    }


@router.post("/oidc/callback", response_model=TokenResponse)
async def oidc_callback(
    payload: OIDCLoginRequest,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Exchange the OIDC authorization code for user info and issue a local JWT.

    Uses Authlib's async OAuth client against the discovered issuer metadata.
    """
    if not await effective_value("OIDC_ENABLED", session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="OIDC disabled")

    from authlib.integrations.httpx_client import AsyncOAuth2Client  # lazy import

    issuer = await effective_value("OIDC_ISSUER_URL", session)
    client_id = await effective_value("OIDC_CLIENT_ID", session)
    client_secret = await effective_value("OIDC_CLIENT_SECRET", session)
    scopes = await effective_value("OIDC_SCOPES", session)
    redirect_uri = payload.redirect_uri or await effective_value("OIDC_REDIRECT_URI", session) \
        or f"{settings.BASE_URL}/api/v1/auth/oidc/callback"

    async with AsyncOAuth2Client(
        client_id, client_secret=client_secret, scope=scopes, redirect_uri=redirect_uri
    ) as client:
        # Discover token & userinfo endpoints from the issuer's well-known config.
        metadata = await client.load_server_metadata(
            f"{issuer.rstrip('/')}/.well-known/openid-configuration"
        )
        token = await client.fetch_token(
            metadata["token_endpoint"], code=payload.code,
            grant_type="authorization_code",
        )
        userinfo = await client.userinfo()

    subject = str(userinfo.get("sub"))
    email = userinfo.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC provider returned no email"
        )

    user = (await session.execute(
        select(User).where(User.oidc_subject == subject)
    )).scalar_one_or_none()

    if user is None:  # JIT provisioning on first login
        existing = (await session.execute(
            select(User).where(User.email == email)
        )).scalar_one_or_none()
        if existing:
            existing.oidc_subject = subject
            existing.auth_provider = AuthProvider.OIDC
            user = existing
        else:
            user = User(
                email=email,
                username=email.split("@")[0],
                full_name=userinfo.get("name"),
                avatar_url=userinfo.get("picture"),
                auth_provider=AuthProvider.OIDC,
                oidc_subject=subject,
                role=UserRole.USER,
            )
            session.add(user)
        await session.flush()

    jwt_token = create_access_token(user.id, {"role": user.role.value})
    _set_auth_cookie(response, jwt_token)
    return TokenResponse(access_token=jwt_token)


# --------------------------------------------------------------------------
# Admin: user management
# --------------------------------------------------------------------------
@router.get("/users", response_model=list[UserOut])
async def list_users(
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> list[User]:
    rows = (await session.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    return rows


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> User:
    exists = (await session.execute(
        select(User).where(User.email == payload.email)
    )).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    role = UserRole.ADMIN if payload.role == "admin" else UserRole.USER
    user = User(
        email=payload.email,
        username=payload.username or payload.email.split("@")[0],
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        auth_provider=AuthProvider.LOCAL,
        role=role,
    )
    session.add(user)
    await session.flush()
    return user


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.role is not None:
        # Prevent an admin from demoting themselves and getting locked out.
        if user.id == admin.id and payload.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove your own admin role",
            )
        user.role = UserRole.ADMIN if payload.role == "admin" else UserRole.USER
    if payload.is_active is not None:
        if user.id == admin.id and not payload.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )
        user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    await session.flush()
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    response: Response,
    session: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
) -> Response:
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await session.delete(user)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


__all__ = ["router"]
