# 物流管理系统 / Logistics Management System

**COMP3500SEF 软件工程项目 · Group Project**

---

## 项目简介 / About

本项目开发一个**基于 Web 的物流管理系统**，覆盖订单管理、库存管理、运输配送、签收确认与物流查询的完整业务链路，提供一个可运行、可演示的 MVP。

This project builds a **web-based Logistics Management System** covering order management, inventory, transport dispatch, delivery confirmation and tracking — delivered as a runnable, demo-ready MVP.

| 项目 Project | 物流管理系统 / Logistics Management System |
|---|---|
| 课程 Course | Course Engineering（软件工程） |
| 团队 Team | 7 名成员，组长：XU Lanxin |
| 沟通 Communication | 线上异步讨论（消息群），不设固定会议时间 |

---

## 团队成员 / Team Members

| 姓名 Name | 角色 Role | 主要职责 Key Responsibilities |
|---|---|---|
| XU Lanxin | 组长 / Team Lead | 项目管理、排期、报告整合与统一提交 |
| Wong Ching Fung | UI/UX 设计 | 用户故事、线框图、Figma 高保真稿、UI 风格指南 |
| Chi Xuanyi | 前端开发 Frontend | 全部 UI 页面、客户端逻辑、接口对接、响应式布局 |
| XIE Jiayan | 后端开发 Backend | REST API、业务逻辑、鉴权与安全 |
| CEN Yin Chi | 数据库 Database | ER 建模、DDL、索引设计、种子数据、备份与迁移 |
| ZHANGZHIYUAN | 测试 QA | 测试计划与用例、单元/集成/回归测试、质量报告 |
| Aw Chun Yin | 运维与文档 DevOps | GitHub 仓库、CI/CD、部署脚本、用户手册与 README |

---

## 仓库结构 / Repository Structure

```
COMP3500SEF-Group-Project/
├── docs/          # 项目文档（章程、模块清单、说明等）
├── frontend/      # 前端代码
├── backend/       # 后端代码（含部署脚本）
├── database/      # 数据库脚本（DDL、迁移、种子数据）
├── tests/         # 测试代码
├── .gitignore     # 版本忽略规则
└── README.md      # 本文件
```

---

## 技术架构 / Tech Stack

| 层 Layer | 技术 Tech |
|---|---|
| 前端 Frontend | 待定（如 React / Vue，开发阶段确定） |
| 后端 Backend | 待定（如 Node.js / Python，开发阶段确定） |
| 数据库 Database | 待定（如 MySQL / PostgreSQL，开发阶段确定） |
| 部署 Deployment | Docker + GitHub Actions（CI/CD） |

> 技术选型在 P1 立项阶段（09-23 设计冻结前）确定并同步至本文件。

---

## 里程碑 / Milestones

| 阶段 Phase | 时间 Time | 关键节点 Key Points |
|---|---|---|
| P1 立项 Initiation | 09-16 — 09-30 | 题目确认、范围冻结、仓库建立、设计对齐、Logbook #1 |
| P2 攻坚 Build | 10-01 — 10-31 | MVP 核心链路跑通（下单→库存→配送→签收→查询）、Logbook #2/#3 |
| P3 汇报 Review | 11-01 — 11-23 | MVP 现场演示、10 分钟脱稿汇报、Logbook #4 |
| P4 定稿 Finalisation | 12-01 — 12-07 | 功能冻结（11-30）、演示视频、报告初稿/终稿 |
| P5 提交 Submission | 12-08 | 报告 + 最终 Logbook 提交（硬截止） |

---

## 如何运行 / How to Run

> 可运行的代码骨架已就位，功能开发进行中。详细代码模板见 `CODE.md`。
> A runnable skeleton is in place; feature development in progress. See `CODE.md` for templates.

- **前端 Frontend**：直接用浏览器打开 `frontend/index.html`（登录页模板）。
- **后端 Backend**：终端运行 `python backend/server.py`，访问 `http://localhost:8000/api/health` 与 `/api/orders`。
- **数据库 Database**：在 MySQL / PostgreSQL / SQLite 中执行 `database/schema.sql`。
- **测试 Tests**：运行 `python -m unittest tests/test_example.py`。

---

## 开发规范 / Dev Conventions

- 分支策略：`main`（稳定版）← `develop`（集成分支）← `feature/xxx`（功能分支）
- 提交信息使用简洁英文描述（如 `add order list page`）
- 合并通过 Pull Request 进行，由相关成员 Review
