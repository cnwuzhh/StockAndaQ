# 仓位管理系统 - 完整说明

## 系统概述

本仓位管理系统用于：
1. **读取资产快照** - 从 `StockAssetSnapshot/` 目录读取最新的资产快照文件
2. **读取操作对账单** - 从 `StockOperationLog/` 目录读取股票操作对账单
3. **数据库存储** - 将快照和对账单数据存入MySQL数据库
4. **持仓计算** - 根据快照和操作记录计算当前实际持仓
5. **报告生成** - 生成当前持仓和盈亏报告

## 文件列表

### 核心程序
1. **position_management.py** - 完整版本（需要pandas, xlrd等库）
   - 支持读取Excel文件
   - 支持数据库操作
   - 完整的持仓计算功能

2. **position_management_standalone.py** - 独立版本（需要pymysql）
   - 不依赖pandas
   - 支持数据库操作
   - 适合服务器环境

3. **position_management_pure_demo.py** - 演示版本（纯Python，无依赖）
   - 不依赖任何外部库
   - 使用示例数据
   - 用于演示计算逻辑

### 工具脚本
4. **analyze_excel_files.py** - Excel文件格式分析工具
   - 帮助理解Excel文件的实际格式

### 文档
5. **POSITION_MANAGEMENT_README.md** - 详细使用说明
6. **README_POSITION_MANAGEMENT.md** - 本文件

## 快速开始

### 方式1：使用演示版本（无需任何依赖）

```bash
python position_management_pure_demo.py
```

这个版本使用内置的示例数据，演示完整的持仓计算流程。

### 方式2：使用完整版本（需要安装依赖）

```bash
# 安装依赖
pip install pymysql pandas xlrd openpyxl

# 运行完整版本
python position_management.py
```

### 方式3：使用独立版本（需要pymysql）

```bash
# 安装pymysql
pip install pymysql

# 运行独立版本
python position_management_standalone.py
```

## 系统架构

### 数据流程

```
StockAssetSnapshot/        StockOperationLog/
     │                            │
     │ 读取最新的快照              │ 读取对账单
     ▼                            ▼
┌──────────────────────────────────────┐
│     快照数据        操作记录      │
└──────────────────────────────────────┘
                 │
                 │ 保存到数据库
                 ▼
┌──────────────────────────────────────┐
│           MySQL 数据库                │
│  ├─ asset_snapshot (资产快照)        │
│  ├─ position_snapshot (持仓快照)     │
│  ├─ stock_operation_log (操作记录)  │
│  └─ current_position (当前持仓)     │
└──────────────────────────────────────┘
                 │
                 │ 计算当前持仓
                 ▼
┌──────────────────────────────────────┐
│         持仓计算引擎                  │
│  ├─ 加载快照持仓                     │
│  ├─ 应用操作记录                     │
│  ├─ 计算加权平均成本                 │
│  └─ 计算市值和盈亏                   │
└──────────────────────────────────────┘
                 │
                 │ 生成报告
                 ▼
┌──────────────────────────────────────┐
│           持仓报告                    │
│  ├─ 汇总信息                         │
│  ├─ 持仓明细                         │
│  └─ 盈亏分析                         │
└──────────────────────────────────────┘
```

## 数据库表结构

### 1. asset_snapshot - 资产快照表
存储每日资产快照信息

```sql
CREATE TABLE asset_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    total_assets DECIMAL(15,2),        -- 总资产
    cash_balance DECIMAL(15,2),         -- 现金余额
    market_value DECIMAL(15,2),         -- 证券市值
    total_position_count INT,           -- 持仓数量
    profit_loss DECIMAL(15,2),          -- 总盈亏
    profit_loss_ratio DECIMAL(10,4),    -- 总盈亏比例
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_snapshot_date (snapshot_date)
);
```

### 2. position_snapshot - 持仓快照表
存储每日持仓快照信息

```sql
CREATE TABLE position_snapshot (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    position_count DECIMAL(15,2),       -- 持仓数量
    available_count DECIMAL(15,2),      -- 可用数量
    cost_price DECIMAL(10,4),           -- 成本价
    current_price DECIMAL(10,4),        -- 当前价
    market_value DECIMAL(15,2),         -- 市值
    profit_loss DECIMAL(15,2),          -- 盈亏
    profit_loss_ratio DECIMAL(10,4),    -- 盈亏比例
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_date_stock (snapshot_date, stock_code)
);
```

### 3. stock_operation_log - 操作对账单表
存储所有股票操作记录

```sql
CREATE TABLE stock_operation_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    operation_date DATE NOT NULL,
    trade_time TIME,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    operation_type VARCHAR(10),         -- 买入/卖出
    operation_count DECIMAL(15,2),      -- 数量
    operation_price DECIMAL(10,4),      -- 成交价格
    operation_amount DECIMAL(15,2),     -- 成交金额
    commission DECIMAL(10,2),           -- 手续费
    stamp_duty DECIMAL(10,2),           -- 印花税
    other_fees DECIMAL(10,2),           -- 其他费用
    net_amount DECIMAL(15,2),           -- 实际发生金额
    remark VARCHAR(255),

    INDEX idx_operation_date (operation_date),
    INDEX idx_stock_code (stock_code)
);
```

### 4. current_position - 当前持仓表
存储计算后的当前持仓

```sql
CREATE TABLE current_position (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    calculation_date DATE NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100),
    current_count DECIMAL(15,2),        -- 当前持仓数量
    available_count DECIMAL(15,2),      -- 可用数量
    avg_cost_price DECIMAL(10,4),       -- 平均成本价
    last_price DECIMAL(10,4),           -- 最新价
    market_value DECIMAL(15,2),         -- 市值
    cost_value DECIMAL(15,2),           -- 成本金额
    profit_loss DECIMAL(15,2),          -- 盈亏
    profit_loss_ratio DECIMAL(10,4),    -- 盈亏比例
    last_update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_date_stock (calculation_date, stock_code)
);
```

## 持仓计算逻辑

### 1. 初始化
从最新快照加载持仓信息作为基准

### 2. 买入操作
```
新持仓数量 = 旧持仓数量 + 买入数量
新成本金额 = 旧成本金额 + 买入金额
新成本价 = 新成本金额 / 新持仓数量  (加权平均)
```

### 3. 卖出操作
```
卖出成本 = 成本金额 * (卖出数量 / 旧持仓数量)
已实现盈亏 = 卖出金额 - 卖出成本
新持仓数量 = 旧持仓数量 - 卖出数量
新成本金额 = 旧成本金额 - 卖出成本
```

### 4. 市值和盈亏计算
```
市值 = 持仓数量 * 最新价格
成本金额 = 持仓数量 * 平均成本价
未实现盈亏 = 市值 - 成本金额
盈亏比例 = 未实现盈亏 / 成本金额
```

## 示例输出

运行 `position_management_pure_demo.py` 的输出：

```
################################################################################
# Position Management System - Pure Python Demo
# Run time: 2025-12-30 17:35:49
################################################################################

Sample data:
  Snapshot date: 2025-11-30
  Snapshot positions: 3
  Operations: 4

Starting calculation...

Initial positions from snapshot:
  招商银行 (600036.XSHG): 1000.00 shares @ 35.50
  贵州茅台 (600519.XSHG): 100.00 shares @ 1850.00
  美的集团 (000333.XSHE): 500.00 shares @ 68.00

[1] 2025-12-05 - 买入
    BUY  招商银行 (600036.XSHG) 200.00 shares @ 36.50 = 7300.00
         New position: 1200.00 shares @ 35.67

[2] 2025-12-10 - 卖出
    SELL 贵州茅台 (600519.XSHG) 50.00 shares @ 1950.00 = 97500.00
         Sold cost: 92500.00, Realized profit: 5000.00
         Remaining: 50.00 shares @ 1850.00

[3] 2025-12-15 - 买入
    BUY  五粮液 (000858.XSHE) 300.00 shares @ 165.00 = 49500.00
         New position: 300.00 shares @ 165.00

[4] 2025-12-20 - 卖出
    SELL 招商银行 (600036.XSHG) 100.00 shares @ 37.80 = 3780.00
         Sold cost: 3566.67, Realized profit: 213.33
         Remaining: 1100.00 shares @ 35.67

================================================================================
Calculation completed:
  Current positions: 4
  Buy trades: 2, Buy amount: 56800.00
  Sell trades: 2, Sell amount: 101280.00
  Total market value: 224830.00
  Total cost: 215233.33
  Total P&L: 9596.67 (4.46%)
================================================================================

CURRENT POSITION REPORT
================================================================================

[Summary]
  Positions: 4
  Buy trades: 2, Buy amount: 56,800.00
  Sell trades: 2, Sell amount: 101,280.00
  Total market value: 224,830.00
  Total cost: 215,233.33
  Total P&L: 9,596.67 (4.46%)

[Position Details]
No   Code           Name           Shares      Avail     Cost    Price       Market      CostVal          P&L     P&L%
----------------------------------------------------------------------------------------------------
1    600036.XSHG    招商银行         1100.00    1100.00    35.67    37.80    41,580.00    39,233.33     2,346.67    5.98%
2    600519.XSHG    贵州茅台           50.00      50.00  1850.00  1950.00    97,500.00    92,500.00     5,000.00    5.41%
3    000333.XSHE    美的集团          500.00     500.00    68.00    72.50    36,250.00    34,000.00     2,250.00    6.62%
4    000858.XSHE    五粮液            300.00     300.00   165.00   165.00    49,500.00    49,500.00         0.00    0.00%
====================================================================================================
```

## 文件格式说明

### 资产快照文件
- **文件名格式**: `YYYYMMDD 资金股份查询.xls`
- **示例**: `20251230 资金股份查询.xls`
- **位置**: `StockAssetSnapshot/` 目录

### 操作对账单文件
- **文件名格式**: `YYYYMMDD 对帐单查询.xls`
- **示例**: `20251230 对帐单查询.xls`
- **位置**: `StockOperationLog/` 目录

## 使用建议

### 1. 定期运行
建议每日收盘后运行一次，更新持仓数据

```bash
# 添加到crontab (Linux)
0 16 * * 1-5 cd /path/to/StockAndaQ && python position_management_standalone.py

# 或使用Windows计划任务
```

### 2. 数据备份
定期备份数据库数据

```bash
mysqldump -u stockDBA -p StockAnalysisDataStore > backup_$(date +%Y%m%d).sql
```

### 3. 扩展功能
可以根据需要添加：
- 邮件通知功能
- Web界面
- 图表可视化
- 风险分析指标
- 持仓集中度分析

## 故障排除

### 问题1：Excel文件读取失败
**解决方案**：
1. 运行 `analyze_excel_files.py` 查看文件格式
2. 安装所需的库：`pip install pandas xlrd openpyxl`
3. 检查文件路径和编码

### 问题2：数据库连接失败
**解决方案**：
1. 检查MySQL服务是否启动
2. 验证DB_CONFIG配置
3. 确保数据库用户有足够权限

### 问题3：计算结果异常
**解决方案**：
1. 检查快照数据是否完整
2. 验证操作记录的日期顺序
3. 确认股票代码格式一致

## 技术要点

### 1. 加权平均成本价计算
买入时使用加权平均法计算新的成本价：
```
新成本价 = (旧成本金额 + 买入金额) / (旧数量 + 买入数量)
```

### 2. 已实现盈亏 vs 未实现盈亏
- **已实现盈亏**: 卖出时的实际盈亏
- **未实现盈亏**: 持仓的浮动盈亏

### 3. 数据一致性
- 使用数据库事务确保数据一致性
- 快照和操作记录按时间顺序处理
- 定期校验计算结果

## 未来改进方向

1. **自动化数据获取** - 直接从券商API获取数据
2. **实时行情** - 集成实时行情数据
3. **智能分析** - 添加AI驱动的持仓建议
4. **风险控制** - 实现止损止盈提醒
5. **多账户管理** - 支持多个交易账户

## 联系支持

如有问题或建议，请检查：
1. Python版本（建议3.6+）
2. 依赖库版本
3. MySQL数据库版本
4. 文件格式和编码

---

**最后更新**: 2025-12-30
**版本**: 1.0.0
