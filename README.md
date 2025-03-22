# User Feedback MCP

This is a project based on [FastMCP](https://github.com/jlowin/fastmcp), to make it easier for the LLM to collect user feedback that requires manual interaction. For more information about the Model Context Protol, see [this post](https://glama.ai/blog/2024-11-25-model-context-protocol-quickstart).

## Installation (Cline)

To install the MCP server in Cline, follow these steps (see screenshot):

![Screenshot showing installation steps](.github/cline-installation.png)

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
    "user-feedback-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "c:\\MCP\\user-feedback-mcp",
        "run",
        "server.py"
      ],
      "timeout": 3600
    }
  }
}

```

## Development

```sh
uv run fastmcp dev server.py
```

This will open a web interface at http://localhost:5173 and allow you to interact with the MCP tools for testing.
