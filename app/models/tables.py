from enum import Enum

from pydantic import NaiveDatetime

from sqlmodel import Field, SQLModel

from app.utils import utcnow


class Papel(str, Enum):
    recepcionista = "recepcionista"
    profissional = "profissional"
    admin = "admin"


class StatusConsulta(str, Enum):
    agendada = "agendada"
    confirmada = "confirmada"
    cancelada = "cancelada"
    concluida = "concluida"


class Profissional(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str
    especialidade: str
    crm: str = Field(unique=True, index=True)


class Usuario(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    senha_hash: str  # bcrypt, nunca texto plano
    papel: Papel
    ativo: bool = True
    profissional_id: int | None = Field(default=None, foreign_key="profissional.id")


class Paciente(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nome: str = Field(index=True)
    cpf: str = Field(unique=True, index=True)  # dado sensível (LGPD)
    email: str
    telefone: str
    criado_por: int | None = None  # campo interno de auditoria


class Consulta(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    paciente_id: int = Field(foreign_key="paciente.id", index=True)
    profissional_id: int = Field(foreign_key="profissional.id", index=True)
    data_hora: NaiveDatetime = Field(index=True)
    motivo: str
    status: StatusConsulta = StatusConsulta.agendada
    observacoes_internas: str | None = None  # NUNCA exposto na API
    criado_por: int | None = None  # auditoria interna
    criado_em: NaiveDatetime = Field(default_factory=utcnow)
