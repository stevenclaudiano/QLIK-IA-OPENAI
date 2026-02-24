from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Any, Dict, List
import asyncpg
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from db import get_connection
from security import (
    verify_password,
    create_access_token,
    hash_password,
    decode_access_token,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Auth / JWT Helpers
# -----------------------------
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Token ausente (Authorization: Bearer ...)")

    token = creds.credentials

    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    user_id = payload.get("user_id")
    role = payload.get("role")

    if not user_id:
        raise HTTPException(status_code=401, detail="Token sem user_id")

    conn = await get_connection()
    try:
        user = await conn.fetchrow(
            """
            SELECT id, username, email, role, is_active
            FROM auth.users
            WHERE id = $1
            LIMIT 1
            """,
            user_id,
        )

        if not user:
            raise HTTPException(status_code=401, detail="Usuário não existe")

        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="Usuário inativo")

        return {
            "id": str(user["id"]),
            "username": user["username"],
            "email": user["email"],
            "role": user["role"] or role,
        }
    finally:
        await conn.close()


# -----------------------------
# Pydantic Models
# -----------------------------
class LoginRequest(BaseModel):
    login: str
    password: str


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class ChartPayload(BaseModel):
    type: str  # "bar", "line", "pie"...
    title: str
    labels: List[str]
    datasets: List[Dict[str, Any]]  # compatível com Chart.js / flexível


class AskResponse(BaseModel):
    ok: bool
    answer: str
    chart: Optional[ChartPayload] = None
    meta: Optional[Dict[str, Any]] = None


# -----------------------------
# Endpoints - Auth
# -----------------------------
@app.post("/api/auth/login")
async def login(data: LoginRequest):
    conn = await get_connection()
    try:
        user = await conn.fetchrow(
            """
            SELECT id, username, email, password_hash, role, is_active
            FROM auth.users
            WHERE username = $1 OR email = $1
            LIMIT 1
            """,
            data.login,
        )

        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")

        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="Usuário inativo")

        if not verify_password(data.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Senha inválida")

        token = create_access_token(
            {"user_id": str(user["id"]), "role": user["role"]}
        )

        return {
            "ok": True,
            "token": token,
            "user": {
                "id": str(user["id"]),
                "username": user["username"],
                "role": user["role"],
            },
        }
    finally:
        await conn.close()

# Criar um admin para testes (endpoint protegido, só rodar uma vez e depois comentar ou proteger melhor)
@app.post("/api/auth/create-admin")
async def create_admin():
    conn = await get_connection()
    try:
        table_exists = await conn.fetchval("SELECT to_regclass('auth.users') IS NOT NULL")
        if not table_exists:
            raise HTTPException(
                status_code=500,
                detail="Tabela auth.users não existe. Rode o SQL de criação do schema/tabela.",
            )

        exists = await conn.fetchval(
            "SELECT 1 FROM auth.users WHERE username=$1 OR email=$2",
            "admin",
            "admin@local",
        )
        if exists:
            raise HTTPException(status_code=409, detail="Admin já existe")

        hashed = hash_password("12345678")
        await conn.execute(
            """
            INSERT INTO auth.users (username, email, password_hash, role)
            VALUES ($1, $2, $3, $4)
            """,
            "admin",
            "admin@local",
            hashed,
            "admin",
        )

        return {"ok": True}

    except HTTPException:
        raise
    except asyncpg.PostgresError as e:
        raise HTTPException(status_code=500, detail=f"Erro Postgres: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {type(e).__name__}: {str(e)}")
    finally:
        await conn.close()


@app.get("/api/auth/me")
async def me(current_user=Depends(get_current_user)):
    return {"ok": True, "user": current_user}


# -----------------------------
# Endpoints - Ask (protected)
# -----------------------------
def _wants_chart(q: str) -> bool:
    ql = q.lower()
    keywords = ["grafico", "gráfico", "chart", "plot", "barra", "linha", "pizza", "mapa"]
    return any(k in ql for k in keywords)


@app.post("/api/ask", response_model=AskResponse)
async def ask(data: AskRequest, current_user=Depends(get_current_user)):
    q = data.question.strip()

    answer = (
        f"Entendi sua pergunta: '{q}'.\n"
        f"Usuário autenticado: {current_user['username']} (role={current_user['role']}).\n"
        "Modo atual: MOCK (sem Qlik)."
    )

    chart = None
    if _wants_chart(q):
        chart = ChartPayload(
            type="bar",
            title="Exemplo (mock) - Top 5 categorias",
            labels=["A", "B", "C", "D", "E"],
            datasets=[{"label": "Quantidade", "data": [12, 9, 7, 5, 3]}],
        )
        answer += "\nTambém gerei um payload de gráfico (mock)."

    return AskResponse(
        ok=True,
        answer=answer,
        chart=chart,
        meta={"mode": "mock", "user_id": current_user["id"]},
    )