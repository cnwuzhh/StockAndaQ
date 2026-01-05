"""
仓位管理系统 - 快速启动脚本
根据环境自动选择合适的版本运行
"""

import sys
import os

def check_dependencies():
    """检查可用的依赖库"""
    available = []

    # 检查pymysql
    try:
        import pymysql
        available.append('pymysql')
    except ImportError:
        pass

    # 检查pandas
    try:
        import pandas
        available.append('pandas')
    except ImportError:
        pass

    # 检查xlrd
    try:
        import xlrd
        available.append('xlrd')
    except ImportError:
        pass

    # 检查openpyxl
    try:
        import openpyxl
        available.append('openpyxl')
    except ImportError:
        pass

    return available


def main():
    """主函数"""
    print("=" * 80)
    print("仓位管理系统 - 自动启动")
    print("=" * 80)

    # 检查依赖
    deps = check_dependencies()

    print(f"\n检测到的依赖库: {', '.join(deps) if deps else '无'}")

    # 根据依赖选择版本
    if 'pymysql' in deps and 'pandas' in deps and 'xlrd' in deps:
        print("\n使用完整版本 (position_management.py)")
        print("支持: Excel文件读取 + 数据库操作\n")
        try:
            import position_management
            position_management.main()
        except Exception as e:
            print(f"运行失败: {e}")
            print("\n尝试使用独立版本...")
            run_standalone()

    elif 'pymysql' in deps:
        print("\n使用独立版本 (position_management_standalone.py)")
        print("支持: 数据库操作\n")
        run_standalone()

    else:
        print("\n使用演示版本 (position_management_pure_demo.py)")
        print("支持: 示例数据演示（无数据库）\n")
        run_demo()


def run_standalone():
    """运行独立版本"""
    try:
        import position_management_standalone
        position_management_standalone.demo()
    except Exception as e:
        print(f"运行失败: {e}")
        print("\n切换到演示版本...")
        run_demo()


def run_demo():
    """运行演示版本"""
    try:
        import position_management_pure_demo
        position_management_pure_demo.demo()
    except Exception as e:
        print(f"运行失败: {e}")


if __name__ == '__main__':
    main()
