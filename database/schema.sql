-- 物流管理系统 · 数据库建表模板 / Database schema template
-- 负责：CEN Yin Chi
-- 说明：兼容 MySQL / PostgreSQL / SQLite；在数据库客户端执行本文件即可建表。
-- 注意：09-23 设计冻结后表结构只减不加，改表前请与组长确认。

CREATE TABLE IF NOT EXISTS customers (
  id         INTEGER PRIMARY KEY,              -- 客户ID / customer id
  name       TEXT NOT NULL,                    -- 姓名 / name
  phone      TEXT,                             -- 电话 / phone
  address    TEXT                              -- 地址 / address
);

CREATE TABLE IF NOT EXISTS orders (
  id           INTEGER PRIMARY KEY,            -- 订单ID / order id
  customer_id  INTEGER REFERENCES customers(id),
  status       TEXT NOT NULL DEFAULT 'pending',-- pending / shipped / delivered
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory (
  id         INTEGER PRIMARY KEY,              -- 库存ID / inventory id
  product    TEXT NOT NULL,                    -- 商品 / product
  quantity   INTEGER NOT NULL DEFAULT 0        -- 数量 / quantity
);

CREATE TABLE IF NOT EXISTS transport (
  id         INTEGER PRIMARY KEY,              -- 运单ID / transport id
  order_id   INTEGER REFERENCES orders(id),
  waybill_no TEXT,                             -- 运单号 / waybill no.
  status     TEXT DEFAULT 'dispatched'         -- 配送状态 / dispatch status
);

-- 示例种子数据 / Sample seed data
INSERT INTO customers (name, phone, address) VALUES ('Alice', '12345678', 'Kowloon');
INSERT INTO inventory (product, quantity) VALUES ('Widget A', 100);
