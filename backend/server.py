# -*- coding: utf-8 -*-
"""物流管理系统 · 后端 REST API 模板 / Backend REST API template
负责：XIE Jiayan
说明：使用 Python 标准库 http.server，零依赖，直接可运行。
运行：python backend/server.py  然后访问 http://localhost:8000/api/health
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# 示例数据 / Sample data（后续接入数据库 database/schema.sql）
ORDERS = [
    {"id": 1, "customer": "Alice", "status": "已发货 Shipped"},
    {"id": 2, "customer": "Bob",   "status": "待签收 Pending"},
]


class Handler(BaseHTTPRequestHandler):
    """处理 HTTP 请求 / HTTP request handler"""

    def _send(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """GET 路由 / routes"""
        if self.path == "/api/health":
            self._send({"status": "ok", "service": "lms-backend"})
        elif self.path == "/api/orders":
            self._send(ORDERS)
        else:
            self._send({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        """安静一点 / quieter logs"""
        print("[%s] %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    PORT = 8000
    print(f"LMS backend running at http://localhost:{PORT}")
    print("Try: http://localhost:8000/api/health")
    HTTPServer(("localhost", PORT), Handler).serve_forever()
