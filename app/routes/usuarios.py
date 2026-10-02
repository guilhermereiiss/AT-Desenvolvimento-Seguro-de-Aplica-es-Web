from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.auth.deps import require_roles
from app.auth.security import hash_password
from app.database import get_session
from app.models import Papel, Profissional, Usuario
from app.models.schemas import UsuarioCreate, UsuarioPublic

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("", response_model=UsuarioPublic, status_code=201)
def criar_usuario(
    payload: UsuarioCreate,
    _admin: Usuario = Depends(require_roles(Papel.admin)),  # rota restrita a admin (+MFA)
    session: Session = Depends(get_session),
):
    if payload.papel == Papel.profissional:
        if payload.profissional_id is None or session.get(Profissional, payload.profissional_id) is None:
            raise HTTPException(422, "profissional_id válido é obrigatório para o papel profissional")
    user = Usuario(
        email=payload.email,
        senha_hash=hash_password(payload.senha),
        papel=payload.papel,
        profissional_id=payload.profissional_id,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "E-mail já cadastrado") from None
    session.refresh(user)
    return user
