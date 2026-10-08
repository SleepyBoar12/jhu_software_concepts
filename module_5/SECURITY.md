# Module 5 dependency vulnerability report

Review date: October 8, 2026.

The original `snyk test` report checked 64 dependencies and found three issues
(two high severity and one medium) through 21 dependency paths. All three
findings affected the same installed package, `urllib3==2.7.0`; the paths
describe repeated routes to that package, rather than 21 distinct flaws.

## Findings and remediation

| Finding | Severity | Affected urllib3 versions | Impact and triggering conditions | Fix applied |
|---|---|---|---|---|
| [Infinite loop: SNYK-PYTHON-URLLIB3-20302845](https://security.snyk.io/vuln/SNYK-PYTHON-URLLIB3-20302845), CVE-2026-97688 | Medium | `>=2.6.2,<2.8.0` | A malicious chunked, Deflate-compressed response can make the streaming decoder repeatedly process trailing data without making progress. The request can hang and consume CPU; a network read timeout does not interrupt this decoder loop. | Upgrade to `2.8.0`, which stops decoding after the compressed stream ends. |
| [Improper certificate validation: SNYK-PYTHON-URLLIB3-20302844](https://security.snyk.io/vuln/SNYK-PYTHON-URLLIB3-20302844), CVE-2026-97687 | High | `>=1.26.0,<2.8.0` | Certain HTTPS proxy configurations can mix the proxy's TLS policy with the destination's policy. Certificate checks can be weakened, allowing an attacker who intercepts the proxy connection to impersonate it. | Upgrade to `2.8.0`, which separates proxy and destination TLS settings. |
| [Allocation of resources without limits or throttling: SNYK-PYTHON-URLLIB3-20302846](https://security.snyk.io/vuln/SNYK-PYTHON-URLLIB3-20302846), CVE-2026-97689 | High | `>=1.10.3,<2.8.0` | While streaming a chunked response, a malicious server can supply a very long chunk-size line without a newline. Buffering that line can exhaust memory. | Upgrade to `2.8.0`, which limits the length of the chunk-size field. |

The urllib3 maintainers document all three fixes in the
[2.8.0 release notes](https://github.com/urllib3/urllib3/releases/tag/2.8.0).
Their detailed advisories cover the
[decoder loop](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g),
[proxy TLS settings](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77),
and [chunk-size buffering](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw).

## Application relevance and patch

The shared Module 2 scraper imports urllib3 to fetch `robots.txt`. Requests and
Selenium also depend on it, so removing it would break required functionality.
The current robots.txt request enables certificate verification and uses a
normal `PoolManager`; it does not explicitly enable streaming or configure an
HTTPS proxy. That inspection does not establish that every indirect library
path is unreachable. Updating the shared dependency fixes the reported
vulnerabilities throughout the environment.

Both `module_5/requirements.txt` and `module_5/src/requirements.txt` now pin
`urllib3==2.8.0`. `setup.py` reads the root requirements file, so its dependency
metadata automatically uses the same pin. The installed Requests constraint
(`urllib3>=1.26,<3`) and Selenium constraint (`urllib3[socks]>=2.6.3,<3`) both
allow version 2.8.0. The remediation is a dependency upgrade and requires no
new application modules or changes to the scraping or database workflows.

## Verification

Checks completed on October 8, 2026, in `module_5/venv`:

| Check | Result |
|---|---|
| Installed urllib3 version | `2.8.0` |
| `python -m pip check` | No broken requirements found. |
| Flask test-client requests | `/analysis` and `/static/styles.css` both returned HTTP 200. |
| `python -m pytest tests --require-postgres` | 147 passed in 1.29 seconds, no skips, 100% statement coverage. PostgreSQL tests used isolated schemas. |
| `snyk test --file=requirements.txt --command=python` | 64 dependencies checked; zero issues and no vulnerable paths; exit code 0. |

The earlier 3 issues and 21 vulnerable paths are no longer reported by the
patched scan. No Snyk ignore rules were added as part of this remediation.

To reproduce the checks, run from `module_5/` with the virtual environment
active and PostgreSQL configured for the isolated test schemas:

```bash
python -m pip install -e .
python -m pip check
python -m pytest tests --require-postgres
snyk test --file=requirements.txt --command=python
```

`snyk-analysis.png` records the original scan. Compare it with a fresh scan
after installing the patched requirements. Snyk's dependency scan assesses
known package vulnerabilities; it does not establish that all application
code, database permissions, or deployments are secure.
