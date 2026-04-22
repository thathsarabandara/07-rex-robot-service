"""API response utilities"""

from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


def success_response(
    data: Any,
    message: str = "Success",
    status_code: int = 200,
) -> JSONResponse:
    """Create a success response"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data,
        },
    )


def error_response(
    error: str,
    message: str,
    status_code: int = 400,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Create an error response"""
    response = {
        "success": False,
        "error": error,
        "message": message,
    }
    if details:
        response["details"] = details
    
    return JSONResponse(status_code=status_code, content=response)


def paginated_response(
    items: list,
    total: int,
    skip: int,
    limit: int,
    status_code: int = 200,
) -> JSONResponse:
    """Create a paginated response"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": items,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "pages": (total + limit - 1) // limit if limit > 0 else 0,
            },
        },
    )
