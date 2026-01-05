"""
仓位管理系统 - 纯Python演示版本
不依赖任何外部库，仅使用Python标准库
用于演示系统功能和计算逻辑
"""

from datetime import datetime, date


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

    # 打印初始持仓
    print("Initial positions from snapshot:")
    for stock_code, pos in position_map.items():
        print(f"  {pos['stock_name']} ({stock_code}): {pos['current_count']:.2f} shares @ {pos['avg_cost_price']:.2f}")
    print()

    # 2. 应用操作记录
    buy_count = 0
    sell_count = 0
    total_buy_amount = 0.0
    total_sell_amount = 0.0

    for i, op in enumerate(operations, 1):
        stock_code = op.get('stock_code')
        op_type = op.get('operation_type', '')
        op_count = float(op.get('operation_count', 0))
        op_price = float(op.get('operation_price', 0))
        op_date = op.get('operation_date', '')

        print(f"[{i}] {op_date} - {op_type}")

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

            print(f"    BUY  {position['stock_name']} ({stock_code}) {abs_count:.2f} shares @ {op_price:.2f} = {buy_amount:.2f}")
            print(f"         New position: {position['current_count']:.2f} shares @ {position['avg_cost_price']:.2f}")

        elif 'sell' in op_type.lower() or '卖出' in op_type or op_count < 0:
            # 卖出操作
            sell_count += 1
            abs_count = abs(op_count)
            sell_amount = abs_count * op_price
            total_sell_amount += sell_amount

            # 更新持仓数量
            old_count = position['current_count']
            new_count = old_count - abs_count

            # 计算卖出成本（按比例）
            sold_cost = position['cost_value'] * (abs_count / old_count) if old_count > 0 else 0
            realized_profit = sell_amount - sold_cost

            if new_count > 0:
                # 按比例更新成本
                position['cost_value'] = position['cost_value'] * (new_count / old_count)
                position['current_count'] = new_count
                position['available_count'] -= abs_count
                print(f"    SELL {position['stock_name']} ({stock_code}) {abs_count:.2f} shares @ {op_price:.2f} = {sell_amount:.2f}")
                print(f"         Sold cost: {sold_cost:.2f}, Realized profit: {realized_profit:.2f}")
                print(f"         Remaining: {position['current_count']:.2f} shares @ {position['avg_cost_price']:.2f}")
            else:
                # 全部卖出
                position['cost_value'] = 0.0
                position['current_count'] = 0.0
                position['available_count'] = 0.0
                print(f"    SELL {position['stock_name']} ({stock_code}) {abs_count:.2f} shares @ {op_price:.2f} = {sell_amount:.2f}")
                print(f"         Sold cost: {sold_cost:.2f}, Realized profit: {realized_profit:.2f}")
                print(f"         Position closed")

        # 更新最新价格
        if op_price > 0:
            position['last_price'] = op_price

        # 重新计算市值和盈亏
        if position['current_count'] > 0:
            position['market_value'] = position['current_count'] * position['last_price']
            position['profit_loss'] = position['market_value'] - position['cost_value']
            if position['cost_value'] > 0:
                position['profit_loss_ratio'] = position['profit_loss'] / position['cost_value']

        print()

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
    print(f"{'-'*100}")

    for i, pos in enumerate(current_positions, 1):
        profit_loss_ratio_pct = pos['profit_loss_ratio'] * 100
        print(f"{i:<4} {pos['stock_code']:<14} {pos['stock_name']:<12} "
              f"{pos['current_count']:>10.2f} {pos['available_count']:>10.2f} "
              f"{pos['avg_cost_price']:>8.2f} {pos['last_price']:>8.2f} "
              f"{pos['market_value']:>12,.2f} {pos['cost_value']:>12,.2f} "
              f"{pos['profit_loss']:>12,.2f} {profit_loss_ratio_pct:>7.2f}%")

    print(f"{'='*100}\n")


def demo():
    """演示版本 - 使用示例数据"""
    print(f"\n{'#'*80}")
    print(f"# Position Management System - Pure Python Demo")
    print(f"# Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}\n")

    print("This demo shows how the position management system works.")
    print("It uses sample data to demonstrate the calculation logic.\n")

    # 示例快照数据（2025-11-30）
    snapshot_date = '2025-11-30'

    snapshot_positions = [
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

    # 示例操作记录（2025-11-30之后的操作）
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

    print(f"Sample data:")
    print(f"  Snapshot date: {snapshot_date}")
    print(f"  Snapshot positions: {len(snapshot_positions)}")
    print(f"  Operations: {len(operations)}")
    print(f"\nStarting calculation...\n")

    # 计算当前持仓
    current_positions, summary = calculate_current_position(
        snapshot_date, snapshot_positions, operations
    )

    # 打印报告
    print_current_positions(current_positions, summary)

    print(f"{'#'*80}")
    print(f"# Position Management Demo Completed")
    print(f"{'#'*80}\n")

    print("Key concepts demonstrated:")
    print("1. Starting from a snapshot position")
    print("2. Applying buy/sell operations")
    print("3. Calculating weighted average cost price")
    print("4. Tracking realized and unrealized profits")
    print("5. Generating summary reports\n")


if __name__ == '__main__':
    demo()
