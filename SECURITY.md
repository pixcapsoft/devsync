# Security Policy

## Supported Versions

Currently, we support the latest beta release and the `main` branch. We only apply security updates and bug fixes to the most recent version of DevSync.

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| Older   | :x:                |

## Reporting a Vulnerability

Security is a priority for DevSync. Because DevSync operates across your local network using protocols like ADB and HTTP to sync source files, security considerations are strongly tied to your local firewall and network trust.

If you discover any security vulnerabilities or exploits directly in DevSync's handling of network sockets, file parsing, ADB permissions, or dependencies (e.g., directory traversal attacks in the HTTP server mode), please **do not** open a public issue.

Instead, please report the vulnerability privately:
1. Reach out to the maintainers directly through email or a GitHub private advisory (if enabled). 
2. Include the following details in your report:
   - A description of the vulnerability.
   - Steps to reproduce it.
   - Potential impact.
   - Suggested mitigations (if any).

We will try to acknowledge your report within a reasonable timeframe and work with you to resolve the issue as quickly as possible. We ask you not to publish information about a security gap publicly until we have shipped a patch/fix for it.

Thank you for helping keep DevSync safe and secure!
