from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    # If response is None, it means a generic 500 error (server crash)
    if response is None:
        return Response({
            "error": "Internal Server Error",
            "detail": str(exc) # For debugging (Remove in production)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Standardize error format
    return Response({
        "error": "Request Failed",
        "detail": response.data
    }, status=response.status_code)