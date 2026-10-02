"""Camada única de autenticação/autorização/ownership. Nenhuma rota reimplementa isso."""
from fastapi import Depends, HTTPException, Path
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.auth.security import decode_token
from app.database import get_session
from app.models import Consulta, Paciente, Papel, Usuario
from sqlmodel import select

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
_401 = {"WWW-Authenticate": "Bearer"}


def get_token_payload(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)


def resolve_user(payload: dict, session: Session) -> Usuario:
    if payload.get("typ") != "user":  # token M2M nunca vira usuário
        raise HTTPException(401, "Token inválido", headers=_401)
    try:
        user = session.get(Usuario, int(payload["sub"]))
    except (ValueError, TypeError):
        user = None
    if not user or not user.ativo:
        raise HTTPException(401, "Token inválido", headers=_401)
    return user


def get_current_user(payload: dict = Depends(get_token_payload), session: Session = Depends(get_session)) -> Usuario:
    return resolve_user(payload, session)


def require_roles(*papeis: Papel):
    """RBAC: papel vem do banco (fonte de verdade), admin exige MFA no token."""

    def checker(user: Usuario = Depends(get_current_user), payload: dict = Depends(get_token_payload)) -> Usuario:
        if user.papel not in papeis:
            raise HTTPException(403, "Sem permissão para este recurso")
        if user.papel == Papel.admin and "otp" not in payload.get("amr", []):
            raise HTTPException(403, "MFA obrigatório para administradores")
        return user

    return checker


def require_scope(scope: str):
    """Rotas M2M: exige token do tipo m2m com o escopo específico."""

    def checker(payload: dict = Depends(get_token_payload)) -> dict:
        if payload.get("typ") != "m2m" or scope not in str(payload.get("scope", "")).split():
            raise HTTPException(403, "Escopo insuficiente")
        return payload

    return checker


ANY_ROLE = (Papel.recepcionista, Papel.profissional, Papel.admin)
WRITE_ROLES = (Papel.profissional, Papel.admin)


def consulta_or_404(consulta_id: int, user: Usuario, session: Session) -> Consulta:
    """Ownership (anti-BOLA): profissional só enxerga as próprias consultas.
    Devolve 404 (não 403) para não revelar que o ID existe."""
    c = session.get(Consulta, consulta_id)
    if c is None or (user.papel == Papel.profissional and c.profissional_id != user.profissional_id):
        raise HTTPException(404, "Consulta não encontrada")
    return c


def consulta_leitura(
    consulta_id: int = Path(gt=0),
    user: Usuario = Depends(require_roles(*ANY_ROLE)),
    session: Session = Depends(get_session),
) -> Consulta:
    return consulta_or_404(consulta_id, user, session)


def consulta_escrita(
    consulta_id: int = Path(gt=0),
    user: Usuario = Depends(require_roles(*WRITE_ROLES)),
    session: Session = Depends(get_session),
) -> Consulta:
    return consulta_or_404(consulta_id, user, session)


def paciente_acessivel(
    paciente_id: int = Path(gt=0),
    user: Usuario = Depends(require_roles(*ANY_ROLE)),
    session: Session = Depends(get_session),
) -> Paciente:
    """Profissional só acessa paciente com quem tem consulta (mesmo padrão de BOLA)."""
    p = session.get(Paciente, paciente_id)
    if p is not None and user.papel == Papel.profissional:
        vinculo = session.exec(
            select(Consulta.id).where(
                Consulta.paciente_id == paciente_id, Consulta.profissional_id == user.profissional_id
            )
        ).first()
        if vinculo is None:
            p = None
    if p is None:
        raise HTTPException(404, "Paciente não encontrado")
    return p
