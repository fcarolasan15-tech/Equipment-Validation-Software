from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, admin, assets, projects, records, templates

app = FastAPI(
    title="DMPI Equipment Validation Software",
    description="Regulated validation document management — DQ→Protocol→IQ→OQ→PQ→Report lifecycle",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(assets.router)
app.include_router(projects.router)
app.include_router(records.router)
app.include_router(templates.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": "DMPI EVS"}
