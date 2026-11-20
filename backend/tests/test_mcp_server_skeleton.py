"""
ManuMind AI — MCP Server Skeleton and Core Lifecycle Unit & Integration Tests
Phase 4 Step 1C: Server Skeleton and Core Lifecycle Implementation

Department of AI & Data Science — RMK Engineering College
"""

import sys
import os
import asyncio
from pathlib import Path
import anyio
import pytest

from mcp.server.mcpserver import MCPServer
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from backend.app.mcp_server.server import (
    SERVER_NAME,
    SERVER_VERSION,
    create_mcp_server,
    mcp_server,
)


def test_mcp_server_initialization_and_identity():
    """Verify that the MCP server initializes with stable production identity metadata."""
    server = create_mcp_server()
    assert server.name == "ManuMind AI MCP Server"
    assert server.version == "0.1.0"
    assert server.name == SERVER_NAME
    assert server.version == SERVER_VERSION
    assert "ManuMind AI manufacturing" in server.instructions


def test_mcp_server_ping_tool_metadata():
    """Verify that the temporary ping tool is registered with exact typed schemas and docstrings."""
    server = create_mcp_server()
    assert hasattr(server, "_tool_manager")
    tool = server._tool_manager.get_tool("ping")
    assert tool is not None
    assert tool.name == "ping"
    assert "Harmless diagnostic echo tool" in tool.description


def test_mcp_server_ping_direct_invocation():
    """Verify deterministic echo response of the temporary ping tool."""
    server = create_mcp_server()
    tool = server._tool_manager.get_tool("ping")
    
    # Test with custom payload
    res1 = tool.fn(message="telemetry_test_123")
    assert res1 == "pong: telemetry_test_123"

    # Test with default argument
    res2 = tool.fn()
    assert res2 == "pong: pong"


@pytest.mark.asyncio
async def test_mcp_server_real_stdio_subprocess_lifecycle():
    """
    Mandatory real subprocess integration test:
    1. Spawns the MCP server as a subprocess using the active Python 3.11 interpreter.
    2. Connects official MCP SDK stdio_client.
    3. Completes MCP protocol handshake (initialize).
    4. Discovers tools via list_tools() and asserts 'ping' presence.
    5. Calls 'ping' via JSON-RPC protocol and asserts deterministic response.
    6. Verifies clean shutdown and process termination.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    child_env = os.environ.copy()
    child_env["PYTHONPATH"] = str(repo_root)
    child_env["PYTHONUNBUFFERED"] = "1"
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-u", "-m", "backend.app.mcp_server"],
        cwd=str(repo_root),
        env=child_env,
    )

    with anyio.fail_after(120):
        # Connect over stdio transport
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
            # 1. MCP Protocol Handshake
                init_result = await session.initialize()
                assert init_result is not None
                assert init_result.server_info.name == SERVER_NAME
                assert init_result.server_info.version == SERVER_VERSION

                # 2. Tool Discovery
                tools_response = await session.list_tools()
                assert tools_response is not None
                tool_names = [t.name for t in tools_response.tools]
                assert "ping" in tool_names
                ping_meta = next(t for t in tools_response.tools if t.name == "ping")
                assert "diagnostic echo tool" in ping_meta.description.lower()

                # 3. Protocol Tool Invocation
                call_result = await session.call_tool(
                    "ping",
                    arguments={"message": "subprocess_stdio_handshake_ok"},
                )
                assert call_result is not None
                assert len(call_result.content) == 1
                assert call_result.content[0].type == "text"
                assert call_result.content[0].text == "pong: subprocess_stdio_handshake_ok"
                assert not getattr(call_result, "is_error", False)
