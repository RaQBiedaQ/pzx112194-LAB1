# ai-generated: 90% - Claude (AI assistant) generated this module under the student's direction (decisions, review, testing)
"""A uniform {"error": {"code", "message"}} JSON error shape (API.md section 7).

ApiError itself has no FastAPI dependency, so plain business-logic modules (sla.py, metrics.py) can
raise it and be unit-tested without importing FastAPI at all; the handlers below are the only part
that needs the framework, and are imported lazily by main.py.
"""


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def api_error_handler(request, exc: ApiError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


async def validation_error_handler(request, exc):
    from fastapi.responses import JSONResponse
    # Catches FastAPI/Pydantic's own RequestValidationError and reshapes it into API.md's format.
    return JSONResponse(status_code=422, content=error_body("validation", str(exc)))


async def http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    # Catches Starlette's own HTTPException (e.g. malformed JSON body, routing 405s) uniformly.
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    code = "not_found" if exc.status_code == 404 else "validation"
    return JSONResponse(status_code=exc.status_code, content=error_body(code, detail))
