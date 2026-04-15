from flask import Flask, request, jsonify
import os
import asyncio
from volcenginesdkarkruntime import Ark, AsyncArk

app = Flask(__name__, template_folder="../templates")

# Load environment variables
api_key = os.getenv("LLM_API_KEY")
MODEL = "doubao-seed-2-0-mini-260215"

# Initialize client
client = Ark(
    base_url='https://ark.cn-beijing.volces.com/api/v3',
    api_key=api_key,
) if api_key else None


@app.route('/')
def index():
    return "Flask app running on Vercel 🚀"


# ================= CHAT =================
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        prompt = data.get('message', '')

        if not client:
            return jsonify({'response': 'AI服务不可用，请检查API Key'})

        response = client.responses.create(
            model=MODEL,
            input=prompt,
        )

        return jsonify({
            'response': response.output[1].content[0].text
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ================= ANALYZE PDF =================
@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        files = request.files.getlist('file')
        task = request.form.get('task', '请分析这个PDF文件')

        if not files:
            return jsonify({"message": "No files"}), 400

        uploads_dir = "/tmp"  # Vercel writable dir

        results = []

        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"message": "Only PDF allowed"}), 400

            file_path = os.path.join(uploads_dir, file.filename)
            file.save(file_path)

            analysis = run_async(analyze_pdf(file_path, task))

            results.append({
                "filename": file.filename,
                "analysis": analysis
            })

        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= ASYNC HANDLER =================
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.ensure_future(coro)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ================= PDF ANALYSIS =================
async def analyze_pdf(file_path, task):
    try:
        async_client = AsyncArk(
            base_url='https://ark.cn-beijing.volces.com/api/v3',
            api_key=api_key
        )

        with open(file_path, "rb") as f:
            file = await async_client.files.create(
                file=f,
                purpose="user_data"
            )

        await async_client.files.wait_for_processing(file.id)

        response = await async_client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_file", "file_id": file.id},
                        {"type": "input_text", "text": task}
                    ]
                }
            ],
        )

        return response.output[1].content[0].text

    except Exception as e:
        return f"分析错误: {str(e)}"


# ================= VERCEL ENTRY =================
# This is REQUIRED
def handler(request, *args):
    return app(request.environ, lambda *a: None)
