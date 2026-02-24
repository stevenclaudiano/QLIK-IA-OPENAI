from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.db import get_connection
from app.core.security import decode_access_token

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
