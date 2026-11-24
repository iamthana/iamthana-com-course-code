import uvicorn

from audit import HttpAudit
from auth import TRANSPORT_SECURITY
from cafe_server import mcp

app = mcp.streamable_http_app(transport_security=TRANSPORT_SECURITY)
app.add_middleware(HttpAudit)

# access_log=False: uvicorn's access log prints the full URL, including any query string.
uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765, access_log=False)).run()
