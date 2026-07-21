from __future__ import annotations


class ApplicationError(Exception):
    """Base error that can be safely mapped to an HTTP response."""

    status_code = 500
    code = "application_error"
    public_message = "The request could not be completed."

    def __init__(self, public_message: str | None = None) -> None:
        super().__init__(public_message or self.public_message)
        self.public_message = public_message or self.public_message


class AuthenticationError(ApplicationError):
    status_code = 401
    code = "authentication_required"
    public_message = "A valid bearer token is required."


class RagUnavailableError(ApplicationError):
    status_code = 503
    code = "rag_unavailable"
    public_message = "The RAG service is not configured."


class RagTimeoutError(ApplicationError):
    status_code = 504
    code = "rag_timeout"
    public_message = "The RAG request did not finish within the allowed time."


class RagExecutionError(ApplicationError):
    status_code = 502
    code = "rag_execution_failed"
    public_message = "The RAG service could not complete the request."


class RagEmptyResponseError(ApplicationError):
    status_code = 502
    code = "rag_empty_response"
    public_message = "The RAG service returned no usable answer."
