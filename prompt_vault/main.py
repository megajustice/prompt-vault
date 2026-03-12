import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from prompt_vault.database import create_db
from prompt_vault.migrate import run_migrations
from prompt_vault.routes import api, gateway, openai_compat, ui

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="Prompt Vault", version="0.2.0")

app.mount("/static", StaticFiles(directory="prompt_vault/static"), name="static")
app.include_router(api.router)
app.include_router(gateway.router)
app.include_router(openai_compat.router)
app.include_router(ui.router)


@app.on_event("startup")
def on_startup():
    run_migrations()
    create_db()
    logging.getLogger("prompt_vault").info("Prompt Vault v0.2 started")
