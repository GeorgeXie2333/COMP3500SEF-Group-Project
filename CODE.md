# 代码共享编辑文档 / CODE.md

> 这是一个**按模块组织的代码模板文档**：找到你自己的模块，把代码写进去 / 替换示例代码。
> This is a **module-based code template**: find your module, write your code here / replace the sample code.
>
> 目标：每个模块的代码都能**独立运行**，方便各自调试，最后拼成完整系统。
> Goal: every module's code should **run independently**, so you can test your part and we merge them into the full system.

---

## 一、模块地图 / Module Map

| 模块 Module | 成员 Member | 文件 Files | 语言 Language |
|---|---|---|---|
| 前端 Frontend | Chi Xuanyi / Wong Ching Fung | `frontend/index.html` `frontend/style.css` `frontend/app.js` | HTML / CSS / JavaScript |
| 后端 Backend | XIE Jiayan | `backend/server.py` | Python |
| 数据库 Database | CEN Yin Chi | `database/schema.sql` | SQL |
| 测试 QA | ZHANGZHIYUAN | `tests/test_example.py` | Python |
| 文档 / 部署 Docs & DevOps | XU Lanxin / Aw Chun Yin | `docs/` `backend/deploy/` | Markdown / 脚本 |

> 每个人只改**自己模块**的文件，不要动别人的文件，避免冲突。
> Only touch your own module's files to avoid conflicts.

---

## 二、前端 Frontend（HTML / CSS / JS）— 负责：Chi Xuanyi、Wong Ching Fung

在 `frontend/` 文件夹里写页面。模板已经能直接运行：

```html
<!-- frontend/index.html - 登录页模板 / Login page template -->
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <title>物流管理系统 / Logistics Management System</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <h1>物流管理系统 / LMS</h1>
  <p>把你的页面写在这里 / Write your screens here.</p>
  <button id="loginBtn">登录 Login</button>
  <script src="app.js"></script>
</body>
</html>
```

```css
/* frontend/style.css - 页面样式 / Page styles */
body { font-family: Arial, sans-serif; margin: 40px; }
h1 { color: #1F4E79; }
```

```js
// frontend/app.js - 前端逻辑 / Frontend logic
// 将来在这里用 fetch 调用后端接口 / Later call backend APIs with fetch:
// fetch('http://localhost:8000/api/orders').then(r => r.json()).then(console.log)
document.getElementById('loginBtn').onclick = () => alert('登录功能开发中 / Login coming soon');
```

**如何运行 How to run**：直接用浏览器打开 `frontend/index.html`，或 VS Code 装 Live Server 插件后右键 Open with Live Server。

---

## 三、后端 Backend（Python）— 负责：XIE Jiayan

在 `backend/server.py` 里写接口。模板是 **Python 标准库**（零依赖，直接能跑）：

```python
# backend/server.py - REST API 模板 / API template (no dependencies needed)
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

ORDERS = [{"id": 1, "status": "已发货 Shipped"}, {"id": 2, "status": "待签收 Pending"}]

class Handler(BaseHTTPRequestHandler):
    def _send(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            self._send({"status": "ok"})
        elif self.path == "/api/orders":
            self._send(ORDERS)   # 示例数据 / sample data
        else:
            self._send({"error": "not found"}, 404)

if __name__ == "__main__":
    print("Server running at http://localhost:8000")
    HTTPServer(("localhost", 8000), Handler).serve_forever()
```

**如何运行 How to run**：
```bash
python backend/server.py
# 浏览器访问 / then open: http://localhost:8000/api/health
# 和 http://localhost:8000/api/orders
```

> 接口定义遵循 API 契约文档（OpenAPI），对接前端时保持路径一致。
> Keep endpoint paths aligned with the API contract when integrating with the frontend.

---

## 四、数据库 Database（SQL）— 负责：CEN Yin Chi

在 `database/schema.sql` 里写建表语句。模板含核心业务表：

```sql
-- database/schema.sql - 核心表模板 / Core tables template
-- 兼容 MySQL / PostgreSQL / SQLite

CREATE TABLE IF NOT EXISTS customers (
  id          INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  phone       TEXT,
  address     TEXT
);

CREATE TABLE IF NOT EXISTS orders (
  id           INTEGER PRIMARY KEY,
  customer_id  INTEGER REFERENCES customers(id),
  status       TEXT NOT NULL DEFAULT 'pending',  -- pending/shipped/delivered
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory (
  id         INTEGER PRIMARY KEY,
  product    TEXT NOT NULL,
  quantity   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transport (
  id         INTEGER PRIMARY KEY,
  order_id   INTEGER REFERENCES orders(id),
  waybill_no TEXT,
  status     TEXT DEFAULT 'dispatched'
);
```

**如何运行 How to run**：在 MySQL / PostgreSQL / SQLite 中执行该文件即可。
> 表结构在 **09-23 设计冻结**后只减不加，改表请先和组长确认。

---

## 五、测试 QA（Python）— 负责：ZHANGZHIYUAN

在 `tests/` 里写测试。模板用 Python 标准库 `unittest`：

```python
# tests/test_example.py - 测试模板 / Test template
import unittest

def calc_freight(weight_kg):
    """示例业务函数：运费计算 / sample: freight calculation"""
    return weight_kg * 2.5 if weight_kg > 0 else 0

class TestFreight(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(calc_freight(10), 25.0)

    def test_zero(self):
        self.assertEqual(calc_freight(0), 0)

if __name__ == "__main__":
    unittest.main()
```

**如何运行 How to run**：
```bash
python -m unittest tests/test_example.py
```

---

## 六、共享编辑约定 / Collaboration Rules

1. **只改自己的模块文件**，提交说明写清楚（如 `add login page`）。
2. **注释用中英双语**，方便大家都能看懂。
3. **不要提交敏感信息**（密码、密钥），`.env` 已被忽略。
4. 想加新文件：在网页编辑器里点 ➕ 新建，文件放到自己模块的文件夹。
5. 不会跑 / 不会写 / 有问题 → 群里问组长或模块负责人。

---

*这份文档也是模板，随着项目推进会持续更新。This doc evolves with the project.*
