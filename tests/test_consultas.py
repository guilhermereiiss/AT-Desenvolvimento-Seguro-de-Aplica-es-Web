from datetime import timedelta

from tests.conftest import auth


def test_criar_consulta_sucesso(client, dados):
    """Ex.1: caminho de sucesso do endpoint de consultas."""
    body = {"paciente_id": dados.pac.id, "data_hora": (dados.amanha + timedelta(hours=2)).isoformat(),
            "motivo": "Consulta de rotina"}
    r = client.post("/consultas", json=body, headers=auth(dados.prof_a))
    assert r.status_code == 201
    j = r.json()
    assert j["profissional_id"] == dados.pa.id and j["status"] == "agendada"
    # Ex.2: response model não vaza campos internos
    assert set(j) == {"id", "paciente_id", "profissional_id", "data_hora", "motivo", "status"}


def test_listar_consultas_sem_campos_internos(client, dados):
    r = client.get("/consultas", headers=auth(dados.recep))
    assert r.status_code == 200 and len(r.json()) == 1
    assert "SEGREDO-INTERNO" not in r.text and "criado_por" not in r.text


def test_conflito_de_horario(client, dados):
    body = {"paciente_id": dados.pac.id, "data_hora": dados.amanha.isoformat(), "motivo": "Outro motivo"}
    assert client.post("/consultas", json=body, headers=auth(dados.prof_a)).status_code == 409


def test_recepcionista_nao_cria_consulta(client, dados):
    body = {"paciente_id": dados.pac.id, "data_hora": (dados.amanha + timedelta(hours=3)).isoformat(),
            "motivo": "Consulta de rotina"}
    assert client.post("/consultas", json=body, headers=auth(dados.recep)).status_code == 403


def test_sem_token_401(client, dados):
    assert client.get("/consultas").status_code == 401
