from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from prompt_vault.database import create_db
from prompt_vault.routes import api, gateway, ui

app = FastAPI(title="Prompt Vault", version="0.1.0")

app.mount("/static", StaticFiles(directory="prompt_vault/static"), name="static")
app.include_router(api.router)
app.include_router(gateway.router)
app.include_router(ui.router)


@app.on_event("startup")
def on_startup():
    create_db()
