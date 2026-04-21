"""
md_semantic_slicer.py

对指定输入目录中的所有 .md 文件进行语义切分。
- 优先按段落（空行分隔）拆分，确保段落边界不被合并。
- 对超过 1000 字符的段落进一步按句子切分。
- 所有切片统一编号，保存为单个 JSON 文件（固定命名为 sliced.json），格式为 [{"id": 1, "text": "..."}, ...]。

用法:
    python md_semantic_slicer.py <输入文件夹> <JSON文件保存文件夹>
"""

import os
import re
import json
import sys
from typing import List, Dict, Any, Iterator


# ---------- 段落级切分 ----------
def split_paragraphs(text: str) -> List[str]:
    """
    按连续换行符（空行）分割文本为段落列表。
    保留 Markdown 标题、列表等逻辑结构。
    """
    # 匹配一个或多个空行（包括可能存在的空格）
    paragraphs = re.split(r'\n\s*\n+', text)
    # 去除首尾空白，并过滤掉空段落
    return [p.strip() for p in paragraphs if p.strip()]


def split_by_sentence(text: str) -> List[str]:
    """
    将文本按中文句号、问号、感叹号进行句子分割，保留分隔符在句尾。
    """
    pattern = r'(?<=[。！？!?])'
    parts = re.split(pattern, text)
    return [p for p in parts if p.strip()]


def semantic_chunk(text: str, max_len: int = 1000) -> List[str]:
    """
    递归语义切分（用于单个段落内部）。
    若文本长度 ≤ max_len 则直接返回；
    否则按句子切分，并尽量合并句子直到接近 max_len。
    如果单个句子长度超过 max_len，则强制按逗号分割或按长度截断。
    """
    if len(text) <= max_len:
        return [text]

    sentences = split_by_sentence(text)
    if not sentences:
        return [text[i:i+max_len] for i in range(0, len(text), max_len)]

    chunks = []
    current_chunk = ""
    for sent in sentences:
        if len(sent) > max_len:
            # 尝试按逗号分割
            comma_parts = re.split(r'(?<=[，,])', sent)
            if len(comma_parts) == 1:
                # 无逗号，强制按长度切分
                for i in range(0, len(sent), max_len):
                    chunks.append(sent[i:i+max_len])
            else:
                for part in comma_parts:
                    if part.strip():
                        chunks.extend(semantic_chunk(part, max_len))
            continue

        if len(current_chunk) + len(sent) <= max_len:
            current_chunk += sent
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sent

    if current_chunk:
        chunks.append(current_chunk)

    # 后处理，确保无超长块
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > max_len:
            final_chunks.extend(semantic_chunk(chunk, max_len))
        else:
            final_chunks.append(chunk)

    return final_chunks


def chunk_paragraph(paragraph: str, max_len: int = 1000) -> List[str]:
    """
    对单个段落进行切分：
    - 如果段落长度 ≤ max_len，直接返回该段落（作为一个切片）。
    - 否则调用 semantic_chunk 进一步切分。
    """
    if len(paragraph) <= max_len:
        return [paragraph]
    return semantic_chunk(paragraph, max_len)


# ---------- 文件遍历与读取 ----------
def find_markdown_files(root_dir: str) -> Iterator[str]:
    """递归遍历目录，返回所有 .md 文件的绝对路径。"""
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.lower().endswith('.md'):
                yield os.path.join(dirpath, fname)


def read_file_content(file_path: str) -> str:
    """读取文件内容，尝试常见编码。"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"无法解码文件: {file_path}")


# ---------- 主流程 ----------
def process_markdown_files(input_dir: str, output_dir: str, max_len: int = 1000) -> str:
    """
    处理输入目录下所有 .md 文件，生成切分后的 JSON 文件到输出目录。
    返回生成的 JSON 文件路径。
    """
    if not os.path.isdir(input_dir):
        raise NotADirectoryError(f"输入目录不存在: {input_dir}")

    os.makedirs(output_dir, exist_ok=True)

    all_slices: List[Dict[str, Any]] = []
    global_id = 1

    for md_path in find_markdown_files(input_dir):
        try:
            content = read_file_content(md_path)
        except Exception as e:
            print(f"警告: 读取文件失败 {md_path} - {e}")
            continue

        # 1. 先按段落分割
        paragraphs = split_paragraphs(content)

        # 2. 对每个段落进行切分（段落边界不合并）
        for para in paragraphs:
            chunks = chunk_paragraph(para, max_len)
            for chunk_text in chunks:
                all_slices.append({
                    "id": global_id,
                    "text": chunk_text
                })
                global_id += 1

    # 输出 JSON（固定命名为 sliced.json）
    output_path = os.path.join(output_dir, "sliced.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_slices, f, ensure_ascii=False, indent=2)

    return output_path


# ---------- 命令行入口 ----------
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python md_semantic_slicer.py <输入文件夹> <JSON文件保存文件夹>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    try:
        result_path = process_markdown_files(input_dir, output_dir)
        md_count = sum(1 for _ in find_markdown_files(input_dir))
        print(f"切分完成！共处理 {md_count} 个 .md 文件。")
        print(f"结果已保存至: {result_path}")
    except Exception as e:
        print(f"处理失败: {e}")
        sys.exit(1)