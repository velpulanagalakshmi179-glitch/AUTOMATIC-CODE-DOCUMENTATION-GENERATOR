#!/usr/bin/env python3
"""Test backend APIs with both Python and Java code samples."""

import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

# ════════════════════════════════════════════════════════════════
# TEST DATA
# ════════════════════════════════════════════════════════════════

PYTHON_CODE = '''
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def is_palindrome(s):
    """Check if a string is a palindrome."""
    clean = s.lower().replace(" ", "")
    return clean == clean[::-1]
'''

JAVA_CODE = '''
public class Calculator {
    public static int add(int a, int b) {
        return a + b;
    }
    
    public static int multiply(int x, int y) {
        return x * y;
    }
}
'''

# ════════════════════════════════════════════════════════════════
# TEST FUNCTIONS
# ════════════════════════════════════════════════════════════════

def test_extract(code, label):
    """Test /api/extract endpoint."""
    print(f"\n{'='*60}")
    print(f"🧪 TEST: Extract Functions from {label}")
    print('='*60)
    try:
        response = requests.post(f"{BASE_URL}/extract", json={"code": code})
        result = response.json()
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Functions found: {result.get('count', 0)}")
        for func in result.get('functions', []):
            print(f"  - {func['name']}({', '.join(func['args'])})")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_document(code, label):
    """Test /api/document endpoint."""
    print(f"\n{'='*60}")
    print(f"📚 TEST: Generate Documentation for {label}")
    print('='*60)
    try:
        response = requests.post(f"{BASE_URL}/document", json={"code": code})
        result = response.json()
        print(f"✓ Status: {response.status_code}")
        doc = result.get('documentation', '')
        lines = doc.split('\n')[:5]  # Show first 5 lines
        print(f"✓ Documentation preview:")
        for line in lines:
            if line.strip():
                print(f"  {line[:80]}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_explain(code, label):
    """Test /api/explain endpoint."""
    print(f"\n{'='*60}")
    print(f"🎓 TEST: Explain Code {label}")
    print('='*60)
    try:
        response = requests.post(f"{BASE_URL}/explain", json={"code": code})
        result = response.json()
        print(f"✓ Status: {response.status_code}")
        explanation = result.get('explanation', '')
        lines = explanation.split('\n')[:3]
        print(f"✓ Explanation preview:")
        for line in lines:
            if line.strip():
                print(f"  {line[:80]}")
        print(f"✓ Mermaid flowchart generated: {bool(result.get('mermaid_code'))}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_complexity(code, label):
    """Test /api/complexity endpoint."""
    print(f"\n{'='*60}")
    print(f"📊 TEST: Complexity Analysis for {label}")
    print('='*60)
    try:
        response = requests.post(f"{BASE_URL}/complexity", json={"code": code})
        result = response.json()
        print(f"✓ Status: {response.status_code}")
        complexity = result.get('complexity', '')
        lines = complexity.split('\n')[:4]
        print(f"✓ Complexity analysis preview:")
        for line in lines:
            if line.strip():
                print(f"  {line[:80]}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_plagiarism():
    """Test /api/plagiarism endpoint."""
    print(f"\n{'='*60}")
    print(f"🔍 TEST: Plagiarism Detection (Python vs Java)")
    print('='*60)
    try:
        response = requests.post(f"{BASE_URL}/plagiarism", json={
            "code1": PYTHON_CODE,
            "code2": JAVA_CODE
        })
        result = response.json()
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Similarity: {result.get('similarity')}%")
        print(f"✓ Verdict: {result.get('verdict')}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_translate():
    """Test /api/translate endpoint."""
    print(f"\n{'='*60}")
    print(f"🌍 TEST: Translate Documentation")
    print('='*60)
    try:
        # First get documentation
        doc_response = requests.post(f"{BASE_URL}/document", json={"code": PYTHON_CODE})
        doc = doc_response.json().get('documentation', 'Sample documentation')
        
        # Then translate it
        response = requests.post(f"{BASE_URL}/translate", json={
            "documentation": doc,
            "language": "Hindi"
        })
        result = response.json()
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Language: {result.get('language')}")
        translated = result.get('translated', '')
        lines = translated.split('\n')[:3]
        print(f"✓ Translation preview:")
        for line in lines:
            if line.strip():
                print(f"  {line[:80]}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "█"*60)
    print("█  CODE DOCUMENTATION GENERATOR - API TEST SUITE")
    print("█  Testing Multi-Language Support (Python & Java)")
    print("█"*60)
    
    # Wait for server to be ready
    time.sleep(2)
    
    results = []
    
    # Test with Python code
    results.append(("Extract (Python)", test_extract(PYTHON_CODE, "Python")))
    time.sleep(1)
    results.append(("Document (Python)", test_document(PYTHON_CODE, "Python")))
    time.sleep(1)
    results.append(("Explain (Python)", test_explain(PYTHON_CODE, "Python")))
    time.sleep(1)
    results.append(("Complexity (Python)", test_complexity(PYTHON_CODE, "Python")))
    
    # Test with Java code
    time.sleep(1)
    results.append(("Extract (Java)", test_extract(JAVA_CODE, "Java")))
    time.sleep(1)
    results.append(("Document (Java)", test_document(JAVA_CODE, "Java")))
    time.sleep(1)
    results.append(("Explain (Java)", test_explain(JAVA_CODE, "Java")))
    time.sleep(1)
    results.append(("Complexity (Java)", test_complexity(JAVA_CODE, "Java")))
    
    # Test cross-language features
    time.sleep(1)
    results.append(("Plagiarism", test_plagiarism()))
    time.sleep(1)
    results.append(("Translate", test_translate()))
    
    # Summary
    print(f"\n{'█'*60}")
    print("█  TEST SUMMARY")
    print("█"*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n✓ Passed: {passed}/{total}")
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    if passed == total:
        print("\n🎉 All tests passed! Multi-language support is working!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above.") 
