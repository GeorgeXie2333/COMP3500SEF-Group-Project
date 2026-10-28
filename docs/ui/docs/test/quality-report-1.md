# Quality Report 1 — Automated and Manual Baseline

- Date: 2026-10-26
- Author: ZHANGZHIYUAN, QA / Test Engineer
- Tested version: main @
  [e4358935ee4c8726dd32b67e1926857f8f451184](https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project/commit/e4358935ee4c8726dd32b67e1926857f8f451184)
- Reported environment: Windows, PowerShell, Node.js v24.22.1, npm 11.19.1.
  Python version, browser name/version and Windows/PowerShell versions were
  not recorded in the linked execution summaries and remain unverified.
- Related task: [GitHub Issue #14](https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project/issues/14)
- Report status: Partial baseline record; environment details and shared raw
  evidence remain outstanding. Publishing this report does not complete Issue #14.

## 1. Purpose and scope

Record the author's baseline results for login, inventory, waybill creation,
order visibility, shipment status updates and insufficient-stock handling.
The goal is a reproducible baseline; the missing environment details and raw
evidence listed below prevent full independent verification of this run.

The baseline includes local automated checks and manual browser/API
verification. It does not cover every logistics module, production
deployment or the complete business workflow.

## 2. Automated results

The [automated execution summary](https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project/issues/14#issuecomment-6421349369)
reports these commands and results. Directories are relative to the repository
root; the frontend commands require the locked dependencies installed with
`npm.cmd ci` in `frontend/`. See the
[frontend setup and Python selection guide](../../../../frontend/README.md#validation)
for the test interpreter configuration.

| Check | Working directory | Command (PowerShell) | Reported result | Status |
|---|---|---|---|---|
| Python unittest discovery | Repository root | `py -3 -m unittest discover -s tests -v` | 83 run, 0 failures, 0 errors | PASS |
| Frontend API workflow tests | `frontend/` | `npm.cmd test` | 5 run, 5 passed, 0 failed | PASS |
| ESLint with zero warnings allowed | `frontend/` | `npm.cmd run lint -- --max-warnings=0` | No errors or warnings, exit code 0 | PASS |
| TypeScript and Vite production build | `frontend/` | `npm.cmd run build` | Completed successfully, exit code 0 | PASS |

The author reported exit code 0 for all commands and a clean Git working tree
after execution. These are the original run's results, not a new test run made
while editing this report. The separate Windows startup suite under
`tests/windows/` was not included in these reported checks.

## 3. Manual results

The [manual execution summary](https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project/issues/14#issuecomment-6422811948)
reports the following results using the isolated database
`manual-e435893-run03.db`, in the order TC-005 → TC-002 → TC-003 → TC-004.
Steps, inputs, expected results and the tracking-event SQL query are in the
[test plan at the tested commit](https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project/blob/e4358935ee4c8726dd32b67e1926857f8f451184/docs/ui/docs/test/test-cases.md).
PASS below records the author's reported outcome; the screenshots and raw
API/database outputs are not yet linked for independent review.

| Case | Reported result summary | Status |
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
- Missing environment versions and unshared raw evidence limit reproducibility
  and independent verification; the linked summaries do not replace those artifacts.
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

The following author-written execution summaries are available to reviewers:

- [Python baseline: command, count and duration](https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project/issues/14#issuecomment-6421028752).
- [Automated baseline: commands, environment and results](https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project/issues/14#issuecomment-6421349369).
- [Manual baseline: database, case order and observed values](https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project/issues/14#issuecomment-6422811948).

The author reports retaining the following raw evidence locally. No shared
attachments or artifact links were present in those comments at review on
2026-10-28, so their contents have not been independently verified:

- Python terminal output in the local QA notes.
- `frontend-tests-main-e435893.txt`, `frontend-lint-main-e435893.txt` and
  `frontend-build-main-e435893.txt`.
- Login, inventory, waybill and status screenshots.
- Tracking-event query output for HK202610260002 and the HTTP 409 response,
  with before/after stock and shipment counts.

QA follow-up in Issue #14: attach or link these artifacts, map them to the
commands/cases above and recover the missing environment details from the
original run if available. Otherwise, record them as unknown for this historical
run and capture them in a separately dated rerun. Do not substitute another
machine's current versions for the original test environment.

## 7. Conclusion and next steps

The author reported that the executed automated and manual checks passed for
the implemented workflow at the tested commit, with TC-001 blocked by missing
registration scope. This partial report preserves those outcomes; it does not
establish independently verified manual coverage or complete Issue #14's
reproducibility and evidence acceptance checks.

Next priorities:

1. Complete the environment and shared-evidence follow-up in Issue #14.
2. Review the dependency audit item without applying automatic fixes.
3. Extend browser-level UI and regression evidence.
4. Agree on acceptance rules for unimplemented logistics modules.
5. Reproduce and assess candidate defects before assigning them.
6. Repeat relevant checks when main changes or fixes are merged.
