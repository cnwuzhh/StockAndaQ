"""
股票数据分析主程序 - Staging Main
功能：
1. 数据获取与计算：获取股票数据并计算技术指标（BOLL等）
2. 数据库存储：将分析结果保存到MySQL数据库
3. 可视化绘图：生成K线图和技术指标图表
4. 触碰提醒：输出触碰BOLL线的股票提醒
"""

from Ashare import get_price
from MyTT import MA, BOLL
import pandas as pd
import numpy as np
from datetime import datetime
import sys

# ==================== Matplotlib中文字体配置 ====================
def setup_chinese_font():
    """
    配置matplotlib以正确显示中文
    支持Windows、Linux和macOS系统
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        import platform
        import os

        system = platform.system()

        if system == 'Windows':
            # Windows系统使用微软雅黑或SimHei
            fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi']
            # 清除字体缓存（Windows中文显示问题的关键）
            try:
                cache_dir = os.path.join(os.path.expanduser('~'), '.matplotlib')
                cache_file = os.path.join(cache_dir, 'fontlist-v330.json')
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    print("✓ 已清除matplotlib字体缓存")
            except:
                pass
        elif system == 'Darwin':  # macOS
            fonts = ['PingFang SC', 'Heiti TC', 'STHeiti']
        else:  # Linux
            fonts = ['WenQuanYi Micro Hei', 'DejaVu Sans']

        # 配置matplotlib
        plt.rcParams['font.sans-serif'] = fonts
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        plt.rcParams['font.family'] = 'sans-serif'

        # 验证字体是否可用
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        found_fonts = [f for f in fonts if f in available_fonts]

        if found_fonts:
            print(f"✓ 中文字体配置完成（系统: {system}, 使用字体: {found_fonts[0]}）")
        else:
            print(f"⚠ 警告: 未找到指定中文字体，可能仍无法显示中文")
            print(f"  可用字体: {available_fonts[:10]}...")

        return True
    except ImportError:
        print("⚠ matplotlib未安装，跳过字体配置")
        return False
    except Exception as e:
        print(f"⚠ 字体配置失败: {e}")
        return False


# 初始化中文字体配置
setup_chinese_font()

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stockDBA',  # 请根据实际情况修改
    'password': 'stockDBA25001',  # 请根据实际情况修改
    'database': 'StockAnalysisDataStore',
    'charset': 'utf8mb4'
}


# ==================== 数据获取与计算模块 ====================

def get_stock_data(stock_code, frequency='1d', count=120):
    """
    获取股票数据并计算技术指标

    参数:
        stock_code: 股票代码，如 '600036.XSHG'
        frequency: 数据频率，默认 '1d' (日线)
        count: 获取最近多少天的数据，默认120天

    返回:
        df: 包含OHLCV和技术指标的DataFrame
    """
    print(f"\n{'='*60}")
    print(f"【数据获取】正在获取股票 {stock_code} 的数据...")
    print(f"{'='*60}")

    # 获取基础行情数据
    df = get_price(stock_code, frequency=frequency, count=count)
    print(f"成功获取 {len(df)} 条数据（{df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')}）")
    print(f"\n最近5个交易日行情:\n{df.tail(5)}")

    # 计算技术指标
    print(f"\n{'='*60}")
    print(f"【技术指标计算】计算均线和布林带指标...")
    print(f"{'='*60}")

    CLOSE = df.close.values
    HIGH = df.high.values
    LOW = df.low.values

    # 计算均线
    MA5 = MA(CLOSE, 5)
    MA10 = MA(CLOSE, 10)
    MA20 = MA(CLOSE, 20)

    # 计算布林带
    boll_upper, boll_middle, boll_lower = BOLL(CLOSE)

    # 将指标添加到DataFrame
    df['MA5'] = MA5
    df['MA10'] = MA10
    df['MA20'] = MA20
    df['BOLL_UPPER'] = boll_upper
    df['BOLL_MIDDLE'] = boll_middle
    df['BOLL_LOWER'] = boll_lower

    print("技术指标计算完成！")
    print(f"最新指标值: MA5={MA5[-1]:.2f}, MA10={MA10[-1]:.2f}, BOLL上轨={boll_upper[-1]:.2f}, BOLL下轨={boll_lower[-1]:.2f}")

    return df


# ==================== BOLL触碰检测模块 ====================

def check_boll_touch(df, lookback_days=1):
    """
    检测指定天数内是否触碰BOLL线

    参数:
        df: 包含BOLL指标的DataFrame
        lookback_days: 检测最近几天，默认为1(昨天)

    返回:
        touched: bool, 是否触碰BOLL线
        touch_info: list, 触碰信息列表
    """
    touched = False
    touch_info = []

    # 获取最近lookback_days天的数据
    recent_data = df.tail(lookback_days)

    for idx, row in recent_data.iterrows():
        date_str = idx.strftime('%Y-%m-%d')
        high = row['high']
        low = row['low']
        upper = row['BOLL_UPPER']
        lower = row['BOLL_LOWER']

        # 检测是否触碰上轨（最高价 >= 上轨）
        if high >= upper:
            touched = True
            touch_info.append({
                'date': date_str,
                'type': 'UPPER',
                'desc': f'最高价 {high:.2f} 触碰布林线上轨 {upper:.2f}'
            })

        # 检测是否触碰下轨（最低价 <= 下轨）
        if low <= lower:
            touched = True
            touch_info.append({
                'date': date_str,
                'type': 'LOWER',
                'desc': f'最低价 {low:.2f} 触碰布林线下轨 {lower:.2f}'
            })

    return touched, touch_info


def print_boll_touch_alert(stock_code, df, lookback_days=1):
    """
    输出BOLL触碰提醒

    参数:
        stock_code: 股票代码
        df: 包含BOLL指标的DataFrame
        lookback_days: 检测最近几天，默认为1(昨天)
    """
    print(f"\n{'='*60}")
    print(f"【BOLL触碰检测】检测股票 {stock_code} 最近{lookback_days}天是否触碰BOLL线")
    print(f"{'='*60}")

    touched, touch_info = check_boll_touch(df, lookback_days=lookback_days)

    if not touched:
        print(f"✓ 最近{lookback_days}天未触碰BOLL线")
    else:
        print(f"⚠ 检测到BOLL线触碰！")
        for info in touch_info:
            touch_type_text = '上轨' if info['type'] == 'UPPER' else '下轨'
            print(f"  📅 {info['date']}: {info['desc']}")
        print(f"  提示：触碰{'上轨' if any(t['type']=='UPPER' for t in touch_info) else ''}{'/' if any(t['type']=='UPPER' for t in touch_info) and any(t['type']=='LOWER' for t in touch_info) else ''}{'下轨' if any(t['type']=='LOWER' for t in touch_info) else ''}可能意味着价格波动较大，请注意风险！")

    print(f"{'='*60}\n")

    return touched, touch_info


# ==================== 数据库存储模块 ====================

def save_to_database(df, stock_code, touch_info):
    """
    将数据保存到MySQL数据库

    参数:
        df: 包含所有指标的DataFrame
        stock_code: 股票代码
        touch_info: BOLL触碰信息
    """
    print(f"\n{'='*60}")
    print(f"【数据库存储】准备保存数据到MySQL数据库...")
    print(f"{'='*60}")

    try:
        import pymysql
        from pymysql.cursors import DictCursor

        # 连接数据库
        print("正在连接数据库...")
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset'],
            cursorclass=DictCursor
        )

        if conn.open:
            print("✓ 数据库连接成功！")

            cursor = conn.cursor()


            # 创建触碰类型映射
            touch_type_map = {info['date']: info['type'] for info in touch_info}

            # 准备插入数据
            insert_count = 0
            update_count = 0

            for idx, row in df.iterrows():
                trade_date = idx.strftime('%Y-%m-%d')
                touch_type = touch_type_map.get(trade_date, None)

                # 检查记录是否已存在
                check_sql = "SELECT id FROM stock_daily_data WHERE stock_code = %s AND trade_date = %s"
                cursor.execute(check_sql, (stock_code, trade_date))
                result = cursor.fetchone()

                # 准备数据
                data = (
                    stock_code,
                    trade_date,
                    float(row['open']),
                    float(row['close']),
                    float(row['high']),
                    float(row['low']),
                    int(row.get('volume', 0)) if pd.notna(row.get('volume')) else 0,
                    float(row['BOLL_UPPER']) if pd.notna(row['BOLL_UPPER']) else None,
                    float(row['BOLL_MIDDLE']) if pd.notna(row['BOLL_MIDDLE']) else None,
                    float(row['BOLL_LOWER']) if pd.notna(row['BOLL_LOWER']) else None,
                    touch_type
                )

                if result:
                    # 更新现有记录
                    update_sql = """
                        UPDATE stock_daily_data
                        SET open = %s, close = %s, high = %s, low = %s, volume = %s,
                            boll_upper = %s, boll_middle = %s, boll_lower = %s, boll_touch_type = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE stock_code = %s AND trade_date = %s
                    """
                    cursor.execute(update_sql, (
                        data[2], data[3], data[4], data[5], data[6],
                        data[7], data[8], data[9], data[10],
                        data[0], data[1]
                    ))
                    update_count += 1
                else:
                    # 插入新记录
                    insert_sql = """
                        INSERT INTO stock_daily_data
                        (stock_code, trade_date, open, close, high, low, volume,
                         boll_upper, boll_middle, boll_lower, boll_touch_type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_sql, data)
                    insert_count += 1

            # 提交事务
            conn.commit()
            print(f"✓ 数据保存成功！")
            print(f"  - 新增记录: {insert_count} 条")
            print(f"  - 更新记录: {update_count} 条")
            print(f"  - 总计处理: {insert_count + update_count} 条")

            cursor.close()
            conn.close()

        else:
            print("✗ 数据库连接失败！")

    except ImportError:
        print("✗ 缺少 pymysql 库")
        print("  请运行: pip install pymysql")
    except Exception as e:
        print(f"✗ 数据库错误: {e}")


# ==================== 可视化绘图模块 ====================

def plot_kline_with_boll(df, stock_code, days=120):
    """
    绘制K线图+布林线指标

    参数:
        df: 包含OHLC和BOLL指标的DataFrame
        stock_code: 股票代码（用于标题和文件名）
        days: 显示最近多少天的数据，默认120天

    返回:
        None
    """
    print(f"\n{'='*60}")
    print(f"【可视化绘图】正在生成K线图...")
    print(f"{'='*60}")

    try:
        import mplfinance as mpf
        import matplotlib.pyplot as plt

        # 重新配置matplotlib中文字体（mplfinance需要额外配置）
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

        # 准备数据，确保索引为 DatetimeIndex
        data = df[['open', 'high', 'low', 'close', 'volume', 'BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']].copy()
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)

        # 添加布林线面板
        add_plots = [
            mpf.make_addplot(data['BOLL_UPPER'].tail(days), color='red', width=1.2),
            mpf.make_addplot(data['BOLL_MIDDLE'].tail(days), color='yellow', width=1.0),
            mpf.make_addplot(data['BOLL_LOWER'].tail(days), color='green', width=1.2)
        ]

        # 标题
        title = f'{stock_code} K线图+布林线（最近{days}日）'

        # 优先尝试交互式显示；若失败则保存为文件以适配无显示环境
        try:
            mpf.plot(data.tail(days), type='candle', mav=(5, 10), volume=True,
                     addplot=add_plots, style='yahoo',
                     title=title, figsize=(15, 8))
            print("✓ K线图已显示")
        except Exception:
            out_file = f'{stock_code}_kline_{datetime.now().strftime("%Y%m%d")}.png'
            mpf.plot(data.tail(days), type='candle', mav=(5, 10), volume=True,
                     addplot=add_plots, style='yahoo',
                     title=title, figsize=(15, 8), savefig=out_file)
            print(f"✓ K线图已保存为文件: {out_file}")

    except ImportError:
        print("✗ 缺少 mplfinance 库")
        print("  如需绘图功能，请运行: pip install mplfinance")
    except Exception as e:
        print(f"✗ 绘图时出错: {e}")


# ==================== 主程序入口 ====================

def main(stock_code='600036.XSHG', frequency='1d', count=120, save_db=False, plot_chart=True):
    """
    主程序入口

    参数:
        stock_code: 股票代码，默认 '600036.XSHG'
        frequency: 数据频率，默认 '1d'
        count: 获取天数，默认120天
        save_db: 是否保存到数据库，默认False
        plot_chart: 是否绘图，默认True
    """
    print(f"\n{'#'*60}")
    print(f"# 股票数据分析系统 - Staging Main")
    print(f"# 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# 股票代码: {stock_code}")
    print(f"{'#'*60}")

    # 1. 数据获取与计算
    df = get_stock_data(stock_code, frequency=frequency, count=count)

    # 2. BOLL触碰检测与提醒
    touched, touch_info = print_boll_touch_alert(stock_code, df, lookback_days=count)


    # 3. 数据库存储
    if save_db:
        save_to_database(df, stock_code, touch_info)

    # 4. 可视化绘图
    if plot_chart:
        plot_kline_with_boll(df, stock_code, days=count)

    print(f"\n{'#'*60}")
    print(f"# 分析完成！")
    print(f"{'#'*60}\n")

    return df, touch_info


# 批量处理多只股票
def batch_analysis(stock_list, count=1, save_db=False, plot_chart=True):
    """
    批量分析多只股票

    参数:
        stock_list: 股票代码列表，如 ['600036.XSHG', '600519.XSHG']
        save_db: 是否保存到数据库
        plot_chart: 是否绘图
    """
    print(f"\n{'='*60}")
    print(f"【批量分析】开始分析 {len(stock_list)} 只股票...")
    print(f"{'='*60}")

    all_results = {}

    for stock_code in stock_list:
        try:
            df, touch_info = main(
                stock_code=stock_code,
                save_db=save_db,
                count=count,
                plot_chart=plot_chart
            )
            all_results[stock_code] = {
                'success': True,
                'touch_count': len(touch_info),
                'touch_info': touch_info
            }
        except Exception as e:
            print(f"✗ 分析股票 {stock_code} 时出错: {e}")
            all_results[stock_code] = {
                'success': False,
                'error': str(e)
            }

    # 输出汇总
    print(f"\n{'='*60}")
    print(f"【批量分析汇总】")
    print(f"{'='*60}")
    success_count = sum(1 for r in all_results.values() if r['success'])
    touch_count = sum(r.get('touch_count', 0) for r in all_results.values() if r['success'])
    print(f"总计分析: {len(stock_list)} 只股票")
    print(f"成功: {success_count} 只")
    print(f"失败: {len(stock_list) - success_count} 只")
    print(f"检测到BOLL触碰: {touch_count} 次")
    print(f"{'='*60}\n")

    return all_results


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    # 解析命令行参数
    if len(sys.argv) > 1:
        # 从命令行参数读取股票代码
        stock_codes = sys.argv[1].split(',')
        save_db = '--save' in sys.argv
        no_plot = '--no-plot' in sys.argv

        if len(stock_codes) > 1:
            # 批量分析
            batch_analysis(stock_codes, save_db=save_db, plot_chart=not no_plot)
        else:
            # 单个股票分析
            main(
                stock_code=stock_codes[0],
                save_db=save_db,
                plot_chart=not no_plot
            )
    else:
        # 默认运行示例
        stock_codes = ['600036.XSHG', '600941.XSHG', '513880.XSHG', '518880.XSHG', '000333.XSHE', '000858.XSHE']  # 可修改为需要分析的股票列表

        all_results = batch_analysis(stock_codes, count=720, save_db=True, plot_chart=False)
        print("批量分析结果:", all_results)
