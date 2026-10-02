import os
from datetime import timedelta
from types import SimpleNamespace

# Variáveis de teste ANTES de importar a app (nenhum segredo real).
os.environ.update(
    APP_ENV="test",
    DATABASE_URL="sqlite://",
    SECRET_KEY="k" * 48,
    BCRYPT_ROUNDS="4",
    MFA_SIMULATED_CODE="000000",
    CORS_ORIGINS='["http://localhost:3000"]',
    LAB_CLIENT_ID="lab-parceiro",
    LAB_CLIENT_SECRET="segredo-lab-de-teste",
    LOGIN_RATE_LIMIT="1000",
    M2M_RATE_LIMIT="1000",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.auth.security import create_token, hash_password
from app.database import get_session
from app.main import app
from app.models import Consulta, Paciente, Papel, Profissional, Usuario
from app.ratelimit import limiter
from app.utils import utcnow

SENHA = "SenhaForte123"


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine):
    def _session():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session
    limiter.reset()
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def dados(session):
    pa = Profissional(nome="Ana Souza", especialidade="Cardiologia", crm="111111/BA")
    pb = Profissional(nome="Bruno Lima", especialidade="Ortopedia", crm="222222/BA")
    session.add_all([pa, pb])
    session.commit()
    users = {
        "admin": Usuario(email="admin@t.example", senha_hash=hash_password(SENHA), papel=Papel.admin),
        "recep": Usuario(email="recep@t.example", senha_hash=hash_password(SENHA), papel=Papel.recepcionista),
        "prof_a": Usuario(email="a@t.example", senha_hash=hash_password(SENHA), papel=Papel.profissional, profissional_id=pa.id),
        "prof_b": Usuario(email="b@t.example", senha_hash=hash_password(SENHA), papel=Papel.profissional, profissional_id=pb.id),
    }
    session.add_all(users.values())
    pac = Paciente(nome="Carla Dias", cpf="12345678901", email="carla@t.example", telefone="71999999999")
    session.add(pac)
    session.commit()
    amanha = utcnow().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
    c = Consulta(paciente_id=pac.id, profissional_id=pa.id, data_hora=amanha, motivo="Retorno",
                 observacoes_internas="SEGREDO-INTERNO", criado_por=users["recep"].id)
    session.add(c)
    session.commit()
    for x in (*users.values(), pac, c, pa, pb):
        session.refresh(x)
    return SimpleNamespace(**users, pac=pac, consulta=c, pa=pa, pb=pb, amanha=amanha)


def auth(user, otp=False):
    amr = ["pwd", "otp"] if otp else ["pwd"]
    return {"Authorization": "Bearer " + create_token(sub=str(user.id), typ="user", role=user.papel.value, amr=amr)}
