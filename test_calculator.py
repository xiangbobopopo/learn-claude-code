#!/usr/bin/env python3
"""
Calculator Test Script
测试计算器程序的各种功能
"""

import sys
sys.path.append('/Users/tudada/vscode/learn-claude-code')

from calculator import Calculator

def test_basic_operations():
    """测试基本运算"""
    calc = Calculator()
    
    print("=== 测试基本运算 ===")
    
    # 加法测试
    result = calc.add(5, 3)
    assert result == 8, f"加法测试失败: 5 + 3 = {result}, 期望 8"
    print(f"✓ 加法测试: 5 + 3 = {result}")
    
    # 减法测试
    result = calc.subtract(10, 4)
    assert result == 6, f"减法测试失败: 10 - 4 = {result}, 期望 6"
    print(f"✓ 减法测试: 10 - 4 = {result}")
    
    # 乘法测试
    result = calc.multiply(6, 7)
    assert result == 42, f"乘法测试失败: 6 × 7 = {result}, 期望 42"
    print(f"✓ 乘法测试: 6 × 7 = {result}")
    
    # 除法测试
    result = calc.divide(15, 3)
    assert result == 5, f"除法测试失败: 15 ÷ 3 = {result}, 期望 5"
    print(f"✓ 除法测试: 15 ÷ 3 = {result}")
    
    # 幂运算测试
    result = calc.power(2, 3)
    assert result == 8, f"幂运算测试失败: 2^3 = {result}, 期望 8"
    print(f"✓ 幂运算测试: 2^3 = {result}")
    
    # 平方根测试
    result = calc.sqrt(16)
    assert result == 4, f"平方根测试失败: √16 = {result}, 期望 4"
    print(f"✓ 平方根测试: √16 = {result}")

def test_error_handling():
    """测试错误处理"""
    calc = Calculator()
    
    print("\n=== 测试错误处理 ===")
    
    # 除零错误测试
    try:
        calc.divide(10, 0)
        assert False, "除零错误应该抛出异常"
    except ValueError as e:
        print(f"✓ 除零错误处理: {e}")
    
    # 负数平方根测试
    try:
        calc.sqrt(-4)
        assert False, "负数平方根应该抛出异常"
    except ValueError as e:
        print(f"✓ 负数平方根错误处理: {e}")

def test_history():
    """测试历史记录功能"""
    calc = Calculator()
    
    print("\n=== 测试历史记录 ===")
    
    # 执行一些计算
    calc.add(1, 2)
    calc.multiply(3, 4)
    calc.divide(10, 2)
    
    # 检查历史记录
    assert len(calc.history) == 3, f"历史记录数量错误: {len(calc.history)}, 期望 3"
    print(f"✓ 历史记录数量: {len(calc.history)}")
    
    # 显示历史记录
    print("计算历史:")
    for i, calc_str in enumerate(calc.history, 1):
        print(f"  {i}. {calc_str}")
    
    # 测试清除历史
    calc.clear_history()
    assert len(calc.history) == 0, "历史记录清除失败"
    print("✓ 历史记录清除成功")

def test_floating_point():
    """测试浮点数运算"""
    calc = Calculator()
    
    print("\n=== 测试浮点数运算 ===")
    
    # 浮点数加法
    result = calc.add(3.5, 2.7)
    expected = 6.2
    assert abs(result - expected) < 1e-10, f"浮点数加法测试失败: {result}, 期望 {expected}"
    print(f"✓ 浮点数加法: 3.5 + 2.7 = {result}")
    
    # 浮点数除法
    result = calc.divide(7, 3)
    expected = 7/3
    assert abs(result - expected) < 1e-10, f"浮点数除法测试失败: {result}, 期望 {expected}"
    print(f"✓ 浮点数除法: 7 ÷ 3 = {result}")

def run_all_tests():
    """运行所有测试"""
    print("开始测试计算器程序...\n")
    
    try:
        test_basic_operations()
        test_error_handling()
        test_history()
        test_floating_point()
        
        print("\n🎉 所有测试通过！计算器程序工作正常。")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    run_all_tests()