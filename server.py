from fastmcp import FastMCP
from typing import Annotated
from pydantic import Field
from feedback_ui import feedback_ui, FeedbackResult

# The log_level is necessary for Cline to work: https://github.com/jlowin/fastmcp/issues/81
mcp = FastMCP("User Feedback", log_level="ERROR")

@mcp.tool()
def user_feedback(
    project_directory: Annotated[str, Field(description="Full path to the project directory")],
    summary: Annotated[str, Field(description="Short, one-line summary of the changes")],
) -> FeedbackResult:
    """Request user feedback for a given project directory and summary"""
    return feedback_ui(project_directory, summary)

if __name__ == "__main__":
    mcp.run(transport="stdio")
