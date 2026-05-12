from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .._metadata import app_name, dist_dir
from .config import AppConfig
from .router import api
from .runtime import Runtime
from .utils import add_not_found_handler
from .logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = AppConfig()
    logger.info(f"Starting app with configuration:\n{config}")

    runtime = Runtime(config)
    # Eagerly initialize lakebase (falls back to mock if unavailable)
    # so the first requests don't stall waiting for a failed connection.
    _ = runtime.lakebase

    app.state.config = config
    app.state.runtime = runtime

    yield


app = FastAPI(title=f"{app_name}", lifespan=lifespan)
ui = StaticFiles(directory=dist_dir, html=True)

app.include_router(api)
app.mount("/", ui)

add_not_found_handler(app)
