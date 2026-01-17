from flask import Flask, render_template, request, jsonify
import pandas as pd
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

sheet_url = "https://docs.google.com/spreadsheets/d/1U2fa6zRPQyrj75ayU4qcnlYna0iVDFYmn3BAyFGEu6k/edit?usp=sharing"
csv_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv')
df = pd.read_csv(csv_url)

gemini_api_key = os.getenv('GEMINI_API_KEY')
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")
genai.configure(api_key=gemini_api_key)

model = genai.GenerativeModel(
    model_name='gemini-2.0-flash-exp',
    tools='code_execution'
)

chat_sessions = {}

def get_data_summary():
    summary = {
        'shape': {'rows': len(df), 'columns': len(df.columns)},
        'columns': df.columns.tolist(),
        'dtypes': df.dtypes.astype(str).to_dict(),
        'sample_rows': df.head(10).to_dict('records'),
    }
    
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        summary['statistics'] = df[numeric_cols].describe().to_dict()
    
    return json.dumps(summary, indent=2, default=str)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/init', methods=['POST'])
def init_session():
    session_id = request.json.get('session_id', 'default')
    
    chat = model.start_chat()
    system_context = f"""You are a data analyst with access to a pandas DataFrame called 'df'.

{get_data_summary()}

Use code execution to analyze the data. The DataFrame 'df' is loaded and ready."""
    
    chat.send_message(system_context)
    chat_sessions[session_id] = chat
    
    return jsonify({
        'status': 'success',
        'rows': len(df),
        'columns': len(df.columns),
        'column_names': df.columns.tolist()
    })

@app.route('/api/query', methods=['POST'])
def query():
    session_id = request.json.get('session_id', 'default')
    user_query = request.json.get('query', '')
    
    if not user_query:
        return jsonify({'error': 'No query provided'}), 400
    
    if session_id not in chat_sessions:
        return jsonify({'error': 'Session not initialized'}), 400
    
    try:
        chat = chat_sessions[session_id]
        response = chat.send_message(user_query)
        
        result = {
            'text': '',
            'code': '',
            'output': ''
        }
        
        for part in response.parts:
            if hasattr(part, 'text') and part.text:
                result['text'] += part.text
            if hasattr(part, 'executable_code') and part.executable_code:
                result['code'] = part.executable_code.code
            if hasattr(part, 'code_execution_result') and part.code_execution_result:
                if part.code_execution_result.output:
                    result['output'] = part.code_execution_result.output
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data-info', methods=['GET'])
def data_info():
    return jsonify({
        'rows': len(df),
        'columns': len(df.columns),
        'column_names': df.columns.tolist(),
        'dtypes': df.dtypes.astype(str).to_dict(),
        'sample': df.head(5).to_dict('records')
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
