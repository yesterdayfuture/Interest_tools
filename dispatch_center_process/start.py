#!/usr/bin/env python3
"""应用启动脚本."""

import uvicorn

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("start")


if __name__ == "__main__":
    logger.info(
        f"Starting {settings.APP_NAME} on {settings.HOST}:{settings.PORT}"
    )
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
