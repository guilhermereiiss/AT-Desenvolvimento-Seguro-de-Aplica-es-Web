import jwt
from sqlmodel import select
import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

from app.auth.deps import consulta_or_404
from app.auth.security import create_token, decode_token
from app.models import Consulta, Papel, Usuario
from app.ratelimit import limiter
from tests.conftest import SENHA, auth

USUARIO_NOVO = {"email": "novo@t.example", "senha": "OutraSenha12345", "papel": "recepcionista"}


def test_nao_admin_bloqueado_em_rota_de_admin(client, dados):
    """Ex.6: usuário sem papel admin não acessa rota restrita a admin."""
    for u in (dados.recep, dados.prof_a):
        assert client.post("/usuarios", json=USUARIO_NOVO, headers=auth(u)).status_code == 403


def test_admin_sem_mfa_bloqueado_e_com_mfa_permitido(client, dados):
    assert client.post("/usuarios", json=USUARIO_NOVO, headers=auth(dados.admin, otp=False)).status_code == 403
    assert client.post("/usuarios", json=USUARIO_NOVO, headers=auth(dados.admin, otp=True)).status_code == 201


def test_senha_armazenada_com_bcrypt(client, dados, session):
    client.post("/usuarios", json=USUARIO_NOVO, headers=auth(dados.admin, otp=True))
    u = session.exec(select(Usuario).where(Usuario.email == "novo@t.example")).one()
    assert u.senha_hash.startswith("$2") and USUARIO_NOVO["senha"] not in u.senha_hash


def test_login_ok_e_falhas(client, dados):
    ok = client.post("/auth/login", data={"username": "a@t.example", "password": SENHA})
    assert ok.status_code == 200 and ok.json()["token_type"] == "bearer"
    assert client.post("/auth/login", data={"username": "a@t.example", "password": "errada"}).status_code == 401
    assert client.post("/auth/login", data={"username": "naoexiste@t.example", "password": SENHA}).status_code == 401


def test_login_admin_exige_mfa(client, dados):
    base = {"username": "admin@t.example", "password": SENHA}
    assert client.post("/auth/login", data=base).status_code == 401
    assert client.post("/auth/login", data={**base, "mfa_code": "999999"}).status_code == 401
    r = client.post("/auth/login", data={**base, "mfa_code": "000000"})
    assert r.status_code == 200 and "otp" in decode_token(r.json()["access_token"])["amr"]


def test_token_expirado_401(client, dados):
    tok = create_token(sub=str(dados.prof_a.id), typ="user", minutes=-1, amr=["pwd"])
    assert client.get("/consultas", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_token_alg_none_rejeitado(client, dados):
    forjado = jwt.encode({"sub": str(dados.admin.id), "typ": "user"}, key=None, algorithm="none")
    assert client.get("/consultas", headers={"Authorization": f"Bearer {forjado}"}).status_code == 401


def test_decode_com_mock_de_expiracao():
    with patch("app.auth.security.jwt.decode", side_effect=jwt.ExpiredSignatureError):
        with pytest.raises(HTTPException) as e:
            decode_token("qualquer")
    assert e.value.status_code == 401


def test_ownership_unitario_com_mock():
    """Unit: sessão mockada, profissional 2 tenta consulta do profissional 1."""
    sess = MagicMock()
    sess.get.return_value = Consulta(id=1, paciente_id=1, profissional_id=1, motivo="x")
    intruso = Usuario(id=9, email="i@t.example", senha_hash="x", papel=Papel.profissional, profissional_id=2)
    with pytest.raises(HTTPException) as e:
        consulta_or_404(1, intruso, sess)
    assert e.value.status_code == 404
    dono = Usuario(id=8, email="d@t.example", senha_hash="x", papel=Papel.profissional, profissional_id=1)
    assert consulta_or_404(1, dono, sess).id == 1


def test_rate_limit_login(client, dados, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "login_rate_limit", 3)
    limiter.reset()
    codes = [client.post("/auth/login", data={"username": "a@t.example", "password": "x"}).status_code
             for _ in range(4)]
    assert codes == [401, 401, 401, 429]
