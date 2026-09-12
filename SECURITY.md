# Security

## Reporting a vulnerability

Please report privately via
**[a draft advisory](https://github.com/seanwylie/planner/security/advisories/new)**.
There is no published email address.

The draft-advisory form only works when private vulnerability reporting is enabled.
If the form is missing, do not open a public issue.

**Expect a slow response.** No production-support commitment.

## What is in scope

- A default path that runs Cursor with `--trust` / `--yolo` / `--agent-force` without the
  operator passing those flags
- Persistence of API keys or run artifacts into the public tree
- A gitlink or vendored copy of a private bones repository

## What is out of scope

- What the Cursor agent does after you opt into force flags
- Model output that is merely wrong
- Attaching your own bones tree

## Secrets

Never commit `.env`, `workspaces/`, or a private `bones/` checkout. `workspaces/` and
`bones/` are gitignored.
