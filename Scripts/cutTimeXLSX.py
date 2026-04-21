import re
import json
import argparse
from pathlib import Path
import pandas as pd

"""
    CLI用法为 python <脚本名> <Excel文件夹路径> <时间要求JSON文件夹> <提取后表格保存文件夹>
    时间要求JSON文件夹内只包含一个JSON文件，形如：
    {
    "start_date": "2020-07-01",
    "end_date": "2020-08-31"
    }
"""
def identify_date_column(df: pd.DataFrame, sample_rows: int = 100) -> str | None:
    """
    智能识别 DataFrame 中的日期列。
    1. 优先根据列名正则匹配。
    2. 若匹配失败，尝试内容转换（抽样检测）。
    """
    # 正则匹配列名
    pattern = re.compile(r'(?i)(date|time|日期|时间)')
    for col in df.columns:
        if pattern.search(str(col)):
            return col

    # 内容推断：对每列尝试转换抽样行，检查成功率
    sample = df.head(sample_rows)
    best_col = None
    best_ratio = 0.0

    for col in df.columns:
        # 跳过全数值列（可能是时间戳），但保留 object 类型列
        if sample[col].dtype.kind in 'iufc':  # 整数、浮点数、复数
            # 数值列可能是时间戳，也尝试转换
            pass
        try:
            converted = pd.to_datetime(sample[col], errors='coerce')
            valid_ratio = converted.notna().mean()
            if valid_ratio > best_ratio:
                best_ratio = valid_ratio
                best_col = col
        except (ValueError, TypeError):
            continue

    if best_ratio >= 0.8:  # 80% 以上成功转换则采纳
        return best_col
    return None


def filter_by_date(df: pd.DataFrame, date_col: str, start_date: str, end_date: str) -> pd.DataFrame:
    """根据日期列过滤 DataFrame，保留位于 [start_date, end_date] 内的行。"""
    # 统一转换为 datetime
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    mask = (df[date_col] >= start) & (df[date_col] <= end)
    return df.loc[mask].copy()


def process_excel(input_path: Path, output_path: Path, start_date: str, end_date: str) -> None:
    """处理单个 Excel 文件：读取 → 识别日期列 → 过滤 → 保存。"""
    # 读取所有 sheet
    with pd.ExcelFile(input_path) as xls:
        sheet_names = xls.sheet_names

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet in sheet_names:
            df = pd.read_excel(input_path, sheet_name=sheet)
            if df.empty:
                df.to_excel(writer, sheet_name=sheet, index=False)
                continue

            date_col = identify_date_column(df)
            if date_col is None:
                print(f"警告：文件 '{input_path.name}' 工作表 '{sheet}' 未找到日期列，将原样保存。")
                df.to_excel(writer, sheet_name=sheet, index=False)
                continue

            print(f"文件 '{input_path.name}' 工作表 '{sheet}' 识别日期列：'{date_col}'")
            filtered_df = filter_by_date(df, date_col, start_date, end_date)
            filtered_df.to_excel(writer, sheet_name=sheet, index=False)


def load_date_config(json_folder: Path) -> tuple[str, str]:
    """从指定文件夹中读取唯一的 JSON 文件，提取 start_date 和 end_date。"""
    json_files = list(json_folder.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"在 '{json_folder}' 中未找到 JSON 文件。")
    if len(json_files) > 1:
        raise ValueError(f"在 '{json_folder}' 中找到多个 JSON 文件，但要求只包含一个。")

    config_path = json_files[0]
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    start_date = config.get("start_date")
    end_date = config.get("end_date")
    if start_date is None or end_date is None:
        raise ValueError(f"JSON 文件必须包含 'start_date' 和 'end_date' 字段。")

    return start_date, end_date


def main():
    parser = argparse.ArgumentParser(
        description='批量根据日期范围过滤 Excel 表格，自动识别日期列。'
    )
    parser.add_argument('excel_folder', type=str, help='存放待处理 Excel 文件的文件夹路径')
    parser.add_argument('json_folder', type=str, help='存放日期范围 JSON 配置文件的文件夹路径（仅一个 JSON 文件）')
    parser.add_argument('output_folder', type=str, help='处理后 Excel 文件的保存文件夹路径')
    args = parser.parse_args()

    excel_folder = Path(args.excel_folder)
    json_folder = Path(args.json_folder)
    output_folder = Path(args.output_folder)

    if not excel_folder.exists():
        raise FileNotFoundError(f"Excel 文件夹不存在：{excel_folder}")
    if not json_folder.exists():
        raise FileNotFoundError(f"JSON 文件夹不存在：{json_folder}")

    # 创建输出文件夹（如果不存在）
    output_folder.mkdir(parents=True, exist_ok=True)

    # 加载日期范围
    try:
        start_date, end_date = load_date_config(json_folder)
        print(f"日期范围：{start_date} 至 {end_date}")
    except Exception as e:
        print(f"读取 JSON 配置失败：{e}")
        raise

    # 查找所有 Excel 文件（支持常见扩展名）
    excel_extensions = ['*.xlsx', '*.xls', '*.xlsm']
    excel_files = []
    for ext in excel_extensions:
        excel_files.extend(excel_folder.glob(ext))
    # 避免重复（例如大小写不同，但 Path.glob 默认区分大小写，Windows 不敏感，无妨）
    excel_files = list(set(excel_files))

    if not excel_files:
        print(f"警告：在 '{excel_folder}' 中未找到任何 Excel 文件。")
        return

    # 处理每个 Excel 文件
    for input_path in excel_files:
        output_path = output_folder / input_path.name
        try:
            print(f"正在处理文件：{input_path}")
            process_excel(input_path, output_path, start_date, end_date)
        except Exception as e:
            print(f"处理文件 '{input_path}' 时出错：{e}")

    print(f"所有文件处理完成，结果保存在：{output_folder}")


if __name__ == '__main__':
    main()