from fastapi.responses import JSONResponse


def error_response(status_code: int, message: str) -> JSONResponse:
    """Return JSON response representing a standardized error message."""
    return JSONResponse(
        status_code=status_code,
        content={"message": message}
    )
