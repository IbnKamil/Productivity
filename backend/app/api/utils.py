from fastapi import Request


def envelope(request: Request, data):
    return {
        "success": True,
        "data": data,
        "request_id": request.state.request_id,
        "correlation_id": request.state.correlation_id,
    }
