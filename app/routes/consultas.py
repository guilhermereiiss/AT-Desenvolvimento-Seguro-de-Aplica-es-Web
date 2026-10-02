from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select

from app.auth.deps import ANY_ROLE, WRITE_ROLES, consulta_escrita, consulta_leitura, require_roles
from app.database import get_session
from app.models import Consulta, Paciente, Papel, Profissional, StatusConsulta, Usuario
from app.models.schemas import ConsultaCreate, ConsultaPublic, ConsultaUpdate

router = APIRouter(prefix="/consultas", tags=["consultas"])


@router.post("", response_model=ConsultaPublic, status_code=201)
def criar(
    payload: ConsultaCreate,
    user: Usuario = Depends(require_roles(*WRITE_ROLES)),
    session: Session = Depends(get_session),
):
    if user.papel == Papel.profissional:
        prof_id = user.profissional_id  # ignora qualquer ID vindo do cliente
    else:
        prof_id = payload.profissional_id
    if prof_id is None or session.get(Profissional, prof_id) is None:
        raise HTTPException(422, "Profissional inválido")
    if session.get(Paciente, payload.paciente_id) is None:
        raise HTTPException(404, "Paciente não encontrado")
    conflito = session.exec(
        select(Consulta.id).where(
            Consulta.profissional_id == prof_id,
            Consulta.data_hora == payload.data_hora,
            Consulta.status != StatusConsulta.cancelada,
        )
    ).first()
    if conflito:
        raise HTTPException(409, "Horário indisponível")
    consulta = Consulta(
        paciente_id=payload.paciente_id,
        profissional_id=prof_id,
        data_hora=payload.data_hora,
        motivo=payload.motivo,
        criado_por=user.id,
    )
    session.add(consulta)
    session.commit()
    session.refresh(consulta)
    return consulta


@router.get("", response_model=list[ConsultaPublic])
def listar(
    dia: date | None = None,
    status: StatusConsulta | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: Usuario = Depends(require_roles(*ANY_ROLE)),
    session: Session = Depends(get_session),
):
    stmt = select(Consulta)
    if user.papel == Papel.profissional:
        stmt = stmt.where(Consulta.profissional_id == user.profissional_id)
    if dia:
        ini = datetime.combine(dia, time.min)
        stmt = stmt.where(Consulta.data_hora >= ini, Consulta.data_hora < ini + timedelta(days=1))
    if status:
        stmt = stmt.where(Consulta.status == status)
    return session.exec(stmt.order_by(Consulta.data_hora).offset(offset).limit(limit)).all()


@router.get("/{consulta_id}", response_model=ConsultaPublic)
def obter(consulta: Consulta = Depends(consulta_leitura)):
    return consulta


@router.patch("/{consulta_id}", response_model=ConsultaPublic)
def atualizar(
    payload: ConsultaUpdate,
    consulta: Consulta = Depends(consulta_escrita),
    session: Session = Depends(get_session),
):
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(consulta, campo, valor)
    session.add(consulta)
    session.commit()
    session.refresh(consulta)
    return consulta


@router.delete("/{consulta_id}", status_code=204)
def cancelar(consulta: Consulta = Depends(consulta_escrita), session: Session = Depends(get_session)):
    consulta.status = StatusConsulta.cancelada  # soft delete: mantém trilha de auditoria
    session.add(consulta)
    session.commit()
    return Response(status_code=204)
