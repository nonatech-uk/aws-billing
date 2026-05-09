"""Keycloak OIDC integration via Authlib + signed session cookie.

Flow:
  GET /auth/login    -> redirect to Keycloak authorize endpoint
  GET /auth/callback -> exchange code, set session cookie, redirect to /
  GET /auth/logout   -> clear cookie, redirect to Keycloak end-session
  GET /auth/me       -> JSON of current session
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeSerializer

from config.settings import settings
from src.api.models import CurrentUser

COOKIE_NAME = "aws_billing_session"
COOKIE_MAX_AGE = 60 * 60 * 12  # 12h

_serializer = URLSafeSerializer(settings.session_secret, salt="session")
_oauth: OAuth | None = None
_discovery_cache: dict[str, Any] | None = None


def _build_oauth() -> OAuth:
    global _oauth
    if _oauth is not None:
        return _oauth
    oauth = OAuth()
    oauth.register(
        name="keycloak",
        client_id=settings.keycloak_client_id,
        client_secret=settings.keycloak_client_secret,
        server_metadata_url=settings.keycloak_discovery_url,
        client_kwargs={"scope": "openid email profile"},
    )
    _oauth = oauth
    return oauth


async def _discovery() -> dict[str, Any]:
    """Fetch Keycloak's OIDC discovery doc (used for end-session endpoint)."""
    global _discovery_cache
    if _discovery_cache is not None:
        return _discovery_cache
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(settings.keycloak_discovery_url)
        r.raise_for_status()
        _discovery_cache = r.json()
    return _discovery_cache


def _encode_session(payload: dict[str, Any]) -> str:
    return _serializer.dumps(payload)


def _decode_session(token: str) -> dict[str, Any] | None:
    try:
        return _serializer.loads(token)
    except BadSignature:
        return None


def _user_from_session(session: dict[str, Any]) -> CurrentUser:
    groups = session.get("groups", [])
    return CurrentUser(
        email=session["email"],
        name=session.get("name", session["email"]),
        is_admin=settings.keycloak_admin_group in groups,
    )


def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency: returns CurrentUser or raises 401."""
    if not settings.auth_enabled:
        return CurrentUser(
            email=settings.dev_user_email,
            name=settings.dev_user_name,
            is_admin=settings.dev_user_is_admin,
        )

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    session = _decode_session(token)
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    groups = session.get("groups", [])
    if settings.keycloak_viewer_group not in groups and settings.keycloak_admin_group not in groups:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not in viewer group")
    return _user_from_session(session)


def require_admin(request: Request) -> CurrentUser:
    user = get_current_user(request)
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


router = APIRouter()


@router.get("/auth/login")
async def login(request: Request):
    if not settings.auth_enabled:
        return RedirectResponse("/")
    oauth = _build_oauth()
    redirect_uri = str(request.url_for("auth_callback"))
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback", name="auth_callback")
async def callback(request: Request):
    oauth = _build_oauth()
    try:
        token = await oauth.keycloak.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"OAuth error: {e}")

    userinfo = token.get("userinfo") or {}
    # Read from a dedicated claim to avoid colliding with realm `groups` mappers.
    groups = userinfo.get("aws_billing_groups") or []
    if not isinstance(groups, list):
        groups = [groups]

    if settings.keycloak_viewer_group not in groups and settings.keycloak_admin_group not in groups:
        # Authenticated but not authorised
        return JSONResponse(
            {"detail": f"Account is not in '{settings.keycloak_viewer_group}'"},
            status_code=403,
        )

    payload = {
        "email": userinfo.get("email") or userinfo.get("preferred_username") or "unknown",
        "name": userinfo.get("name") or userinfo.get("preferred_username") or "",
        "groups": groups,
    }
    response = RedirectResponse("/")
    response.set_cookie(
        COOKIE_NAME,
        _encode_session(payload),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.get("/auth/logout")
async def logout(request: Request):
    response = RedirectResponse("/")
    response.delete_cookie(COOKIE_NAME)
    if settings.auth_enabled:
        try:
            disco = await _discovery()
            end_session = disco.get("end_session_endpoint")
            if end_session:
                response = RedirectResponse(
                    f"{end_session}?post_logout_redirect_uri={request.base_url}"
                )
                response.delete_cookie(COOKIE_NAME)
        except Exception:
            pass
    return response


@router.get("/auth/me", response_model=CurrentUser)
async def me(request: Request) -> CurrentUser:
    return get_current_user(request)
