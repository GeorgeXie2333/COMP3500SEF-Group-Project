# -*- coding: utf-8 -*-
"""物流管理系统 · 测试模板 / Test template
负责：ZHANGZHIYUAN
说明：Python 标准库 unittest，零依赖。
运行：python -m unittest tests/test_example.py
"""
import unittest


def calc_freight(weight_kg):
    """示例业务函数：运费计算 / sample: freight calculation (HKD per kg)"""
    return weight_kg * 2.5 if weight_kg > 0 else 0


class TestFreight(unittest.TestCase):
    """运费函数测试 / freight function tests"""

    def test_normal(self):
        self.assertEqual(calc_freight(10), 25.0)

    def test_zero(self):
        self.assertEqual(calc_freight(0), 0)

    def test_negative(self):
        self.assertEqual(calc_freight(-5), 0)


if __name__ == "__main__":
    unittest.main()
