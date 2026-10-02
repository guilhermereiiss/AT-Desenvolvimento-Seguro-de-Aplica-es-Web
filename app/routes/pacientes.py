from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.auth.deps import ANY_ROLE, paciente_acessivel, require_roles
from app.database import get_session
from app.models import Consulta, Paciente, Papel, Usuario
from app.models.schemas import PacienteCreate, PacientePublic

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


@router.post("", response_model=PacientePublic, status_code=201)
def criar(
    payload: PacienteCreate,
    user: Usuario = Depends(require_roles(Papel.recepcionista, Papel.admin)),
    session: Session = Depends(get_session),
):
    p = Paciente(**payload.model_dump(), criado_por=user.id)
    session.add(p)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "CPF já cadastrado") from None
    session.refresh(p)
    return p


@router.get("", response_model=list[PacientePublic])
def listar(
    q: str | None = Query(default=None, pattern=r"^[A-Za-zÀ-ÿ' \-]{1,100}$"),  # whitelist
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: Usuario = Depends(require_roles(*ANY_ROLE)),
    session: Session = Depends(get_session),
):
    stmt = select(Paciente)
    if user.papel == Papel.profissional:  # só pacientes com vínculo
        stmt = stmt.where(
            Paciente.id.in_(select(Consulta.paciente_id).where(Consulta.profissional_id == user.profissional_id))
        )
    if q:
        stmt = stmt.where(Paciente.nome.ilike(f"%{q}%"))  # valor vai como bind parameter
    return session.exec(stmt.offset(offset).limit(limit)).all()


@router.get("/{paciente_id}", response_model=PacientePublic)
def obter(paciente: Paciente = Depends(paciente_acessivel)):
    return paciente
