# 仓位管理系统 - 创建成功！

## 系统文件清单

已为您创建以下文件：

### 核心程序
1. **position_management.py** - 完整版本（需要pandas等库）
   - 支持读取Excel文件
   - 完整的数据库功能
   - 持仓计算引擎

2. **position_management_standalone.py** - 独立版本（需要pymysql）
   - 不依赖pandas
   - 完整的数据库功能

3. **position_management_pure_demo.py** - 演示版本（无依赖）
   - 纯Python实现
   - 使用示例数据
   - ✅ **已测试成功运行**

### 工具脚本
4. **start_position_management.py** - 快速启动脚本
   - 自动检测环境
   - 选择合适的版本
   - ✅ **已测试成功运行**

5. **analyze_excel_files.py** - Excel文件分析工具
6. **check_file_format.py** - 文件格式检查工具

### 文档
7. **README_POSITION_MANAGEMENT.md** - 完整使用说明
8. **POSITION_MANAGEMENT_README.md** - 详细文档

## 快速开始

### 立即体验（无需任何依赖）

```bash
python start_position_management.py
```

或直接运行演示版本：

```bash
python position_management_pure_demo.py
```

## 系统功能

### 1. 读取资产快照
- 📁 从 `StockAssetSnapshot/` 读取最新的资产快照
- 📅 文件格式：`YYYYMMDD 资金股份查询.xls`

### 2. 读取操作对账单
- 📁 从 `StockOperationLog/` 读取股票操作对账单
- 📅 文件格式：`YYYYMMDD 对帐单查询.xls`

### 3. 数据库存储
- 💾 自动创建4个数据库表
- 💾 保存快照和操作记录
- 💾 保存计算结果

### 4. 持仓计算
- 🔄 从快照开始应用所有操作
- 🔄 计算加权平均成本价
- 🔄 计算市值和盈亏

### 5. 报告生成
- 📊 生成详细的持仓报告
- 📊 包含汇总信息和明细
- 📊 显示盈亏情况

## 演示输出示例

```
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

## 使用真实数据

### 步骤1：安装依赖

```bash
pip install pymysql pandas xlrd openpyxl
```

### 步骤2：准备数据文件

将您的券商导出文件放到对应目录：

```
StockAndaQ/
├── StockAssetSnapshot/
│   └── 20251230 资金股份查询.xls    ← 您的资产快照
└── StockOperationLog/
    └── 20251230 对帐单查询.xls       ← 您的操作对账单
```

### 步骤3：运行程序

```bash
python position_management.py
```

## 数据库表结构

系统会自动创建以下4个表：

| 表名 | 用途 |
|------|------|
| asset_snapshot | 资产快照 |
| position_snapshot | 持仓快照 |
| stock_operation_log | 操作记录 |
| current_position | 当前持仓（计算结果） |

## 核心计算逻辑

### 买入操作
```
新持仓数量 = 旧持仓数量 + 买入数量
新成本价 = (旧成本金额 + 买入金额) / 新持仓数量  # 加权平均
```

### 卖出操作
```
卖出成本 = 成本金额 × (卖出数量 / 旧持仓数量)
已实现盈亏 = 卖出金额 - 卖出成本
```

### 盈亏计算
```
市值 = 持仓数量 × 最新价格
未实现盈亏 = 市值 - 成本金额
```

## 目录结构

```
StockAndaQ/
├── StockAssetSnapshot/              ← 资产快照目录
│   ├── 20251130 资金股份查询.xls
│   └── 20251230 资金股份查询.xls
│
├── StockOperationLog/               ← 操作对账单目录
│   └── 20251230 对帐单查询.xls
│
├── position_management.py           ← 完整版本
├── position_management_standalone.py ← 独立版本
├── position_management_pure_demo.py  ← 演示版本 ✅
├── start_position_management.py     ← 快速启动 ✅
│
└── README_POSITION_MANAGEMENT.md    ← 完整文档
```

## 下一步

1. ✅ **运行演示** - 查看系统效果
   ```bash
   python start_position_management.py
   ```

2. 📖 **阅读文档** - 了解详细功能
   - [README_POSITION_MANAGEMENT.md](README_POSITION_MANAGEMENT.md)
   - [POSITION_MANAGEMENT_README.md](POSITION_MANAGEMENT_README.md)

3. 🔧 **安装依赖** - 准备使用真实数据
   ```bash
   pip install pymysql pandas xlrd openpyxl
   ```

4. 📊 **准备数据** - 放置Excel文件到对应目录

5. 🚀 **正式运行** - 分析真实持仓
   ```bash
   python position_management.py
   ```

## 技术支持

如遇问题，请检查：
- Python版本（建议3.6+）
- 依赖库安装情况
- Excel文件格式和路径
- MySQL数据库连接

---

**系统版本**: 1.0.0
**创建日期**: 2025-12-30
**状态**: ✅ 已测试并成功运行
