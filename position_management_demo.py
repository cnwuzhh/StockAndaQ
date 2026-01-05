"""
仓位管理系统 - 演示版
用于在没有Excel文件的情况下演示系统功能
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def demo_with_sample_data():
    """使用示例数据演示仓位管理功能"""

    print("\n" + "="*80)
    print("仓位管理系统 - 演示模式")
    print("="*80)
    print("\n由于无法读取Excel文件，使用示例数据演示系统功能...")

    # 1. 示例快照数据（2025-11-30）
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

    # 2. 示例操作记录（2025-11-30之后的操作）
    operations = [
        {
            'operation_date': '2025-12-05',
            'stock_code': '600036.XSHG',
            'stock_name': '招商银行',
            'operation_type': '买入',
            'operation_count': 200,
            'operation_price': 36.50,
            'operation_amount': 7300,
            'commission': 5.0,
            'stamp_duty': 0,
            'net_amount': 7305
        },
        {
            'operation_date': '2025-12-10',
            'stock_code': '600519.XSHG',
            'stock_name': '贵州茅台',
            'operation_type': '卖出',
            'operation_count': -50,
            'operation_price': 1950.00,
            'operation_amount': 97500,
            'commission': 5.0,
            'stamp_duty': 97.5,
            'net_amount': 97397.5
        },
        {
            'operation_date': '2025-12-15',
            'stock_code': '000858.XSHE',
            'stock_name': '五粮液',
            'operation_type': '买入',
            'operation_count': 300,
            'operation_price': 165.00,
            'operation_amount': 49500,
            'commission': 5.0,
            'stamp_duty': 0,
            'net_amount': 49505
        },
        {
            'operation_date': '2025-12-20',
            'stock_code': '600036.XSHG',
            'stock_name': '招商银行',
            'operation_type': '卖出',
            'operation_count': -100,
            'operation_price': 37.80,
            'operation_amount': 3780,
            'commission': 5.0,
            'stamp_duty': 3.78,
            'net_amount': 3771.22
        }
    ]

    print(f"\n快照日期: {snapshot_date}")
    print(f"快照持仓数: {len(snapshot_positions)}")
    print(f"后续操作数: {len(operations)}")

    # 3. 计算当前持仓
    from position_management import calculate_current_position, print_current_positions

    current_positions, summary = calculate_current_position(
        snapshot_date, snapshot_positions, operations
    )

    # 4. 打印报告
    print_current_positions(current_positions, summary)

    return current_positions, summary


if __name__ == '__main__':
    # 首先尝试导入主模块
    try:
        from position_management import main
        print("\n使用真实数据运行...")
        main()
    except Exception as e:
        print(f"\n真实数据运行失败: {e}")
        print("\n切换到演示模式...")
        demo_with_sample_data()
