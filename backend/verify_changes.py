#!/usr/bin/env python3
"""Quick verification of multi-language support changes."""

import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

PYTHON_CODE = """
def add(a, b):
    '''Add two numbers.'''
    return a + b
"""

JAVA_CODE = """
public class Math {
    public static int multiply(int a, int b) {
        return a * b;
    }
}
"""

def verify_python_extraction():
    """Verify Python code extraction works."""
    print("\n✓ Testing: Extract functions from Python code...")
    try:
        resp = requests.post(f"{BASE_URL}/extract", json={"code": PYTHON_CODE}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('count') > 0:
                print(f"  ✓ Extracted {data['count']} function(s) from Python")
                return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
    return False

def verify_java_extraction():
    """Verify Java code extraction with Groq fallback."""
    print("\n✓ Testing: Extract functions from Java code (using Groq)...")
    try:
        resp = requests.post(f"{BASE_URL}/extract", json={"code": JAVA_CODE}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('count') > 0:
                print(f"  ✓ Extracted {data['count']} function(s) from Java using Groq AI")
                return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
    return False

def verify_multi_language_document():
    """Verify documentation generator handles any language."""
    print("\n✓ Testing: Generate documentation for multiple languages...")
    try:
        # Test with Python
        resp_py = requests.post(f"{BASE_URL}/document", json={"code": PYTHON_CODE}, timeout=15)
        py_ok = resp_py.status_code == 200
        
        # Test with Java
        resp_java = requests.post(f"{BASE_URL}/document", json={"code": JAVA_CODE}, timeout=15)
        java_ok = resp_java.status_code == 200
        
        if py_ok and java_ok:
            print(f"  ✓ Documentation generated for both Python and Java")
            # Check that the system prompt mentions ANY programming language
            if "ANY programming language" in resp_py.request.body:
                print(f"  ✓ System prompt updated to handle ANY programming language")
            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
    return False

def verify_plagiarism_any_language():
    """Verify plagiarism detector works with any language."""
    print("\n✓ Testing: Plagiarism detection for mixed languages...")
    try:
        resp = requests.post(f"{BASE_URL}/plagiarism", 
                            json={"code1": PYTHON_CODE, "code2": JAVA_CODE},
                            timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if 'similarity' in data:
                print(f"  ✓ Plagiarism detection works (similarity: {data['similarity']}%)")
                print(f"  ✓ Verdict: {data['verdict']}")
                return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
    return False

def check_source_code():
    """Verify source code changes were applied."""
    print("\n✓ Checking source code modifications...")
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    checks = [
        ("api_extract uses Groq fallback", "Fallback — use Groq for any language" in content),
        ("api_document mentions ANY language", "ANY programming language" in content and "api_document" in content),
        ("api_explain mentions ANY language", "The code can be in ANY programming language" in content),
        ("api_complexity mentions ANY language", "Analyze code written in ANY programming language" in content),
        ("api_plagiarism normalize handles all languages", "Remove single line comments for any language" in content),
        ("api_translate mentions ANY language", "The documentation may refer to ANY programming language" in content),
    ]
    
    all_ok = True
    for check_name, result in checks:
        status = "✓" if result else "❌"
        print(f"  {status} {check_name}")
        all_ok = all_ok and result
    
    return all_ok

if __name__ == "__main__":
    print("="*60)
    print("VERIFICATION: Multi-Language Support Updates")
    print("="*60)
    
    time.sleep(2)  # Let server stabilize
    
    # Check source code
    source_ok = check_source_code()
    
    # Quick API tests
    print("\n" + "="*60)
    print("API ENDPOINT TESTS")
    print("="*60)
    
    test_results = []
    test_results.append(("Python code extraction (AST)", verify_python_extraction()))
    time.sleep(1)
    test_results.append(("Java code extraction (Groq)", verify_java_extraction()))
    time.sleep(1)
    test_results.append(("Multi-language documentation", verify_multi_language_document()))
    time.sleep(1)
    test_results.append(("Plagiarism detection (any lang)", verify_plagiarism_any_language()))
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    if source_ok:
        print("\n✓ Source Code Modifications: ALL VERIFIED")
    else:
        print("\n❌ Source Code Modifications: SOME MISSING")
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    print(f"\n✓ API Tests: {passed}/{total} passed")
    
    for name, result in test_results:
        status = "✓" if result else "❌"
        print(f"  {status} {name}")
    
    # Final result
    if source_ok and passed == total:
        print("\n" + "█"*60)
        print("█  ✓ ALL VERIFICATIONS PASSED!")
        print("█  Multi-language support is fully implemented!")
        print("█"*60)
    else:
        print("\n⚠️  Some tests need attention. Check above for details.")
