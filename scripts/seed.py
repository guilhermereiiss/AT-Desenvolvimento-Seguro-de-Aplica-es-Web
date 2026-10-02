"""Cria usuários iniciais. Uso: SEED_PASSWORD='...' python -m scripts.seed"""
import os
from getpass import getpass

from sqlmodel import Session, select

from app.auth.security import hash_password
from app.database import engine, init_db
from app.models import Papel, Profissional, Usuario

init_db()
senha = os.environ.get("SEED_PASSWORD") or getpass("Senha para os usuários seed (12+ chars): ")
with Session(engine) as s:
    if s.exec(select(Usuario)).first():
        raise SystemExit("Banco já populado.")
    prof = Profissional(nome="Ana Souza", especialidade="Cardiologia", crm="123456/BA")
    s.add(prof)
    s.commit()
    s.refresh(prof)
    for email, papel, pid in [
        ("admin@clinica.example", Papel.admin, None),
        ("recepcao@clinica.example", Papel.recepcionista, None),
        ("ana@clinica.example", Papel.profissional, prof.id),
    ]:
        s.add(Usuario(email=email, senha_hash=hash_password(senha), papel=papel, profissional_id=pid))
    s.commit()
print("Seed ok.")
