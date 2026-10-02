from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db
from app.middleware import add_security_headers
from app.routes import auth, consultas, lab, pacientes, profissionais, usuarios, web

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="API de Agendamento de Consultas",
    version="1.0.0",
    lifespan=lifespan,
    # em produção a superfície de documentação some
    docs_url=None if settings.is_prod else "/docs",
    redoc_url=None,
    openapi_url=None if settings.is_prod else "/openapi.json",
)

add_security_headers(app)
app.add_middleware(  # allowlist explícita, sem "*"
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

for r in (auth.router, usuarios.router, profissionais.router, pacientes.router,
          consultas.router, lab.router, web.router):
    app.include_router(r)
