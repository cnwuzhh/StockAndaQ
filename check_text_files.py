"""
检查文本文件格式
"""
import os
import re

# 读取资产快照文件
print("="*80)
print("资产快照文件内容:")
print("="*80)
snapshot_file = 'StockAssetSnapshot/20260105 资金股份查询.txt'

try:
    with open(snapshot_file, 'r', encoding='gbk') as f:
        content = f.read()
        print(content[:2000])
except Exception as e:
    print(f"错误: {e}")

print("\n" + "="*80)
print("对账单文件内容:")
print("="*80)
operation_file = 'StockOperationLog/20260105 对帐单查询.txt'

try:
    with open(operation_file, 'r', encoding='gbk') as f:
        content = f.read()
        print(content[:2000])
except Exception as e:
    print(f"错误: {e}")
