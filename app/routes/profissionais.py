from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.auth.deps import ANY_ROLE, require_roles
from app.database import get_session
from app.models import Papel, Profissional, Usuario
from app.models.schemas import ProfissionalCreate, ProfissionalPublic

router = APIRouter(prefix="/profissionais", tags=["profissionais"])


@router.get("", response_model=list[ProfissionalPublic])
def listar(_: Usuario = Depends(require_roles(*ANY_ROLE)), session: Session = Depends(get_session)):
    return session.exec(select(Profissional)).all()


@router.post("", response_model=ProfissionalPublic, status_code=201)
def criar(
    payload: ProfissionalCreate,
    _: Usuario = Depends(require_roles(Papel.admin)),
    session: Session = Depends(get_session),
):
    prof = Profissional(**payload.model_dump())
    session.add(prof)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "CRM já cadastrado") from None
    session.refresh(prof)
    return prof
