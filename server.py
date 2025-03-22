from fastmcp import FastMCP
from feedback_ui import feedback_ui, FeedbackResult

# The log_level is necessary for Cline to work: https://github.com/jlowin/fastmcp/issues/81
mcp = FastMCP("User Feedback", log_level="ERROR")

@mcp.tool()
def user_feedback(project_directory: str, prompt: str) -> FeedbackResult:
    """Request user feedback for a given project directory and prompt"""
    return feedback_ui(project_directory, prompt)

if __name__ == "__main__":
    mcp.run(transport="stdio")
