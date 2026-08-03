# SEC-009 — branch protection verification pending

The read-only GitHub REST request for `main` branch protection returned
`401 Requires authentication`. The currently configured GitHub MCP token does
not have repository-administration scope, so required PR reviews and required
checks cannot be proven from an authenticated settings API response.

Do not mark SEC-009 Pass yet. An operator with repository administration access
must capture the Branch protection / Ruleset screen showing the required CI
checks and PR rule, without exposing tokens.

