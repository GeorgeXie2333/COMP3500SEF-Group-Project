# Phase 2: Page Mockups & Usability Checks

**Document status:** Planning draft. No mockup assets, completed usability checks
or handovers are recorded yet. Add versioned design links and review evidence as
work progresses; an existing application screen is not evidence of a design review.

The current baseline is the [React frontend](../../frontend/README.md),
[API contract](../openapi.yaml) and [SQLite schema](../../database/schema.sql).
The [test cases](docs/test/test-cases.md) distinguish checks runnable today from
checks blocked by future features. Coordinate scope with the owners in the
[project record](../PROJECT.md).

---

## 1. Mockups Delivery Progress

Low-fidelity wireframes are the proposed next deliverable for every row below.
"Not supplied" means no asset can yet be reviewed or marked ready for handover.

| Page Name | Design Assets / Review Status | Available in the Current Application | Proposed Work (Not Implemented) |
| :--- | :--- | :--- | :--- |
| User Registration & Login | Not supplied / Not reviewed | Username/password sign-in and error feedback | Registration, email/phone verification, password visibility toggle |
| Address Book Management | Not supplied / Not reviewed | Receiver address is entered as free text on a waybill | Saved HK-style addresses and mobile verification |
| Online Order Placement | Not supplied / Not reviewed | New waybill: signed-in sender, SKU, quantity, receiver, phone and address; stock deducted on creation | Service types, weight/dimensions and shipping fee calculation |
| Order List & Details | Not supplied / Not reviewed | Orders and waybills share shipment rows; search, status filters and pagination | Separate detail screen |
| Order Status Flow | Not supplied / Not reviewed | Status choices: `pending`, `shipped`, `delivered` | Agreed transition rules, expanded stages and failure/cancellation states |
| Logistics Tracking Timeline | Not supplied / Not reviewed | Backend stores timestamped tracking events; tracking page is a placeholder | Timeline screen and a read API for events |
| Dispatch Task Assignment | Not supplied / Not reviewed | Fleet page is a placeholder | Courier assignment and bulk dispatch |
| Delivery Confirmation | Not supplied / Not reviewed | Shipment status can be set to `delivered` | Signature capture and proof-of-delivery record |
| Warehouse & Inventory Management | Not supplied / Not reviewed | Catalogue and stock view; waybill creation deducts stock and rejects insufficient stock | Stock-in/out registration and a dedicated inventory movement history |
| Admin Dashboard (User/Role/Status Config) | Not supplied / Not reviewed | Dashboard/settings pages are placeholders | User/role management and configuration screens |

The proposed seven-stage flow
`created → picked_up → in_warehouse → in_transit → at_station → out_for_delivery → delivered`
and failure/cancellation states require agreement and API/schema changes before
implementation or acceptance testing. Today the API validates the three allowed
status values, but does not enforce their transition order. UI labels are
"Pending pickup" (`pending`), "In transit" (`shipped`) and "Delivered" (`delivered`).
The status dictionary is fixed in the API/schema, not editable in an admin screen.

---

## 2. Pre-implementation Usability Checklist

> **When to execute**: Before handing over any page to the frontend development team, the design team must verify it against this checklist. Only after passing these checks should the page be marked as ready for implementation.

Copy the checklist for each page and asset version. Record the reviewer, date,
desktop/mobile viewport, result and evidence, plus any outstanding issues.
Unchecked items are not yet verified. Record a reason for any non-applicable item.

### ✅ Basic Experience Checks

- [ ] **Information Architecture (IA)**: Is the page hierarchy clear? Are core functions accessible within 3 clicks?
- [ ] **Navigation Consistency**: Are the top/side navigation bars and breadcrumbs consistent across all pages?
- [ ] **Exit/Back Mechanisms**: Does every sub-page or modal have a clear close or back-to-previous action?

### ✅ Interaction & Feedback Checks

- [ ] **Empty States**: Are there friendly prompts or guiding actions when data lists or pages are empty?
- [ ] **Loading States**: Are Skeleton screens or Loading animations designed for data fetching?
- [ ] **Error Messages**: Are there clear, readable error prompts for form submission failures or API errors?
- [ ] **Micro-interactions**: Are there clear visual feedbacks for button Hover and Active states?

### ✅ Visual & Accessibility Checks

- [ ] **Responsive Layout**: Are there corresponding wireframes/UIs for both Desktop and Mobile views?
- [ ] **Text Readability**: Does the contrast between text and background color meet accessibility standards? Is the font size hierarchy reasonable?
- [ ] **Component Reusability**: Are the designs utilizing the unified Design System / UI Kit components?

---

## 3. Handover Records

No handovers have been recorded. Replace the template row only after an actual
review; include the asset version and checklist evidence before marking it ready.

| Handover Date | Pages / Asset Version | Reviewer / Frontend Developer | Checklist Evidence / Outstanding Issues | Handover Result |
| :--- | :--- | :--- | :--- | :--- |
| To be recorded | To be supplied | To be assigned | To be recorded | Not ready — no review evidence |
