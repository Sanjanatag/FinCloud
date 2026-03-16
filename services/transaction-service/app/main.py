import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FinCloud Transaction Service",
    description="Transaction processing microservice for the FinCloud fintech platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1/transactions", tags=["transactions"])


@app.on_event("startup")
def startup():
    logger.info("Starting Transaction Service...")
    logger.info("Transaction Service started successfully")
