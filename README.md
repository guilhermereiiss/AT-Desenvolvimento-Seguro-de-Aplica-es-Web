# API de Agendamento de Consultas

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # preencha os valores (SECRET_KEY etc.)
SEED_PASSWORD='SuaSenha12345' python -m scripts.seed
uvicorn app.main:app --reload
pytest -q
```
Docs: http://localhost:8000/docs · Agenda HTML: `/agenda` (faça login em `/auth/login` antes; admin envia `mfa_code`).
