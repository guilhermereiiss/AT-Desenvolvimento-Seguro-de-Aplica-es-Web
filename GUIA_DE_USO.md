# Guia de Uso da API — DR2 AT (Segurança de APIs)

API de agendamento de consultas para clínicas (FastAPI + SQLModel + JWT/OAuth2).

## Links da entrega


| Item                             | Link                                                                          |
| -------------------------------- | ----------------------------------------------------------------------------- |
| Projeto no GitHub                | https://github.com/guilhermereiiss/AT-Desenvolvimento-Seguro-de-Aplica-es-Web |
| Vídeo no YouTube (não listado) | https://youtu.be/apNllafHHmA?si=J-I-BCc-2sfNaCrW                              |
| Relatório técnico              | [`docs/RELATORIO.md`](docs/RELATORIO.md)                                      |

## Onde ver o relatório


| O que                                   | Onde                                                                                              |
| --------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Relatório técnico (Markdown)          | No GitHub, abra a pasta`docs/` e clique em `RELATORIO.md`. Ele aparece formatado, com as tabelas. |
| Relatório técnico (Word)              | `Relatorio_DR2_AT.docx`, dentro do ZIP da entrega                                                 |
| Código vulnerável do Ex. 8            | `docs/evidencias/ex08_codigo_vulneravel.py`                                                       |
| Pipeline de segurança (Ex. 12)         | `.github/workflows/security.yml`                                                                  |
| Resultado do pipeline e do ZAP (Ex. 13) | Aba**Actions** do GitHub → run mais recente → **Artifacts** → `zap-report`                     |
| Testes automatizados                    | Pasta`tests/` (26 testes)                                                                         |
| Testes no Postman                       | Pasta`postman/`                                                                                   |

## Como usar a API (Windows / PowerShell)

Requisitos: Python 3.12+, Git e Postman.

**1. Baixar o projeto**

```powershell
git clone https://github.com/guilhermereiiss/AT-Desenvolvimento-Seguro-de-Aplica-es-Web.git
cd AT-Desenvolvimento-Seguro-de-Aplica-es-Web
```

**2. Criar e ativar o ambiente virtual**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se der erro de execução de scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. No Linux/Mac use `source .venv/bin/activate`.

**3. Instalar as dependências**

```powershell
pip install -r requirements-dev.txt
```

**4. Rodar os testes** (não precisa de `.env`)

```powershell
pytest -q
```

Esperado: `26 passed`.

**5. Criar o `.env` com segredos aleatórios**

```powershell
Copy-Item .env.example .env
python -c "import re,secrets,pathlib; p=pathlib.Path('.env'); t=p.read_text(encoding='utf-8'); t=re.sub(r'(?m)^SECRET_KEY=.*','SECRET_KEY='+secrets.token_hex(32),t); t=re.sub(r'(?m)^MFA_SIMULATED_CODE=.*','MFA_SIMULATED_CODE='+secrets.token_hex(3),t); t=re.sub(r'(?m)^LAB_CLIENT_SECRET=.*','LAB_CLIENT_SECRET='+secrets.token_urlsafe(24),t); t=re.sub(r'(?m)^LOGIN_RATE_LIMIT=.*','LOGIN_RATE_LIMIT=30',t); p.write_text(t,encoding='utf-8')"
```

O `.env` nunca vai para o GitHub (está no `.gitignore`). `LOGIN_RATE_LIMIT=30` é só para a demo.

**6. Criar o banco e os usuários** (senha de 12+ caracteres, com letras e números)

```powershell
$env:SEED_PASSWORD = "SuaSenha12345"
python -m scripts.seed
```

Esperado: `Seed ok.`

**7. Subir a API**

```powershell
uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000/docs (Swagger). Deixe esse terminal aberto.

## Usuários e papéis


| Usuário (criado pelo seed) | Papel              | Pode                                                     |
| --------------------------- | ------------------ | -------------------------------------------------------- |
| `admin@clinica.example`     | admin              | Tudo; o login exige o`mfa_code`                          |
| `recepcao@clinica.example`  | recepcionista      | Cadastrar pacientes e ver a agenda; não cria consulta   |
| `ana@clinica.example`       | profissional       | Criar e gerir só as próprias consultas                 |
| Laboratório parceiro (M2M) | client credentials | Só`GET /lab/horarios-disponiveis` (escopo `slots:read`) |

## Principais endpoints


| Rota                                    | Para quê                                           | Quem acessa                                      |
| --------------------------------------- | --------------------------------------------------- | ------------------------------------------------ |
| `POST /auth/login`                      | Login (form: username, password, mfa_code p/ admin) | Público (com rate limit)                        |
| `POST /oauth/token`                     | Token do laboratório (client_credentials)          | Laboratório                                     |
| `POST /usuarios`                        | Criar usuário                                      | Admin (com MFA)                                  |
| `POST /pacientes`, `GET /pacientes`     | Cadastrar e buscar pacientes                        | Recepção e admin; profissional só vê os seus |
| `POST /consultas`                       | Criar consulta                                      | Profissional, admin                              |
| `GET /consultas`, `GET /consultas/{id}` | Listar e ver consulta                               | Todos os papéis (profissional só as suas)      |
| `PATCH` / `DELETE /consultas/{id}`      | Atualizar e cancelar                                | Profissional dono, admin                         |
| `GET /lab/horarios-disponiveis`         | Horários livres de um profissional                 | Token do laboratório                            |
| `GET /agenda?data=AAAA-MM-DD`           | Página HTML da agenda do dia                       | Logado (cookie ou token)                         |

## Problemas comuns


| Sintoma                           | Causa e solução                                                                                                                             |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Login`401 Credenciais inválidas` | `senha_seed` do Postman diferente da usada no seed. Pare a API, rode `Remove-Item clinicas.db -Force`, repita o passo 6 e suba a API de novo. |
| `401 Token inválido ou expirado` | O token vale 15 minutos. Faça o login de novo (pasta 1).                                                                                     |
| `429 Muitas tentativas`           | Rate limit do login. Espere 1 minuto, ou use`LOGIN_RATE_LIMIT=30` no `.env` e reinicie a API.                                                 |
| Mudei o`.env` e nada mudou        | O`.env` só é lido ao iniciar. Pare a API (Ctrl+C) e suba de novo.                                                                           |
