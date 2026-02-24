from fastapi import APIRouter, Depends

from app.deps.auth import get_current_user
from app.schemas.ask import AskRequest, AskResponse, ChartPayload

router = APIRouter()

def _wants_chart(q: str) -> bool:
    ql = q.lower()
    keywords = ["grafico", "gráfico", "chart", "plot", "barra", "linha", "pizza", "mapa"]
    return any(k in ql for k in keywords)

@router.post("/ask", response_model=AskResponse)
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
