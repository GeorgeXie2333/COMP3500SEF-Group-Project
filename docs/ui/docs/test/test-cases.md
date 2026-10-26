# Test Cases — HK Logistics System

## Scope and Setup

This is a manual test plan, not a record of successful execution. Use the
[frontend setup guide](../../../../frontend/README.md) and run the backend against
a new disposable SQLite file selected with `LMS_DB_PATH`. Do not rebuild a shared
database. Keep that server/database for dependent cases and record the tested
commit, browser, tester and date with each result.

The [API contract](../../../openapi.yaml),
[schema](../../../../database/schema.sql) and
[mockup plan](../../p2-mockups.md) define the current scope. Orders and waybills
are views of the same shipments. Only `pending`, `shipped` and `delivered` are
accepted statuses; their transition order is not currently enforced.

## Overview

| Module | Priority | Owner | Cases / Execution Status |
| :--- | :--- | :--- | :--- |
| User Login | P1 | QA | TC-005 / Not Run |
| User Registration | P1 | QA | TC-001 / Blocked: no registration page or API |
| Address Book Management | P1 | QA | Planned / Blocked: not implemented |
| Online Order Placement | P0 | QA | TC-002 / Not Run: current waybill workflow only |
| Order List & Details | P1 | QA | List visibility checked in TC-002; dedicated detail page is planned |
| Order Status Flow | P0 | QA | TC-003 / Not Run: current three statuses only |
| Logistics Tracking Timeline | P1 | QA | Planned / Blocked: timeline UI and event read API unavailable |
| Dispatch Task Assignment | P1 | QA | Planned / Blocked: not implemented |
| Delivery Confirmation | P1 | QA | Status checked in TC-003; signature/proof of delivery is planned |
| Warehouse & Inventory Management | P0 | QA | TC-004 / Not Run: deduction and stock guard only |
| Admin Dashboard | P2 | QA | Planned / Blocked: placeholder page |

Registration, address-book selection, service types, shipping fees, expanded
logistics stages and stock-in/out registration remain future scope. Agree their
contracts before making them acceptance criteria for this build.

## Test Case Template

| Field | Description |
| :--- | :--- |
| Test Case ID | Unique ID, e.g. TC-001 |
| Module | Related feature module |
| Priority | P0 / P1 / P2 |
| Preconditions | Environment, account, or data requirements |
| Steps | Step-by-step operations |
| Input Data | Test data used |
| Expected Result | What should happen |
| Actual Result | Fill after execution; include observed values and errors |
| Status | Pass / Fail / Blocked / Not Run |
| Execution Evidence | Commit, browser, tester, date and screenshot/request evidence |

## TC-001 — User Registration with Valid Data (Future Scope)

- **Module:** User Registration
- **Priority:** P1
- **Preconditions:** Registration UI/API and account-validation rules have been
  agreed and implemented; the email or phone number is not registered.
- **Input Data:** An unused test email/phone and a password meeting the agreed rules.
- **Proposed Steps:** Open registration, enter the account and password, confirm
  the password, then submit.
- **Proposed Expected Result:** An account is created and the agreed success
  message and destination are shown. Finalise these expectations with the feature.
- **Actual Result:** Not executed.
- **Status:** Blocked — current UI/API supports login only.
- **Execution Evidence:** None.

## TC-002 — Create a Waybill and Find It in Orders

- **Module:** Online Order Placement / Order List
- **Priority:** P0
- **Preconditions:** TC-005 passed; a fresh test database has `TECH-WM-001` stock
  of 120; no other tester is changing it.
- **Input Data:** SKU `TECH-WM-001`, quantity `2`, receiver `QA Receiver`, phone
  `+852-90000001`, address `Flat A, 8/F, Test Building, Wan Chai` (test data only).
- **Steps:**
  1. Open Inventory, search for the SKU and record its stock.
  2. Open Waybills and choose **New waybill**. Check the sender is `demo`.
  3. Select the SKU and enter the quantity, receiver, phone and address above.
  4. Choose **Create and deduct stock** and record the generated tracking number.
  5. Search for that tracking number in Waybills and then Orders; ensure the
     status filter is **All statuses**.
  6. Return to Inventory and refresh the SKU; reload Orders to check persistence.
- **Expected Result:** One shipment is created with the entered data and quantity
  2. Both lists show the same tracking number and **Pending pickup** (`pending`).
  Stock is 118; reloading does not create another shipment or deduct stock again.
- **Actual Result:** Not executed.
- **Status:** Not Run.
- **Execution Evidence:** None.

## TC-003 — Update Supported Shipment Statuses

- **Module:** Order Status Flow
- **Priority:** P0
- **Preconditions:** The pending shipment created in TC-002 exists; user is logged in.
- **Input Data:** TC-002 tracking number; status choices **In transit** (`shipped`)
  and **Delivered** (`delivered`).
- **Steps:**
  1. Search for the shipment in Waybills with **All statuses** selected.
  2. Change its status from **Pending pickup** to **In transit**.
  3. Open Orders and verify the same shipment's status, then change it to **Delivered**.
  4. Reload Waybills and refresh Inventory.
- **Expected Result:** Each update persists in both views; inventory stays at
  118. The API appends a tracking event for each update. Verify events using a
  read-only database query below; the timeline screen is not implemented.

  ```sql
  SELECT s.tracking_number, e.status, e.description, e.event_time
  FROM tracking_events AS e
  JOIN shipments AS s ON s.shipment_id = e.shipment_id
  WHERE s.tracking_number = '<replace with TC-002 tracking number>'
  ORDER BY e.event_time, e.event_id;
  ```

  Expect `pending`, `shipped`, `delivered` events in that order for this procedure.
  This sequence is a test scenario, not an enforced state machine. Unsupported
  status values are rejected by the API; reverse changes among supported values
  are currently allowed.
- **Actual Result:** Not executed.
- **Status:** Not Run.
- **Execution Evidence:** None.

## TC-004 — Prevent a Waybill from Exceeding Available Stock

- **Module:** Warehouse & Inventory Management
- **Priority:** P0
- **Preconditions:** TC-002 completed, stock is 118 for `TECH-WM-001`, and user is
  logged in. Record the shipment count; no other tester is writing to this database.
- **Input Data:** Same receiver fields as TC-002; SKU `TECH-WM-001`, quantity `119`.
- **Steps:**
  1. Open **New waybill**, select the SKU and enter the input data.
  2. Check the available-stock warning and submit button state.
  3. Cancel the dialog and refresh Inventory and the shipment list.
  4. Separately, use an API client to log in with `POST /api/auth/login`, then send
     `POST /api/shipments` with `Content-Type: application/json` and
     `Authorization: Bearer <returned token>`. Use the returned `user.id` as
     `sender_id`, the receiver fields from TC-002 and quantity 119, following the
     [request schema](../../../openapi.yaml).
  5. Refresh Inventory and the shipment list after the rejected request.
- **Expected Result:** The UI shows **Exceeds available stock** and disables
  **Create and deduct stock**. The direct API request returns HTTP 409 with
  `{"error":"insufficient inventory"}`. Stock remains 118 and the shipment count
  is unchanged. This checks the UI guard and backend rejection separately.
- **Actual Result:** Not executed.
- **Status:** Not Run.
- **Execution Evidence:** None.

## TC-005 — Sign In with the Demo Account

- **Module:** User Login
- **Priority:** P1
- **Preconditions:** Backend and frontend are running as described above; use a
  fresh browser session and open `/login` directly.
- **Input Data:** Username `demo`; first password `wrong-password`, then `demo123`.
- **Steps:**
  1. Submit the incorrect password and observe the error.
  2. Replace it with `demo123` and choose **Sign in**.
- **Expected Result:** Incorrect credentials keep the user on the sign-in page
  with an error. Correct credentials open `/orders`; the session identifies `demo`.
- **Actual Result:** Not executed.
- **Status:** Not Run.
- **Execution Evidence:** None.

## Execution Order and Automated Evidence

Run TC-005 → TC-002 → TC-003 → TC-004 on the same disposable database. Use a fresh
database for another run so stock assumptions remain valid. TC-001 remains blocked.

Existing [backend tests](../../../../tests/test_backend.py) and
[frontend API workflow tests](../../../../frontend/tests/workflow.test.ts) exercise
related API/database behavior. Their passing results do not mark these manual
browser cases or the usability checklist as passed. Record manual results and
evidence only after executing the steps.
