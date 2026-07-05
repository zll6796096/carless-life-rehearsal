from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import data_quality, diagnosis, fixtures, rehearsals
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(fixtures.router)
app.include_router(diagnosis.router)
app.include_router(rehearsals.router)
app.include_router(data_quality.router)
