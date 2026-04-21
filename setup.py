#!/usr/bin/env python3
"""
自动创建虚拟环境、安装依赖、启动 app.py、打开浏览器，按回车关闭服务。
"""

import subprocess
import sys
import re
import threading
import webbrowser
import time
import os
import venv
from pathlib import Path

# 虚拟环境目录名称
VENV_DIR = "venv"


def get_venv_python():
    """返回虚拟环境中 Python 解释器的路径（跨平台）"""
    if os.name == "nt":
        python_exe = VENV_DIR / "Scripts" / "python.exe"
    else:
        python_exe = VENV_DIR / "bin" / "python"
    return python_exe


def get_venv_pip():
    """返回虚拟环境中 pip 可执行文件的路径（跨平台），但推荐使用 python -m pip"""
    return [str(get_venv_python()), "-m", "pip"]


def create_virtual_environment():
    """如果 venv 目录不存在，则创建虚拟环境"""
    venv_path = Path(VENV_DIR)
    if venv_path.exists():
        print(f"[✓] 虚拟环境已存在: {VENV_DIR}")
        return True

    print(f"[*] 正在创建虚拟环境: {VENV_DIR}")
    try:
        venv.create(venv_path, with_pip=True)
        print("[✓] 虚拟环境创建成功。")
        return True
    except Exception as e:
        print(f"[✗] 虚拟环境创建失败: {e}", file=sys.stderr)
        return False


def install_requirements():
    """在虚拟环境中安装 requirements.txt 中的依赖"""
    req_file = Path("requirements.txt")
    if not req_file.is_file():
        print("[!] 未找到 requirements.txt，跳过依赖安装。")
        return True

    print(f"[*] 正在虚拟环境中安装依赖: {req_file}")
    pip_cmd = get_venv_pip() + ["install", "-r", str(req_file)]

    try:
        subprocess.run(
            pip_cmd,
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        print("[✓] 依赖安装完成。")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[✗] 依赖安装失败: {e}", file=sys.stderr)
        return False


def run_app():
    """
    使用虚拟环境的 Python 启动 app.py，捕获输出，检测网址并打开浏览器，
    等待用户按回车后终止进程。
    """
    print("[*] 使用虚拟环境启动 app.py ...")
    python_exe = get_venv_python()

    # 启动子进程，使用行缓冲实时输出
    proc = subprocess.Popen(
        [str(python_exe), "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,          # 合并 stderr 到 stdout
        universal_newlines=True,
        bufsize=1,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )

    url_found = None
    # 匹配常见的本地服务地址
    url_pattern = re.compile(r"https?://(?:127\.0\.0\.1|localhost):\d+")

    def read_output():
        """在独立线程中逐行读取子进程输出，打印并查找 URL"""
        nonlocal url_found
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            sys.stdout.write(line)          # 实时输出
            sys.stdout.flush()

            if not url_found:
                match = url_pattern.search(line)
                if match:
                    url_found = match.group(0)
                    print(f"\n[✓] 检测到服务网址: {url_found}")
                    webbrowser.open(url_found)
                    print("[*] 已在默认浏览器中打开，按 Enter 键停止服务并退出...")

    # 启动读取线程
    reader_thread = threading.Thread(target=read_output, daemon=True)
    reader_thread.start()

    try:
        input()  # 等待用户按下 Enter
    except KeyboardInterrupt:
        print("\n[!] 收到中断信号，正在停止服务...")
    finally:
        print("[*] 正在停止 app.py ...")
        if os.name == "nt":
            # Windows: 发送 Ctrl+Break 事件
            proc.send_signal(subprocess.CTRL_BREAK_EVENT)
        else:
            proc.terminate()   # Unix: SIGTERM

        try:
            proc.wait(timeout=5)
            print("[✓] app.py 已停止。")
        except subprocess.TimeoutExpired:
            print("[!] 进程未在 5 秒内退出，强制终止。")
            proc.kill()
            proc.wait()


def main():
    print("=" * 50)
    print("  自动部署与运行脚本 (虚拟环境模式)")
    print("=" * 50)

    # 1. 创建虚拟环境
    if not create_virtual_environment():
        sys.exit(1)

    # 2. 安装依赖
    if not install_requirements():
        sys.exit(1)

    # 3. 运行应用
    run_app()


if __name__ == "__main__":
    main()