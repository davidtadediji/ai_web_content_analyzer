from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from logger import configured_logger
import os
import modal

# Load environment variables from .env file
load_dotenv()

# Get the app name from environment variables
app_name = os.getenv("APP_NAME")

# Define the Modal image with necessary dependencies
image = modal.Image.debian_slim().pip_install_from_requirements("requirements.txt")

# Create a Modal app
app_modal = modal.App(name=app_name, image=image, mounts=[modal.Mount.from_local_file(".env", remote_path="/root/.env")])

# Define lifespan context for FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    configured_logger.info(f"Starting {app_name} Service...")
    try:
        yield
    finally:
        configured_logger.info(f"Shutting down {app_name} Service...")

# Create the FastAPI app
app = FastAPI(
    title=f"{app_name} Service",
    lifespan=lifespan,  # Define the lifespan context manager
)

# Include your router (assuming it's defined in `router.py`)
from router import router
app.include_router(router)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    configured_logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# Define a root route
@app.get("/", response_class=JSONResponse)
async def root():
    return {"detail": f"Welcome to the Root of the {app_name} Service!"}

# Define the Modal function to serve the FastAPI app
@app_modal.function()
@modal.asgi_app()
def fastapi_app():
    return app

# Local development setup
if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8001, reload=True)
