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


class AgentUnavailableError(ApplicationError):
    status_code = 503
    code = "agent_unavailable"
    public_message = "The agent is not configured."


class AgentTimeoutError(ApplicationError):
    status_code = 504
    code = "agent_timeout"
    public_message = "The agent did not finish within the allowed time."


class AgentLimitError(ApplicationError):
    status_code = 429
    code = "agent_limit_exceeded"
    public_message = "The agent reached an execution safety limit."


class AgentExecutionError(ApplicationError):
    status_code = 502
    code = "agent_execution_failed"
    public_message = "The model provider could not complete the request."


class AgentEmptyResponseError(ApplicationError):
    status_code = 502
    code = "agent_empty_response"
    public_message = "The agent returned no usable response."
