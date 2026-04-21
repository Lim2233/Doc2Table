#!/usr/bin/env python3
"""
通用 JSON 重构脚本 - 基于模板的大模型字段提取（增强版）

用法：
    python extract_by_template.py <输入文件夹> <模板文件夹> <输出文件夹>

参数说明：
    - 输入文件夹：存放待处理的 JSON 文件（支持多个文件，每个文件可含单个或多个对象）。
    - 模板文件夹：存放至多一个 JSON 模板文件，用于定义输出字段。
    - 输出文件夹：保存提取后的结构化 JSON 文件。
"""

import json
import sys
import os
import glob
from typing import List, Dict, Optional, Any
from APIKey import DASHSCOPE_API_KEY

try:
    import dashscope
    from dashscope import Generation
except ImportError:
    print("错误：请先安装 dashscope：pip install dashscope", file=sys.stderr)
    sys.exit(1)

# ---------- API 配置 ----------
def get_api_key() -> str:
    
    key = DASHSCOPE_API_KEY
    if not key:
        key = input("请输入 DashScope API Key: ").strip()
        if not key:
            print("未提供 API Key，程序退出。", file=sys.stderr)
            sys.exit(1)
    return key

dashscope.api_key = get_api_key()
MODEL_NAME = "qwen-plus"

# ---------- 中国省份列表（用于后处理补全大洲）----------
CHINESE_PROVINCES = {
    "北京市", "天津市", "上海市", "重庆市",
    "河北省", "山西省", "辽宁省", "吉林省", "黑龙江省",
    "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省",
    "河南省", "湖北省", "湖南省", "广东省", "海南省",
    "四川省", "贵州省", "云南省", "陕西省", "甘肃省", "青海省", "台湾省",
    "内蒙古自治区", "广西壮族自治区", "西藏自治区", "宁夏回族自治区", "新疆维吾尔自治区",
    "香港特别行政区", "澳门特别行政区"
}

# ---------- 模板处理 ----------
def load_template(template_dir: str) -> List[str]:
    """
    从模板文件夹中读取唯一的 JSON 模板文件，返回字段列表。
    若无模板文件则报错退出。
    """
    json_files = glob.glob(os.path.join(template_dir, "*.json"))
    if len(json_files) == 0:
        print("错误：模板文件夹中没有 JSON 模板文件。", file=sys.stderr)
        sys.exit(1)
    if len(json_files) > 1:
        print("警告：模板文件夹中有多个 JSON 文件，将使用第一个。", file=sys.stderr)

    template_path = json_files[0]
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = json.load(f)
    except Exception as e:
        print(f"错误：无法解析模板文件 {template_path}：{e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(template, dict):
        print("错误：模板文件必须是 JSON 对象。", file=sys.stderr)
        sys.exit(1)

    fields = list(template.keys())
    if not fields:
        print("错误：模板对象没有字段。", file=sys.stderr)
        sys.exit(1)

    print(f"已加载模板，字段：{fields}", file=sys.stderr)
    return fields

# ---------- 输入解析 ----------
def load_objects_from_file(file_path: str) -> List[Dict[str, Any]]:
    """从单个 JSON 文件读取对象列表（支持单个对象或数组）"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 处理多个独立对象（非标准数组）的情况
    if not content.strip().startswith("["):
        content = "[" + content.strip().rstrip(",") + "]"

    try:
        data = json.loads(content)
        if isinstance(data, dict):
            data = [data]
        return data
    except json.JSONDecodeError as e:
        print(f"文件 {file_path} JSON 解析错误：{e}", file=sys.stderr)
        return []

# ---------- 动态提示词构建（增强版）----------
def build_extraction_prompt(fields: List[str], text: str) -> str:
    """根据字段列表和文本构建提取提示词"""
    field_list = "\n".join(f'  - "{f}"' for f in fields)
    prompt = f"""你是一个信息提取助手。请从以下文本中提取指定字段，严格按照 JSON 格式输出。

【需要提取的字段】
{field_list}

【提取规则】
1. 只提取一个主要对象，通常对应一个省份或地区。如果文本中没有明确的主体，返回空对象 {{}}。
2. "国家/地区" 字段应提取省份或地区名称，即使文本中使用加粗标记（如 **湖北省**）也要提取内部文字。
3. "大洲" 字段若文本未提及，但地区属于中国，请填写 "Asia"。
4. 数值字段（如人口、GDP、检测数、病例数等）：
   - 只提取数字部分，转换为纯数字字符串，不带单位（如“万”、“亿”、“元”），不带千分位逗号。
   - 约数如“约 5775 万人”转换为 "57750000"（将万转换为乘以10000，亿乘以100000000）。
   - 若出现“全零报告”、“无新增”、“零新增”等表述，对应的病例数字段填 "0"。
5. 若某字段在文本中未找到，填写空字符串 ""。
6. 输出必须为单行 JSON，不包含任何额外文字或 markdown 标记。

文本内容：
---
{text}
---

请输出提取结果（只输出 JSON）："""
    return prompt

def extract_fields(fields: List[str], text: str) -> Optional[Dict[str, str]]:
    """调用大模型提取字段，成功返回字典，失败返回 None"""
    prompt = build_extraction_prompt(fields, text)
    try:
        response = Generation.call(
            model=MODEL_NAME,
            prompt=prompt,
            result_format='message',
            temperature=0.1,
            max_tokens=500,
        )
        if response.status_code != 200:
            print(f"API 调用失败：{response.code} - {response.message}", file=sys.stderr)
            return None

        content = response.output.choices[0].message.content.strip()
        # 清洗可能的 markdown 代码块
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(lines[1:-1]) if len(lines) >= 3 else content
            content = content.strip()

        data = json.loads(content)
        if not isinstance(data, dict):
            return None

        # 确保返回字段与模板一致
        result = {field: data.get(field, "") for field in fields}
        return result
    except json.JSONDecodeError:
        print(f"模型返回非 JSON 内容：{content[:100]}...", file=sys.stderr)
        return None
    except Exception as e:
        print(f"提取过程出错：{e}", file=sys.stderr)
        return None

# ---------- 后处理补丁 ----------
def post_process_result(result: Dict[str, str], fields: List[str]) -> Dict[str, str]:
    """
    对提取结果进行智能修补，例如补全大洲、修正病例数等。
    """
    # 如果存在"国家/地区"字段且值为中国省份，且"大洲"字段为空，则补为 Asia
    if "国家/地区" in result and "大洲" in result:
        province = result["国家/地区"].strip()
        if province in CHINESE_PROVINCES and not result["大洲"]:
            result["大洲"] = "Asia"
            print(f"    [后处理] 补全大洲为 Asia", file=sys.stderr)

    # 可选：如果病例数字段为空，但文本中明确提到“零报告”（已在提示词处理，这里仅作为后备）
    # 由于模型可能仍漏掉，这里不做强制修改，以免引入错误。

    return result

# ---------- 主流程 ----------
def main():
    if len(sys.argv) != 4:
        print("用法：python extract_by_template.py <输入文件夹> <模板文件夹> <输出文件夹>", file=sys.stderr)
        sys.exit(1)

    input_dir = sys.argv[1]
    template_dir = sys.argv[2]
    output_dir = sys.argv[3]

    # 检查文件夹是否存在
    for path, name in [(input_dir, "输入"), (template_dir, "模板"), (output_dir, "输出")]:
        if not os.path.isdir(path):
            print(f"错误：{name}文件夹不存在：{path}", file=sys.stderr)
            sys.exit(1)

    # 加载模板字段
    fields = load_template(template_dir)

    # 创建输出目录（若不存在）
    os.makedirs(output_dir, exist_ok=True)

    # 扫描输入文件夹中的所有 JSON 文件
    input_files = glob.glob(os.path.join(input_dir, "*.json"))
    if not input_files:
        print(f"警告：输入文件夹中没有 JSON 文件。", file=sys.stderr)
        sys.exit(0)

    print(f"找到 {len(input_files)} 个输入文件。", file=sys.stderr)

    for input_path in input_files:
        base_name = os.path.basename(input_path)
        print(f"正在处理：{base_name}", file=sys.stderr)

        objects = load_objects_from_file(input_path)
        if not objects:
            print(f"  文件无有效数据，跳过。", file=sys.stderr)
            continue

        results = []
        for obj in objects:
            if "text" not in obj:
                print(f"  警告：对象缺少 'text' 字段，已跳过。", file=sys.stderr)
                continue

            extracted = extract_fields(fields, obj["text"])
            if extracted:
                # 后处理修补
                extracted = post_process_result(extracted, fields)
                # 只要有一个非空字段即视为有效
                if any(v for v in extracted.values() if v):
                    results.append(extracted)
                    first_val = next((v for v in extracted.values() if v), "?")
                    print(f"    提取成功：{first_val}", file=sys.stderr)
                else:
                    print(f"    提取结果全部为空，跳过。", file=sys.stderr)
            else:
                print(f"    未提取到有效数据，跳过。", file=sys.stderr)

        # 保存结果到输出文件夹
        output_path = os.path.join(output_dir, base_name)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"  已保存 {len(results)} 条记录到 {output_path}", file=sys.stderr)

    print("处理完成。", file=sys.stderr)

if __name__ == "__main__":
    main()