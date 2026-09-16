# Logistics Management System

**COMP3500SEF Course Project · Software Engineering**

---

## 1. Project Topic

This project develops a **web-based Logistics Management System (LMS)** covering the full business cycle of a logistics company:

- **Order Management** — create and manage customer orders
- **Inventory Management** — track stock levels and product data
- **Transport Dispatch** — assign shipments and manage waybills
- **Delivery Confirmation** — record and update delivery status
- **Order Tracking** — real-time shipment lookup for customers

The system is delivered as a **runnable, demo-ready MVP**, developed through the full software-engineering lifecycle: requirements → design → implementation → testing → deployment.

---

## 2. Background

**Why this topic?** The logistics industry is undergoing rapid digital transformation. Many small and medium-sized logistics companies still rely on spreadsheets and phone calls to manage orders, stock and shipments, which leads to errors, delays and poor visibility. A unified web platform helps them:

- centralise order and inventory data in one place
- reduce manual errors through automated status updates
- give customers a transparent view of their shipments
- support scalable growth with a modern, database-backed system

**Course context.** This is the group project of the Course Engineering (Software Engineering) module. It gives the team hands-on practice of the full development workflow — defining scope, designing the database schema and API contract, building the frontend and backend, testing, and finally presenting a working product — while collaborating as a 7-member team through Git and GitHub.

**Team.** 7 members, led by XU Lanxin. Role assignments and module ownership are listed in [`CODE.md`](CODE.md).

---

## 3. Repository Guide

### Structure

```
├── CODE.md           # Module map & code templates — find your module here
├── docs/             # Project documents (charter, module list, guides)
├── frontend/         # Frontend code (HTML / CSS / JavaScript)
├── backend/          # Backend REST API (Python, stdlib, zero dependencies)
├── database/         # Database schema (SQL)
└── tests/            # Unit tests (Python unittest)
```

### Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML / CSS / JavaScript |
| Backend | Python (`http.server` standard library) |
| Database | SQL (MySQL / PostgreSQL / SQLite compatible) |
| DevOps | Git + GitHub (CI/CD to be added) |

### How to Run

- **Frontend** — open `frontend/index.html` in any browser.
- **Backend** — run `python backend/server.py`, then visit `http://localhost:8000/api/health` and `/api/orders`.
- **Database** — execute `database/schema.sql` in MySQL / PostgreSQL / SQLite.
- **Tests** — run `python -m unittest tests/test_example.py`.

### How We Collaborate

- Branch strategy: `main` (stable) ← `develop` (integration) ← `feature/xxx` (feature branches)
- Each member works inside their own module folder (see `CODE.md`)
- Changes are merged via **Pull Requests** after review
- Commit messages are written in clear English

### Milestones

| Phase | Time | Key Points |
|---|---|---|
| P1 Initiation | 09-16 — 09-30 | Scope freeze, repository setup, design alignment, Logbook #1 |
| P2 Build | 10-01 — 10-31 | MVP flow end to end, Logbook #2/#3 |
| P3 Review | 11-01 — 11-23 | Live demo, 10-minute presentation, Logbook #4 |
| P4 Finalisation | 12-01 — 12-07 | Feature freeze (11-30), demo video, report |
| P5 Submission | 12-08 | Report & final Logbook submitted (hard deadline) |
