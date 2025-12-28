-- 股票代码与名称关联表
-- 用于存储股票代码与股票名称的映射关系

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

-- 示例数据插入
INSERT INTO stock_info (stock_code, stock_name, market, code_prefix, industry, sector) VALUES
-- 上海股票示例
('600036.XSHG', '招商银行', 'XSHG', '600036', '银行', '金融'),
('600519.XSHG', '贵州茅台', 'XSHG', '600519', '白酒', '消费'),
('600941.XSHG', '中国移动', 'XSHG', '600941', '通信', '通信'),
('513880.XSHG', '证券ETF', 'XSHG', '513880', 'ETF', '基金'),
('518880.XSHG', '医疗ETF', 'XSHG', '518880', 'ETF', '基金'),

-- 深圳股票示例
('000333.XSHE', '美的集团', 'XSHE', '000333', '家电', '消费'),
('000858.XSHE', '五粮液', 'XSHE', '000858', '白酒', '消费'),

-- 指数示例
('000001.XSHG', '上证指数', 'XSHG', '000001', '指数', '指数'),
('399006.XSHE', '创业板指', 'XSHE', '399006', '指数', '指数')

ON DUPLICATE KEY UPDATE
    stock_name = VALUES(stock_name),
    updated_at = CURRENT_TIMESTAMP;

-- 查询示例
-- 1. 根据股票代码查询名称
-- SELECT stock_name FROM stock_info WHERE stock_code = '600036.XSHG';

-- 2. 根据股票名称模糊查询
-- SELECT stock_code, stock_name FROM stock_info WHERE stock_name LIKE '%银行%';

-- 3. 查询某个市场的所有股票
-- SELECT stock_code, stock_name FROM stock_info WHERE market = 'XSHG' AND is_active = 1;

-- 4. 更新股票名称
-- UPDATE stock_info SET stock_name = '新名称' WHERE stock_code = '600036.XSHG';

-- 5. 批量导入股票数据的实用查询
-- SELECT CONCAT(stock_code, ' - ', stock_name) as stock_display FROM stock_info WHERE is_active = 1;
