#!/usr/bin/env python3
"""
从文本文件中提取时间范围并输出 JSON 文件。

python <脚本名> <文本文件夹> <JSON保存文件夹>

{
  "start_date": "2020-07-01",
  "end_date": "2020-08-31"
}

"""

import re
import json
import argparse
import os
import sys
import logging
from datetime import datetime
from typing import List, Optional, Dict


# ------------------- 日志配置 -------------------
def setup_logging(verbose: bool = False) -> None:
    """配置日志输出格式和级别。"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


logger = logging.getLogger("time_extractor")


# ------------------- 日期解析核心 -------------------
# 使用 (?<!\d) 和 (?!\d) 作为数字边界，确保日期前后不是数字，避免误匹配长数字串
DATE_PATTERNS = [
    (re.compile(r'(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)'), '%Y-%m-%d'),
    (re.compile(r'(?<!\d)(\d{4})/(\d{1,2})/(\d{1,2})(?!\d)'), '%Y/%m/%d'),
    (re.compile(r'(?<!\d)(\d{1,2})-(\d{1,2})-(\d{4})(?!\d)'), '%m-%d-%Y'),
    (re.compile(r'(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)'), '%m/%d/%Y'),
    (re.compile(r'(?<!\d)(\d{4})年(\d{1,2})月(\d{1,2})日(?!\d)'), '%Y年%m月%d日'),
    (re.compile(r'(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)'), '%d.%m.%Y'),
]


def parse_date(date_str: str) -> Optional[datetime]:
    """尝试将字符串解析为日期对象，支持多种格式。"""
    logger.debug(f"尝试解析日期字符串: '{date_str}'")
    for pattern, fmt in DATE_PATTERNS:
        match = pattern.search(date_str)
        if match:
            if fmt == '%Y年%m月%d日':
                year, month, day = match.groups()
                date_str_fixed = f"{year}年{int(month):02d}月{int(day):02d}日"
            else:
                date_str_fixed = match.group(0)
            try:
                dt = datetime.strptime(date_str_fixed, fmt)
                logger.debug(f"解析成功: '{date_str}' -> {dt.strftime('%Y-%m-%d')} (格式: {fmt})")
                return dt
            except ValueError as e:
                logger.debug(f"格式匹配但解析失败: '{date_str_fixed}' ({fmt}) - {e}")
                continue
    logger.debug(f"无法解析日期: '{date_str}'")
    return None


def extract_dates(text: str) -> List[datetime]:
    """从文本中提取所有日期，按出现顺序返回（已去重并排序）。"""
    logger.info("开始从文本中提取日期...")
    dates = []
    seen = set()
    line_count = 0

    for line in text.splitlines():
        line_count += 1
        logger.debug(f"处理第 {line_count} 行: {line[:50]}...")
        for pattern, _ in DATE_PATTERNS:
            matches = list(pattern.finditer(line))
            if matches:
                logger.debug(f"在第 {line_count} 行发现 {len(matches)} 个可能的日期匹配")
            for match in matches:
                date_str = match.group(0)
                dt = parse_date(date_str)
                if dt and date_str not in seen:
                    seen.add(date_str)
                    dates.append(dt)
                    logger.debug(f"接受日期: {dt.strftime('%Y-%m-%d')} (原始字符串: '{date_str}')")
                elif dt:
                    logger.debug(f"重复日期已跳过: {date_str}")

    logger.info(f"共提取到 {len(dates)} 个有效日期")
    if dates:
        logger.debug(f"提取的日期列表: {[d.strftime('%Y-%m-%d') for d in dates]}")
    return dates


# ------------------- 时间范围提取 -------------------
def extract_time_range(text: str) -> Dict[str, str]:
    """
    从文本中提取时间范围。

    返回格式：{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
    若提取到的日期少于两个，则抛出 ValueError。
    """
    dates = extract_dates(text)
    if len(dates) < 2:
        logger.error(f"日期数量不足：需要至少2个日期，实际只有 {len(dates)} 个")
        raise ValueError("文本中至少需要两个日期才能确定时间范围。")

    start = min(dates)
    end = max(dates)
    logger.info(f"确定时间范围: {start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}")
    return {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d")
    }


# ------------------- 文件处理与导出 -------------------
def process_txt_file(input_path: str, output_dir: str = ".", output_name: Optional[str] = None) -> str:
    """
    处理单个 TXT 文件，提取时间范围并保存为 JSON。

    Args:
        input_path: 输入 TXT 文件路径
        output_dir: 输出目录，默认为当前目录
        output_name: 输出文件名（不含扩展名），默认使用输入文件名

    Returns:
        生成的 JSON 文件完整路径
    """
    logger.info(f"开始处理文件: {input_path}")
    logger.debug(f"输出目录: {output_dir}")

    # 检查输入文件是否存在
    if not os.path.isfile(input_path):
        logger.error(f"输入文件不存在: {input_path}")
        raise FileNotFoundError(f"文件不存在: {input_path}")

    # 读取文本
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.info(f"成功读取文件，大小: {len(text)} 字符")
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        raise

    # 提取时间范围
    try:
        time_range = extract_time_range(text)
        logger.debug(f"提取结果: {time_range}")
    except Exception as e:
        logger.error(f"提取时间范围失败: {e}")
        raise

    # 准备输出路径
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    out_name = output_name if output_name else base_name
    out_path = os.path.join(output_dir, f"{out_name}.json")

    logger.debug(f"输出文件路径: {out_path}")

    # 写入 JSON
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(time_range, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 文件已保存: {out_path}")
    except Exception as e:
        logger.error(f"写入 JSON 文件失败: {e}")
        raise

    return out_path


# ------------------- 命令行接口 -------------------
def main():
    parser = argparse.ArgumentParser(
        description="从 TXT 文件中提取时间范围并输出为 JSON 文件。支持批处理文件夹内所有 .txt 文件。"
    )
    parser.add_argument("input_dir", help="包含 TXT 文件的输入文件夹路径")
    parser.add_argument("output_dir", help="JSON 文件保存文件夹路径")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="输出详细的调试日志（DEBUG 级别）")
    args = parser.parse_args()

    # 配置日志
    setup_logging(args.verbose)

    # 检查输入文件夹是否存在
    if not os.path.isdir(args.input_dir):
        logger.error(f"输入文件夹不存在: {args.input_dir}")
        print(f"❌ 错误：输入文件夹不存在: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    # 确保输出文件夹存在
    os.makedirs(args.output_dir, exist_ok=True)

    # 收集所有 .txt 文件
    txt_files = [f for f in os.listdir(args.input_dir) if f.lower().endswith('.txt')]
    if not txt_files:
        logger.warning(f"在输入文件夹中未找到任何 .txt 文件: {args.input_dir}")
        print(f"⚠️ 警告：在 {args.input_dir} 中未找到 .txt 文件。")
        return

    logger.info(f"找到 {len(txt_files)} 个 TXT 文件待处理")

    success_count = 0
    fail_count = 0

    for filename in txt_files:
        input_path = os.path.join(args.input_dir, filename)
        try:
            output_path = process_txt_file(input_path, args.output_dir)
            print(f"✅ {filename} -> {os.path.basename(output_path)}")
            success_count += 1
        except Exception as e:
            logger.error(f"处理文件 {filename} 时出错: {e}")
            print(f"❌ {filename} 处理失败: {e}", file=sys.stderr)
            fail_count += 1

    # 输出统计信息
    print("\n===== 处理完成 =====")
    print(f"成功: {success_count} 个文件")
    print(f"失败: {fail_count} 个文件")
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()