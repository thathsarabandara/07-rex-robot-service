import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler to return error responses with unified {"message": "..."} payload."""
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
        if errors:
            err = errors[0]
            field = ".".join(str(loc) for loc in err.get("loc", []))
            msg = err.get("msg", "invalid input")
            message = f"Validation failed: {msg} on {field}"
        else:
            message = "Validation error"
            
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": message}
        )
    
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.detail}
        )
        
    logger.exception(f"Unhandled exception encountered: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An internal server error occurred"}
    )
