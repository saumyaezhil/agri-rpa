from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine

from .routes.applications import (
    router as application_router
)

from .routes.documents import (
    router as document_router
)

from .routes.verification import (
    router as verification_router
)

from .routes.rpa import (
    router as rpa_router
)

from .routes.status import (
    router as status_router
)

from .routes.review import (
    router as review_router
)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

Base.metadata.create_all(
    bind=engine
)


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="Agricultural e-Governance RPA",
    description=(
        "Hybrid AI + RPA platform "
        "for agricultural service requests"
    ),
    version="0.1.0"
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",

        "http://127.0.0.1:8080",
        "http://localhost:8080"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# --------------------------------------------------
# ROUTES
# --------------------------------------------------

app.include_router(
    application_router
)

app.include_router(
    document_router
)

app.include_router(
    verification_router
)

app.include_router(
    rpa_router
)

app.include_router(
    status_router
)

app.include_router(
    review_router
)


# --------------------------------------------------
# ROOT
# --------------------------------------------------

@app.get("/")
def root():

    return {
        "system":
            "Agricultural e-Governance RPA",

        "status":
            "running"
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():

    return {
        "status":
            "healthy"
    }
