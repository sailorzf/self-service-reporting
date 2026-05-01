from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.api import data_types, imports, reports, ai, share

Base.metadata.create_all(bind=engine)

app = FastAPI(title="自助报表系统", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_types.router, prefix="/api/data-types", tags=["data-types"])
app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(share.router, prefix="/api/share", tags=["share"])

@app.get("/api/health")
def health():
    return {"status": "ok"}
