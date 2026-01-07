"""
股票信息管理工具
用于管理股票代码与名称的关联关系
"""

import pymysql
from datetime import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stockDBA',
    'password': 'stockDBA25001',
    'database': 'StockAnalysisDataStore',
    'charset': 'utf8mb4'
}


def create_stock_info_table():
    """创建股票信息表"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS stock_info (
            id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            stock_code VARCHAR(20) NOT NULL COMMENT '股票代码（如：600036.XSHG）',
            stock_name VARCHAR(100) NOT NULL COMMENT '股票名称（如：招商银行）',
            market VARCHAR(10) COMMENT '市场代码（XSHG=上海, XSHE=深圳）',
            code_prefix VARCHAR(10) COMMENT '股票代码前缀（不含市场后缀）',
            industry VARCHAR(50) COMMENT '所属行业',
            sector VARCHAR(50) COMMENT '所属板块',
            is_active TINYINT(1) DEFAULT 1 COMMENT '是否有效（1=有效, 0=无效）',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

            UNIQUE KEY uk_stock_code (stock_code),
            INDEX idx_stock_name (stock_name),
            INDEX idx_market (market),
            INDEX idx_code_prefix (code_prefix),
            INDEX idx_industry (industry)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基本信息表';
        """

        cursor.execute(create_table_sql)
        conn.commit()
        print("✓ 股票信息表创建成功！")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"✗ 创建表失败: {e}")
        return False


def insert_stock_info(stock_list):
    """
    批量插入股票信息

    参数:
        stock_list: 股票信息列表，每个元素为字典
            [
                {
                    'stock_code': '600036.XSHG',
                    'stock_name': '招商银行',
                    'market': 'XSHG',
                    'code_prefix': '600036',
                    'industry': '银行',
                    'sector': '金融'
                },
                ...
            ]
    """
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        insert_sql = """
        INSERT INTO stock_info (stock_code, stock_name, market, code_prefix, industry, sector)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            market = VALUES(market),
            code_prefix = VALUES(code_prefix),
            industry = VALUES(industry),
            sector = VALUES(sector),
            updated_at = CURRENT_TIMESTAMP
        """

        insert_count = 0
        update_count = 0

        for stock in stock_list:
            try:
                cursor.execute(insert_sql, (
                    stock['stock_code'],
                    stock['stock_name'],
                    stock.get('market'),
                    stock.get('code_prefix'),
                    stock.get('industry'),
                    stock.get('sector')
                ))

                if cursor.rowcount == 1:
                    insert_count += 1
                elif cursor.rowcount == 2:
                    update_count += 1

            except Exception as e:
                print(f"  ✗ 插入失败 {stock.get('stock_code', 'Unknown')}: {e}")

        conn.commit()
        print(f"✓ 批量插入完成！")
        print(f"  新增: {insert_count} 条")
        print(f"  更新: {update_count} 条")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"✗ 批量插入失败: {e}")
        return False


def get_stock_name(stock_code):
    """根据股票代码获取股票名称"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query = "SELECT stock_name, market, industry FROM stock_info WHERE stock_code = %s AND is_active = 1"
        cursor.execute(query, (stock_code,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return {
                'stock_name': result[0],
                'market': result[1],
                'industry': result[2]
            }
        else:
            return None

    except Exception as e:
        print(f"✗ 查询失败: {e}")
        return None


def get_all_stocks():
    """获取所有有效股票列表"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        query = """
        SELECT stock_code, stock_name, market, code_prefix, industry, sector
        FROM stock_info
        WHERE is_active = 1
        ORDER BY market, code_prefix
        """
        cursor.execute(query)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return results

    except Exception as e:
        print(f"✗ 查询失败: {e}")
        return []


def print_stock_list():
    """打印所有股票列表"""
    stocks = get_all_stocks()

    if not stocks:
        print("未找到股票数据")
        return

    print(f"\n{'='*80}")
    print(f"股票代码        股票名称        市场        行业        板块")
    print(f"{'='*80}")

    for stock in stocks:
        print(f"{stock['stock_code']:<15} {stock['stock_name']:<10} {stock['market']:<8} {stock['industry'] or '-':<10} {stock['sector'] or '-'}")

    print(f"{'='*80}")
    print(f"总计: {len(stocks)} 只股票\n")


# 示例股票数据
SAMPLE_STOCKS = [
    # 上海市场股票
    {'stock_code': '600036.XSHG', 'stock_name': '招商银行', 'market': 'XSHG', 'code_prefix': '600036', 'industry': '银行', 'sector': '金融'},
    {'stock_code': '600519.XSHG', 'stock_name': '贵州茅台', 'market': 'XSHG', 'code_prefix': '600519', 'industry': '白酒', 'sector': '消费'},
    {'stock_code': '600941.XSHG', 'stock_name': '中国移动', 'market': 'XSHG', 'code_prefix': '600941', 'industry': '通信', 'sector': '通信'},
    {'stock_code': '601318.XSHG', 'stock_name': '中国平安', 'market': 'XSHG', 'code_prefix': '601318', 'industry': '保险', 'sector': '金融'},
    {'stock_code': '600276.XSHG', 'stock_name': '恒瑞医药', 'market': 'XSHG', 'code_prefix': '600276', 'industry': '医药', 'sector': '医疗'},

    # ETF基金
    {'stock_code': '512400.XSHG', 'stock_name': '有色ETF', 'market': 'XSHG', 'code_prefix': '512400', 'industry': 'ETF', 'sector': '基金'},
    {'stock_code': '513880.XSHG', 'stock_name': '证券ETF', 'market': 'XSHG', 'code_prefix': '513880', 'industry': 'ETF', 'sector': '基金'},
    {'stock_code': '518880.XSHG', 'stock_name': '黄金ETF', 'market': 'XSHG', 'code_prefix': '518880', 'industry': 'ETF', 'sector': '基金'},
    {'stock_code': '512880.XSHG', 'stock_name': '证券保险ETF', 'market': 'XSHG', 'code_prefix': '512880', 'industry': 'ETF', 'sector': '基金'},
    {'stock_code': '510300.XSHG', 'stock_name': '沪深300ETF', 'market': 'XSHG', 'code_prefix': '510300', 'industry': 'ETF', 'sector': '基金'},
    {'stock_code': '510500.XSHG', 'stock_name': '中证500ETF', 'market': 'XSHG', 'code_prefix': '510500', 'industry': 'ETF', 'sector': '基金'},

    # 深圳市场股票
    {'stock_code': '000333.XSHE', 'stock_name': '美的集团', 'market': 'XSHE', 'code_prefix': '000333', 'industry': '家电', 'sector': '消费'},
    {'stock_code': '000858.XSHE', 'stock_name': '五粮液', 'market': 'XSHE', 'code_prefix': '000858', 'industry': '白酒', 'sector': '消费'},
    {'stock_code': '000001.XSHE', 'stock_name': '平安银行', 'market': 'XSHE', 'code_prefix': '000001', 'industry': '银行', 'sector': '金融'},
    {'stock_code': '002594.XSHE', 'stock_name': '比亚迪', 'market': 'XSHE', 'code_prefix': '002594', 'industry': '汽车', 'sector': '制造'},

    # 指数
    {'stock_code': '000001.XSHG', 'stock_name': '上证指数', 'market': 'XSHG', 'code_prefix': '000001', 'industry': '指数', 'sector': '指数'},
    {'stock_code': '399006.XSHE', 'stock_name': '创业板指', 'market': 'XSHE', 'code_prefix': '399006', 'industry': '指数', 'sector': '指数'},
]


if __name__ == '__main__':
    import sys

    print("=" * 80)
    print("股票信息管理工具")
    print("=" * 80)

    # 创建表
    print("\n【步骤1】创建股票信息表...")
    create_stock_info_table()

    # 插入示例数据
    print("\n【步骤2】插入示例股票数据...")
    insert_stock_info(SAMPLE_STOCKS)

    # 显示所有股票
    print("\n【步骤3】显示股票列表...")
    print_stock_list()

    # 查询示例
    print("\n【步骤4】查询示例")
    test_code = '600036.XSHG'
    info = get_stock_name(test_code)
    if info:
        print(f"{test_code} -> {info['stock_name']} ({info['industry']})")

    print("\n" + "=" * 80)
    print("操作完成！")
    print("=" * 80)

    print("\n使用说明:")
    print("1. 查看所有股票: python import_stock_info.py")
    print("2. 添加新股票: 在代码中修改 SAMPLE_STOCKS 列表")
    print("3. 获取股票名称: get_stock_name('600036.XSHG')")
    print("4. 获取所有股票: get_all_stocks()")
