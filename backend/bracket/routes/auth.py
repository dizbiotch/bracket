from typing import Any, Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from heliclockter import datetime_utc, timedelta
from jwt import DecodeError, ExpiredSignatureError
from pydantic import BaseModel, StringConstraints
from starlette.requests import Request

from bracket.config import config
from bracket.database import database
from bracket.models.db.tournament import Tournament
from bracket.models.db.user import UserInDB, UserPublic
from bracket.schema import tournaments
from bracket.sql.tournaments import sql_get_tournament_by_endpoint_name
from bracket.sql.users import (
    get_user,
    get_user_access_to_club,
    get_user_access_to_tournament,
    update_user_password,
)
from bracket.utils.db import fetch_all_parsed
from bracket.utils.id_types import ClubId, TournamentId, UserId
from bracket.utils.security import hash_password, verify_password
from bracket.utils.types import assert_some

router = APIRouter(prefix=config.api_prefix)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60  # 1 week
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 60  # 1 hour

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# def convert_openid(response: dict[str, Any]) -> OpenID:
#     """Convert user information returned by OIDC"""
#     return OpenID(display_name=response["sub"])


# os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# sso = GoogleSSO(
#     client_id="test",
#     client_secret="secret",
#     redirect_uri="http://localhost:8080/sso_callback",
#     allow_insecure_http=config.allow_insecure_http_sso,
# )


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: UserId


class TokenData(BaseModel):
    email: str | None = None


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetToken(BaseModel):
    reset_token: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: Annotated[str, StringConstraints(min_length=8, max_length=48)]


class PasswordResetSuccess(BaseModel):
    success: bool = True


async def authenticate_user(email: str, password: str) -> UserInDB | None:
    user = await get_user(email)

    if not user or not verify_password(password, user.password_hash):
        return None

    return user


def create_access_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime_utc.now() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.jwt_secret, algorithm=ALGORITHM)


def create_password_reset_token(email: str, expires_delta: timedelta) -> str:
    to_encode: dict[str, Any] = {"reset_user": email}
    expire = datetime_utc.now() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.jwt_secret, algorithm=ALGORITHM)


async def check_jwt_and_get_user(token: str) -> UserPublic | None:
    try:
        payload = jwt.decode(token, config.jwt_secret, algorithms=[ALGORITHM])
        email: str = str(payload.get("user"))
        if email is None:
            return None
        token_data = TokenData(email=email)
    except (DecodeError, ExpiredSignatureError):
        return None

    user = await get_user(email=assert_some(token_data.email))
    if user is None:
        return None

    return UserPublic.model_validate(user.model_dump())


async def user_authenticated(token: str = Depends(oauth2_scheme)) -> UserPublic:
    user = await check_jwt_and_get_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserPublic.model_validate(user.model_dump())


async def user_authenticated_for_tournament(
    tournament_id: TournamentId, token: str = Depends(oauth2_scheme)
) -> UserPublic:
    user = await check_jwt_and_get_user(token)

    if not user or not await get_user_access_to_tournament(tournament_id, user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserPublic.model_validate(user.model_dump())


async def user_authenticated_for_club(
    club_id: ClubId, token: str = Depends(oauth2_scheme)
) -> UserPublic:
    user = await check_jwt_and_get_user(token)

    if not user or not await get_user_access_to_club(club_id, user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserPublic.model_validate(user.model_dump())


async def user_authenticated_or_public_dashboard(
    tournament_id: TournamentId, request: Request
) -> UserPublic | None:
    try:
        token: str = assert_some(await oauth2_scheme(request))
        user = await check_jwt_and_get_user(token)
        if user is not None and await get_user_access_to_tournament(tournament_id, user.id):
            return user
    except HTTPException:
        pass

    tournaments_fetched = await fetch_all_parsed(
        database, Tournament, tournaments.select().where(tournaments.c.id == tournament_id)
    )
    if len(tournaments_fetched) < 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or page is not publicly available",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return None


async def user_authenticated_or_public_dashboard_by_endpoint_name(
    token: str = Depends(oauth2_scheme), endpoint_name: str | None = None
) -> UserPublic | None:
    if endpoint_name is not None:
        if await sql_get_tournament_by_endpoint_name(endpoint_name) is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    return await user_authenticated(token)


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer", user_id=user.id)


@router.post("/auth/request-password-reset", response_model=PasswordResetToken)
async def request_password_reset(body: PasswordResetRequest) -> PasswordResetToken:
    """Create a short-lived password reset token for the given email.

    For now, the token is returned in the response so it can be
    delivered by the frontend or used during development.
    """

    user = await get_user(body.email)

    # Always return a response without revealing whether the email exists.
    if not user:
        return PasswordResetToken(reset_token="")

    reset_token_expires = timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    reset_token = create_password_reset_token(user.email, reset_token_expires)
    return PasswordResetToken(reset_token=reset_token)


@router.post("/auth/reset-password", response_model=PasswordResetSuccess)
async def reset_password(body: PasswordResetConfirm) -> PasswordResetSuccess:
    """Reset a user's password using a previously issued reset token."""

    try:
        payload = jwt.decode(body.token, config.jwt_secret, algorithms=[ALGORITHM])
        email_raw = payload.get("reset_user")
        email = str(email_raw) if email_raw is not None else None
    except (DecodeError, ExpiredSignatureError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        ) from None

    if email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    user = await get_user(email=email)
    if user is None:
        # Token is invalid if the user no longer exists.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    await update_user_password(user.id, hash_password(body.new_password))

    return PasswordResetSuccess()
    return SuccessResponse()


# @router.get("/login", summary='SSO login')
# async def sso_login() -> RedirectResponse:
#     """Generate login url and redirect"""
#     return cast(RedirectResponse, await sso.get_login_redirect())
#
#
# @router.get("/sso_callback", summary='SSO callback')
# async def sso_callback(request: Request) -> dict[str, Any]:
#     """Process login response from OIDC and return user info"""
#     user = await sso.verify_and_process(request)
#     if user is None:
#         raise HTTPException(401, "Failed to fetch user information")
#     return {
#         "id": user.id,
#         "picture": user.picture,
#         "display_name": user.display_name,
#         "email": user.email,
#         "provider": user.provider,
#     }
