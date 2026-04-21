import argparse
import json
import os
from pathlib import Path
"""
 python <脚本名> <输入文件夹> <JSON模板保存文件夹>
"""

try:
    import pandas as pd
except ImportError:
    print("错误：需要安装 pandas 和 openpyxl，请执行: pip install pandas openpyxl")
    exit(1)


def get_excel_columns(file_path):
    """读取 Excel 第一个工作表的列名列表"""
    try:
        # 只读取第一行，快速获取列名
        df = pd.read_excel(file_path, nrows=1)
        return df.columns.tolist()
    except Exception as e:
        print(f"警告：无法读取文件 {file_path}，错误: {e}")
        return None


def create_template(columns):
    """根据列名生成模板字典"""
    return {col: "" for col in columns}


def main():
    parser = argparse.ArgumentParser(
        description="从文件夹中提取所有 xlsx 文件的列名，生成 JSON 模板文件"
    )
    parser.add_argument("input_dir", help="包含 xlsx 文件的输入文件夹路径")
    parser.add_argument("output_dir", help="JSON 模板文件保存文件夹路径")
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)

    if not input_path.is_dir():
        print(f"错误：输入文件夹不存在或不是目录: {input_path}")
        exit(1)

    # 创建输出文件夹（如不存在）
    output_path.mkdir(parents=True, exist_ok=True)

    # 查找所有 .xlsx 文件（不区分大小写）
    xlsx_files = list(input_path.glob("*.xlsx")) + list(input_path.glob("*.XLSX"))
    if not xlsx_files:
        print(f"警告：在 {input_path} 中未找到任何 .xlsx 文件")
        return

    generated_count = 0
    for file_path in xlsx_files:
        print(f"正在处理: {file_path.name}")
        columns = get_excel_columns(file_path)
        if columns is None:
            continue

        template = create_template(columns)
        # 生成输出文件名，例如 "原文件名_template.json"
        output_filename = f"{file_path.stem}_template.json"
        output_file = output_path / output_filename

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            print(f"  已生成模板: {output_file}")
            generated_count += 1
        except Exception as e:
            print(f"  错误：保存文件失败 {output_file}，原因: {e}")

    print(f"\n完成！共处理 {len(xlsx_files)} 个文件，成功生成 {generated_count} 个模板。")


if __name__ == "__main__":
    main()