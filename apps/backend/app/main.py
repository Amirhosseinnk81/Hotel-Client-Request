from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import setup_logging
import logging
from app.core.exceptions import global_exception_handler
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "Hotel Client Request API",
    }
    
app.add_exception_handler(
    Exception,
    global_exception_handler,
)

setup_logging()
logger = logging.getLogger(__name__)
    
@app.on_event("startup")
async def startup_event():
    logger.info("Application started successfully.")
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application stopped.")