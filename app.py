import os
import uuid
import shutil
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename

from process import process_and_fill

app = Flask(__name__)

# 配置上传文件夹（固定目录）
INPUT_RAW_DATA = 'input/rawData'
INPUT_TEMPLATE = 'input/template'
INPUT_USER_INPUT = 'input/userInput'
RESULT_FOLDER = 'results'

# 创建所需目录
for folder in [INPUT_RAW_DATA, INPUT_TEMPLATE, INPUT_USER_INPUT, RESULT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 最大100MB

# 允许上传的文件扩展名
ALLOWED_EXTENSIONS = {'xlsx', 'docx', 'md', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """显示上传页面"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    """处理上传请求"""
    # 1. 检查数据文档（多文件）
    data_files = request.files.getlist('data_files')
    if not data_files or all(f.filename == '' for f in data_files):
        return jsonify({'error': '至少上传一个数据文档'}), 400

    # 2. 检查模板文件
    template_file = request.files.get('template_file')
    if not template_file or template_file.filename == '':
        return jsonify({'error': '请上传表格模板文件'}), 400

    # 3. 获取需求文本（文件或文本框）
    requirements_text = None
    req_file = request.files.get('requirements_file')
    if req_file and req_file.filename != '':
        # 用户上传了需求文件
        requirements_text = req_file.read().decode('utf-8')
    else:
        # 用户直接在文本框输入
        requirements_text = request.form.get('requirements_text', '').strip()
        if not requirements_text:
            return jsonify({'error': '请提供需求内容（上传文件或填写文本框）'}), 400

    try:
        # 4. 保存数据文件到 input/rawData
        for f in data_files:
            if f.filename == '':
                continue
            if not allowed_file(f.filename):
                return jsonify({'error': f'不支持的文件类型: {f.filename}'}), 400
            filename = secure_filename(f.filename)
            save_path = os.path.join(INPUT_RAW_DATA, filename)
            f.save(save_path)

        # 5. 保存模板文件到 input/template
        template_filename = secure_filename(template_file.filename)
        template_path = os.path.join(INPUT_TEMPLATE, template_filename)
        template_file.save(template_path)

        # 6. 保存需求文本到 input/userInput/requirements.txt
        requirements_path = os.path.join(INPUT_USER_INPUT, 'requirements.txt')
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(requirements_text)

        # 7. 调用处理函数（无参数，内部读取固定目录）
        process_and_fill()

        # 8. 查找结果文件（假设处理函数会在 RESULT_FOLDER 下生成固定名称的文件）
        #    这里按原有逻辑生成结果文件名，若 process_and_fill 行为不同需调整
        result_filename = 'result.xlsx'   # 根据实际情况修改
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

        if not os.path.exists(result_path):
            return jsonify({'error': '处理完成但未生成结果文件'}), 500

        # 9. 返回结果文件供下载
        return send_file(
            result_path,
            as_attachment=True,
            download_name=f'填写结果_{uuid.uuid4().hex[:8]}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

    finally:
        # 可选：清理上传的输入文件（若需要可取消注释）
        # try:
        #     for f in os.listdir(INPUT_RAW_DATA):
        #         os.remove(os.path.join(INPUT_RAW_DATA, f))
        #     for f in os.listdir(INPUT_TEMPLATE):
        #         os.remove(os.path.join(INPUT_TEMPLATE, f))
        #     os.remove(os.path.join(INPUT_USER_INPUT, 'requirements.txt'))
        # except:
        #     pass
        pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)