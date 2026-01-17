#!/usr/bin/env python3
"""
Local Test Script - Run this before deploying to Render
Tests: Google Sheet access, API key, Gemini connection
"""

import os
import sys

print("=" * 70)
print("LOCAL TEST - AI Spreadsheet Analyst")
print("=" * 70)

# Test 1: Load .env
print("\n1. Testing .env file...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"   ✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    else:
        print("   ✗ API Key not found in .env file")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 2: Load Google Sheet
print("\n2. Testing Google Sheet access...")
try:
    import pandas as pd
    sheet_url = "https://docs.google.com/spreadsheets/d/1U2fa6zRPQyrj75ayU4qcnlYna0iVDFYmn3BAyFGEu6k/edit?usp=sharing"
    csv_url = sheet_url.replace('/edit?usp=sharing', '/export?format=csv')
    print(f"   URL: {csv_url}")
    df = pd.read_csv(csv_url)
    print(f"   ✓ Loaded: {len(df)} rows × {len(df.columns)} columns")
    print(f"   Columns: {df.columns.tolist()}")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Test 3: Configure Gemini
print("\n3. Testing Gemini API...")
try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    print("   ✓ API configured")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

# Test 4: Initialize Model
print("\n4. Testing model initialization...")
try:
    # Try stable GA version first (best for production)
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        tools='code_execution'
    )
    print("   ✓ Model initialized (gemini-2.5-flash)")
except Exception as e:
    print(f"   ✗ Failed with gemini-2.5-flash: {e}")
    print("   Trying gemini-1.5-flash...")
    try:
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools='code_execution'
        )
        print("   ✓ Model initialized (gemini-1.5-flash)")
        print("   ⚠️  Consider upgrading to gemini-2.5-flash")
    except Exception as e2:
        print(f"   ✗ Also failed with gemini-1.5-flash: {e2}")
        sys.exit(1)

# Test 5: Send test message
print("\n5. Testing chat functionality...")
try:
    chat = model.start_chat()
    response = chat.send_message("What is 2+2?")
    print("   ✓ Chat works")
    print(f"   Response: {response.text[:100]}")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("=" * 70)
print("\nYou're ready to deploy to Render.")
print("\nNext steps:")
print("1. Push to GitHub")
print("2. Deploy on Render")
print("3. Set GEMINI_API_KEY in Render environment variables")
print()
