# 组员协作指南 · ONBOARDING（临时文件，学会后可删除）

> 这份文件是**操作教程**，不是项目文档。大家按下面步骤弄好后，组长会把它从仓库删掉。
> 正式的项目介绍请看根目录的 `README.md`。

---

## 🌟 方法一：网页直接编辑（最简单，推荐新手，不用装任何软件）

1. 注册 GitHub 账号：打开 github.com → 右上角 **Sign up**（免费）→ 把**用户名**发给组长
2. 组长邀请你后，打开仓库链接并登录：
   `https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project`
3. 在仓库页面按键盘 **`.` 键**（英文句号）→ 进入**网页版编辑器**（github.dev）
4. 像用记事本一样直接改文件（Ctrl+S 保存）
5. 点左边「源代码管理」图标 → 写一句说明（如 "add login page"）→ 点 **✓ 提交 Commit** → 点 **同步 Publish/Sync** 推送

> 更简单的小改：文件列表点开文件 → 点右上角 **✏️ 铅笔图标** → 改完页面底部 **Commit changes**。

---

## 💻 方法二：本地 VS Code 开发（想认真写代码的同学用这个）

### 第 1 步：注册 GitHub
github.com → Sign up，把**用户名**发给组长。

### 第 2 步：安装 Git 和 VS Code
- Git：git-scm.com/download/win（一路 Next）
- VS Code：code.visualstudio.com（一路 Next）

打开终端（开始菜单搜 PowerShell），设置一次身份：

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱"
```

### 第 3 步：克隆仓库（一次即可）
VS Code 里按 **Ctrl+Shift+P** → 输入 **Git: Clone** → 粘贴仓库地址：

```
https://github.com/xulanxin30-tech/COMP3500SEF-Group-Project.git
```

选一个本地文件夹，然后用 **File → Open Folder** 打开。

### 第 4 步：每天的工作流
1. **拉取**：点左下角「同步」按钮（或终端 `git pull`）
2. **干活**：在自己的模块文件夹里改代码
3. **提交**：左边「源代码管理」→ 点 `+` 暂存 → 写说明 → ✓ 提交
4. **推送**：点「同步」/ Push
5. **合并**：功能完成后在 GitHub 网页发起 **Pull Request**，审核后合并

---

## 📁 每个人写在哪里

| 成员 Member | 角色 Role | 代码/文档放哪里 Where |
|---|---|---|
| XU Lanxin | 组长 / 整体交付 | docs/ |
| Wong Ching Fung | UI/UX 设计 | docs/design/ |
| Chi Xuanyi | 前端开发 | frontend/ |
| XIE Jiayan | 后端开发 | backend/ |
| CEN Yin Chi | 数据库 | database/ |
| ZHANGZHIYUAN | 测试 QA | tests/ |
| Aw Chun Yin | 运维与文档 | backend/deploy/ + docs/ |

---

## 🤝 小组约定

- 不要直接在 `main` 上乱改，做新功能先建分支：`git checkout -b feature/你的功能名`
- 提交说明写清楚做了什么
- 推送被拒绝（non-fast-forward）→ 先 `git pull` 再 push
- 不要提交密码、密钥（`.env` 已被自动忽略）
- 搞不定先问组长或对应模块负责人

---

## ✅ 完成清单

- [ ] 注册 GitHub 并发了用户名给组长
- [ ] 能打开仓库链接并登录
- [ ] 用网页版（`. 键`）或本地 VS Code 成功编辑过文件
- [ ] 完成第一次提交 + 推送
