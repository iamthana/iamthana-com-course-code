from auth import TRANSPORT_SECURITY
from cafe_server import mcp

mcp.run(transport="streamable-http", host="127.0.0.1", port=8765, transport_security=TRANSPORT_SECURITY)
