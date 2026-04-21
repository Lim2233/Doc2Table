import os
import uuid
import shutil
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename

# 导入你已有的处理函数（假设它叫 process_and_fill）
# 请根据你的实际情况调整导入路径
from your_processing_module import process_and_fill

app = Flask(__name__)

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 最大100MB，可调

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

    # 3. 获取需求文本（可以是文件上传，也可以是文本框输入）
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

    # 4. 创建本次请求的唯一工作目录，避免文件名冲突
    job_id = str(uuid.uuid4())
    job_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    os.makedirs(job_upload_dir, exist_ok=True)

    try:
        # 5. 保存所有上传的文件到工作目录
        saved_data_paths = []
        for f in data_files:
            if f.filename == '':
                continue
            if not allowed_file(f.filename):
                return jsonify({'error': f'不支持的文件类型: {f.filename}'}), 400
            filename = secure_filename(f.filename)
            save_path = os.path.join(job_upload_dir, filename)
            f.save(save_path)
            saved_data_paths.append(save_path)

        # 保存模板文件（保留原始扩展名）
        template_filename = secure_filename(template_file.filename)
        template_path = os.path.join(job_upload_dir, template_filename)
        template_file.save(template_path)

        # 保存需求文本为临时文件（如果你的处理函数需要文件路径）
        requirements_path = os.path.join(job_upload_dir, 'requirements.txt')
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(requirements_text)

        # 6. 定义结果文件路径
        result_filename = f'result_{job_id}.xlsx'  # 假设输出是 xlsx，根据实际调整
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)

        # 7. 调用你已有的处理函数
        #    请根据你实际的函数签名调整参数传递方式
        process_and_fill(
            data_files=saved_data_paths,
            template_file=template_path,
            requirements_file=requirements_path,
            output_file=result_path
        )

        # 8. 返回结果文件供下载（前端会触发下载）
        return send_file(
            result_path,
            as_attachment=True,
            download_name=f'填写结果_{job_id[:8]}.xlsx',  # 下载时的文件名
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        # 处理出错时返回错误信息
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

    finally:
        # 9. 清理临时上传的文件（可选，防止占用磁盘）
        #    如果不想立即清理，可以注释掉，定期用脚本清理旧目录
        try:
            shutil.rmtree(job_upload_dir)
        except:
            pass
        # 注意：结果文件建议保留一段时间再清理，这里直接保留，你可以后续加个定时任务删除旧文件

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)