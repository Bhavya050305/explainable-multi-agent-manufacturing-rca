"""
ManuMind AI — MCP Server CLI Entrypoint
Executes the MCP server on stdio transport.
"""

from backend.app.mcp_server.server import run_stdio

if __name__ == "__main__":
    run_stdio()
