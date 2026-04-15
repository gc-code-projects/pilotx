from flask import Flask, render_template, request, jsonify
import os
import asyncio
from volcenginesdkarkruntime import Ark, AsyncArk

# 👇 IMPORTANT: point to templates folder correctly
app = Flask(__name__, template_folder="../templates")

# =========================
# Global initialization
# =========================
api_key = os.getenv("LLM_API_KEY")
MODEL = "doubao-seed-2-0-mini-260215"

client = None
if api_key:
    client = Ark(
        base_url='https://ark.cn-beijing.volces.com/api/v3',
        api_key=api_key,
    )

# =========================
# Routes
# =========================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/historical-materials')
def historical_materials():
    return render_template('historical-materials.html')

@app.route('/historical-analysis')
def historical_analysis():
    return render_template('historical-analysis.html')

@app.route('/time-travel')
def time_travel():
    return render_template('time-travel.html')

@app.route('/time-travel-scenario')
def time_travel_scenario():
    return render_template('time-travel-scenario.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        prompt = data.get('message', '')
        
        if not client:
            return jsonify({'response': '抱歉，AI服务暂时不可用。请联系管理员设置API密钥。'})
        
        response = client.responses.create(
            model=MODEL,
            input=prompt, # Replace with your prompt
            # thinking={"type": "disabled"}, #  Manually disable deep thinking
        )
        
        return jsonify({'response': response.output[1].content[0].text})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'response': f'抱歉，处理您的请求时发生错误：{str(e)}'})


@app.route('/upload', methods=['POST'])
def upload():
    try:
        # 1. 校验文件是否存在
        if 'file' not in request.files:
            return jsonify({"message": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"message": "No selected file"}), 400

        # 2. 只允许PDF
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"message": "请上传 PDF 文件"}), 400

        # 3. 保存文件到本地
        uploads_dir = os.path.join(app.root_path, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, file.filename)
        file.save(file_path)

        # 4. 调用豆包分析 PDF
        analysis = analyze_pdf(file_path, "请分析这个PDF文件")

        return jsonify({
            "message": f"文件 {file.filename} 上传并分析成功",
            "ai_analysis": analysis
        })

    except Exception as e:
        return jsonify({"error": f"服务器错误：{str(e)}"}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # 1. 校验文件是否存在
        if 'file' not in request.files:
            return jsonify({"message": "No file part"}), 400

        # 2. 获取所有文件 (支持多个文件)
        files = request.files.getlist('file')
        if not files:
            return jsonify({"message": "No selected files"}), 400

        # 3. 只允许PDF
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"message": "请上传 PDF 文件"}), 400

        # 4. 获取任务描述
        task = request.form.get('task', '请分析这个PDF文件')

        # 5. 保存文件到本地并分析
        uploads_dir = os.path.join(app.root_path, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)

        analysis_results = []
        for file in files:
            file_path = os.path.join(uploads_dir, file.filename)
            file.save(file_path)
            
            # 调用豆包分析 PDF
            analysis = analyze_pdf(file_path, task)

            analysis_results.append({
                "filename": file.filename,
                "analysis": analysis
            })

        # 生成综合分析结果
        combined_analysis = """
# PDF文件分析结果

"""
        for result in analysis_results:
            combined_analysis += f"## {result['filename']}\n{result['analysis']}\n\n"

        return jsonify({
            "message": f"{len(files)} 个文件分析完成",
            "ai_analysis": combined_analysis
        })

    except Exception as e:
        return jsonify({"error": f"服务器错误：{str(e)}"}), 500

def analyze_pdf(file_path, task="请分析这个PDF文件"):
    async def analyze_async():
        try:
            # Create AsyncArk client
            async_client = AsyncArk(
                base_url='https://ark.cn-beijing.volces.com/api/v3',
                api_key=api_key
            )
            
            # Upload PDF file
            print("Uploading PDF file...")
            with open(file_path, "rb") as f:
                file = await async_client.files.create(
                    file=f,
                    purpose="user_data"
                )
            print(f"File uploaded: {file.id}")
            
            # Wait for the file to finish processing
            print("Waiting for file processing...")
            await async_client.files.wait_for_processing(file.id)
            print(f"File processed: {file.id}")
            
            # Create response with the file and task
            response = await async_client.responses.create(
                model=MODEL,
                input=[
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "input_file",
                                "file_id": file.id  # ref pdf file id
                            },
                            {
                                "type": "input_text",
                                "text": task
                            }
                        ]
                    },
                ],
            )
            
            # Extract and return the analysis result
            if response and response.output and len(response.output) > 1:
                analysis_content = response.output[1].content[0].text
                return analysis_content
            else:
                return "分析完成，但未获取到分析结果。"
                
        except Exception as e:
            print(f"Error during PDF analysis: {e}")
            return f"分析过程中发生错误: {str(e)}"
    
    # Run the async function
    return asyncio.run(analyze_async())
    


# =========================
# 👇 Vercel entrypoint
# =========================
def handler(request, *args, **kwargs):
    return app(request.environ, lambda *args: None)