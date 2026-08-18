class AgentError(Exception):
    """Base exception for agent errors."""
    pass

class AgentTimeoutError(AgentError):
    pass

class AgentCancelledError(AgentError):
    pass

class AgentValidationError(AgentError):
    pass