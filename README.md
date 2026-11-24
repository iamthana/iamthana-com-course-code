# course-code

Code for the courses on [iamthana.com](https://iamthana.com/courses). Each lesson's code is a git tag, so you can compare your work with a version that runs, or start from any lesson without typing the ones before it.

> [!WARNING]
> **For learning only.** This code accompanies the courses and is written to teach one idea per lesson. Parts of it are not production grade: for example, the token check in `auth.py` compares tokens from environment variables instead of using a real authorization server, the servers only listen on `127.0.0.1`, and there is no rate limiting. Some files in the security course are vulnerable on purpose (see Demo Attack Code below). Do not deploy this code or copy it into a production system as is.

## Courses

| Folder                 | Course                                                            | Lessons |
| ---------------------- | ----------------------------------------------------------------- | ------- |
| [`cafe-mcp`](cafe-mcp) | [MCP Server with Python](https://iamthana.com/courses/mcp-server) | 11      |
| [`cafe-mcp`](cafe-mcp) | [MCP Security](https://iamthana.com/courses/mcp-security)         | 12      |

The MCP Security course continues from the end of the MCP Server course, so both use the same folder.

## Find the Code for a Lesson

The code at the end of each lesson is a git tag named `<course>/<lesson>`.

```bash
git clone https://github.com/iamthana/iamthana-com-course-code.git course-code
cd course-code
git tag
git checkout mcp-server/05-orders
cd cafe-mcp
uv sync --locked
```

You need Python 3.13 and [uv](https://docs.astral.sh/uv/).

Every lesson that adds code has its own tag. A lesson without new code uses the tag before it:

| Lesson              | Tag                             | Why                                     |
| ------------------- | ------------------------------- | --------------------------------------- |
| mcp-server 04       | `mcp-server/03-inspect-traffic` | Reading only                            |
| mcp-security 01, 02 | `mcp-server/11-testing`         | Starts from the end of the first course |

## Demo Attack Code

The MCP Security course has servers that are vulnerable on purpose, so you can attack them. Their first line is a `# DEMO` comment.

- `promo_server.py` and `promo_rugpull_server.py` write the "stolen" data to a file on your machine. Nothing goes over the network.
- `open_server.py` has no token and no Host or Origin check. It listens on `127.0.0.1` only.
- `receipt_vulnerable.py` builds a shell command from order data. Do not copy this pattern.

Run them on your own machine only. Do not let other machines connect to them, and do not point them at real data.

## Files You Create Yourself

- `cafe.db`, `stock.db` and `notify.db` are created on the first run.
- `.mcp.json` is created by `claude mcp add` as the lessons show, because it holds paths from your machine.
- `tokens.env` for the MCP Security course is created in the lesson Require a Token.

## License

[MIT](LICENSE)
