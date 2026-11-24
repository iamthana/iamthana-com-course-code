"""List every MCP server declared in .mcp.json files under a folder.

  uv run python inventory.py ROOT
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

SKIPPED_FOLDERS = {"node_modules", ".venv", ".git"}
# A version after a package name: some-server@1.2.3 or some-server==1.2.3. A scope such as @1password/ is not a version.
PIN_PATTERN = re.compile(r"\S@\d|==\d")
LAUNCHERS_THAT_DOWNLOAD = {"npx", "uvx"}


def find_config_files(root: Path):
    for path in sorted(root.rglob(".mcp.json")):
        if not SKIPPED_FOLDERS & set(path.relative_to(root).parts):
            yield path


def describe(server: dict) -> tuple[str, str]:
    if "url" in server:
        parts = urlsplit(server["url"])
        # user:password@ and ?query can carry a token, so the printed URL keeps only scheme, host, port and path.
        url = parts._replace(netloc=parts.netloc.rpartition("@")[2], query="", fragment="").geturl()
        header_names = ",".join(server.get("headers", {}))
        return server.get("type", "http"), f"{url}  headers: {header_names or '-'}"
    command = [server["command"], *server.get("args", [])]
    floating = command[0] in LAUNCHERS_THAT_DOWNLOAD and not PIN_PATTERN.search(" ".join(command))
    env_names = ",".join(server.get("env", {}))
    return "stdio", f"{' '.join(command)}  env: {env_names or '-'}" + ("  FLOATING" if floating else "")


def main(root: Path) -> int:
    count = 0
    for config in find_config_files(root):
        servers = json.loads(config.read_text()).get("mcpServers", {})
        for name, server in servers.items():
            kind, detail = describe(server)
            print(f"{config.parent.relative_to(root)}  {name}  {kind}  {detail}")
            count += 1
    print(f"{count} servers")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
