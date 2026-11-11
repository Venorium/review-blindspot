# Safety boundaries

This is a research starter, not a sandbox or a security product. Its subprocess runner
executes only the bundled, trusted synthetic fixtures. A timeout and Python isolated
mode do not stop file access, network access, spawned processes or malicious code.
Never use this runner for arbitrary pull requests or reviewer-generated test code.

For untrusted code, first add a separately audited ephemeral sandbox with no secrets,
restricted filesystem and process privileges, explicit CPU/memory/time limits and no
network. Containers themselves also require appropriate configuration; a directory
named sandbox is not isolation.

Review inputs must not contain credentials, professional code, production data,
personal profiles or private model results. Reviewer access boundaries must be imposed
by the external harness. The exported packet layout reduces accidental disclosure; it
cannot prevent a CLI agent from reading its host's parent directories.

Hashes check consistency, not authorship or resistance to a privileged adversary.
A user who can replace data and checksums can forge both. The local storage API is
write-once, not tamper-proof storage. Signing and remote immutable storage are not implemented.

Network calls and model budget enforcement are outside the core. API credentials must
stay in the provider environment, never in submissions or this repository. Do not
log secrets or publish raw traces without inspecting and removing sensitive data.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting: open the repository's **Security** tab and
choose **Report a vulnerability**. Please include the affected command or file, the
version or commit, and a minimal non-sensitive reproduction. Do not open a public issue
for a vulnerability, and do not publish live third-party vulnerabilities or confidential
reproductions as corpus examples.

Supported version: the latest release on the default branch. Areas most relevant to
security are the transport (`rbs/transport.py`, which starts operator-declared commands
and HTTP requests), the skill helper (`skills/review-blindspot/scripts`, which calls Git
with filters, hooks and external diff tools disabled) and the fixture runner.
