# Phase 2: Page Mockups & Usability Checks
> **Task Description**: Add screen mockups as implementation progresses; run usability checks before implementation.  
> **Document Status**: 🚧 Work in Progress

---

## 1. Mockups Delivery Progress

| Page Name | Delivery Phase | Design Assets (Figma/Image Links) | Core Interaction / Notes |
| :--- | :--- | :--- | :--- |
| User Registration & Login | Low-fidelity Wireframe |  | Form validation, error feedback, password visibility toggle |
| Address Book Management | Low-fidelity Wireframe |  | HK-style address fields (district/building/block/floor/unit), mobile verification |
| Online Order Placement | Low-fidelity Wireframe |  | Auto shipping fee calculation (first weight + additional weight/volumetric weight), service type selection | 
| Order List & Details | Low-fidelity Wireframe |  | Search bar, filter dropdowns, pagination, order status display |
| Order Status Flow | Low-fidelity Wireframe |  | Status machine progression (created→picked_up→in_warehouse→in_transit→at_station→out_for_delivery→delivered), failed/cancelled terminal states |
| Logistics Tracking Timeline | Low-fidelity Wireframe |  | Timeline view of tracking_events, chronological event display with timestamps | 
| Dispatch Task Assignment | Low-fidelity Wireframe |  | Task assignment to couriers, order status tracking, bulk dispatch |
| Delivery Confirmation | Low-fidelity Wireframe |  | Signature capture, timestamp recording, receiver name, notes field |
| Warehouse & Inventory Management | Low-fidelity Wireframe |  | Stock in/out registration, inventory view with negative stock prevention | 
| Admin Dashboard (User/Role/Status Config) | Low-fidelity Wireframe |  | User & role management, status dictionary editing, system configuration | 
---

## 2. Pre-implementation Usability Checklist

> **When to execute**: Before handing over any page to the frontend development team, the design team must verify it against this checklist. Only after passing these checks should the page be marked as ready for implementation.

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

| Handover Date | Handed Over Pages | Frontend Developer | Handover Result |
| :--- | :--- | :--- | :--- |
| *e.g., 2024-05-20* | *Home Page, Login Page* | *@Dev_Name* | ✅ Mockups reviewed, ready for development |
