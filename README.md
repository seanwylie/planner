# Planner

Turns a short idea into a gated plan and spec, then optionally asks the Cursor
CLI to implement the spec.

**Experimental software, released for study and adaptation. Maintained as time
permits. No production-support commitment.** The suite is thin: slug checks and
prompt smoke only. Live draft/refine/execute against Cursor or OpenAI is not
covered by CI.

Created by Sean Wylie and released as an open-source experiment through Wise
Kids Studios.

## What it does

```text
draft    paragraph → idea markdown (Cursor expand + optional OpenAI review)
init     snapshot the idea into a workspace
refine   Cursor plan/spec → OpenAI (or Bedrock) review → gates → patch → repeat
execute  Cursor implements final_spec.md
```

Gates are explicit: score, must-fix, open questions, high-risk should-fix, and
readiness thresholds. Execute uses only `final_spec.md`.

## Coupling (honest)

| Dependency | Required? | Notes |
| --- | --- | --- |
| Python 3.10+ | Yes | |
| Cursor CLI (`agent`) | For draft/refine/execute | Or `--manual-cursor` / `--dry-run` |
| `OPENAI_API_KEY` | For default review | Skip with `--cursor-only` |
| AWS Bedrock | Only consensus models with `anthropic.` / `amazon.` ids | |
| **bones** | **No** | Optional notes tree. See below. |

This tool drives an external coding agent. It does not contain the product you
are planning.

## Bones (optional)

Planner is sharper when a `bones/` directory of architectural notes is present.
That tree is **not shipped** and is **not a git submodule** of this repository.
A private bones repo must stay private; do not add a gitlink to it here.

If you have bones, attach it yourself in either place:

```text
planner/bones/README.md          # next to this tool
../bones/README.md               # host project, sibling of planner/
```

When `README.md` is found, refine/execute prompts mention bones. When it is
missing, Planner still runs and the prompts simply omit that guidance. That is
the supported public path.

```sh
# example only — use your own source, not a required URL
git clone <your-bones-repo> bones
```

## Prove it without Cursor or keys

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH="$(dirname "$PWD")" .venv/bin/pytest -q
```

Clone or check out this repository as a directory named `planner` so
`import planner` resolves (the historical layout). CI does that automatically.

`./planner init example-health-check` creates a workspace from the fictional
example idea. That writes under `workspaces/` (gitignored).

## Safe defaults

`--trust`, `--yolo`, and `--agent-force` exist so a headless run can skip
Cursor's confirmation prompts. They let the agent run commands without asking.
**They are opt-in.** The documented path is manual or `--manual-cursor`. Do not
pass force flags unless you accept that risk.

```sh
./planner refine example-health-check --manual-cursor
./planner execute example-health-check --dry-run
```

## Layout

```text
CHECKLIST.md          generic engineering gates (GEN-0 …)
ideas/                idea markdown (one fictional example ships)
workspaces/           run artifacts (gitignored; you generate these)
scripts/              draft, refine, execute, replay
templates/            idea / plan / spec / patch / execute
```

## Ownership

Created by Sean Wylie and released as an open-source experiment through Wise
Kids Studios. Planner is a software project, not a legal person.
