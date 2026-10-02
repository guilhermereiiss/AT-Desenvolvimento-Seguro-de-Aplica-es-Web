from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.auth.deps import require_scope
from app.database import get_session
from app.models import Consulta, StatusConsulta
from app.models.schemas import LabSlot

router = APIRouter(prefix="/lab", tags=["laboratorio"])


@router.get("/horarios-disponiveis", response_model=list[LabSlot])
def horarios(
    data: date,
    profissional_id: int = Query(gt=0),
    _claims: dict = Depends(require_scope("slots:read")),
    session: Session = Depends(get_session),
):
    ini = datetime.combine(data, time.min)
    ocupados = set(
        session.exec(
            select(Consulta.data_hora).where(
                Consulta.profissional_id == profissional_id,
                Consulta.data_hora >= ini,
                Consulta.data_hora < ini + timedelta(days=1),
                Consulta.status != StatusConsulta.cancelada,
            )
        ).all()
    )
    return [LabSlot(data_hora=ini.replace(hour=h)) for h in range(8, 18) if ini.replace(hour=h) not in ocupados]
