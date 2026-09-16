# 物流管理系统 · 小组协作文档仓库
# Logistics Management System · Team Collaboration Repo

> 本仓库用于团队**共享编辑**项目文档与代码。
> This repository is for the team to **collaboratively edit** project docs and code.
>
> 📌 谁改了什么都会有记录（Git 历史），改坏了随时能回滚。

---

## 一、项目简介 / About

| 项目 Project | 物流管理系统 / Logistics Management System |
|---|---|
| 课程 Course | Course Engineering（软件工程） |
| 团队 Team | 7 人，组长：XU Lanxin |
| 沟通 Communication | 线上异步讨论（消息群），不设固定会议时间 |

**目标 Objective**：开发一个可运行的 Web 物流管理系统，覆盖订单 → 库存 → 运输 → 签收 → 查询的核心业务链路。

---

## 二、团队成员 / Team Members

| 姓名 Name | 角色 Role | 模块 Module |
|---|---|---|
| XU Lanxin | 组长 / Team Lead | 项目管理、整体交付 |
| Wong Ching Fung | UI/UX 设计 | 用户故事、线框图、高保真稿 |
| Chi Xuanyi | 前端开发 Frontend | 全部 UI 页面、接口对接 |
| XIE Jiayan | 后端开发 Backend | REST API、业务逻辑、鉴权 |
| CEN Yin Chi | 数据库 Database | ER 建模、DDL、索引、迁移 |
| ZHANGZHIYUAN | 测试 QA | 测试计划、用例、质量报告 |
| Aw Chun Yin | 运维与文档 DevOps | GitHub 仓库、CI/CD、部署、手册 |

---

## 三、目录结构 / Folder Structure

```
物流管理系统_LMS/
├── docs/          # 项目文档（章程、模块清单、说明等）
├── frontend/      # 前端代码（Chi Xuanyi / Wong Ching Fung）
├── backend/       # 后端代码（XIE Jiayan）
├── database/      # 数据库脚本（CEN Yin Chi）
├── tests/         # 测试代码（ZHANGZHIYUAN）
└── README.md      # 本文件
```

> 各成员在自己的模块文件夹里写代码，互不干扰。

---

## 四、协作流程 / How We Collaborate

1. **克隆仓库**：`git clone <仓库地址>`（每人本地一份）
2. **建分支**：开发前先建自己的分支，如 `feature/frontend-login`，不要在 main 上直接改
3. **开发 & 提交**：改完代码 → `git add .` → `git commit -m "描述改动"` → `git push`
4. **合并请求（PR）**：在 GitHub 网页发起 Pull Request，由相关成员 Review 后合并
5. **同步最新**：每天开始前先 `git pull`，避免冲突

```
main ──── 稳定版（可运行）
  └── develop ──── 日常开发集成分支
        └── feature/xxx ──── 每个人的功能分支，完成后合并回 develop
```

---

## 五、里程碑 / Milestones

| 阶段 Phase | 时间 Time | 关键节点 Key Points |
|---|---|---|
| P1 立项 Initiation | 09-16 — 09-30 | 范围冻结、仓库建立、设计对齐、Logbook #1 |
| P2 攻坚 Build | 10-01 — 10-31 | MVP 全链路跑通、Logbook #2/#3 |
| P3 汇报 Review | 11-01 — 11-23 | 10 分钟汇报、Logbook #4 |
| P4 定稿 Finalisation | 12-01 — 12-07 | 功能冻结（11-30）、演示视频、报告 |
| P5 提交 Submission | 12-08 | 报告 + Logbook 提交（硬截止） |

---

## 六、快速开始 / Quick Start（VS Code）

1. 安装 **Git** 与 **VS Code**
2. VS Code 打开本文件夹（File → Open Folder）
3. 左下角「源代码管理 Source Control」图标 → 查看改动 → 提交 Commit → 同步 Sync

> 首次提交前需要设置身份（一次即可）：
> ```bash
> git config --global user.name "你的名字 Your Name"
> git config --global user.email "你的邮箱 your@email.com"
> ```
