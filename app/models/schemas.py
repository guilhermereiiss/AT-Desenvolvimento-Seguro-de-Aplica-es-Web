from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.tables import Papel, StatusConsulta
from app.utils import utcnow

# Whitelists (regex): só o que é esperado entra. Rejeita < > " ' { } etc. no motivo.
NOME_RE = r"^[A-Za-zÀ-ÿ' \-]{2,100}$"
MOTIVO_RE = r"^[\w\sÀ-ÿ.,;:!?()\-/]{3,200}$"
CPF_RE = r"^\d{11}$"
TEL_RE = r"^\d{10,11}$"
CRM_RE = r"^\d{4,7}/[A-Z]{2}$"


class Strict(BaseModel):
    """Base de entrada: campo não declarado => 422 (mass assignment bloqueado)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _futuro(v: datetime) -> datetime:
    if v.tzinfo:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    if v <= utcnow():
        raise ValueError("data_hora deve estar no futuro")
    return v


# ---------- Consultas ----------
class ConsultaCreate(Strict):
    paciente_id: int = Field(gt=0)
    profissional_id: int | None = Field(default=None, gt=0)  # só admin informa
    data_hora: datetime
    motivo: str = Field(pattern=MOTIVO_RE)

    _v = field_validator("data_hora")(_futuro)


class ConsultaUpdate(Strict):
    data_hora: datetime | None = None
    motivo: str | None = Field(default=None, pattern=MOTIVO_RE)
    status: StatusConsulta | None = None

    @field_validator("data_hora")
    @classmethod
    def _f(cls, v):
        return _futuro(v) if v else v


class ConsultaPublic(BaseModel):
    """Response model: whitelist de saída. Sem observacoes_internas / criado_por."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    paciente_id: int
    profissional_id: int
    data_hora: datetime
    motivo: str
    status: StatusConsulta


# ---------- Pacientes ----------
class PacienteCreate(Strict):
    nome: str = Field(pattern=NOME_RE)
    cpf: str = Field(pattern=CPF_RE)
    email: EmailStr
    telefone: str = Field(pattern=TEL_RE)


class PacientePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: EmailStr
    telefone: str  # CPF e auditoria não saem na API


# ---------- Profissionais ----------
class ProfissionalCreate(Strict):
    nome: str = Field(pattern=NOME_RE)
    especialidade: str = Field(pattern=NOME_RE)
    crm: str = Field(pattern=CRM_RE)


class ProfissionalPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    especialidade: str


# ---------- Usuários / Auth ----------
class UsuarioCreate(Strict):
    email: EmailStr
    senha: str = Field(min_length=12, max_length=72)
    papel: Papel
    profissional_id: int | None = Field(default=None, gt=0)

    @field_validator("senha")
    @classmethod
    def _senha(cls, v: str) -> str:
        if len(v.encode()) > 72:  # limite do bcrypt
            raise ValueError("senha excede 72 bytes")
        if not (any(c.isalpha() for c in v) and any(c.isdigit() for c in v)):
            raise ValueError("senha precisa de letras e números")
        return v


class UsuarioPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    papel: Papel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LabSlot(BaseModel):
    data_hora: datetime  # laboratório só vê horários livres, nada de paciente
