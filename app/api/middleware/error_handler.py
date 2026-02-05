import datetime
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

async def error_handler_middleware(request: Request, call_next):
    """Catch and handle all errors gracefully"""
    
    try:
        # Try to process the request
        response = await call_next(request)
        return response
        
    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Validation Error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        # Handle any unexpected errors
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "timestamp": datetime.datetime.now().isoformat()
            }
        )