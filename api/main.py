"""
FastAPI application entry point.
"""

import logging
import time
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.routes import health, meetings, todos, decisions, analytics, exports, insights, slack, auth
from api.security import get_auth_token
from api.errors import ErrorResponseDTO, ErrorDTO

LOGGER = logging.getLogger(__name__)

app = FastAPI(
    title="Meeting Brain API",
    version="1.0",
    description="Read-only API for Meeting Brain data"
)

# Log auth status at startup
auth_token = get_auth_token()
if auth_token is None:
    LOGGER.warning(
        "API_AUTH_TOKEN is not set. API endpoints are accessible without authentication (dev mode). "
        "Set API_AUTH_TOKEN in environment to enable authentication."
    )
else:
    LOGGER.info("API authentication enabled (API_AUTH_TOKEN is set)")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP requests with method, path, status, and duration."""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        LOGGER.info(
            "%s %s -> %d (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms
        )
        return response
    except Exception as exc:
        # Re-raise exception so exception handlers can catch it
        duration_ms = (time.time() - start_time) * 1000
        LOGGER.info(
            "%s %s -> exception (%.2f ms)",
            request.method,
            request.url.path,
            duration_ms
        )
        raise


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTPException with standardized error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponseDTO(
            error=ErrorDTO(
                code="http_error",
                message=exc.detail
            )
        ).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with standardized error response."""
    # Extract first error message
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        message = f"Validation error: {first_error.get('msg', 'Invalid request')}"
        if "loc" in first_error:
            loc = first_error["loc"]
            if len(loc) > 1:
                message += f" at {'/'.join(str(x) for x in loc[1:])}"
    else:
        message = "Validation error: Invalid request"
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponseDTO(
            error=ErrorDTO(
                code="validation_error",
                message=message
            )
        ).model_dump()
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with standardized error response."""
    LOGGER.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponseDTO(
            error=ErrorDTO(
                code="internal_error",
                message="Unexpected error"
            )
        ).model_dump()
    )


# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(meetings.router, tags=["meetings"])
app.include_router(todos.router, tags=["todos"])
app.include_router(decisions.router, tags=["decisions"])
app.include_router(analytics.router, tags=["analytics"])
app.include_router(exports.router, tags=["exports"])
app.include_router(insights.router, prefix="/insights", tags=["insights"])
app.include_router(slack.router, prefix="/slack", tags=["slack"])

