"""
API FastAPI pour l'agent de veille technologique.
Exercice M5E4 : containerisation Docker.
"""
from fastapi import FastAPI
from pydantic import BaseModel

from main import agent_react

app = FastAPI(title="Agent Veille Technologique", version="1.0.0")


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    reponse: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    reponse = agent_react(req.question)
    return AskResponse(reponse=reponse)
