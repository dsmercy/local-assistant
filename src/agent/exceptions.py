class AgentDepthError(Exception):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Agent exceeded max tool-call depth of {limit}.")


class AgentStuckError(Exception):
    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Agent is stuck repeating '{tool_name}'. Stopping.")
