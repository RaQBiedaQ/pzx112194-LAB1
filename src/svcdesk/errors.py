# ai-generated: 90% - Claude (AI assistant) generated this module under the student's direction (decisions, review, testing)
"""A uniform {"error": {"code", "message"}} JSON error shape (API.md section 7)."""
from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


async def validation_error_handler(request: Request, exc) -> JSONResponse:
    # Catches FastAPI/Pydantic's own RequestValidationError and reshapes it into API.md's format.
    return JSONResponse(status_code=422, content=error_body("validation", str(exc)))


async def http_exception_handler(request: Request, exc) -> JSONResponse:
    # Catches Starlette's own HTTPException (e.g. malformed JSON body, routing 405s) uniformly.
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    code = "not_found" if exc.status_code == 404 else "validation"
    return JSONResponse(status_code=exc.status_code, content=error_body(code, detail))
