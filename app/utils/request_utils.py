"""Utility functions for request handling"""

from typing import Dict, Any, Optional
from fastapi import Request


async def extract_ip_address(request: Request) -> str:
    """
    Extract client IP address from request.
    Handles X-Forwarded-For and other proxy headers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (proxy)
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    
    # Check other proxy headers
    if "x-real-ip" in request.headers:
        return request.headers["x-real-ip"]
    
    # Use client IP from request
    if request.client:
        return request.client.host
    
    return "0.0.0.0"


def extract_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request"""
    return request.headers.get("user-agent")
