import logging
import time
from fastapi import Request

logger = logging.getLogger(__name__)

async def logging_middleware(request: Request, call_next):
    """Log all incoming requests and their processing time"""
    
    # Before processing request
    start_time = time.time()
    
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    logger.debug(f"Headers: {request.headers}")
    
    # Process the request
    response = await call_next(request)
    
    # After processing request
    process_time = time.time() - start_time
    logger.info(f"Request completed in {process_time:.2f}s - Status: {response.status_code}")
    
    # Add processing time to response headers
    response.headers["X-Process-Time"] = str(process_time)
    
    return response