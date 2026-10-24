# Test Cases — HK Logistics System

## Overview

| Module | Priority | Owner | Status |
| :--- | :--- | :--- | :--- |
| User Registration & Login | P1 | QA | Not Started |
| Address Book Management | P1 | QA | Not Started |
| Online Order Placement | P0 | QA | Not Started |
| Order List & Details | P1 | QA | Not Started |
| Order Status Flow | P0 | QA | Not Started |
| Logistics Tracking Timeline | P1 | QA | Not Started |
| Dispatch Task Assignment | P1 | QA | Not Started |
| Delivery Confirmation | P1 | QA | Not Started |
| Warehouse & Inventory Management | P0 | QA | Not Started |
| Admin Dashboard | P2 | QA | Not Started |

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
| Actual Result | Fill after execution |
| Status | Pass / Fail / Blocked / Not Run |

## TC-001 — User Registration with Valid Data

- **Module:** User Registration & Login
- **Priority:** P1
- **Preconditions:**
  - Test environment is accessible
  - Email or phone number has not been registered
- **Steps:**
  1. Open the registration page
  2. Enter a valid email or phone number
  3. Enter a valid password
  4. Confirm the password
  5. Click “Register”
- **Expected Result:**
  - Registration succeeds
  - User is redirected to login or dashboard
  - Success message is displayed

## TC-002 — Online Order Placement

- **Module:** Online Order Placement
- **Priority:** P0
- **Preconditions:**
  - User is logged in
  - Address book contains at least one valid address
- **Steps:**
  1. Select sender address
  2. Select receiver address
  3. Choose service type
  4. Enter package weight or dimensions
  5. Confirm shipping fee calculation
  6. Submit the order
- **Expected Result:**
  - Order is created successfully
  - Order status shows “created”
  - Order appears in the order list

## TC-003 — Order Status Flow

- **Module:** Order Status Flow
- **Priority:** P0
- **Preconditions:**
  - At least one order exists
- **Steps:**
  1. Check initial status is “created”
  2. Trigger pickup
  3. Trigger warehouse check-in
  4. Trigger transit update
  5. Trigger out-for-delivery update
  6. Trigger delivery confirmation
- **Expected Result:**
  - Status follows:
    `created → picked_up → in_warehouse → in_transit → at_station → out_for_delivery → delivered`
  - Invalid transitions are rejected

## TC-004 — Warehouse Inventory Update

- **Module:** Warehouse & Inventory Management
- **Priority:** P0
- **Preconditions:**
  - Warehouse module is available
  - Test inventory record exists
- **Steps:**
  1. Open inventory page
  2. Register stock-in
  3. Register stock-out
  4. Check updated inventory quantity
- **Expected Result:**
  - Inventory quantity updates correctly
  - Negative stock is prevented when required
  - All changes are recorded with timestamps
