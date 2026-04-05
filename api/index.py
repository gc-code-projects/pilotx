from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv

app = Flask(__name__, template_folder="../templates")

load_dotenv()

api_key = os.getenv("LLM_API_KEY")

client = None
model = "qwen/qwen3.6-plus:free"

if api_key:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        prompt = data.get('message', '')

        if not client:
            return jsonify({'response': 'AI service unavailable'})

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )

        return jsonify({
            'response': response.choices[0].message.content
        })

    except Exception as e:
        return jsonify({'response': str(e)})

# 👇 IMPORTANT for Vercel
def handler(request, *args, **kwargs):
    return app(request.environ, lambda *args: None)