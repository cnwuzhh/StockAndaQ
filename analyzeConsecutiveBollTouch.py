"""
连续触碰BOLL线分析工具
功能：从数据库获取指定股票的记录，分析最近三段连续触碰BOLL线的情况
- 连续触碰的次数和时间
- 距离上一次触碰的间隔时间
- 触碰的是上轨还是下轨
- 支持邮件自动发送分析结果
"""

import pandas as pd
import pymysql
from datetime import datetime
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 数据库配置（与staging_main.py保持一致）
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stockDBA',
    'password': 'stockDBA25001',
    'database': 'StockAnalysisDataStore',
    'charset': 'utf8mb4'
}


def get_stock_name(stock_code):
    """
    从数据库获取股票名称

    参数:
        stock_code: 股票代码

    返回:
        str: 股票名称，如果查询失败返回None
    """
    try:
        import pymysql

        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset']
        )

        query = "SELECT stock_name FROM stock_info WHERE stock_code = %s AND is_active = 1"
        cursor = conn.cursor()
        cursor.execute(query, (stock_code,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return result[0]
        else:
            return None

    except Exception as e:
        print(f"  ⚠ 查询股票名称失败: {e}")
        return None


def format_stock_display(stock_code, stock_name=None):
    """
    格式化股票显示为"名称 + 代码"

    参数:
        stock_code: 股票代码
        stock_name: 股票名称（可选）

    返回:
        str: 格式化后的显示文本
    """
    if not stock_name:
        # 尝试从数据库获取
        stock_name = get_stock_name(stock_code)

    if stock_name:
        return f"{stock_name} ({stock_code})"
    else:
        # 如果没有找到名称，只显示代码
        return stock_code

# 邮件配置
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',  # SMTP服务器地址
    'smtp_port': 587,  # SMTP端口（TLS通常使用587）
    'sender_email': 'your_email@gmail.com',  # 发件人邮箱
    'sender_password': 'your_app_password',  # 邮箱授权码（不是登录密码）
    'sender_name': '股票分析系统',  # 发件人名称
    'recipients': []  # 收件人列表，运行时动态设置
}


def get_touch_data_from_db(stock_code, limit_days=365):
    """
    从数据库获取指定股票的触碰记录

    参数:
        stock_code: 股票代码
        limit_days: 查询最近多少天的记录，默认365天

    返回:
        DataFrame: 包含触碰记录的数据
    """
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset']
        )

        query = """
            SELECT trade_date, boll_touch_type, high, low, boll_upper, boll_lower
            FROM stock_daily_data
            WHERE stock_code = %s
            AND boll_touch_type IS NOT NULL
            AND trade_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            ORDER BY trade_date ASC
        """

        df = pd.read_sql(query, conn, params=(stock_code, limit_days))
        conn.close()

        # 转换日期格式
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date

        return df

    except Exception as e:
        print(f"✗ 数据库查询失败: {e}")
        return None


def analyze_consecutive_touches(df):
    """
    分析连续触碰情况，返回最近三段连续触碰序列

    参数:
        df: 包含触碰记录的DataFrame

    返回:
        list: 连续触碰序列列表，每个元素包含：
            - start_date: 开始日期
            - end_date: 结束日期
            - count: 连续次数
            - touch_type: 触碰类型
            - gap_days: 距离上一段的间隔天数
    """
    if df is None or df.empty:
        return []

    # 按日期排序
    df = df.sort_values('trade_date').reset_index(drop=True)

    consecutive_sequences = []
    current_sequence = None

    for i in range(len(df)):
        row = df.iloc[i]
        touch_date = row['trade_date']
        touch_type = row['boll_touch_type']

        if i == 0:
            # 第一条记录，开始新的序列
            current_sequence = {
                'start_date': touch_date,
                'end_date': touch_date,
                'count': 1,
                'touch_type': touch_type,
                'gap_days': None  # 第一段序列没有间隔
            }
        else:
            prev_row = df.iloc[i - 1]
            prev_date = prev_row['trade_date']
            prev_type = prev_row['boll_touch_type']

            # 计算日期差
            days_diff = (touch_date - prev_date).days

            # 判断是否连续（相差1天）且触碰类型相同
            if days_diff == 1 and touch_type == prev_type:
                # 连续触碰，更新当前序列
                current_sequence['end_date'] = touch_date
                current_sequence['count'] += 1
            else:
                # 不连续或触碰类型改变，保存当前序列并开始新序列
                consecutive_sequences.append(current_sequence.copy())

                current_sequence = {
                    'start_date': touch_date,
                    'end_date': touch_date,
                    'count': 1,
                    'touch_type': touch_type,
                    'gap_days': days_diff - 1  # 距离上一段的间隔天数（不包括两个触碰日）
                }

    # 添加最后一个序列
    if current_sequence:
        consecutive_sequences.append(current_sequence)

    return consecutive_sequences


def format_consecutive_info(sequence):
    """
    格式化连续触碰信息为可读字符串

    参数:
        sequence: 连续触碰序列信息

    返回:
        str: 格式化的字符串
    """
    touch_type_text = '上轨' if sequence['touch_type'] == 'UPPER' else '下轨'

    info = f"【{touch_type_text}触碰】"
    info += f"\n  • 连续次数: {sequence['count']} 次"
    info += f"\n  • 起始日期: {sequence['start_date']}"
    info += f"\n  • 结束日期: {sequence['end_date']}"

    if sequence['gap_days'] is not None:
        info += f"\n  • 距离上一段: {sequence['gap_days']} 天"
    else:
        info += f"\n  • 距离上一段: 无（第一段）"

    return info


def format_consecutive_info_html(sequence):
    """
    格式化连续触碰信息为HTML格式（用于邮件）

    参数:
        sequence: 连续触碰序列信息

    返回:
        str: HTML格式的字符串
    """
    touch_type_text = '上轨' if sequence['touch_type'] == 'UPPER' else '下轨'
    touch_type_color = '#d9534f' if sequence['touch_type'] == 'UPPER' else '#5bc0de'

    html = f"""
    <div style="background-color: #f8f9fa; padding: 10px; margin: 10px 0; border-left: 3px solid {touch_type_color}; border-radius: 3px;">
        <h4 style="color: {touch_type_color}; margin: 0 0 10px 0;">{touch_type_text}触碰</h4>
        <table style="border-collapse: collapse;">
            <tr>
                <td style="padding: 5px; font-weight: bold;">连续次数:</td>
                <td style="padding: 5px;">{sequence['count']} 次</td>
            </tr>
            <tr>
                <td style="padding: 5px; font-weight: bold;">起始日期:</td>
                <td style="padding: 5px;">{sequence['start_date']}</td>
            </tr>
            <tr>
                <td style="padding: 5px; font-weight: bold;">结束日期:</td>
                <td style="padding: 5px;">{sequence['end_date']}</td>
            </tr>
            <tr>
                <td style="padding: 5px; font-weight: bold;">距离上一段:</td>
                <td style="padding: 5px;">{sequence['gap_days']} 天</td>
            </tr>
        </table>
    </div>
    """

    return html


def send_email_report(stock_code, result, recipients):
    """
    发送分析报告邮件（不包含K线图，邮件不支持嵌入图片）

    参数:
        stock_code: 股票代码
        result: 分析结果
        recipients: 收件人邮箱列表

    返回:
        bool: 发送是否成功
    """
    if not recipients:
        print("⚠ 未配置收件人邮箱，跳过邮件发送")
        return False

    try:
        # 创建邮件对象
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(f'【股票分析】{stock_code} 连续触碰BOLL线报告', 'utf-8')
        msg['From'] = Header(f"{EMAIL_CONFIG['sender_name']} <{EMAIL_CONFIG['sender_email']}>", 'utf-8')
        msg['To'] = ', '.join(recipients)

        # 生成HTML内容（不包含K线图）
        html_content = generate_html_report(stock_code, result, chart_filename=None)

        # 创建HTML邮件
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)

        # 连接SMTP服务器并发送
        print(f"\n{'='*70}")
        print(f"【邮件发送】正在发送分析报告...")
        print(f"{'='*70}")

        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()  # 启用TLS加密
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.sendmail(EMAIL_CONFIG['sender_email'], recipients, msg.as_string())
        server.quit()

        print(f"✓ 邮件发送成功！")
        print(f"  收件人: {', '.join(recipients)}")
        print(f"{'='*70}\n")

        return True

    except Exception as e:
        print(f"✗ 邮件发送失败: {e}")
        return False


def generate_html_report(stock_code, result, chart_filename=None, latest_touch=None):
    """
    生成HTML格式的分析报告

    参数:
        stock_code: 股票代码
        result: 分析结果
        chart_filename: K线图文件名（可选）
        latest_touch: 最新触碰状态信息（可选）

    返回:
        str: HTML内容
    """
    if not result or 'sequences' not in result:
        return """
        <html>
        <body>
            <h2>股票分析报告 - {stock_code}</h2>
            <p style="color: red;">未找到分析数据</p>
        </body>
        </html>
        """.format(stock_code=stock_code)

    sequences = result['sequences']

    # 获取股票名称
    stock_display = format_stock_display(stock_code)

    # 构建HTML内容
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: "Microsoft YaHei", Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #34495e;
                margin-top: 30px;
            }}
            .summary {{
                background-color: #ecf0f1;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .latest-touch {{
                background-color: #fff3cd;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
                border-left: 4px solid #ffc107;
            }}
            .latest-touch.touched {{
                background-color: #d4edda;
                border-left-color: #28a745;
            }}
            .latest-touch.touched-upper {{
                background-color: #f8d7da;
                border-left-color: #dc3545;
            }}
            .latest-touch.touched-lower {{
                background-color: #d1ecf1;
                border-left-color: #17a2b8;
            }}
            .chart-container {{
                margin: 30px 0;
                text-align: center;
                background-color: #f8f9fa;
                padding: 20px;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }}
            .chart-container img {{
                max-width: 100%;
                height: auto;
                border: 1px solid #ccc;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #bdc3c7;
                color: #7f8c8d;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <h1>📊 股票分析报告</h1>
        <h2>{stock_display} - 连续触碰BOLL线分析</h2>

        <div class="summary">
            <h3>📈 分析摘要</h3>
            <p><strong>分析时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>总计连续触碰段数:</strong> {result.get('total_sequences', 0)}</p>
        </div>

        <h3>🎯 最新交易日触碰状态</h3>
    """

    # 添加最新触碰状态
    if latest_touch:
        touch_date = latest_touch.get('touch_date', '未知')
        if latest_touch['touched']:
            touch_type_cn = '上轨' if latest_touch['touch_type'] == 'UPPER' else '下轨'
            touch_class = 'touched-upper' if latest_touch['touch_type'] == 'UPPER' else 'touched-lower'
            html += f"""
        <div class="latest-touch {touch_class}">
            <h4>⚠ 触碰BOLL线！</h4>
            <p><strong>日期:</strong> {touch_date}</p>
            <p><strong>触碰类型:</strong> {touch_type_cn}</p>
            <p><strong>详情:</strong> {latest_touch.get('description', '无')}</p>
        </div>
        """
        else:
            html += f"""
        <div class="latest-touch">
            <h4>✓ 未触碰BOLL线</h4>
            <p><strong>日期:</strong> {touch_date}</p>
            <p><strong>状态:</strong> {latest_touch.get('description', '无')}</p>
        </div>
        """
    else:
        html += """
        <div class="latest-touch">
            <p style="color: #7f8c8d;">无法获取最新触碰状态</p>
        </div>
        """

    html += f"""
        <h3>📊 K线图与布林线</h3>
    """

    # 添加K线图（如果存在）
    if chart_filename:
        html += f"""
        <div class="chart-container">
            <p><strong>图表说明：</strong>K线图包含价格走势、成交量及布林带上中下轨（红、黄、绿线）</p>
            <img src="{chart_filename}" alt="{stock_code} K线图与布林线">
        </div>
        """
    else:
        html += """
        <div class="chart-container">
            <p style="color: #7f8c8d;">K线图生成失败或不可用</p>
        </div>
        """

    html += f"""
        <h3>📋 最近 {len(sequences)} 段连续触碰详情</h3>
    """

    # 添加每段连续触碰的详情
    for i, seq in enumerate(sequences, 1):
        html += f"""
        <h4>第 {i} 段连续触碰</h4>
        {format_consecutive_info_html(seq)}
        """

    # 添加页脚
    html += f"""
        <div class="footer">
            <p>本报告由股票分析系统自动生成</p>
            <p>如有疑问，请联系系统管理员</p>
        </div>
    </body>
    </html>
    """

    return html


def send_batch_email_report(results, recipients):
    """
    发送批量分析报告邮件

    参数:
        results: 所有股票的分析结果
        recipients: 收件人邮箱列表

    返回:
        bool: 发送是否成功
    """
    if not recipients:
        print("⚠ 未配置收件人邮箱，跳过邮件发送")
        return False

    try:
        # 创建邮件对象
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(f'【批量分析】股票连续触碰BOLL线报告 - {datetime.now().strftime("%Y-%m-%d")}', 'utf-8')
        msg['From'] = Header(f"{EMAIL_CONFIG['sender_name']} <{EMAIL_CONFIG['sender_email']}>", 'utf-8')
        msg['To'] = ', '.join(recipients)

        # 生成HTML内容
        html_content = generate_batch_html_report(results)

        # 创建HTML邮件
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)

        # 连接SMTP服务器并发送
        print(f"\n{'='*70}")
        print(f"【邮件发送】正在发送批量分析报告...")
        print(f"{'='*70}")

        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.sendmail(EMAIL_CONFIG['sender_email'], recipients, msg.as_string())
        server.quit()

        print(f"✓ 批量报告邮件发送成功！")
        print(f"  收件人: {', '.join(recipients)}")
        print(f"{'='*70}\n")

        return True

    except Exception as e:
        print(f"✗ 批量报告邮件发送失败: {e}")
        return False


def get_latest_touch_status(stock_code):
    """
    获取最新交易日的触碰状态

    参数:
        stock_code: 股票代码

    返回:
        dict: 包含触碰状态信息
            - touched: bool, 是否触碰
            - touch_type: str, 触碰类型 (UPPER/LOWER)
            - touch_date: str, 触碰日期
            - price: float, 触碰价格
            - boll_value: float, BOLL值
    """
    try:
        from Ashare import get_price
        from MyTT import BOLL

        # 获取最近2天的数据（确保有最新交易日）
        df = get_price(stock_code, frequency='1d', count=2)

        if df.empty:
            return None

        # 计算BOLL指标
        CLOSE = df.close.values
        up, mid, lower = BOLL(CLOSE)
        df['BOLL_UPPER'] = up
        df['BOLL_MIDDLE'] = mid
        df['BOLL_LOWER'] = lower

        # 获取最新交易日（最后一条数据）
        latest = df.iloc[-1]
        latest_date = df.index[-1]

        high = latest['high']
        low = latest['low']
        upper = latest['BOLL_UPPER']
        lower_boll = latest['BOLL_LOWER']

        # 检测触碰
        if high >= upper:
            return {
                'touched': True,
                'touch_type': 'UPPER',
                'touch_date': latest_date.strftime('%Y-%m-%d'),
                'price': high,
                'boll_value': upper,
                'description': f'最高价 {high:.2f} 触碰上轨 {upper:.2f}'
            }
        elif low <= lower_boll:
            return {
                'touched': True,
                'touch_type': 'LOWER',
                'touch_date': latest_date.strftime('%Y-%m-%d'),
                'price': low,
                'boll_value': lower_boll,
                'description': f'最低价 {low:.2f} 触碰下轨 {lower_boll:.2f}'
            }
        else:
            return {
                'touched': False,
                'touch_type': None,
                'touch_date': latest_date.strftime('%Y-%m-%d'),
                'price': latest['close'],
                'boll_value': None,
                'description': f'未触碰BOLL线（收盘价 {latest["close"]:.2f}）'
            }
    except Exception as e:
        print(f"  ✗ 获取触碰状态失败: {e}")
        return None


def generate_kline_chart(stock_code, output_dir='.', days=120):
    """
    生成K线图并保存为图片文件

    参数:
        stock_code: 股票代码
        output_dir: 输出目录
        days: 显示最近多少天的数据

    返回:
        str: 图片文件的相对路径（相对于output_dir），失败返回None
    """
    try:
        from Ashare import get_price
        from MyTT import BOLL
        import mplfinance as mpf
        import matplotlib.pyplot as plt
        import pandas as pd
        import os

        # 创建images子目录
        images_dir = os.path.join(output_dir, 'images')
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)

        # 获取股票数据
        print(f"  正在获取 {stock_code} 的K线数据...")
        df = get_price(stock_code, frequency='1d', count=days)

        # 计算BOLL指标
        CLOSE = df.close.values
        up, mid, lower = BOLL(CLOSE)
        df['BOLL_UPPER'] = up
        df['BOLL_MIDDLE'] = mid
        df['BOLL_LOWER'] = lower

        # 配置中文字体
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi']
        plt.rcParams['axes.unicode_minus'] = False

        # 准备数据
        data = df[['open', 'high', 'low', 'close', 'volume', 'BOLL_UPPER', 'BOLL_MIDDLE', 'BOLL_LOWER']].copy()
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)

        # 生成图片文件名
        date_str = datetime.now().strftime('%Y-%m-%d')
        chart_filename = f"{date_str}_{stock_code}_kline.png"
        chart_filepath = os.path.join(images_dir, chart_filename)

        # 添加布林线面板
        add_plots = [
            mpf.make_addplot(data['BOLL_UPPER'].tail(days), color='red', width=1.2),
            mpf.make_addplot(data['BOLL_MIDDLE'].tail(days), color='yellow', width=1.0),
            mpf.make_addplot(data['BOLL_LOWER'].tail(days), color='green', width=1.2)
        ]

        # 绘制并保存K线图
        title = f'{stock_code} K线图+布林线（最近{days}日）'
        mpf.plot(data.tail(days), type='candle', mav=(5, 10), volume=True,
                addplot=add_plots, style='yahoo',
                title=title, figsize=(15, 8), savefig=chart_filepath)

        # 返回相对路径（相对于output_dir）
        relative_path = f"images/{chart_filename}"
        print(f"  ✓ K线图已生成: {relative_path}")
        return relative_path

    except Exception as e:
        print(f"  ✗ 生成K线图失败: {e}")
        return None


def save_html_report(stock_code, result, output_dir='.'):
    """
    保存HTML报告到文件（包含K线图和最新触碰状态）

    参数:
        stock_code: 股票代码
        result: 分析结果
        output_dir: 输出目录，默认为当前目录

    返回:
        str: 保存的文件路径，失败返回None
    """
    try:
        import os

        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 获取最新触碰状态
        print(f"  正在获取 {stock_code} 的最新触碰状态...")
        latest_touch = get_latest_touch_status(stock_code)

        # 生成K线图
        chart_filename = generate_kline_chart(stock_code, output_dir)

        # 生成文件名：日期_股票代码_analysis.html
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}_{stock_code}_analysis.html"
        filepath = os.path.join(output_dir, filename)

        # 生成HTML内容（包含K线图和最新触碰状态）
        html_content = generate_html_report(stock_code, result, chart_filename, latest_touch)

        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✓ HTML报告已保存: {filepath}")
        return filepath

    except Exception as e:
        print(f"✗ 保存HTML报告失败: {e}")
        return None


def save_batch_html_report(results, output_dir='.'):
    """
    保存批量分析的HTML报告到文件（包含K线图和最新触碰状态）

    参数:
        results: 所有股票的分析结果
        output_dir: 输出目录，默认为当前目录

    返回:
        str: 保存的文件路径，失败返回None
    """
    try:
        import os

        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 为每只股票生成K线图并获取最新触碰状态
        chart_files = {}
        latest_touches = {}
        for stock_code, result in results.items():
            if result and 'sequences' in result:
                print(f"\n生成 {stock_code} 的K线图和触碰状态...")
                # 获取最新触碰状态
                latest_touches[stock_code] = get_latest_touch_status(stock_code)
                # 生成K线图
                chart_files[stock_code] = generate_kline_chart(stock_code, output_dir)

        # 生成文件名：日期_batch_analysis.html
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}_batch_analysis.html"
        filepath = os.path.join(output_dir, filename)

        # 生成HTML内容（包含K线图和最新触碰状态）
        html_content = generate_batch_html_report(results, chart_files, latest_touches)

        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"\n✓ 批量HTML报告已保存: {filepath}")
        return filepath

    except Exception as e:
        print(f"✗ 保存批量HTML报告失败: {e}")
        return None


def generate_batch_html_report(results, chart_files=None, latest_touches=None):
    """
    生成批量分析的HTML报告

    参数:
        results: 所有股票的分析结果
        chart_files: K线图文件字典 {stock_code: filename}（可选）
        latest_touches: 最新触碰状态字典 {stock_code: touch_info}（可选）

    返回:
        str: HTML内容
    """
    if chart_files is None:
        chart_files = {}
    if latest_touches is None:
        latest_touches = {}

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: "Microsoft YaHei", Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
            }}
            .stock-section {{
                margin: 30px 0;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 5px;
                border-left: 4px solid #3498db;
            }}
            .stock-title {{
                color: #2c3e50;
                font-size: 18px;
                font-weight: bold;
                margin: 0 0 15px 0;
            }}
            .latest-touch-box {{
                background-color: #fff3cd;
                padding: 12px;
                border-radius: 5px;
                margin: 15px 0;
                border-left: 4px solid #ffc107;
                font-size: 14px;
            }}
            .latest-touch-box.touched-upper {{
                background-color: #f8d7da;
                border-left-color: #dc3545;
            }}
            .latest-touch-box.touched-lower {{
                background-color: #d1ecf1;
                border-left-color: #17a2b8;
            }}
            .chart-container {{
                margin: 20px 0;
                text-align: center;
                background-color: #ffffff;
                padding: 15px;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }}
            .chart-container img {{
                max-width: 100%;
                height: auto;
                border: 1px solid #ccc;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }}
            th, td {{
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #3498db;
                color: white;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #bdc3c7;
                color: #7f8c8d;
                font-size: 12px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <h1>📊 批量股票分析报告</h1>
        <p><strong>分析时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    """

    # 为每只股票添加分析结果
    for stock_code, result in results.items():
        if result and 'sequences' in result:
            sequences = result['sequences']
            chart_file = chart_files.get(stock_code)
            latest_touch = latest_touches.get(stock_code)

            # 获取股票显示名称
            stock_display = format_stock_display(stock_code)

            html += f"""
            <div class="stock-section">
                <div class="stock-title">{stock_display}</div>
                <p><strong>总计连续触碰段数:</strong> {result.get('total_sequences', 0)}</p>

                <h4>🎯 最新交易日触碰状态</h4>
            """

            # 添加最新触碰状态
            if latest_touch:
                if latest_touch['touched']:
                    touch_type_cn = '上轨' if latest_touch['touch_type'] == 'UPPER' else '下轨'
                    touch_class = 'touched-upper' if latest_touch['touch_type'] == 'UPPER' else 'touched-lower'
                    html += f"""
                <div class="latest-touch-box {touch_class}">
                    <strong>⚠ 触碰BOLL线！</strong> ({latest_touch.get('touch_date', '未知')})<br>
                    类型: {touch_type_cn} | {latest_touch.get('description', '无')}
                </div>
                """
                else:
                    html += f"""
                <div class="latest-touch-box">
                    <strong>✓ 未触碰BOLL线</strong> ({latest_touch.get('touch_date', '未知')})<br>
                    {latest_touch.get('description', '无')}
                </div>
                """
            else:
                html += """
                <div class="latest-touch-box">
                    无法获取最新触碰状态
                </div>
                """

            html += f"""
                <h4>📊 K线图与布林线</h4>
            """

            # 添加K线图（如果存在）
            if chart_file:
                html += f"""
                <div class="chart-container">
                    <img src="{chart_file}" alt="{stock_display} K线图与布林线">
                </div>
                """
            else:
                html += """
                <div class="chart-container">
                    <p style="color: #7f8c8d;">K线图生成失败或不可用</p>
                </div>
                """

            html += f"""
                <h4>📋 最近 {len(sequences)} 段连续触碰:</h4>
                <table>
                    <tr>
                        <th>序号</th>
                        <th>类型</th>
                        <th>连续次数</th>
                        <th>起始日期</th>
                        <th>结束日期</th>
                        <th>间隔天数</th>
                    </tr>
            """

            for i, seq in enumerate(sequences, 1):
                touch_type_text = '上轨' if seq['touch_type'] == 'UPPER' else '下轨'
                html += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{touch_type_text}</td>
                        <td>{seq['count']}</td>
                        <td>{seq['start_date']}</td>
                        <td>{seq['end_date']}</td>
                        <td>{seq['gap_days'] if seq['gap_days'] is not None else '-'}</td>
                    </tr>
                """

            html += """
                </table>
            </div>
            """

    # 添加页脚
    html += f"""
        <div class="footer">
            <p>本报告由股票分析系统自动生成</p>
            <p>分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """

    return html



def analyze_stock(stock_code, limit_days=365, top_n=3, send_email=False, save_html=False, output_dir='.', recipients=None):
    """
    分析指定股票的连续触碰情况

    参数:
        stock_code: 股票代码
        limit_days: 查询最近多少天的记录，默认365天
        top_n: 显示最近几段连续触碰，默认3段
        send_email: 是否发送邮件报告，默认False
        save_html: 是否保存HTML报告到文件，默认False
        output_dir: HTML文件输出目录，默认为当前目录
        recipients: 收件人邮箱列表，如果为None则使用EMAIL_CONFIG中的配置

    返回:
        dict: 分析结果
    """
    print(f"\n{'='*70}")
    print(f"【连续触碰BOLL线分析】股票代码: {stock_code}")
    print(f"{'='*70}")

    # 获取触碰数据
    df = get_touch_data_from_db(stock_code, limit_days)

    if df is None or df.empty:
        print(f"⚠ 未找到股票 {stock_code} 的触碰记录")
        return None

    print(f"✓ 查询到 {len(df)} 条触碰记录")
    print(f"  日期范围: {df['trade_date'].min()} 至 {df['trade_date'].max()}")

    # 分析连续触碰
    sequences = analyze_consecutive_touches(df)

    if not sequences:
        print(f"⚠ 未发现连续触碰序列")
        return None

    print(f"\n📊 分析结果（最近 {min(top_n, len(sequences))} 段连续触碰）：")
    print(f"{'='*70}")

    # 显示最近N段连续触碰（倒序，最新的在前）
    recent_sequences = sequences[-top_n:][::-1]

    result = {
        'stock_code': stock_code,
        'total_sequences': len(sequences),
        'sequences': recent_sequences
    }

    for i, seq in enumerate(recent_sequences, 1):
        print(f"\n【第 {i} 段连续触碰】")
        print(format_consecutive_info(seq))

    # 统计信息
    print(f"\n{'='*70}")
    print(f"【统计摘要】")
    print(f"  总计连续触碰段数: {len(sequences)}")

    # 按类型统计
    upper_count = sum(1 for s in sequences if s['touch_type'] == 'UPPER')
    lower_count = sum(1 for s in sequences if s['touch_type'] == 'LOWER')
    print(f"  上轨触碰段数: {upper_count}")
    print(f"  下轨触碰段数: {lower_count}")

    # 最长连续触碰
    longest = max(sequences, key=lambda x: x['count'])
    longest_type = '上轨' if longest['touch_type'] == 'UPPER' else '下轨'
    print(f"  最长连续触碰: {longest['count']} 次（{longest_type}，{longest['start_date']} 至 {longest['end_date']}）")

    # 平均间隔
    gaps = [s['gap_days'] for s in sequences if s['gap_days'] is not None]
    if gaps:
        avg_gap = sum(gaps) / len(gaps)
        print(f"  平均间隔天数: {avg_gap:.1f} 天")

    print(f"{'='*70}\n")

    # 发送邮件报告
    if send_email:
        email_recipients = recipients if recipients else EMAIL_CONFIG.get('recipients', [])
        send_email_report(stock_code, result, email_recipients)

    # 保存HTML报告到文件
    if save_html:
        save_html_report(stock_code, result, output_dir)

    return result


def batch_analyze_stocks(stock_list, limit_days=365, top_n=3, send_email=False, save_html=False, output_dir='.', recipients=None):
    """
    批量分析多只股票的连续触碰情况

    参数:
        stock_list: 股票代码列表
        limit_days: 查询最近多少天的记录
        top_n: 每只股票显示最近几段连续触碰
        send_email: 是否发送邮件报告，默认False
        save_html: 是否保存HTML报告到文件，默认False
        output_dir: HTML文件输出目录，默认为当前目录
        recipients: 收件人邮箱列表

    返回:
        dict: 所有股票的分析结果
    """
    print(f"\n{'#'*70}")
    print(f"# 批量连续触碰分析")
    print(f"# 分析股票数量: {len(stock_list)}")
    print(f"# 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")

    results = {}

    for stock_code in stock_list:
        try:
            result = analyze_stock(stock_code, limit_days, top_n, send_email=False, save_html=False)
            results[stock_code] = result
        except Exception as e:
            print(f"✗ 分析股票 {stock_code} 时出错: {e}")
            results[stock_code] = None

    # 汇总统计
    print(f"\n{'='*70}")
    print(f"【批量分析汇总】")
    print(f"{'='*70}")
    print(f"总计分析: {len(stock_list)} 只股票")

    success_count = sum(1 for r in results.values() if r is not None)
    print(f"成功: {success_count} 只")
    print(f"失败或无数据: {len(stock_list) - success_count} 只")

    # 找出连续触碰次数最多的股票
    all_sequences = []
    for stock_code, result in results.items():
        if result and 'sequences' in result:
            for seq in result['sequences']:
                all_sequences.append({
                    'stock_code': stock_code,
                    'count': seq['count'],
                    'touch_type': seq['touch_type'],
                    'start_date': seq['start_date'],
                    'end_date': seq['end_date']
                })

    if all_sequences:
        longest = max(all_sequences, key=lambda x: x['count'])
        longest_type = '上轨' if longest['touch_type'] == 'UPPER' else '下轨'
        print(f"\n最长连续触碰: {longest['stock_code']} - {longest['count']}次{longest_type}")
        print(f"  时间: {longest['start_date']} 至 {longest['end_date']}")

    print(f"{'='*70}\n")

    # 发送邮件报告
    if send_email:
        email_recipients = recipients if recipients else EMAIL_CONFIG.get('recipients', [])
        send_batch_email_report(results, email_recipients)

    # 保存HTML报告到文件
    if save_html:
        save_batch_html_report(results, output_dir)

    return results


# ==================== 命令行入口 ====================

if __name__ == '__main__':
    # 检查命令行参数
    send_email = '--email' in sys.argv or '--mail' in sys.argv
    save_html = '--html' in sys.argv

    # 获取输出目录（可选）
    output_dir = './StockAnalysisReports'
    for i, arg in enumerate(sys.argv):
        if arg == '--output' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            break

    if send_email:
        # 配置收件人邮箱（请在使用前修改）
        EMAIL_CONFIG['recipients'] = ['recipient@example.com']  # 修改为实际收件人邮箱
        print("✓ 已启用邮件发送功能")

    if save_html:
        print(f"✓ 已启用HTML文件保存功能 (输出目录: {output_dir})")

    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        # 从命令行参数读取股票代码
        stock_codes = sys.argv[1].split(',')
        print("\n从命令行读取股票代码:", stock_codes)

        if len(stock_codes) == 1:
            # 单只股票分析
            analyze_stock(stock_codes[0], limit_days=365, top_n=3,
                        send_email=send_email, save_html=save_html, output_dir=output_dir)
        else:
            # 批量分析
            batch_analyze_stocks(stock_codes, limit_days=365, top_n=3,
                              send_email=send_email, save_html=save_html, output_dir=output_dir)
    else:
        # 默认运行示例
        print("\n使用方法:")
        print("  python analyzeConsecutiveBollTouch.py 600036.XSHG")
        print("  python analyzeConsecutiveBollTouch.py 600036.XSHG,600519.XSHG,000333.XSHE")
        print("  python analyzeConsecutiveBollTouch.py 600036.XSHG --email  # 发送邮件报告")
        print("  python analyzeConsecutiveBollTouch.py 600036.XSHG --html  # 保存HTML报告")
        print("  python analyzeConsecutiveBollTouch.py 600036.XSHG,600519.XSHG --html --output ./reports  # 批量分析并保存HTML")
        print("\n提示: 发送邮件前请在 EMAIL_CONFIG 中配置收件人邮箱")
        print("\n使用默认配置运行示例...\n")

        # 示例股票列表
        stock_codes = ['600036.XSHG', '600941.XSHG', '512400.XSHG','513880.XSHG', '518880.XSHG','000333.XSHE', '000858.XSHE']

        # 批量分析（不发送邮件，保存HTML）
        results = batch_analyze_stocks(stock_codes, limit_days=365, top_n=3,
                                     send_email=False, save_html=True, output_dir=output_dir)

 