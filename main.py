from fastapi import FastAPI
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("MACRO starting up...")
    yield
    # Shutdown
    print("MACRO shutting down...")


app = FastAPI(title="MACRO", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/events/latest")
async def latest_events():
    # TODO: pull from PostgreSQL
    return {"events": []}


@app.get("/signals/active")
async def active_signals():
    # TODO: pull from PostgreSQL
    return {"signals": []}
