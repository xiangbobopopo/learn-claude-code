#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日期计算器程序
功能：
1. 计算两个日期之间的天数差
2. 计算指定天数后的日期
3. 计算指定天数前的日期
4. 格式化日期显示
"""

from datetime import datetime, timedelta
import re

class DateCalculator:
    def __init__(self):
        self.date_formats = [
            '%Y-%m-%d',      # 2023-12-25
            '%Y/%m/%d',      # 2023/12/25
            '%Y.%m.%d',      # 2023.12.25
            '%Y年%m月%d日',   # 2023年12月25日
            '%m/%d/%Y',      # 12/25/2023
            '%d/%m/%Y',      # 25/12/2023
        ]
    
    def parse_date(self, date_str):
        """解析日期字符串为datetime对象"""
        if not date_str or not isinstance(date_str, str):
            return None
        
        # 清理输入
        date_str = date_str.strip()
        
        # 尝试不同的日期格式
        for fmt in self.date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def format_date(self, date_obj, fmt='%Y-%m-%d'):
        """格式化日期对象为字符串"""
        if not isinstance(date_obj, datetime):
            return None
        return date_obj.strftime(fmt)
    
    def days_between(self, date1_str, date2_str):
        """计算两个日期之间的天数差"""
        date1 = self.parse_date(date1_str)
        date2 = self.parse_date(date2_str)
        
        if not date1 or not date2:
            return None
        
        delta = date2 - date1
        return abs(delta.days)
    
    def add_days(self, date_str, days):
        """计算指定日期加上指定天数后的日期"""
        date_obj = self.parse_date(date_str)
        if not date_obj:
            return None
        
        new_date = date_obj + timedelta(days=days)
        return self.format_date(new_date)
    
    def subtract_days(self, date_str, days):
        """计算指定日期减去指定天数后的日期"""
        date_obj = self.parse_date(date_str)
        if not date_obj:
            return None
        
        new_date = date_obj - timedelta(days=days)
        return self.format_date(new_date)
    
    def get_weekday(self, date_str):
        """获取指定日期是星期几"""
        date_obj = self.parse_date(date_str)
        if not date_obj:
            return None
        
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        return weekdays[date_obj.weekday()]
    
    def is_valid_date(self, date_str):
        """检查日期字符串是否有效"""
        return self.parse_date(date_str) is not None

def main():
    calc = DateCalculator()
    
    print("=== 日期计算器 ===")
    print("支持的功能：")
    print("1. 计算两个日期之间的天数差")
    print("2. 计算指定天数后的日期")
    print("3. 计算指定天数前的日期")
    print("4. 获取日期是星期几")
    print("5. 验证日期格式")
    print("\n支持的日期格式：")
    print("- YYYY-MM-DD (如：2023-12-25)")
    print("- YYYY/MM/DD (如：2023/12/25)")
    print("- YYYY.MM.DD (如：2023.12.25)")
    print("- YYYY年MM月DD日 (如：2023年12月25日)")
    print("- MM/DD/YYYY (如：12/25/2023)")
    print("- DD/MM/YYYY (如：25/12/2023)")
    print("\n输入 'quit' 退出程序")
    
    while True:
        print("\n" + "="*50)
        choice = input("\n请选择功能 (1-5): ").strip()
        
        if choice.lower() == 'quit':
            print("感谢使用日期计算器！")
            break
        
        if choice == '1':
            print("\n--- 计算两个日期之间的天数差 ---")
            date1 = input("请输入第一个日期: ")
            date2 = input("请输入第二个日期: ")
            
            if date1.lower() == 'quit' or date2.lower() == 'quit':
                break
            
            days = calc.days_between(date1, date2)
            if days is not None:
                print(f"\n{date1} 和 {date2} 之间相差 {days} 天")
            else:
                print("\n日期格式错误，请检查输入！")
        
        elif choice == '2':
            print("\n--- 计算指定天数后的日期 ---")
            date_str = input("请输入起始日期: ")
            if date_str.lower() == 'quit':
                break
            
            try:
                days = int(input("请输入要添加的天数: "))
                result = calc.add_days(date_str, days)
                if result:
                    print(f"\n{date_str} 加上 {days} 天后是: {result}")
                    print(f"{result} 是 {calc.get_weekday(result)}")
                else:
                    print("\n日期格式错误，请检查输入！")
            except ValueError:
                print("\n天数必须是数字！")
        
        elif choice == '3':
            print("\n--- 计算指定天数前的日期 ---")
            date_str = input("请输入起始日期: ")
            if date_str.lower() == 'quit':
                break
            
            try:
                days = int(input("请输入要减去的天数: "))
                result = calc.subtract_days(date_str, days)
                if result:
                    print(f"\n{date_str} 减去 {days} 天后是: {result}")
                    print(f"{result} 是 {calc.get_weekday(result)}")
                else:
                    print("\n日期格式错误，请检查输入！")
            except ValueError:
                print("\n天数必须是数字！")
        
        elif choice == '4':
            print("\n--- 获取日期是星期几 ---")
            date_str = input("请输入日期: ")
            if date_str.lower() == 'quit':
                break
            
            weekday = calc.get_weekday(date_str)
            if weekday:
                print(f"\n{date_str} 是 {weekday}")
            else:
                print("\n日期格式错误，请检查输入！")
        
        elif choice == '5':
            print("\n--- 验证日期格式 ---")
            date_str = input("请输入要验证的日期: ")
            if date_str.lower() == 'quit':
                break
            
            if calc.is_valid_date(date_str):
                print(f"\n✓ {date_str} 是有效的日期格式")
            else:
                print(f"\n✗ {date_str} 不是有效的日期格式")
        
        else:
            print("\n无效选择，请输入 1-5 之间的数字！")

if __name__ == "__main__":
    main()