# User Feedback MCP

Simple [MCP Server](https://modelcontextprotocol.io/introduction) to enable a human-in-the-loop workflow in tools like [Cline](https://cline.bot) and [Cursor](https://www.cursor.com). This is especially useful for developing desktop applications that require complex user interactions to test.

![Screenshot showing the feedback UI](https://github.com/mrexodia/user-feedback-mcp/blob/main/.github/feedback-ui.png?raw=true)

## Prompt Engineering

For the best results, add the following to your custom prompt:

> Before completing the task, use the user_feedback MCP tool to ask the user for feedback.

This will ensure Cline uses this MCP server to request user feedback before marking the task as completed.

## `.user-feedback.json`

Hitting _Save Configuration_ creates a `.user-feedback.json` file in your project directory that looks like this:

```json
{
  "command": "npm run dev",
  "execute_automatically": false
}
```

This configuration will be loaded on startup and if `execute_automatically` is enabled your `command` will be instantly executed (you will not have to click _Run_ manually). For multi-step commands you should use something like [Task](https://taskfile.dev).

## Installation (Cline)

To install the MCP server in Cline, follow these steps (see screenshot):

![Screenshot showing installation steps](https://github.com/mrexodia/user-feedback-mcp/blob/main/.github/cline-installation.png?raw=true)

1. Install [uv](https://github.com/astral-sh/uv) globally:
   - Windows: `pip install uv`
   - Linux/Mac: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Clone this repository, for this example `C:\MCP\user-feedback-mcp`.
3. Navigate to the Cline _MCP Servers_ configuration (see screenshot).
4. Click on the _Installed_ tab.
5. Click on _Configure MCP Servers_, which will open `cline_mcp_settings.json`.
6. Add the `user-feedback-mcp` server:

```json
{
  "mcpServers": {
    "github.com/mrexodia/user-feedback-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "c:\\MCP\\user-feedback-mcp",
        "run",
        "server.py"
      ],
      "timeout": 600,
      "autoApprove": [
        "user_feedback"
      ]
    }
  }
}

```

## Development

```sh
uv run fastmcp dev server.py
```

This will open a web interface at http://localhost:5173 and allow you to interact with the MCP tools for testing.

## Available tools

```
<use_mcp_tool>
<server_name>github.com/mrexodia/user-feedback-mcp</server_name>
<tool_name>user_feedback</tool_name>
<arguments>
{
  "project_directory": "C:/MCP/user-feedback-mcp",
  "summary": "I've implemented the changes you requested."
}
</arguments>
</use_mcp_tool>
```