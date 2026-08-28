# Security Policy

## Supported versions

Security fixes are provided for the latest released minor version of DataCore CLI.

## Reporting a vulnerability

Please use GitHub private vulnerability reporting for this repository. Do not open a public issue for suspected credential exposure, authorization bypass, command injection, dependency compromise, or release-artifact tampering.

Include the affected version, operating system, reproduction steps, observed impact, and whether any DataCore token or user data may have been exposed. We will acknowledge the report and coordinate remediation and disclosure through the private report.

## Credential handling

Interactive login stores the revocable DataCore authorization in the operating-system keychain. Headless automation should use `DATACORE_TOKEN`. File-based credential persistence is disabled unless the user explicitly opts in.
