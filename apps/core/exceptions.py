"""
Custom DRF exception handler that wraps every error response in a
consistent envelope:

    {
        "success": false,
        "message": "<human readable message>",
        "errors": { ... }   # present only for validation errors
    }
"""

from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        return response

    message = "An error occurred while processing your request."
    errors = None

    if isinstance(response.data, dict):
        detail = response.data.get("detail")
        if detail is not None:
            message = str(detail)
        else:
            # Validation errors: field -> [messages]
            errors = response.data
            message = "Validation failed for one or more fields."
    elif isinstance(response.data, list):
        errors = response.data
        message = "Validation failed for one or more fields."

    payload = {"success": False, "message": message}
    if errors is not None:
        payload["errors"] = errors

    response.data = payload
    return response
