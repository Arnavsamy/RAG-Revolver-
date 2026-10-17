"""Small shared bounded tool loop used by bot runs."""
from typing import Any, Callable

def run_agent(task: str, tools: list[tuple[str, Callable[[dict[str, Any]], Any]]], step_limit: int = 6):
    state: dict[str, Any] = {"task": task, "trace": [], "step_limit": step_limit}
    for step, (name, tool) in enumerate(tools[:step_limit], start=1):
        state["trace"].append({"step": step, "tool": name, "status": "started"})
        try:
            state[name] = tool(state)
            state["trace"][-1]["status"] = "completed"
        except Exception as exc:
            state["trace"][-1].update({"status": "error", "error": str(exc)})
            break
    state["stopped_at_limit"] = len(state["trace"]) >= step_limit and len(tools) > step_limit
    return state
