"""
仓位管理系统 - 独立演示版本
不依赖pandas和其他复杂库，仅使用Python标准库
"""

import pymysql
from datetime import datetime, date
from decimal import Decimal

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stockDBA',
    'password': 'stockDBA25001',
    'database': 'StockAnalysisDataStore',
    'charset': 'utf8mb4'
}


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

        print("OK - Database tables created successfully")
        return True

    except Exception as e:
        print(f"ERROR - Failed to create tables: {e}")
        return False


def get_latest_snapshot_from_db():
    """
    从数据库获取最新的资产快照日期和持仓

    返回:
        tuple: (snapshot_date, asset_info, positions)
            snapshot_date: date object or None
            asset_info: dict or None
            positions: list of dicts
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

        print(f"OK - Loaded snapshot from database (date: {snapshot_date})")
        return snapshot_date, asset_info, positions

    except Exception as e:
        print(f"ERROR - Failed to load snapshot from database: {e}")
        return None, None, []


def save_snapshot_to_db(snapshot_date, asset_info, positions):
    """将快照数据保存到数据库"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 保存持仓快照
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

        print(f"OK - Snapshot saved to database (date: {snapshot_date})")
        return True

    except Exception as e:
        print(f"ERROR - Failed to save snapshot: {e}")
        return False


def calculate_current_position(snapshot_date_str, snapshot_positions, operations):
    """
    根据快照和操作记录计算当前持仓

    参数:
        snapshot_date_str: 快照日期字符串 (YYYY-MM-DD)
        snapshot_positions: 快照时的持仓列表
        operations: 快照之后的操作记录列表

    返回:
        tuple: (current_positions, summary)
    """
    print(f"\n{'='*80}")
    print(f"Calculating positions based on snapshot {snapshot_date_str}")
    print(f"and {len(operations)} subsequent operations")
    print(f"{'='*80}\n")

    # 初始化持仓字典
    position_map = {}

    # 1. 从快照初始化持仓
    for pos in snapshot_positions:
        stock_code = pos['stock_code']
        position_map[stock_code] = {
            'stock_code': stock_code,
            'stock_name': pos.get('stock_name', ''),
            'current_count': float(pos.get('position_count', 0)),
            'available_count': float(pos.get('available_count', 0)),
            'avg_cost_price': float(pos.get('cost_price', 0)),
            'last_price': float(pos.get('current_price', 0)),
            'cost_value': float(pos.get('position_count', 0)) * float(pos.get('cost_price', 0)),
            'market_value': float(pos.get('market_value', 0)),
            'profit_loss': float(pos.get('profit_loss', 0)),
            'profit_loss_ratio': float(pos.get('profit_loss_ratio', 0))
        }

    print(f"Initialized {len(position_map)} positions from snapshot\n")

    # 2. 应用操作记录
    buy_count = 0
    sell_count = 0
    total_buy_amount = 0.0
    total_sell_amount = 0.0

    for op in operations:
        stock_code = op.get('stock_code')
        op_type = op.get('operation_type', '')
        op_count = float(op.get('operation_count', 0))
        op_price = float(op.get('operation_price', 0))

        # 初始化持仓（如果之前没有）
        if stock_code not in position_map:
            position_map[stock_code] = {
                'stock_code': stock_code,
                'stock_name': op.get('stock_name', ''),
                'current_count': 0.0,
                'available_count': 0.0,
                'avg_cost_price': 0.0,
                'last_price': 0.0,
                'cost_value': 0.0,
                'market_value': 0.0,
                'profit_loss': 0.0,
                'profit_loss_ratio': 0.0
            }

        position = position_map[stock_code]

        # 根据操作类型更新持仓
        if 'buy' in op_type.lower() or '买入' in op_type or op_count > 0:
            # 买入操作
            buy_count += 1
            abs_count = abs(op_count)
            buy_amount = abs_count * op_price
            total_buy_amount += buy_amount

            # 更新持仓数量和成本价（加权平均）
            old_count = position['current_count']
            old_cost_value = position['cost_value']
            new_count = old_count + abs_count

            if new_count > 0:
                position['avg_cost_price'] = (old_cost_value + buy_amount) / new_count
                position['current_count'] = new_count
                position['available_count'] += abs_count
                position['cost_value'] = old_cost_value + buy_amount
            else:
                position['avg_cost_price'] = op_price
                position['current_count'] = abs_count
                position['available_count'] = abs_count
                position['cost_value'] = buy_amount

            print(f"BUY  {stock_code} {abs_count:.2f} shares @ {op_price:.2f} = {buy_amount:.2f}")

        elif 'sell' in op_type.lower() or '卖出' in op_type or op_count < 0:
            # 卖出操作
            sell_count += 1
            abs_count = abs(op_count)
            sell_amount = abs_count * op_price
            total_sell_amount += sell_amount

            # 更新持仓数量
            old_count = position['current_count']
            new_count = old_count - abs_count

            if new_count > 0:
                # 按比例更新成本
                position['cost_value'] = position['cost_value'] * (new_count / old_count)
                position['current_count'] = new_count
                position['available_count'] -= abs_count
            else:
                # 全部卖出
                position['cost_value'] = 0.0
                position['current_count'] = 0.0
                position['available_count'] = 0.0

            print(f"SELL {stock_code} {abs_count:.2f} shares @ {op_price:.2f} = {sell_amount:.2f}")

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
        'calculation_date': date.today(),
        'snapshot_date': snapshot_date_str,
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

    print(f"\n{'='*80}")
    print(f"Calculation completed:")
    print(f"  Current positions: {summary['total_positions']}")
    print(f"  Buy trades: {summary['buy_count']}, Buy amount: {summary['total_buy_amount']:.2f}")
    print(f"  Sell trades: {summary['sell_count']}, Sell amount: {summary['total_sell_amount']:.2f}")
    print(f"  Total market value: {summary['total_market_value']:.2f}")
    print(f"  Total cost: {summary['total_cost_value']:.2f}")
    print(f"  Total P&L: {summary['total_profit_loss']:.2f} ({summary['total_profit_loss_ratio']*100:.2f}%)")
    print(f"{'='*80}\n")

    return current_positions, summary


def save_current_position_to_db(calculation_date, current_positions, summary):
    """将计算结果保存到数据库"""
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

        print(f"OK - Saved current positions to database (date: {calculation_date})")
        return True

    except Exception as e:
        print(f"ERROR - Failed to save current positions: {e}")
        return False


def print_current_positions(current_positions, summary):
    """打印当前持仓报告"""
    print(f"\n{'='*80}")
    print(f"CURRENT POSITION REPORT")
    print(f"{'='*80}")
    print(f"Calculation date: {summary['calculation_date']}")
    print(f"Base snapshot: {summary['snapshot_date']}")
    print(f"{'='*80}\n")

    print(f"[Summary]")
    print(f"  Positions: {summary['total_positions']}")
    print(f"  Buy trades: {summary['buy_count']}, Buy amount: {summary['total_buy_amount']:,.2f}")
    print(f"  Sell trades: {summary['sell_count']}, Sell amount: {summary['total_sell_amount']:,.2f}")
    print(f"  Total market value: {summary['total_market_value']:,.2f}")
    print(f"  Total cost: {summary['total_cost_value']:,.2f}")
    print(f"  Total P&L: {summary['total_profit_loss']:,.2f} ({summary['total_profit_loss_ratio']*100:.2f}%)")

    print(f"\n[Position Details]")
    print(f"{'No':<4} {'Code':<14} {'Name':<12} {'Shares':>10} {'Avail':>10} {'Cost':>8} {'Price':>8} {'Market':>12} {'CostVal':>12} {'P&L':>12} {'P&L%':>8}")
    print(f"{'-'*80}")

    for i, pos in enumerate(current_positions, 1):
        profit_loss_ratio_pct = pos['profit_loss_ratio'] * 100
        print(f"{i:<4} {pos['stock_code']:<14} {pos['stock_name']:<12} "
              f"{pos['current_count']:>10.2f} {pos['available_count']:>10.2f} "
              f"{pos['avg_cost_price']:>8.2f} {pos['last_price']:>8.2f} "
              f"{pos['market_value']:>12,.2f} {pos['cost_value']:>12,.2f} "
              f"{pos['profit_loss']:>12,.2f} {profit_loss_ratio_pct:>7.2f}%")

    print(f"{'='*80}\n")


def demo():
    """演示版本 - 使用示例数据"""
    print(f"\n{'#'*80}")
    print(f"# Position Management System - Demo Mode")
    print(f"# Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}\n")

    # 1. 创建数据库表
    print("[Step 1] Creating database tables...")
    create_position_tables()

    # 2. 尝试从数据库获取快照，如果没有则使用示例数据
    print("\n[Step 2] Loading snapshot...")
    db_snapshot_date, db_asset_info, db_snapshot_positions = get_latest_snapshot_from_db()

    # 示例快照数据
    demo_snapshot_date = datetime.strptime('2025-11-30', '%Y-%m-%d').date()
    demo_snapshot_positions = [
        {
            'stock_code': '600036.XSHG',
            'stock_name': '招商银行',
            'position_count': 1000,
            'available_count': 1000,
            'cost_price': 35.50,
            'current_price': 36.20,
            'market_value': 36200,
            'profit_loss': 700,
            'profit_loss_ratio': 0.0197
        },
        {
            'stock_code': '600519.XSHG',
            'stock_name': '贵州茅台',
            'position_count': 100,
            'available_count': 100,
            'cost_price': 1850.00,
            'current_price': 1920.00,
            'market_value': 192000,
            'profit_loss': 7000,
            'profit_loss_ratio': 0.0378
        },
        {
            'stock_code': '000333.XSHE',
            'stock_name': '美的集团',
            'position_count': 500,
            'available_count': 500,
            'cost_price': 68.00,
            'current_price': 72.50,
            'market_value': 36250,
            'profit_loss': 2250,
            'profit_loss_ratio': 0.0662
        }
    ]

    # 比较数据库快照和演示快照的日期，选择更新的
    if db_snapshot_date and db_snapshot_positions:
        print(f"\n[Snapshot Comparison]")
        print(f"  Database snapshot date: {db_snapshot_date}")
        print(f"  Demo snapshot date: {demo_snapshot_date}")

        if db_snapshot_date > demo_snapshot_date:
            print(f"  -> Using database snapshot (newer)")
            snapshot_date = db_snapshot_date
            snapshot_positions = db_snapshot_positions
        elif db_snapshot_date < demo_snapshot_date:
            print(f"  -> Using demo snapshot (newer)")
            snapshot_date = demo_snapshot_date
            snapshot_positions = demo_snapshot_positions
            # 保存演示快照到数据库
            save_snapshot_to_db(demo_snapshot_date, {}, demo_snapshot_positions)
        else:
            print(f"  -> Same date, using database snapshot")
            snapshot_date = db_snapshot_date
            snapshot_positions = db_snapshot_positions
    else:
        # 没有数据库快照，使用演示数据
        print(f"\n[Using demo data - no database snapshot found]")
        snapshot_date = demo_snapshot_date
        snapshot_positions = demo_snapshot_positions
        # 保存演示快照到数据库
        save_snapshot_to_db(demo_snapshot_date, {}, demo_snapshot_positions)

    print(f"  Final snapshot date: {snapshot_date}")
    print(f"  Snapshot positions: {len(snapshot_positions)}")

    # 3. 示例操作记录（2025-11-30之后的操作）
    operations = [
        {
            'operation_date': '2025-12-05',
            'stock_code': '600036.XSHG',
            'stock_name': '招商银行',
            'operation_type': '买入',
            'operation_count': 200,
            'operation_price': 36.50,
            'operation_amount': 7300
        },
        {
            'operation_date': '2025-12-10',
            'stock_code': '600519.XSHG',
            'stock_name': '贵州茅台',
            'operation_type': '卖出',
            'operation_count': -50,
            'operation_price': 1950.00,
            'operation_amount': 97500
        },
        {
            'operation_date': '2025-12-15',
            'stock_code': '000858.XSHE',
            'stock_name': '五粮液',
            'operation_type': '买入',
            'operation_count': 300,
            'operation_price': 165.00,
            'operation_amount': 49500
        },
        {
            'operation_date': '2025-12-20',
            'stock_code': '600036.XSHG',
            'stock_name': '招商银行',
            'operation_type': '卖出',
            'operation_count': -100,
            'operation_price': 37.80,
            'operation_amount': 3780
        }
    ]

    print(f"  Demo operations: {len(operations)}")

    # 4. 计算当前持仓
    print(f"\n[Step 3] Calculating current positions...")
    current_positions, summary = calculate_current_position(
        str(snapshot_date), snapshot_positions, operations
    )

    # 5. 保存计算结果
    print(f"\n[Step 4] Saving results...")
    calculation_date = date.today()
    save_current_position_to_db(calculation_date, current_positions, summary)

    # 6. 打印报告
    print(f"\n[Step 5] Generating report...")
    print_current_positions(current_positions, summary)

    print(f"{'#'*80}")
    print(f"# Position Management Completed")
    print(f"{'#'*80}\n")

    return current_positions, summary


if __name__ == '__main__':
    demo()
