"""
检查文件格式的临时脚本
"""
import pandas as pd
import os

# 检查资产快照文件
snapshot_file = 'StockAssetSnapshot/20251230 资金股份查询.xls'
print("="*60)
print("资产快照文件格式:")
print("="*60)

df_snapshot = pd.read_excel(snapshot_file)
print("\n列名:")
print(df_snapshot.columns.tolist())
print("\n前5行:")
print(df_snapshot.head())
print("\n数据类型:")
print(df_snapshot.dtypes)
print("\n文件形状:", df_snapshot.shape)

# 检查操作对账单文件
operation_file = 'StockOperationLog/20251230 对帐单查询.xls'
print("\n" + "="*60)
print("操作对账单文件格式:")
print("="*60)

df_operation = pd.read_excel(operation_file)
print("\n列名:")
print(df_operation.columns.tolist())
print("\n前10行:")
print(df_operation.head(10))
print("\n数据类型:")
print(df_operation.dtypes)
print("\n文件形状:", df_operation.shape)
