"""Consistent, friendly error responses.

Every validation failure is returned as:

    {"detail": "Please correct the highlighted fields.",
     "field_errors": {"preferred_date": "Please choose a date in the future."}}

so the frontend can show each message next to its form field.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

FORM_ERROR_DETAIL = "Please correct the highlighted fields."


class FieldValidationError(Exception):
    """Raised by services when input is well-formed but breaks a business rule."""

    def __init__(self, field_errors: dict[str, str]):
        super().__init__(FORM_ERROR_DETAIL)
        self.field_errors = field_errors


def _friendly_message(error: dict) -> str:
    error_type = error.get("type", "")
    if error_type == "missing":
        return "This field is required."
    if error_type.startswith("date") or error_type.startswith("datetime"):
        return "Please enter a valid date."
    if error_type == "string_too_long":
        return "This entry is too long."
    if error_type == "string_type":
        return "Please enter text."
    if error_type in ("literal_error", "enum"):
        return "Please choose one of the options."
    if error_type == "bool_type":
        return "Please answer yes or no."
    if error_type == "too_long":
        return "Too many items selected."
    message = str(error.get("msg", "This value is not valid."))
    return message.removeprefix("Value error, ")


def validation_error_response(field_errors: dict[str, str]) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": FORM_ERROR_DETAIL, "field_errors": field_errors})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        field_errors: dict[str, str] = {}
        for error in exc.errors():
            location = [part for part in error.get("loc", ()) if part not in ("body", "query", "path", "header")]
            # Use the top-level field name, so an error in a list item
            # ("symptom_ids", 2) is reported under "symptom_ids".
            names = [part for part in location if isinstance(part, str)]
            field = names[0] if names else "form"
            # Keep the first (most relevant) message per field.
            field_errors.setdefault(field, _friendly_message(error))
        return validation_error_response(field_errors)

    @app.exception_handler(FieldValidationError)
    async def handle_field_validation(_request: Request, exc: FieldValidationError) -> JSONResponse:
        return validation_error_response(exc.field_errors)
