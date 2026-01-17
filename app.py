from flask import Flask, render_template, request, jsonify
import pandas as pd
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv
import sys
import traceback

load_dotenv()

app = Flask(__name__)

print("=" * 70)
print("Starting AI Spreadsheet Analyst")
print("=" * 70)

# Load sheet
print("1. Loading Google Sheet...")
try:
    sheet_url = "https://docs.google.com/spreadsheets/d/1U2fa6zRPQyrj75ayU4qcnlYna0iVDFYmn3BAyFGEu6k/edit?usp=sharing"
    csv_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv')
    print(f"   CSV URL: {csv_url}")
    df = pd.read_csv(csv_url)
    print(f"   ✓ Loaded: {len(df)} rows × {len(df.columns)} columns")
    print(f"   Columns: {df.columns.tolist()}")
except Exception as e:
    print(f"   ✗ Failed to load sheet: {e}")
    print(traceback.format_exc())
    sys.exit(1)

# Configure API
print("\n2. Configuring Gemini API...")
try:
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    print(f"   API Key: {gemini_api_key[:10]}...{gemini_api_key[-4:]}")
    genai.configure(api_key=gemini_api_key)
    print("   ✓ API configured")
except Exception as e:
    print(f"   ✗ Failed to configure API: {e}")
    sys.exit(1)

# Initialize model
print("\n3. Initializing Gemini model...")
try:
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',  # Stable GA model, best for production
        tools='code_execution'
    )
    print("   ✓ Model initialized")
except Exception as e:
    print(f"   ✗ Failed to initialize model: {e}")
    print(traceback.format_exc())
    sys.exit(1)

print("\n" + "=" * 70)
print("Server ready!")
print("=" * 70 + "\n")

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
    try:
        print("\n" + "=" * 70)
        print("INIT SESSION REQUEST")
        print("=" * 70)
        
        session_id = request.json.get('session_id', 'default')
        print(f"Session ID: {session_id}")
        
        print("\n1. Creating chat session...")
        chat = model.start_chat()
        print("   ✓ Chat created")
        
        print("\n2. Preparing data summary...")
        data_summary = get_data_summary()
        print(f"   ✓ Summary prepared ({len(data_summary)} chars)")
        
        print("\n3. Sending system context to Gemini...")
        system_context = f"""You are a data analyst with access to a pandas DataFrame called 'df'.

{data_summary}

Use code execution to analyze the data. The DataFrame 'df' is loaded and ready."""
        
        print(f"   Context length: {len(system_context)} chars")
        response = chat.send_message(system_context)
        print("   ✓ Context sent successfully")
        
        print("\n4. Storing session...")
        chat_sessions[session_id] = chat
        print(f"   ✓ Session stored. Active sessions: {len(chat_sessions)}")
        
        result = {
            'status': 'success',
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': df.columns.tolist()
        }
        
        print("\n" + "=" * 70)
        print("INIT SUCCESS")
        print("=" * 70 + "\n")
        
        return jsonify(result)
        
    except Exception as e:
        error_msg = str(e)
        print("\n" + "=" * 70)
        print("INIT FAILED")
        print("=" * 70)
        print(f"Error: {error_msg}")
        print("\nFull traceback:")
        print(traceback.format_exc())
        print("=" * 70 + "\n")
        
        return jsonify({
            'error': error_msg,
            'details': traceback.format_exc()
        }), 500

@app.route('/api/query', methods=['POST'])
def query():
    try:
        session_id = request.json.get('session_id', 'default')
        user_query = request.json.get('query', '')
        
        if not user_query:
            return jsonify({'error': 'No query provided'}), 400
        
        if session_id not in chat_sessions:
            print(f"Session {session_id} not found. Available sessions: {list(chat_sessions.keys())}")
            return jsonify({'error': 'Session not initialized. Please refresh the page.'}), 400
        
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
        print(f"Query error: {str(e)}")
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

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        health_status = {
            'status': 'healthy',
            'checks': {
                'dataframe_loaded': len(df) > 0,
                'api_key_configured': bool(os.getenv('GEMINI_API_KEY')),
                'model_initialized': model is not None,
                'active_sessions': len(chat_sessions)
            },
            'data': {
                'rows': len(df),
                'columns': len(df.columns)
            }
        }
        return jsonify(health_status)
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
