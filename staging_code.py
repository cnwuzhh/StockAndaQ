#股市行情数据获取和作图 -2
from  Ashare import *          #股票数据库    https://github.com/mpquant/Ashare
from  MyTT import *            #myTT麦语言工具函数指标库  https://github.com/mpquant/MyTT
    
# 证券代码兼容多种格式 通达信，同花顺，聚宽
# sh000001 (000001.XSHG)    sz399006 (399006.XSHE)   sh600519 ( 600519.XSHG ) 

df=get_price('600036.XSHG',frequency='1d',count=120)      #默认获取今天往前120天的日线行情
print('上证指数日线行情\n',df.tail(5))

#-------有数据了，下面开始正题 -------------
CLOSE=df.close.values;         OPEN=df.open.values           #基础数据定义，只要传入的是序列都可以  Close=df.close.values 
HIGH=df.high.values;           LOW=df.low.values             #例如  CLOSE=list(df.close) 都是一样
VOLUME=df.volume.values;       

MA5=MA(CLOSE,5)                                #获取5日均线序列
MA10=MA(CLOSE,10)                              #获取10日均线序列
up,mid,lower=BOLL(CLOSE)                       #获取布林带指标数据

# 将BOLL数据添加到DataFrame中
df['BOLL_UPPER']=up
df['BOLL_MIDDLE']=mid
df['BOLL_LOWER']=lower




#-------------------------检测BOLL线触碰函数-----------------------------------------------------------------
def check_boll_touch(df, lookback_days=1):
    """
    检测指定天数内是否触碰BOLL线

    参数:
        df: 包含BOLL指标的DataFrame
        lookback_days: 检测最近几天，默认为1(昨天)

    返回:
        touched: bool, 是否触碰BOLL线
        touch_info: dict, 触碰信息 {日期: 触碰的BOLL线类型}
    """
    touched = False
    touch_info = {}

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
            touch_info[date_str] = '上轨(UPPER)'
            print(f"【BOLL触碰】{date_str}: 最高价 {high:.2f} 触碰布林线上轨 {upper:.2f}")

        # 检测是否触碰下轨（最低价 <= 下轨）
        elif low <= lower:
            touched = True
            touch_info[date_str] = '下轨(LOWER)'
            print(f"【BOLL触碰】{date_str}: 最低价 {low:.2f} 触碰布林线下轨 {lower:.2f}")

    return touched, touch_info


#-------------------------执行检测-----------------------------------------------------------------
print("\n" + "="*60)
print("检测昨天是否触碰BOLL线")
print("="*60)

touched, touch_info = check_boll_touch(df, lookback_days=1)

if not touched:
    print("昨天未触碰BOLL线")
else:
    print("触碰详情:", touch_info)

print("="*60 + "\n")


#-------------------------K线图绘制函数-----------------------------------------------------------------
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
    try:
        import mplfinance as mpf
        import pandas as pd

        # 准备数据，确保索引为 DatetimeIndex
        data = df[['open','high','low','close','volume','BOLL_UPPER','BOLL_MIDDLE','BOLL_LOWER']].copy()
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
            mpf.plot(data.tail(days), type='candle', mav=(5,10), volume=True,
                     addplot=add_plots, style='yahoo',
                     title=title, figsize=(15,8))
        except Exception:
            out_file = f'{stock_code}_kline.png'
            mpf.plot(data.tail(days), type='candle', mav=(5,10), volume=True, 
                     addplot=add_plots, style='yahoo',
                     title=title, figsize=(15,8), savefig=out_file)
            print(f"绘图交互显示失败或在无 GUI 环境，已将 K 线图保存为 {out_file}")
    except ImportError:
        print("绘制K线图需要安装 mplfinance：运行 'pip install mplfinance' 后可获得更好显示。")


#-------------------------执行绘图-----------------------------------------------------------------
plot_kline_with_boll(df, '600036', days=120)
