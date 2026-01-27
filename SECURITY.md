# Security Policy

## Supported Versions

Only the latest release of `pr-orchestrator-mcp` is currently supported with security updates.

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please do not create a public issue.  Instead, send an e‑mail to our private security address: <security@saakshi.dev>.  Please include a detailed description of the vulnerability and steps to reproduce it.  You will receive a response within 72 hours.

All vulnerability reports are treated as confidential.  We will investigate the issue and work with you to prepare a fix.  Credit will be given in the release notes unless you request otherwise.

## General Guidelines

* Never hard‑code secrets in the source code.  Use environment variables and `.env` files for secret configuration.
* Follow the principle of least privilege when interacting with external services.  Tokens should be scoped only to the operations required by the MCP server.
* Audit dependencies regularly for known vulnerabilities using tools such as `pip-audit` or `safety`.
* Avoid shelling out to arbitrary commands.  Only allowed commands specified in the specification may be executed.