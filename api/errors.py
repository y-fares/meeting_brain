"""
Standardized error response DTOs.
"""

from pydantic import BaseModel


class ErrorDTO(BaseModel):
    """Error details."""
    code: str
    message: str


class ErrorResponseDTO(BaseModel):
    """Standardized error response envelope."""
    error: ErrorDTO

