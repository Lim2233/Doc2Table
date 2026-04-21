import os
import uuid
import shutil
import zipfile
import io
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename

from process import process_and_fill

app = Flask(__name__)

# 配置固定目录
INPUT_RAW_DATA = r'input/rawData'
INPUT_TEMPLATE = r'input/template'
INPUT_USER_INPUT = r'input/userInput'
RESULT_FOLDER = r'results'

# 创建所需目录
for folder in [INPUT_RAW_DATA, INPUT_TEMPLATE, INPUT_USER_INPUT, RESULT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 最大100MB

ALLOWED_EXTENSIONS = {'xlsx', 'docx', 'md', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clear_folder(folder_path):
    """清空指定文件夹内的所有文件和子文件夹"""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'清理失败 {file_path}: {e}')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    # ---------- 新请求开始时，清理结果文件夹 ----------
    clear_folder(RESULT_FOLDER)

    # 1. 检查数据文档（多文件）
    data_files = request.files.getlist('data_files')
    if not data_files or all(f.filename == '' for f in data_files):
        return jsonify({'error': '至少上传一个数据文档'}), 400

    # 2. 检查模板文件
    template_file = request.files.get('template_file')
    if not template_file or template_file.filename == '':
        return jsonify({'error': '请上传表格模板文件'}), 400

    # 3. 获取需求文本
    requirements_text = None
    req_file = request.files.get('requirements_file')
    if req_file and req_file.filename != '':
        requirements_text = req_file.read().decode('utf-8')
    else:
        requirements_text = request.form.get('requirements_text', '').strip()
        if not requirements_text:
            return jsonify({'error': '请提供需求内容'}), 400

    try:
        # 4. 保存数据文件
        for f in data_files:
            if f.filename == '':
                continue
            if not allowed_file(f.filename):
                return jsonify({'error': f'不支持的文件类型: {f.filename}'}), 400
            filename = secure_filename(f.filename)
            f.save(os.path.join(INPUT_RAW_DATA, filename))

        # 5. 保存模板文件
        template_filename = secure_filename(template_file.filename)
        template_path = os.path.join(INPUT_TEMPLATE, template_filename)
        template_file.save(template_path)

        # 6. 保存需求文本
        requirements_path = os.path.join(INPUT_USER_INPUT, 'requirements.txt')
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(requirements_text)

        # 7. 调用处理函数（生成结果到 results 文件夹）
        process_and_fill()

        # 8. 检查结果文件夹是否有文件
        result_files = os.listdir(RESULT_FOLDER)
        if not result_files:
            return jsonify({'error': '处理完成但未生成任何结果文件'}), 500

        # 9. 将所有结果文件打包为 ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename in result_files:
                file_path = os.path.join(RESULT_FOLDER, filename)
                if os.path.isfile(file_path):
                    zip_file.write(file_path, arcname=filename)

        zip_buffer.seek(0)

        # 10. 返回 ZIP 文件供下载
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=f'results_{uuid.uuid4().hex[:8]}.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

    finally:
        # 清理上传的输入文件（保持原有逻辑）
        try:
            for f in os.listdir(INPUT_RAW_DATA):
                os.remove(os.path.join(INPUT_RAW_DATA, f))
            for f in os.listdir(INPUT_TEMPLATE):
                os.remove(os.path.join(INPUT_TEMPLATE, f))
            os.remove(os.path.join(INPUT_USER_INPUT, 'requirements.txt'))
        except:
            pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)