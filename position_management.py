"""
仓位管理系统
功能：
1. 读取StockAssetSnapshot目录下的最新资产快照文件
2. 读取StockOperationLog目录下的股票操作对账单
3. 将操作对账单存入数据库
4. 根据最新快照和操作记录生成当前结算后的资产和持仓
"""

import os
import re
import pymysql
from datetime import datetime, timedelta
from pathlib import Path

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stockDBA',
    'password': 'stockDBA25001',
    'database': 'StockAnalysisDataStore',
    'charset': 'utf8mb4'
}

# 目录配置
SNAPSHOT_DIR = 'StockAssetSnapshot'
OPERATION_LOG_DIR = 'StockOperationLog'


# ==================== 数据库表创建 ====================

def create_position_tables():
    """创建仓位管理相关表"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 1. 资产快照表
        create_snapshot_sql = """
        CREATE TABLE IF NOT EXISTS asset_snapshot (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            snapshot_date DATE NOT NULL COMMENT '快照日期',
            total_assets DECIMAL(15,2) COMMENT '总资产',
            cash_balance DECIMAL(15,2) COMMENT '现金余额',
            market_value DECIMAL(15,2) COMMENT '证券市值',
            total_position_count INT COMMENT '持仓数量',
            profit_loss DECIMAL(15,2) COMMENT '总盈亏',
            profit_loss_ratio DECIMAL(10,4) COMMENT '总盈亏比例',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

            UNIQUE KEY uk_snapshot_date (snapshot_date),
            INDEX idx_snapshot_date (snapshot_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='资产快照表';
        """

        # 2. 持仓快照表
        create_position_sql = """
        CREATE TABLE IF NOT EXISTS position_snapshot (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            snapshot_date DATE NOT NULL COMMENT '快照日期',
            stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
            stock_name VARCHAR(100) COMMENT '股票名称',
            position_count DECIMAL(15,2) COMMENT '持仓数量',
            available_count DECIMAL(15,2) COMMENT '可用数量',
            cost_price DECIMAL(10,4) COMMENT '成本价',
            current_price DECIMAL(10,4) COMMENT '当前价',
            market_value DECIMAL(15,2) COMMENT '市值',
            profit_loss DECIMAL(15,2) COMMENT '盈亏',
            profit_loss_ratio DECIMAL(10,4) COMMENT '盈亏比例',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

            UNIQUE KEY uk_date_stock (snapshot_date, stock_code),
            INDEX idx_snapshot_date (snapshot_date),
            INDEX idx_stock_code (stock_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='持仓快照表';
        """

        # 3. 操作对账单表
        create_operation_sql = """
        CREATE TABLE IF NOT EXISTS stock_operation_log (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            operation_date DATE NOT NULL COMMENT '操作日期',
            trade_time TIME COMMENT '成交时间',
            stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
            stock_name VARCHAR(100) COMMENT '股票名称',
            operation_type VARCHAR(10) NOT NULL COMMENT '操作类型（买入/卖出/分红/配股等）',
            operation_count DECIMAL(15,2) COMMENT '操作数量（正数为买入，负数为卖出）',
            operation_price DECIMAL(10,4) COMMENT '成交价格',
            operation_amount DECIMAL(15,2) COMMENT '成交金额',
            commission DECIMAL(10,2) COMMENT '手续费',
            stamp_duty DECIMAL(10,2) COMMENT '印花税',
            other_fees DECIMAL(10,2) COMMENT '其他费用',
            net_amount DECIMAL(15,2) COMMENT '实际发生金额',
            remark VARCHAR(255) COMMENT '备注',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

            INDEX idx_operation_date (operation_date),
            INDEX idx_stock_code (stock_code),
            INDEX idx_operation_type (operation_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票操作对账单表';
        """

        # 4. 当前持仓表（实时计算结果）
        create_current_position_sql = """
        CREATE TABLE IF NOT EXISTS current_position (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            calculation_date DATE NOT NULL COMMENT '计算日期',
            stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
            stock_name VARCHAR(100) COMMENT '股票名称',
            current_count DECIMAL(15,2) COMMENT '当前持仓数量',
            available_count DECIMAL(15,2) COMMENT '可用数量',
            avg_cost_price DECIMAL(10,4) COMMENT '平均成本价',
            last_price DECIMAL(10,4) COMMENT '最新价',
            market_value DECIMAL(15,2) COMMENT '市值',
            cost_value DECIMAL(15,2) COMMENT '成本金额',
            profit_loss DECIMAL(15,2) COMMENT '盈亏',
            profit_loss_ratio DECIMAL(10,4) COMMENT '盈亏比例',
            last_update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',

            UNIQUE KEY uk_date_stock (calculation_date, stock_code),
            INDEX idx_calculation_date (calculation_date),
            INDEX idx_stock_code (stock_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='当前持仓表';
        """

        # 创建表
        for sql in [create_snapshot_sql, create_position_sql,
                    create_operation_sql, create_current_position_sql]:
            cursor.execute(sql)

        conn.commit()
        cursor.close()
        conn.close()

        print("✓ 仓位管理表创建成功！")
        return True

    except Exception as e:
        print(f"✗ 创建表失败: {e}")
        return False


# ==================== 文件读取模块 ====================

def get_latest_snapshot_file():
    """
    获取最新的资产快照文件

    返回:
        tuple: (文件路径, 快照日期)
    """
    if not os.path.exists(SNAPSHOT_DIR):
        print(f"✗ 快照目录不存在: {SNAPSHOT_DIR}")
        return None, None

    # 查找所有快照文件
    snapshot_files = []
    pattern = re.compile(r'^(\d{8})\s+资金股份查询\.(txt|xls)$')

    for filename in os.listdir(SNAPSHOT_DIR):
        match = pattern.match(filename)
        if match:
            date_str = match.group(1)
            try:
                snapshot_date = datetime.strptime(date_str, '%Y%m%d').date()
                filepath = os.path.join(SNAPSHOT_DIR, filename)
                snapshot_files.append((filepath, snapshot_date))
            except ValueError:
                continue

    if not snapshot_files:
        print(f"✗ 未找到有效的快照文件（格式: YYYYMMDD 资金股份查询.txt 或 .xls）")
        return None, None

    # 按日期排序，返回最新的
    snapshot_files.sort(key=lambda x: x[1], reverse=True)
    latest_file, latest_date = snapshot_files[0]

    print(f"✓ 找到最新快照文件: {os.path.basename(latest_file)} (日期: {latest_date})")
    return latest_file, latest_date


def read_snapshot_file(filepath):
    """
    读取资产快照文件（文本格式）

    参数:
        filepath: 快照文件路径

    返回:
        tuple: (资产信息dict, 持仓列表list)
    """
    try:
        print(f"正在读取快照文件: {filepath}")

        # 读取文本文件（使用GBK编码）
        with open(filepath, 'r', encoding='gbk', errors='ignore') as f:
            lines = f.readlines()

        print(f"✓ 文件读取成功，共 {len(lines)} 行")

        # 解析资产信息（第一行）
        # 格式：可用:2971.44  可取:6097269.58  获取:2971.44  余颖:6094299.69  证券市值:3350251.14  总资产:9552735.94  盈亏:-20201.52
        asset_info = {
            'snapshot_date': None,
            'total_assets': None,
            'cash_balance': None,
            'market_value': None,
            'total_position_count': 0,
            'profit_loss': None,
            'profit_loss_ratio': None
        }

        if lines and ':' in lines[0]:
            # 尝试解析第一行的资产信息
            first_line = lines[0]
            # 使用正则表达式提取数值
            import re
            # 查找"总资产:"后面的数值
            match = re.search(r'总资产[^\d]*([\d\.-]+)', first_line)
            if match:
                asset_info['total_assets'] = float(match.group(1))

            # 查找"证券市值:"后面的数值
            match = re.search(r'证券市值[^\d]*([\d\.-]+)', first_line)
            if match:
                asset_info['market_value'] = float(match.group(1))

            # 查找"盈亏:"后面的数值
            match = re.search(r'盈亏[^\d]*([\d\.-]+)', first_line)
            if match:
                asset_info['profit_loss'] = float(match.group(1))

        # 解析持仓信息（从第5行开始，跳过前4行的表头）
        positions = []
        data_started = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 跳过分隔线和表头
            if line.startswith('-') or '证券代码' in line:
                if '证券代码' in line:
                    data_started = True
                continue

            # 数据行开始后才开始解析
            if not data_started:
                continue

            # 按空白字符分割行
            parts = line.split()
            if len(parts) < 8:
                continue

            try:
                # 解析持仓数据
                # 格式：证券代码 证券名称  股东代码  可用数量  成本价    当前价    市值         盈亏           盈亏比例(%)
                # 示例：000858  五  粮  液   5500    5500     125.6651  107.34  590370.000  -100788.080  -14.58

                stock_code = parts[0].strip()

                # 跳过非股票代码行（如汇总行）
                if not stock_code or not stock_code[0].isdigit():
                    continue

                # 合并证券名称（可能包含空格）
                # 从parts[1]开始，直到遇到数字
                name_parts = []
                for i in range(1, len(parts)):
                    if parts[i].replace('.', '').replace('-', '').isdigit():
                        break
                    name_parts.append(parts[i])
                stock_name = ''.join(name_parts).strip()

                # 找到数值字段的起始位置
                numeric_start = 1 + len(name_parts)

                if numeric_start + 8 >= len(parts):
                    continue

                position_count = float(parts[numeric_start]) if numeric_start < len(parts) else 0
                available_count = float(parts[numeric_start + 1]) if numeric_start + 1 < len(parts) else 0
                cost_price = float(parts[numeric_start + 2]) if numeric_start + 2 < len(parts) else 0
                current_price = float(parts[numeric_start + 3]) if numeric_start + 3 < len(parts) else 0
                market_value = float(parts[numeric_start + 4]) if numeric_start + 4 < len(parts) else 0
                profit_loss = float(parts[numeric_start + 5]) if numeric_start + 5 < len(parts) else 0
                profit_loss_ratio = float(parts[numeric_start + 6]) if numeric_start + 6 < len(parts) else 0

                position = {
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'position_count': position_count,
                    'available_count': available_count,
                    'cost_price': cost_price,
                    'current_price': current_price,
                    'market_value': market_value,
                    'profit_loss': profit_loss,
                    'profit_loss_ratio': profit_loss_ratio / 100 if profit_loss_ratio != 0 else 0  # 转换为小数
                }
                positions.append(position)

            except (ValueError, IndexError) as e:
                # 跳过解析失败的行
                continue

        print(f"✓ 解析到 {len(positions)} 个持仓")

        # 打印前几个持仓用于调试
        if positions:
            print("  前3个持仓:")
            for i, pos in enumerate(positions[:3], 1):
                print(f"    {i}. {pos.get('stock_name', '')} ({pos.get('stock_code', '')}): "
                      f"{pos.get('position_count', 0):.2f}股 @ {pos.get('cost_price', 0):.2f}元")

        return asset_info, positions

    except Exception as e:
        print(f"✗ 读取快照文件失败: {e}")
        import traceback
        traceback.print_exc()
        return None, []


def get_operation_log_files(after_date=None):
    """
    获取操作对账单文件列表

    参数:
        after_date: 只获取此日期之后的文件（datetime.date对象）

    返回:
        list: [(文件路径, 对账单日期), ...]
    """
    if not os.path.exists(OPERATION_LOG_DIR):
        print(f"✗ 对账单目录不存在: {OPERATION_LOG_DIR}")
        return []

    # 查找所有对账单文件
    operation_files = []
    pattern = re.compile(r'^(\d{8})\s+对帐单查询\.(txt|xls)$')

    for filename in os.listdir(OPERATION_LOG_DIR):
        match = pattern.match(filename)
        if match:
            date_str = match.group(1)
            try:
                log_date = datetime.strptime(date_str, '%Y%m%d').date()
                # 如果指定了after_date，只返回之后的文件
                if after_date is None or log_date > after_date:
                    filepath = os.path.join(OPERATION_LOG_DIR, filename)
                    operation_files.append((filepath, log_date))
            except ValueError:
                continue

    # 按日期排序
    operation_files.sort(key=lambda x: x[0])

    print(f"✓ 找到 {len(operation_files)} 个对账单文件")
    for filepath, log_date in operation_files:
        print(f"  - {os.path.basename(filepath)} (日期: {log_date})")

    return operation_files


def read_operation_log_file(filepath):
    """
    读取操作对账单文件（文本格式）

    参数:
        filepath: 对账单文件路径

    返回:
        list: 操作记录列表 [{'operation_date', 'stock_code', 'operation_type', ...}, ...]
    """
    try:
        print(f"正在读取对账单文件: {filepath}")

        # 读取文本文件（使用GBK编码）
        with open(filepath, 'r', encoding='gbk', errors='ignore') as f:
            lines = f.readlines()

        print(f"✓ 文件读取成功，共 {len(lines)} 行")

        operations = []
        data_started = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 跳过分隔线和表头
            if line.startswith('-') or '操作日期' in line or '证券代码' in line:
                if '操作日期' in line or '证券代码' in line:
                    data_started = True
                continue

            # 数据行开始后才开始解析
            if not data_started:
                continue

            # 按空白字符分割行
            parts = line.split()
            if len(parts) < 5:
                continue

            try:
                # 解析操作记录
                # 格式：操作日期  业务名称    证券代码  证券名称  成交价格  成交数量  成交金额  方向  手续费  印花税  其他费用  发生金额  资金余额  委托编号  成交编号  委托价格  委托数量  股东代码  资金账户  备注
                # 示例：2025-12-05  证券买入  600941  中国移动  101.0000  1500  151500.00  买入  35.66  0.00  1.51  -151537.17  5415782.00  ...

                operation_date = parts[0].strip()

                # 跳过非日期行
                if not operation_date or len(operation_date) < 8:
                    continue

                # 判断是否为股票操作（第3列是证券代码）
                if len(parts) < 10:
                    continue

                # 证券名称可能包含空格，需要特殊处理
                # 找到证券代码的位置（第3列，索引2）
                if len(parts) < 8:
                    continue

                stock_code = parts[2].strip()

                # 跳过非股票操作（如国债回购、申购等）
                # 股票代码通常是6位数字
                if not stock_code or not stock_code[0].isdigit():
                    continue

                # 合并证券名称（可能包含空格）
                # 从parts[3]开始，直到遇到数值
                name_parts = []
                for i in range(3, len(parts)):
                    if parts[i].replace('.', '').replace('-', '').isdigit():
                        break
                    name_parts.append(parts[i])
                stock_name = ''.join(name_parts).strip()

                # 找到数值字段的起始位置
                numeric_start = 3 + len(name_parts)

                if numeric_start + 5 >= len(parts):
                    continue

                operation_price = float(parts[numeric_start]) if numeric_start < len(parts) else 0
                operation_count = float(parts[numeric_start + 1]) if numeric_start + 1 < len(parts) else 0
                operation_amount = float(parts[numeric_start + 2]) if numeric_start + 2 < len(parts) else 0
                operation_type = parts[numeric_start + 3] if numeric_start + 3 < len(parts) else ''
                commission = float(parts[numeric_start + 4]) if numeric_start + 4 < len(parts) else 0

                # 计算操作数量（买入为正，卖出为负）
                # 根据操作类型判断
                if '买入' in operation_type or '申购' in operation_type:
                    operation_count = abs(operation_count)
                elif '卖出' in operation_type or '赎回' in operation_type:
                    operation_count = -abs(operation_count)

                operation = {
                    'operation_date': operation_date,
                    'trade_time': None,
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'operation_type': operation_type,
                    'operation_count': operation_count,
                    'operation_price': operation_price,
                    'operation_amount': operation_amount,
                    'commission': commission,
                    'stamp_duty': 0,
                    'other_fees': 0,
                    'net_amount': 0,
                    'remark': ''
                }
                operations.append(operation)

            except (ValueError, IndexError) as e:
                # 跳过解析失败的行
                continue

        print(f"✓ 解析到 {len(operations)} 条操作记录")

        # 打印前几条操作用于调试
        if operations:
            print("  前3条操作:")
            for i, op in enumerate(operations[:3], 1):
                print(f"    {i}. {op.get('operation_date', '')} {op.get('stock_name', '')} "
                      f"{op.get('operation_type', '')} {op.get('operation_count', 0):.2f}股 "
                      f"@ {op.get('operation_price', 0):.2f}元")

        return operations

    except Exception as e:
        print(f"✗ 读取对账单文件失败: {e}")
        import traceback
        traceback.print_exc()
        return []


# ==================== 数据库操作模块 ====================

def save_snapshot_to_db(snapshot_date, asset_info, positions):
    """
    将快照数据保存到数据库

    参数:
        snapshot_date: 快照日期
        asset_info: 资产信息字典
        positions: 持仓列表
    """
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 1. 保存资产快照
        insert_asset_sql = """
        INSERT INTO asset_snapshot
            (snapshot_date, total_assets, cash_balance, market_value,
             total_position_count, profit_loss, profit_loss_ratio)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            total_assets = VALUES(total_assets),
            cash_balance = VALUES(cash_balance),
            market_value = VALUES(market_value),
            total_position_count = VALUES(total_position_count),
            profit_loss = VALUES(profit_loss),
            profit_loss_ratio = VALUES(profit_loss_ratio)
        """

        cursor.execute(insert_asset_sql, (
            snapshot_date,
            asset_info.get('total_assets'),
            asset_info.get('cash_balance'),
            asset_info.get('market_value'),
            asset_info.get('total_position_count', len(positions)),
            asset_info.get('profit_loss'),
            asset_info.get('profit_loss_ratio')
        ))

        # 2. 保存持仓快照
        insert_position_sql = """
        INSERT INTO position_snapshot
            (snapshot_date, stock_code, stock_name, position_count, available_count,
             cost_price, current_price, market_value, profit_loss, profit_loss_ratio)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            position_count = VALUES(position_count),
            available_count = VALUES(available_count),
            cost_price = VALUES(cost_price),
            current_price = VALUES(current_price),
            market_value = VALUES(market_value),
            profit_loss = VALUES(profit_loss),
            profit_loss_ratio = VALUES(profit_loss_ratio)
        """

        for pos in positions:
            cursor.execute(insert_position_sql, (
                snapshot_date,
                pos.get('stock_code'),
                pos.get('stock_name'),
                pos.get('position_count'),
                pos.get('available_count'),
                pos.get('cost_price'),
                pos.get('current_price'),
                pos.get('market_value'),
                pos.get('profit_loss'),
                pos.get('profit_loss_ratio')
            ))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✓ 快照数据已保存到数据库 (日期: {snapshot_date})")
        return True

    except Exception as e:
        print(f"✗ 保存快照数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_operations_to_db(operations):
    """
    将操作记录保存到数据库

    参数:
        operations: 操作记录列表
    """
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        insert_sql = """
        INSERT INTO stock_operation_log
            (operation_date, trade_time, stock_code, stock_name, operation_type,
             operation_count, operation_price, operation_amount, commission,
             stamp_duty, other_fees, net_amount, remark)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        count = 0
        for op in operations:
            try:
                cursor.execute(insert_sql, (
                    op.get('operation_date'),
                    op.get('trade_time'),
                    op.get('stock_code'),
                    op.get('stock_name'),
                    op.get('operation_type'),
                    op.get('operation_count'),
                    op.get('operation_price'),
                    op.get('operation_amount'),
                    op.get('commission'),
                    op.get('stamp_duty'),
                    op.get('other_fees'),
                    op.get('net_amount'),
                    op.get('remark')
                ))
                count += 1
            except Exception as e:
                print(f"  ⚠ 插入操作记录失败: {op.get('stock_code')} - {e}")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✓ 已保存 {count} 条操作记录到数据库")
        return count

    except Exception as e:
        print(f"✗ 保存操作记录失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


def get_latest_snapshot_from_db():
    """
    从数据库获取最新的资产快照和持仓

    返回:
        tuple: (snapshot_date, asset_info, positions)
    """
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 获取最新快照日期
        cursor.execute("SELECT MAX(snapshot_date) as max_date FROM asset_snapshot")
        result = cursor.fetchone()
        snapshot_date = result['max_date'] if result and result['max_date'] else None

        if not snapshot_date:
            cursor.close()
            conn.close()
            return None, None, []

        # 获取资产信息
        cursor.execute("""
            SELECT * FROM asset_snapshot
            WHERE snapshot_date = %s
        """, (snapshot_date,))
        asset_info = cursor.fetchone()

        # 获取持仓信息
        cursor.execute("""
            SELECT * FROM position_snapshot
            WHERE snapshot_date = %s
            ORDER BY market_value DESC
        """, (snapshot_date,))
        positions = cursor.fetchall()

        cursor.close()
        conn.close()

        print(f"✓ 从数据库读取快照数据 (日期: {snapshot_date})")
        return snapshot_date, asset_info, positions

    except Exception as e:
        print(f"✗ 从数据库读取快照失败: {e}")
        return None, None, []


def get_operations_after_date(after_date):
    """
    从数据库获取指定日期之后的操作记录

    参数:
        after_date: 起始日期

    返回:
        list: 操作记录列表
    """
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("""
            SELECT * FROM stock_operation_log
            WHERE operation_date > %s
            ORDER BY operation_date ASC, trade_time ASC
        """, (after_date,))

        operations = cursor.fetchall()

        cursor.close()
        conn.close()

        print(f"✓ 从数据库读取 {len(operations)} 条操作记录 (日期: {after_date} 之后)")
        return operations

    except Exception as e:
        print(f"✗ 从数据库读取操作记录失败: {e}")
        return []


# ==================== 持仓计算模块 ====================

def calculate_current_position(snapshot_date, snapshot_positions, operations):
    """
    根据快照和操作记录计算当前持仓

    参数:
        snapshot_date: 快照日期
        snapshot_positions: 快照时的持仓列表
        operations: 快照之后的操作记录列表

    返回:
        tuple: (current_positions, summary)
            current_positions: 当前持仓列表
            summary: 汇总信息 {'total_market_value', 'total_profit_loss', ...}
    """
    print(f"\n{'='*60}")
    print(f"【持仓计算】基于快照日期 {snapshot_date} 和后续操作记录")
    print(f"{'='*60}")

    # 初始化持仓字典（以股票代码为key）
    position_map = {}

    # 1. 从快照初始化持仓
    for pos in snapshot_positions:
        stock_code = pos['stock_code']
        position_map[stock_code] = {
            'stock_code': stock_code,
            'stock_name': pos.get('stock_name', ''),
            'current_count': pos.get('position_count', 0),
            'available_count': pos.get('available_count', 0),
            'avg_cost_price': pos.get('cost_price', 0),
            'last_price': pos.get('current_price', 0),
            'cost_value': pos.get('position_count', 0) * pos.get('cost_price', 0),
            'market_value': pos.get('market_value', 0),
            'profit_loss': pos.get('profit_loss', 0),
            'profit_loss_ratio': pos.get('profit_loss_ratio', 0)
        }

    print(f"✓ 从快照初始化 {len(position_map)} 个持仓")

    # 2. 应用操作记录
    buy_count = 0
    sell_count = 0
    total_buy_amount = 0
    total_sell_amount = 0

    for op in operations:
        stock_code = op.get('stock_code')
        op_type = op.get('operation_type', '')
        op_count = op.get('operation_count', 0)
        op_price = op.get('operation_price', 0)

        # 初始化持仓（如果之前没有）
        if stock_code not in position_map:
            position_map[stock_code] = {
                'stock_code': stock_code,
                'stock_name': op.get('stock_name', ''),
                'current_count': 0,
                'available_count': 0,
                'avg_cost_price': 0,
                'last_price': 0,
                'cost_value': 0,
                'market_value': 0,
                'profit_loss': 0,
                'profit_loss_ratio': 0
            }

        position = position_map[stock_code]

        # 根据操作类型更新持仓
        if '买入' in op_type or op_count > 0:
            # 买入操作
            buy_count += 1
            buy_amount = abs(op_count) * op_price
            total_buy_amount += buy_amount

            # 更新持仓数量和成本价（加权平均）
            old_count = position['current_count']
            old_cost_value = position['cost_value']
            new_count = old_count + abs(op_count)

            if new_count > 0:
                position['avg_cost_price'] = (old_cost_value + buy_amount) / new_count
                position['current_count'] = new_count
                position['available_count'] += abs(op_count)
                position['cost_value'] = old_cost_value + buy_amount
            else:
                position['avg_cost_price'] = op_price
                position['current_count'] = abs(op_count)
                position['available_count'] = abs(op_count)
                position['cost_value'] = buy_amount

            print(f"  买入: {stock_code} {abs(op_count):.2f}股 @ {op_price:.2f}元")

        elif '卖出' in op_type or op_count < 0:
            # 卖出操作
            sell_count += 1
            sell_amount = abs(op_count) * op_price
            total_sell_amount += sell_amount

            # 更新持仓数量
            old_count = position['current_count']
            new_count = old_count - abs(op_count)

            if new_count > 0:
                # 按比例更新成本
                position['cost_value'] = position['cost_value'] * (new_count / old_count)
                position['current_count'] = new_count
                position['available_count'] -= abs(op_count)
            else:
                # 全部卖出
                realized_profit = sell_amount - position['cost_value'] * (abs(op_count) / old_count)
                position['cost_value'] = 0
                position['current_count'] = 0
                position['available_count'] = 0

            print(f"  卖出: {stock_code} {abs(op_count):.2f}股 @ {op_price:.2f}元")

        # 更新最新价格
        if op_price > 0:
            position['last_price'] = op_price

        # 重新计算市值和盈亏
        if position['current_count'] > 0:
            position['market_value'] = position['current_count'] * position['last_price']
            position['profit_loss'] = position['market_value'] - position['cost_value']
            if position['cost_value'] > 0:
                position['profit_loss_ratio'] = position['profit_loss'] / position['cost_value']

    # 3. 移除零持仓
    current_positions = [pos for pos in position_map.values() if pos['current_count'] > 0]

    # 4. 生成汇总信息
    total_market_value = sum(pos['market_value'] for pos in current_positions)
    total_cost_value = sum(pos['cost_value'] for pos in current_positions)
    total_profit_loss = sum(pos['profit_loss'] for pos in current_positions)

    summary = {
        'calculation_date': datetime.now().date(),
        'snapshot_date': snapshot_date,
        'total_positions': len(current_positions),
        'buy_count': buy_count,
        'sell_count': sell_count,
        'total_buy_amount': total_buy_amount,
        'total_sell_amount': total_sell_amount,
        'total_market_value': total_market_value,
        'total_cost_value': total_cost_value,
        'total_profit_loss': total_profit_loss,
        'total_profit_loss_ratio': total_profit_loss / total_cost_value if total_cost_value > 0 else 0
    }

    print(f"\n{'='*60}")
    print(f"【计算完成】")
    print(f"  当前持仓数: {summary['total_positions']}")
    print(f"  买入次数: {summary['buy_count']}, 买入金额: {summary['total_buy_amount']:.2f}")
    print(f"  卖出次数: {summary['sell_count']}, 卖出金额: {summary['total_sell_amount']:.2f}")
    print(f"  总市值: {summary['total_market_value']:.2f}")
    print(f"  总成本: {summary['total_cost_value']:.2f}")
    print(f"  总盈亏: {summary['total_profit_loss']:.2f} ({summary['total_profit_loss_ratio']*100:.2f}%)")
    print(f"{'='*60}\n")

    return current_positions, summary


def save_current_position_to_db(calculation_date, current_positions, summary):
    """
    将计算结果保存到数据库

    参数:
        calculation_date: 计算日期
        current_positions: 当前持仓列表
        summary: 汇总信息
    """
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 先删除该日期的旧数据
        cursor.execute("DELETE FROM current_position WHERE calculation_date = %s", (calculation_date,))

        # 插入新数据
        insert_sql = """
        INSERT INTO current_position
            (calculation_date, stock_code, stock_name, current_count, available_count,
             avg_cost_price, last_price, market_value, cost_value, profit_loss, profit_loss_ratio)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        for pos in current_positions:
            cursor.execute(insert_sql, (
                calculation_date,
                pos.get('stock_code'),
                pos.get('stock_name'),
                pos.get('current_count'),
                pos.get('available_count'),
                pos.get('avg_cost_price'),
                pos.get('last_price'),
                pos.get('market_value'),
                pos.get('cost_value'),
                pos.get('profit_loss'),
                pos.get('profit_loss_ratio')
            ))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✓ 当前持仓已保存到数据库 (日期: {calculation_date})")
        return True

    except Exception as e:
        print(f"✗ 保存当前持仓失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_current_positions(current_positions, summary):
    """
    打印当前持仓报告

    参数:
        current_positions: 当前持仓列表
        summary: 汇总信息
    """
    print(f"\n{'='*80}")
    print(f"当前持仓报告")
    print(f"{'='*80}")
    print(f"计算日期: {summary['calculation_date']}")
    print(f"基准快照: {summary['snapshot_date']}")
    print(f"{'='*80}\n")

    print(f"【汇总信息】")
    print(f"  持仓数量: {summary['total_positions']}")
    print(f"  买入次数: {summary['buy_count']}, 买入金额: ¥{summary['total_buy_amount']:,.2f}")
    print(f"  卖出次数: {summary['sell_count']}, 卖出金额: ¥{summary['total_sell_amount']:,.2f}")
    print(f"  总市值: ¥{summary['total_market_value']:,.2f}")
    print(f"  总成本: ¥{summary['total_cost_value']:,.2f}")
    print(f"  总盈亏: ¥{summary['total_profit_loss']:,.2f} ({summary['total_profit_loss_ratio']*100:.2f}%)")

    print(f"\n【持仓明细】")
    print(f"{'序号':<4} {'代码':<12} {'名称':<10} {'持仓':>10} {'可用':>10} {'成本价':>8} {'现价':>8} {'市值':>12} {'成本':>12} {'盈亏':>12} {'盈亏率':>8}")
    print(f"{'-'*80}")

    for i, pos in enumerate(current_positions, 1):
        profit_loss_ratio_pct = pos['profit_loss_ratio'] * 100
        print(f"{i:<4} {pos['stock_code']:<12} {pos['stock_name']:<10} "
              f"{pos['current_count']:>10.2f} {pos['available_count']:>10.2f} "
              f"{pos['avg_cost_price']:>8.2f} {pos['last_price']:>8.2f} "
              f"¥{pos['market_value']:>11,.2f} ¥{pos['cost_value']:>11,.2f} "
              f"¥{pos['profit_loss']:>11,.2f} {profit_loss_ratio_pct:>7.2f}%")

    print(f"{'='*80}\n")


# ==================== 主程序入口 ====================

def main():
    """主程序"""
    print(f"\n{'#'*80}")
    print(f"# 仓位管理系统")
    print(f"# 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}\n")

    # 1. 创建数据库表
    print("【步骤1】创建数据库表...")
    create_position_tables()

    # 2. 读取最新快照（比较文件和数据库，选择更新的）
    print("\n【步骤2】读取最新资产快照...")
    latest_snapshot_file, file_snapshot_date = get_latest_snapshot_file()
    db_snapshot_date, db_asset_info, db_snapshot_positions = get_latest_snapshot_from_db()

    # 决定使用哪个快照作为基准
    use_file_snapshot = False
    use_db_snapshot = False

    if latest_snapshot_file and db_snapshot_date:
        # 两个都有，比较日期
        print(f"\n📅 快照日期比较:")
        print(f"  - 文件快照日期: {file_snapshot_date}")
        print(f"  - 数据库快照日期: {db_snapshot_date}")

        if file_snapshot_date > db_snapshot_date:
            print(f"  ✓ 使用文件快照（更新）")
            use_file_snapshot = True
        elif file_snapshot_date < db_snapshot_date:
            print(f"  ✓ 使用数据库快照（更新）")
            use_db_snapshot = True
        else:
            # 日期相同，优先使用数据库（因为可能已包含更多信息）
            print(f"  ✓ 日期相同，使用数据库快照")
            use_db_snapshot = True

    elif latest_snapshot_file:
        # 只有文件
        print(f"📅 仅找到文件快照: {file_snapshot_date}")
        use_file_snapshot = True

    elif db_snapshot_date:
        # 只有数据库
        print(f"📅 仅找到数据库快照: {db_snapshot_date}")
        use_db_snapshot = True
    else:
        # 都没有
        print("✗ 未找到任何快照数据，程序退出")
        return

    # 根据决策读取数据
    if use_file_snapshot:
        snapshot_date = file_snapshot_date
        print(f"\n正在读取文件快照: {latest_snapshot_file}")
        asset_info, snapshot_positions = read_snapshot_file(latest_snapshot_file)

        # 保存到数据库（如果成功读取）
        if snapshot_positions:
            save_snapshot_to_db(snapshot_date, asset_info, snapshot_positions)

    elif use_db_snapshot:
        snapshot_date = db_snapshot_date
        asset_info = db_asset_info
        snapshot_positions = db_snapshot_positions
        print(f"\n使用数据库快照: {snapshot_date}")
        print(f"  持仓数量: {len(snapshot_positions)}")

    # 3. 读取操作对账单（快照日期之后的）
    print("\n【步骤3】读取操作对账单...")
    operation_files = get_operation_log_files(after_date=snapshot_date)

    all_operations = []
    for op_file, _ in operation_files:
        operations = read_operation_log_file(op_file)
        if operations:
            all_operations.extend(operations)
            # 保存到数据库
            save_operations_to_db(operations)

    # 如果没有新文件，从数据库读取
    if not operation_files:
        print("未找到新的对账单文件，从数据库读取操作记录...")
        all_operations = get_operations_after_date(snapshot_date)

    # 4. 计算当前持仓
    print("\n【步骤4】计算当前持仓...")
    current_positions, summary = calculate_current_position(
        snapshot_date, snapshot_positions, all_operations
    )

    # 5. 保存计算结果
    print("\n【步骤5】保存计算结果...")
    calculation_date = datetime.now().date()
    save_current_position_to_db(calculation_date, current_positions, summary)

    # 6. 打印报告
    print("\n【步骤6】生成报告...")
    print_current_positions(current_positions, summary)

    print(f"{'#'*80}")
    print(f"# 仓位管理完成")
    print(f"{'#'*80}\n")

    return current_positions, summary


if __name__ == '__main__':
    main()
