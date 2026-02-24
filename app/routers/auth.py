import asyncpg
from fastapi import APIRouter, HTTPException, Depends

from app.core.db import get_connection
from app.core.security import verify_password, create_access_token, hash_password
from app.deps.auth import get_current_user
from app.schemas.auth import LoginRequest

router = APIRouter()

@router.post("/login")
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

        token = create_access_token({"user_id": str(user["id"]), "role": user["role"]})

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

@router.post("/create-admin")
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

@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return {"ok": True, "user": current_user}
