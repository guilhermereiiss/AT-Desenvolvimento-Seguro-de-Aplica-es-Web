from datetime import timedelta

from app.auth.security import create_token
from app.models import Consulta
from tests.conftest import auth


def test_bola_profissional_nao_acessa_consulta_alheia(client, dados):
    """Ex.8/9: trocar o ID na URL não vaza dado de outro profissional."""
    cid = dados.consulta.id
    assert client.get(f"/consultas/{cid}", headers=auth(dados.prof_a)).status_code == 200
    assert client.get(f"/consultas/{cid}", headers=auth(dados.prof_b)).status_code == 404
    # mesmo padrão em outros endpoints (Ex.9: endpoint adicional corrigido)
    assert client.patch(f"/consultas/{cid}", json={"motivo": "Hack"}, headers=auth(dados.prof_b)).status_code == 404
    assert client.delete(f"/consultas/{cid}", headers=auth(dados.prof_b)).status_code == 404
    assert client.get(f"/pacientes/{dados.pac.id}", headers=auth(dados.prof_b)).status_code == 404
    assert client.get(f"/pacientes/{dados.pac.id}", headers=auth(dados.prof_a)).status_code == 200


def test_mass_assignment_bloqueado(client, dados):
    body = {"paciente_id": dados.pac.id, "data_hora": (dados.amanha + timedelta(hours=4)).isoformat(),
            "motivo": "Consulta de rotina", "status": "concluida", "criado_por": 1, "profissional_id": 999}
    r = client.post("/consultas", json=body, headers=auth(dados.prof_a))
    assert r.status_code == 422 or r.json()["profissional_id"] == dados.pa.id
    extra = {"papel": "admin"}
    assert client.patch(f"/consultas/{dados.consulta.id}", json=extra, headers=auth(dados.prof_a)).status_code == 422


def test_xss_rejeitado_na_entrada(client, dados):
    body = {"paciente_id": dados.pac.id, "data_hora": (dados.amanha + timedelta(hours=5)).isoformat(),
            "motivo": "<script>alert(1)</script>"}
    assert client.post("/consultas", json=body, headers=auth(dados.prof_a)).status_code == 422


def test_xss_escapado_na_saida_html(client, dados, session):
    """Defesa em profundidade: mesmo se dado sujo já estiver no banco, o Jinja2 escapa."""
    c = session.get(Consulta, dados.consulta.id)
    c.motivo = "<script>alert('xss')</script>"
    session.add(c)
    session.commit()
    r = client.get(f"/agenda?data={dados.amanha.date().isoformat()}", headers=auth(dados.recep))
    assert r.status_code == 200
    assert "<script>alert" not in r.text and "&lt;script&gt;" in r.text
    assert "SEGREDO-INTERNO" not in r.text and "12345678901" not in r.text


def test_agenda_exige_login(client, dados):
    assert client.get("/agenda").status_code == 401


def test_sqli_nas_queries_rejeitado(client, dados):
    h = auth(dados.recep)
    assert client.get("/pacientes", params={"q": "' OR '1'='1"}, headers=h).status_code == 422
    assert client.get("/consultas", params={"status": "x' OR 1=1--"}, headers=h).status_code == 422
    # payload passa como dado literal no login (parametrizado) e falha só por credencial
    r = client.post("/auth/login", data={"username": "' OR 1=1--", "password": "x"})
    assert r.status_code == 401


def test_headers_de_seguranca(client, dados):
    r = client.get("/consultas", headers=auth(dados.recep))
    assert "max-age" in r.headers["strict-transport-security"]
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_cors_allowlist(client):
    ok = client.options("/consultas", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    ruim = client.options("/consultas", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in ruim.headers


def test_lab_m2m_fluxo_e_isolamento(client, dados):
    r = client.post("/oauth/token", data={"grant_type": "client_credentials", "client_id": "lab-parceiro",
                                          "client_secret": "segredo-lab-de-teste"})
    assert r.status_code == 200
    lab = {"Authorization": "Bearer " + r.json()["access_token"]}
    q = {"data": dados.amanha.date().isoformat(), "profissional_id": dados.pa.id}
    slots = client.get("/lab/horarios-disponiveis", params=q, headers=lab)
    assert slots.status_code == 200 and dados.amanha.isoformat() not in [s["data_hora"] for s in slots.json()]
    # token do lab NÃO acessa dados de consultas/pacientes
    assert client.get("/consultas", headers=lab).status_code == 401
    assert client.get(f"/pacientes/{dados.pac.id}", headers=lab).status_code == 401
    # token de profissional NÃO acessa rota do lab
    assert client.get("/lab/horarios-disponiveis", params=q, headers=auth(dados.prof_a)).status_code == 403
    # token m2m com escopo errado
    ruim = create_token(sub="lab-parceiro", typ="m2m", scope="outro:escopo")
    assert client.get("/lab/horarios-disponiveis", params=q, headers={"Authorization": f"Bearer {ruim}"}).status_code == 403


def test_oauth_credenciais_e_escopo_invalidos(client):
    base = {"grant_type": "client_credentials", "client_id": "lab-parceiro"}
    assert client.post("/oauth/token", data={**base, "client_secret": "errado"}).status_code == 401
    assert client.post("/oauth/token", data={**base, "client_secret": "segredo-lab-de-teste",
                                              "scope": "consultas:write"}).status_code == 400
    assert client.post("/oauth/token", data={**base, "client_secret": "segredo-lab-de-teste",
                                              "grant_type": "password"}).status_code == 400


def test_auditoria_openapi(client):
    """Ex.13: OpenAPI sem campos internos, rotas protegidas e entrada estrita."""
    spec = client.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]
    for nome in ("ConsultaPublic", "PacientePublic"):
        props = set(schemas[nome]["properties"])
        assert not props & {"observacoes_internas", "criado_por", "cpf", "senha_hash"}
    for nome in ("ConsultaCreate", "ConsultaUpdate", "PacienteCreate", "UsuarioCreate"):
        assert schemas[nome].get("additionalProperties") is False
    publicos = {"/auth/login", "/oauth/token"}
    for path, ops in spec["paths"].items():
        if path in publicos:
            continue
        for op in ops.values():
            assert op.get("security"), f"{path} sem security"
