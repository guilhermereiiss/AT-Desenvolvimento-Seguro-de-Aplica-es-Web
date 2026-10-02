import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException

from app.config import get_settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except ValueError:
        return False


_DUMMY_HASH = hash_password("senha-falsa-para-equalizar-tempo")


def dummy_verify(plain: str) -> None:
    """Gasta o mesmo tempo quando o usuário não existe (evita enumeração por timing)."""
    verify_password(plain, _DUMMY_HASH)


def create_token(*, sub: str, typ: str, minutes: int | None = None, **claims) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "typ": typ,  # "user" (humano) ou "m2m" (laboratório)
        "iss": s.jwt_issuer,
        "aud": s.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=minutes or s.access_token_minutes),
        "jti": uuid.uuid4().hex,
        **claims,
    }
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(
            token,
            s.secret_key,
            algorithms=[s.jwt_algorithm],  # allowlist: bloqueia alg=none
            audience=s.jwt_audience,
            issuer=s.jwt_issuer,
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "Token inválido ou expirado", headers={"WWW-Authenticate": "Bearer"}) from exc
