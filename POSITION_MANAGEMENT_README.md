# 仓位管理系统使用说明

## 系统功能

本系统用于管理股票仓位，包括以下功能：

1. **读取资产快照** - 从`StockAssetSnapshot`目录读取最新的资产快照文件
2. **读取操作对账单** - 从`StockOperationLog`目录读取股票操作对账单
3. **数据库存储** - 将快照和对账单数据存入MySQL数据库
4. **持仓计算** - 根据快照和操作记录计算当前实际持仓
5. **报告生成** - 生成当前持仓和盈亏报告

## 文件说明

### 核心文件

- `position_management.py` - 主程序文件，包含所有核心功能
- `position_management_demo.py` - 演示版本，使用示例数据
- `analyze_excel_files.py` - Excel文件格式分析工具

### 目录结构

```
StockAndaQ/
├── StockAssetSnapshot/          # 资产快照目录
│   ├── 20251130 资金股份查询.xls
│   └── 20251230 资金股份查询.xls
├── StockOperationLog/           # 操作对账单目录
│   └── 20251230 对帐单查询.xls
└── position_management.py       # 主程序
```

## 文件命名规范

### 资产快照文件
- 格式：`YYYYMMDD 资金股份查询.xls`
- 示例：`20251230 资金股份查询.xls`

### 操作对账单文件
- 格式：`YYYYMMDD 对帐单查询.xls`
- 示例：`20251230 对帐单查询.xls`

## 数据库表结构

### 1. asset_snapshot (资产快照表)
存储每日资产快照信息

| 字段 | 类型 | 说明 |
|------|------|------|
| snapshot_date | DATE | 快照日期 |
| total_assets | DECIMAL(15,2) | 总资产 |
| cash_balance | DECIMAL(15,2) | 现金余额 |
| market_value | DECIMAL(15,2) | 证券市值 |
| total_position_count | INT | 持仓数量 |
| profit_loss | DECIMAL(15,2) | 总盈亏 |
| profit_loss_ratio | DECIMAL(10,4) | 总盈亏比例 |

### 2. position_snapshot (持仓快照表)
存储每日持仓快照信息

| 字段 | 类型 | 说明 |
|------|------|------|
| snapshot_date | DATE | 快照日期 |
| stock_code | VARCHAR(20) | 股票代码 |
| stock_name | VARCHAR(100) | 股票名称 |
| position_count | DECIMAL(15,2) | 持仓数量 |
| available_count | DECIMAL(15,2) | 可用数量 |
| cost_price | DECIMAL(10,4) | 成本价 |
| current_price | DECIMAL(10,4) | 当前价 |
| market_value | DECIMAL(15,2) | 市值 |
| profit_loss | DECIMAL(15,2) | 盈亏 |
| profit_loss_ratio | DECIMAL(10,4) | 盈亏比例 |

### 3. stock_operation_log (操作对账单表)
存储所有股票操作记录

| 字段 | 类型 | 说明 |
|------|------|------|
| operation_date | DATE | 操作日期 |
| trade_time | TIME | 成交时间 |
| stock_code | VARCHAR(20) | 股票代码 |
| stock_name | VARCHAR(100) | 股票名称 |
| operation_type | VARCHAR(10) | 操作类型 |
| operation_count | DECIMAL(15,2) | 操作数量 |
| operation_price | DECIMAL(10,4) | 成交价格 |
| operation_amount | DECIMAL(15,2) | 成交金额 |
| commission | DECIMAL(10,2) | 手续费 |
| stamp_duty | DECIMAL(10,2) | 印花税 |
| other_fees | DECIMAL(10,2) | 其他费用 |
| net_amount | DECIMAL(15,2) | 实际发生金额 |

### 4. current_position (当前持仓表)
存储计算后的当前持仓

| 字段 | 类型 | 说明 |
|------|------|------|
| calculation_date | DATE | 计算日期 |
| stock_code | VARCHAR(20) | 股票代码 |
| stock_name | VARCHAR(100) | 股票名称 |
| current_count | DECIMAL(15,2) | 当前持仓数量 |
| available_count | DECIMAL(15,2) | 可用数量 |
| avg_cost_price | DECIMAL(10,4) | 平均成本价 |
| last_price | DECIMAL(10,4) | 最新价 |
| market_value | DECIMAL(15,2) | 市值 |
| cost_value | DECIMAL(15,2) | 成本金额 |
| profit_loss | DECIMAL(15,2) | 盈亏 |
| profit_loss_ratio | DECIMAL(10,4) | 盈亏比例 |

## 使用方法

### 前提条件

1. 安装必要的Python库：
```bash
pip install pymysql pandas xlrd openpyxl
```

2. 确保MySQL数据库已创建并配置正确

### 运行主程序

```bash
# 完整功能版本（需要Excel文件）
python position_management.py

# 演示版本（使用示例数据）
python position_management_demo.py

# 分析Excel文件格式
python analyze_excel_files.py
```

## 工作流程

1. **创建数据库表**
   - 系统自动创建所需的4个表

2. **读取最新快照**
   - 从`StockAssetSnapshot`目录读取最新的资产快照
   - 如果目录不存在或没有文件，从数据库读取最新快照

3. **读取操作对账单**
   - 从`StockOperationLog`目录读取快照日期之后的对账单
   - 将对账单数据存入数据库

4. **计算当前持仓**
   - 以快照为基准
   - 应用后续的所有买入/卖出操作
   - 计算每个股票的当前持仓、成本、盈亏

5. **生成报告**
   - 显示汇总信息（总市值、总盈亏等）
   - 显示每个股票的详细持仓信息

## 示例输出

```
================================================================================
当前持仓报告
================================================================================
计算日期: 2025-12-30
基准快照: 2025-11-30
================================================================================

【汇总信息】
  持仓数量: 3
  买入次数: 2, 买入金额: ¥56,800.00
  卖出次数: 2, 卖出金额: ¥101,280.00
  总市值: ¥285,700.00
  总成本: ¥275,450.00
  总盈亏: ¥10,250.00 (3.72%)

【持仓明细】
序号 代码          名称         持仓      可用    成本价    现价     市值         成本         盈亏      盈亏率
--------------------------------------------------------------------------------
1    600036.XSHG   招商银行    1,100.00  1,100.00   35.65    37.50  ¥41,250.00   ¥39,215.00   ¥2,035.00    5.19%
2    600519.XSHG   贵州茅台       50.00     50.00  1850.00  1950.00 ¥97,500.00   ¥92,500.00   ¥5,000.00    5.41%
3    000333.XSHE   美的集团      500.00    500.00   68.00    72.50 ¥36,250.00   ¥34,000.00   ¥2,250.00    6.62%
================================================================================
```

## Excel文件格式说明

### 资产快照文件格式（资金股份查询.xls）

通常包含以下列：
- 证券代码
- 证券名称
- 持仓数量
- 可用数量
- 成本价
- 当前价
- 市值
- 盈亏
- 盈亏比例

以及资产汇总信息：
- 总资产
- 现金余额
- 证券市值
- 总盈亏

### 操作对账单文件格式（对帐单查询.xls）

通常包含以下列：
- 操作日期
- 成交时间
- 证券代码
- 证券名称
- 操作类型（买入/卖出）
- 成交数量
- 成交价格
- 成交金额
- 手续费
- 印花税
- 发生金额

## 注意事项

1. **文件编码**：Excel文件应使用标准格式，避免特殊字符
2. **日期格式**：文件名中的日期必须为YYYYMMDD格式
3. **股票代码**：建议使用完整格式（如600036.XSHG）
4. **数据库配置**：修改`position_management.py`中的DB_CONFIG以匹配您的数据库
5. **数据备份**：建议定期备份数据库数据

## 故障排除

### 问题1：无法读取Excel文件
**解决方案**：
- 安装所需的库：`pip install pandas xlrd openpyxl`
- 检查文件路径是否正确
- 运行`analyze_excel_files.py`查看文件格式

### 问题2：数据库连接失败
**解决方案**：
- 检查MySQL服务是否启动
- 验证DB_CONFIG中的连接信息
- 确保数据库用户有足够权限

### 问题3：计算结果不正确
**解决方案**：
- 检查快照数据是否完整
- 验证操作记录的日期范围
- 确认操作类型识别正确（买入/卖出）

## 扩展功能

您可以根据需要扩展以下功能：

1. **自动定时运行** - 使用cron或Windows计划任务每日运行
2. **邮件通知** - 发送每日持仓报告到邮箱
3. **Web界面** - 使用Flask或Django创建Web管理界面
4. **图表可视化** - 生成持仓分布、盈亏趋势等图表
5. **风险分析** - 添加持仓集中度、行业分布等分析

## 技术支持

如有问题，请检查：
1. Python版本（建议3.6+）
2. 依赖库版本
3. MySQL数据库版本
4. 文件格式和编码
