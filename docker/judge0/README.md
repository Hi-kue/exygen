# Judge0 (self-hosted, local development)

Runs a local [Judge0](https://github.com/judge0/judge0) instance so the agent's
`CodeSandboxAgent` can execute generated code in an isolated sandbox instead of
on the host.

Based on the official Judge0 `v1.13.1` `docker-compose.yml` and `judge0.conf`.
The server and worker containers run `privileged: true` because Judge0 uses
[isolate](https://github.com/ioi/isolate) for sandboxing. This setup is for
local development only.

## Requirements

- Docker Desktop (Linux containers) or Docker Engine with Compose v2
- ~2 GB free disk for the images and database volume
- Port `2358` free on the host

## Start

From the repository root:

```bash
docker compose -f docker/judge0/docker-compose.yml up -d
```

Or from this directory:

```bash
cd docker/judge0
docker compose up -d
```

The first start pulls the images and initializes the PostgreSQL database; give
it a minute or two. Check progress with:

```bash
docker compose -f docker/judge0/docker-compose.yml ps
docker compose -f docker/judge0/docker-compose.yml logs -f server
```

Wait until `server` responds:

```bash
curl http://localhost:2358/system_info
```

## Configure the agent

The defaults already match this stack. `apps/agent/.env` can override them:

```bash
JUDGE0_API_URL="http://localhost:2358"
JUDGE0_AUTH_TOKEN=""
JUDGE0_EXEC_TIMEOUT_SECONDS=5
JUDGE0_MEMORY_LIMIT_KB=256000
JUDGE0_REQUEST_TIMEOUT_SECONDS=60
```

`apps/agent/src/exygen_agent/settings.py` reads these through the
`Judge0Settings` group (`JUDGE0_*`). Authentication is disabled in
`judge0.conf`; to require it, set `AUTHN_TOKEN` there and the same value as
`JUDGE0_AUTH_TOKEN` in `apps/agent/.env`. The service sends it as
`X-Auth-Token`.

## Verify

```bash
PYTHONPATH=apps/agent/src python -c "
from exygen_agent.sandbox.code_executor import execute_in_sandbox
print(execute_in_sandbox('print(sum(range(10)))', 'python'))
"
```

Expected: `is_success=True exit_code=0 output='45\n' error=None`

Then the full agent demo:

```bash
PYTHONPATH=apps/agent/src python -m exygen_agent.mock
```

## How the agent uses Judge0

`Judge0Service` (`apps/agent/src/exygen_agent/sandbox/judge0_service.py`) posts
to `POST /submissions?base64_encoded=false&wait=true`:

- **Python** uses language id `71` (`Python (3.8.1)`) with `source_code` set to
  the contents of `solution.py`.
- **Java** uses language id `62` (`Java (OpenJDK 13.0.1)`) with `Main.java` as
  `source_code`. Every other prepared file is packed into a ZIP and sent as
  `additional_files`; Judge0 always base64-decodes that field and extracts the
  archive into the submission directory.
- Status id `3` (`Accepted`) means the program compiled and exited successfully.
  Any other status is returned as a failure with the compile output, stderr,
  and status description joined into the error message.

Language IDs are pinned to the Judge0 `v1.13.1` language set, which is why the
image tag is pinned in `docker-compose.yml`.

## Stop

```bash
docker compose -f docker/judge0/docker-compose.yml down      # keep data
docker compose -f docker/judge0/docker-compose.yml down -v   # wipe volumes
```

## Troubleshooting

**`Connection refused` on port 2358** — the server is still starting, or the
port is already in use. Check `docker compose ... ps` and change the host port
in `docker-compose.yml` if needed, then update `JUDGE0_API_URL`.

**`status 422` from `/submissions`** — Judge0 rejected a field. Check
`docker compose ... logs server`. A common cause is a `memory_limit` or
`wall_time_limit` above the `MAX_*` values in `judge0.conf`.

**Java compilation cannot find a class** — the prepared files must include
`Main.java`; the agent returns an explicit error when it is missing. Other
`.java` files are sent through `additional_files`.

**Worker containers exit immediately** — `privileged: true` is required. Make
sure Docker is running Linux containers (not Windows containers).
