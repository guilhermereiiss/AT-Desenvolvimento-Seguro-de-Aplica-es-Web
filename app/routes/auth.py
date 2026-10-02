import hmac

from fastapi import APIRouter, Depends, Form, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.auth.security import create_token, dummy_verify, verify_password
from app.config import get_settings
from app.database import get_session
from app.models import Papel, Usuario
from app.models.schemas import Token
from app.ratelimit import rate_limit

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=Token, dependencies=[Depends(rate_limit("login"))])
def login(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    mfa_code: str | None = Form(default=None),
    session: Session = Depends(get_session),
):
    s = get_settings()
    user = session.exec(select(Usuario).where(Usuario.email == form.username)).first()  # parametrizado
    if user:
        ok = verify_password(form.password, user.senha_hash)
    else:
        dummy_verify(form.password)
        ok = False
    if not (user and ok and user.ativo):
        raise HTTPException(401, "Credenciais inválidas", headers={"WWW-Authenticate": "Bearer"})

    amr = ["pwd"]
    if user.papel == Papel.admin:  # MFA simulado (em produção: TOTP)
        if not mfa_code or not hmac.compare_digest(mfa_code, s.mfa_simulated_code):
            raise HTTPException(401, "Código MFA inválido ou ausente", headers={"WWW-Authenticate": "Bearer"})
        amr.append("otp")

    token = create_token(sub=str(user.id), typ="user", role=user.papel.value, amr=amr)
    response.set_cookie(  # usado só pela página HTML da recepção
        "access_token", token, httponly=True, secure=s.is_prod, samesite="strict", max_age=s.access_token_minutes * 60
    )
    return Token(access_token=token)


@router.post("/oauth/token", response_model=Token, dependencies=[Depends(rate_limit("m2m"))])
def m2m_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    scope: str = Form(default="slots:read"),
):
    """OAuth2 Client Credentials (M2M): laboratório parceiro. Escopo máximo: slots:read."""
    s = get_settings()
    if grant_type != "client_credentials":
        raise HTTPException(400, "unsupported_grant_type")
    id_ok = hmac.compare_digest(client_id, s.lab_client_id)
    secret_ok = hmac.compare_digest(client_secret, s.lab_client_secret)
    if not (id_ok and secret_ok):
        raise HTTPException(401, "invalid_client", headers={"WWW-Authenticate": "Basic"})
    pedidos = set(scope.split())
    if not pedidos or not pedidos <= {"slots:read"}:
        raise HTTPException(400, "invalid_scope")
    return Token(access_token=create_token(sub=client_id, typ="m2m", minutes=10, scope=" ".join(sorted(pedidos))))
