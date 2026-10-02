from datetime import date, datetime, time, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.auth.deps import ANY_ROLE, resolve_user
from app.auth.security import decode_token
from app.database import get_session
from app.models import Consulta, Paciente, Papel, Profissional, Usuario
from app.utils import utcnow

router = APIRouter(tags=["web"], include_in_schema=False)
# Jinja2Templates liga autoescape para .html: {{ var }} sempre escapado (nunca usar |safe)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def web_user(request: Request, session: Session = Depends(get_session)) -> Usuario:
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Faça login em /auth/login")
    user = resolve_user(decode_token(token), session)
    if user.papel not in ANY_ROLE:
        raise HTTPException(403, "Sem permissão")
    return user


@router.get("/agenda", response_class=HTMLResponse)
def agenda(
    request: Request,
    data: date | None = None,
    user: Usuario = Depends(web_user),
    session: Session = Depends(get_session),
):
    dia = data or utcnow().date()
    ini = datetime.combine(dia, time.min)
    stmt = (
        select(Consulta, Paciente, Profissional)
        .where(Consulta.paciente_id == Paciente.id, Consulta.profissional_id == Profissional.id)
        .where(Consulta.data_hora >= ini, Consulta.data_hora < ini + timedelta(days=1))
        .order_by(Consulta.data_hora)
    )
    if user.papel == Papel.profissional:
        stmt = stmt.where(Consulta.profissional_id == user.profissional_id)
    linhas = [
        {"hora": c.data_hora.strftime("%H:%M"), "paciente": p.nome, "profissional": pr.nome,
         "motivo": c.motivo, "status": c.status.value}
        for c, p, pr in session.exec(stmt).all()
    ]
    return templates.TemplateResponse(request, "agenda.html", {"dia": dia.isoformat(), "consultas": linhas})
