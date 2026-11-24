import json

import inventory


def write_config(folder, servers):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ".mcp.json").write_text(json.dumps({"mcpServers": servers}))


def run(root, capsys) -> str:
    inventory.main(root)
    return capsys.readouterr().out


def test_lists_stdio_and_http_servers(tmp_path, capsys):
    write_config(tmp_path / "shop", {"cafe": {"command": "uv", "args": ["run", "cafe_server.py"]}})
    write_config(tmp_path / "lab", {"remote": {"type": "http", "url": "http://10.0.0.5:8080/mcp"}})
    output = run(tmp_path, capsys)
    assert "shop  cafe  stdio  uv run cafe_server.py" in output
    assert "lab  remote  http  http://10.0.0.5:8080/mcp" in output
    assert "2 servers" in output


def test_flags_unpinned_downloads_only(tmp_path, capsys):
    write_config(
        tmp_path,
        {
            "floating": {"command": "npx", "args": ["-y", "some-mcp-server"]},
            "pinned": {"command": "npx", "args": ["-y", "some-mcp-server@1.2.3"]},
            "pinned-uvx": {"command": "uvx", "args": ["--from", "some-server==1.2.3", "run"]},
            "local": {"command": "uv", "args": ["run", "server.py"]},
            "scoped": {"command": "npx", "args": ["-y", "@1password/mcp"]},
        },
    )
    flagged = [line.split()[1] for line in run(tmp_path, capsys).splitlines() if line.endswith("FLOATING")]
    assert flagged == ["floating", "scoped"]


def test_prints_names_never_secret_values(tmp_path, capsys):
    write_config(
        tmp_path,
        {
            "a": {"command": "uv", "args": ["run", "a.py"], "env": {"API_KEY": "value-one"}},
            "b": {"type": "http", "url": "https://x.example/mcp", "headers": {"Authorization": "value-two"}},
            "c": {"type": "http", "url": "https://user:value-three@y.example:8443/mcp?api_key=value-four"},
        },
    )
    output = run(tmp_path, capsys)
    assert not any(value in output for value in ("value-one", "value-two", "value-three", "value-four"))
    assert "API_KEY" in output and "Authorization" in output and "https://y.example:8443/mcp" in output


def test_skips_dependency_folders(tmp_path, capsys):
    write_config(tmp_path / "node_modules" / "pkg", {"hidden": {"command": "x"}})
    assert "0 servers" in run(tmp_path, capsys)
