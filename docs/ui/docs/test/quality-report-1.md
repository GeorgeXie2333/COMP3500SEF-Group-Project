# Quality Report 1 — Automated and Manual Baseline

- Date: 2026-10-26
- Author: ZHANGZHIYUAN, QA / Test Engineer
- Tested version: main @ e4358935ee4c8726dd32b67e1926857f8f451184
- Environment: Windows, PowerShell, Python [actual version],
  Node.js v24.22.1, npm 11.19.1, [browser and version]
- Related task: GitHub Issue 14

## 1. Purpose and scope

Establish a reproducible quality baseline for login, inventory,
waybill creation, order visibility, shipment status updates and
insufficient-stock handling.

The baseline includes local automated checks and manual browser/API
verification. It does not cover every logistics module, production
deployment or the complete business workflow.

## 2. Automated results

| Check | Result | Status |
|---|---|---|
| Python unittest discovery | 83 run, 0 failures, 0 errors | PASS |
| Frontend API workflow tests | 5 run, 5 passed, 0 failed | PASS |
| ESLint with zero warnings allowed | Exit code 0 | PASS |
| TypeScript and Vite production build | Completed successfully | PASS |

All automated commands returned exit code 0. The Git working tree
remained clean after execution.

## 3. Manual results

Tests used the isolated database `manual-e435893-run03.db`.

| Case | Result summary | Status |
|---|---|---|
| TC-005 login | Invalid credentials rejected; valid demo login succeeded | PASS |
| TC-002 waybill creation | Shipment HK202610260002 created; stock reduced from 120 to 118; both views agreed; reload caused no extra deduction | PASS |
| TC-003 status flow | pending → shipped → delivered persisted in both views; stock remained 118; three tracking events were recorded in order | PASS |
| TC-004 stock guard | Excess quantity was rejected; API returned HTTP 409; stock and shipment count remained unchanged | PASS |
| TC-001 registration | Registration UI/API unavailable | BLOCKED |

An earlier TC-002 attempt was invalidated by two tester submissions.
It was not classified as a product defect. The reported result comes
from a later run using a fresh database.

## 4. Confirmed defects

No new product defect was confirmed during this baseline run.

This statement applies only to the executed scope. It does not mean
that the whole system is defect-free.

## 5. Risks and limitations

- Frontend workflow tests exercise the API layer, not browser UI rendering.
- Registration, tracking timeline and several placeholder modules remain
  outside the implemented or executable scope.
- Docker, deployment and GitHub Actions results were not verified locally.
- Dependency installation reported one high-severity audit item;
  its affected package and exploitability require investigation.
- The possible tracking-number concurrency issue identified during
  static review remains unconfirmed and was not reported as a defect.
- Public read APIs, demo credentials, process-local tokens and unrestricted
  transitions among supported statuses require product-risk review;
  they are not automatically classified as new defects.
- Results apply only to the tested commit and environment.

## 6. Evidence

Evidence retained in the local QA notes includes:

- Automated command outputs for Python, frontend tests, lint and build.
- Login, inventory, waybill and status screenshots.
- Tracking-event query output for HK202610260002.
- HTTP 409 API result and before/after stock and shipment counts.
- GitHub Issue 14 progress comments.

## 7. Conclusion and next steps

The executed automated and manual baseline passed for the current
implemented workflow, with TC-001 blocked by missing registration scope.

Next priorities:

1. Review the dependency audit item without applying automatic fixes.
2. Extend browser-level UI and regression evidence.
3. Agree on acceptance rules for unimplemented logistics modules.
4. Reproduce and assess candidate defects before assigning them.
5. Repeat relevant checks when main changes or fixes are merged.