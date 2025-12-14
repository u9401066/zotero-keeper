"""Check MCP SDK capabilities"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test")

print("=== FastMCP Methods ===")
for attr in dir(mcp):
    if not attr.startswith('_'):
        print(f"  {attr}")

print("\n=== Check for elicitation ===")
import mcp
print(f"MCP package dir: {dir(mcp)}")

# Check if elicitation is supported
try:
    from mcp.types import ElicitationRequest
    print("✅ ElicitationRequest found!")
except ImportError as e:
    print(f"❌ ElicitationRequest not found: {e}")

# Check for resources
print("\n=== Check for resources ===")
try:
    print(f"mcp.resource decorator: {hasattr(mcp, 'resource')}")
    print(f"FastMCP.resource: {hasattr(FastMCP, 'resource')}")
except Exception as e:
    print(f"Error: {e}")
