import sys
import os
import pandas as pd
from pathlib import Path
"""
python extract_columns.py <数据文件夹> <模板文件夹> <输出文件夹>
"""


def find_template_file(template_dir):
    """
    在模板文件夹中查找唯一的Excel模板文件。
    返回完整路径；若没有或存在多个则报错退出。
    """
    template_dir = Path(template_dir)
    if not template_dir.is_dir():
        print(f"❌ 模板文件夹不存在: {template_dir}")
        sys.exit(1)

    # 支持的Excel扩展名
    excel_exts = {'.xlsx', '.xls'}
    template_files = [f for f in template_dir.iterdir() 
                      if f.is_file() and f.suffix.lower() in excel_exts]

    if len(template_files) == 0:
        print(f"❌ 模板文件夹中没有找到Excel文件（.xlsx/.xls）")
        sys.exit(1)
    elif len(template_files) > 1:
        print(f"❌ 模板文件夹中存在多个Excel文件，请只保留一个模板文件：")
        for f in template_files:
            print(f"   - {f.name}")
        sys.exit(1)

    return template_files[0]

def extract_columns_from_file(data_path, template_path, output_dir):
    """
    从单个数据文件中提取模板指定的列，保存到输出文件夹。
    """
    # ---------- 1. 读取模板文件列名 ----------
    try:
        template_df = pd.read_excel(template_path, header=0, nrows=1)
    except Exception as e:
        print(f"❌ 读取模板文件失败: {e}")
        return False

    # 清理列名
    raw_columns = template_df.columns.tolist()
    template_columns = []
    seen = set()
    for col in raw_columns:
        col_clean = str(col).strip()
        if col_clean and col_clean not in seen:
            template_columns.append(col_clean)
            seen.add(col_clean)

    if not template_columns:
        print(f"⚠️ 模板文件中没有有效的列名，跳过文件: {data_path}")
        return False

    # ---------- 2. 读取数据文件列名 ----------
    try:
        data_head = pd.read_excel(data_path, header=0, nrows=0)
    except Exception as e:
        print(f"❌ 读取数据文件失败 {data_path}: {e}")
        return False

    data_columns = [str(col).strip() for col in data_head.columns]

    # ---------- 3. 匹配列 ----------
    extract_cols = [col for col in template_columns if col in data_columns]
    missing_cols = [col for col in template_columns if col not in data_columns]

    if missing_cols:
        print(f"⚠️ 文件 {Path(data_path).name} 中缺少以下模板列，已跳过: {missing_cols}")

    if not extract_cols:
        print(f"❌ 文件 {Path(data_path).name} 中没有匹配的列，跳过。")
        return False

    # ---------- 4. 读取数据并提取列 ----------
    try:
        df = pd.read_excel(data_path, header=0, usecols=extract_cols)
    except Exception as e:
        print(f"❌ 读取数据内容失败 {data_path}: {e}")
        return False

    # ---------- 5. 生成输出路径 ----------
    data_path_obj = Path(data_path)
    output_filename = f"{data_path_obj.stem}_Extracted{data_path_obj.suffix}"
    output_path = Path(output_dir) / output_filename

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_excel(output_path, index=False, engine='openpyxl')
        print(f"✅ 成功处理: {data_path_obj.name} -> {output_filename} (提取 {len(extract_cols)} 列)")
        return True
    except Exception as e:
        print(f"❌ 保存文件失败 {output_path}: {e}")
        return False

def process_folder(data_dir, template_path, output_dir):
    """
    遍历数据文件夹，处理所有Excel文件。
    """
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        print(f"❌ 数据文件夹不存在: {data_dir}")
        sys.exit(1)

    # 支持的Excel扩展名
    excel_exts = {'.xlsx', '.xls'}
    data_files = [f for f in data_dir.iterdir() 
                  if f.is_file() and f.suffix.lower() in excel_exts]

    if not data_files:
        print(f"⚠️ 数据文件夹中没有Excel文件。")
        return

    print(f"找到 {len(data_files)} 个Excel文件待处理。\n")

    success_count = 0
    for data_file in data_files:
        if extract_columns_from_file(data_file, template_path, output_dir):
            success_count += 1

    print(f"\n处理完成: 成功 {success_count} 个，失败/跳过 {len(data_files) - success_count} 个。")

def main():
    if len(sys.argv) != 4:
        print("用法: python extract_columns.py <数据文件夹> <模板文件夹> <输出文件夹>")
        print("示例: python extract_columns.py ./data ./template ./output")
        sys.exit(1)

    data_dir = sys.argv[1]
    template_dir = sys.argv[2]
    output_dir = sys.argv[3]

    # 查找唯一的模板文件
    template_path = find_template_file(template_dir)
    print(f"📄 使用模板文件: {template_path.name}\n")

    # 批量处理
    process_folder(data_dir, template_path, output_dir)

if __name__ == "__main__":
    main()