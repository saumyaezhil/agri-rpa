from fastapi import FastAPI
from .database import Base, engine
from .routes.applications import router as application_router
from .routes.documents import router as document_router
from .routes.verification import router as verification_router
from .routes.rpa import router as rpa_router
from .routes.status import router as status_router

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Agricultural e-Governance RPA",
    description="Hybrid AI + RPA platform for agricultural service requests",
    version="0.1.0"
)


app.include_router(application_router)
app.include_router(document_router)
app.include_router(verification_router)
app.include_router(rpa_router)
app.include_router(status_router)




@app.get("/")
def root():
    return {
        "system": "Agricultural e-Governance RPA",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

