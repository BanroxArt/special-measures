# Security

Report a vulnerability privately through GitHub's "Report a vulnerability" button on this repository (Security tab). Please do not open a public issue for it.

This package reads a JSON file and, for `watch` only, sends GET requests to the public Federal Register API. It holds no secrets.

Things worth a private report:

- Input that makes the screener miss a name it should match, in a way an outsider could use to slip a payment past a system built on it.
- A path by which `watch` could be pointed at another host or made to write files.

A wrong date or citation in the registry is a correctness bug; a public issue is fine for that.
