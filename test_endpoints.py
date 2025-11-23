#!/usr/bin/env python3
"""
Simple script to test API endpoints.
Usage: python test_endpoints.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health():
    """Test health endpoint."""
    print_section("Testing GET /health")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_save_company_profile():
    """Test saving a company profile."""
    print_section("Testing POST /save_company_profile")

    payload = {
        "domain": "testcompany.com",
        "company_profile": {
            "name": "Test Company",
            "description": "A test company for API testing",
            "core_business": {
                "industry": "Technology",
                "description": "Software testing"
            }
        },
        "solutions_profile": [
            {
                "Title": "Test Product",
                "Description": "Main test product",
                "Key_Features": ["Testing", "Automation"]
            }
        ],
        "analysis_metadata": {
            "source": "test",
            "timestamp": "2025-11-23"
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/save_company_profile",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_company_profile():
    """Test getting a company profile."""
    print_section("Testing GET /company_profile")

    try:
        response = requests.get(f"{BASE_URL}/company_profile?domain=testcompany.com")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_solutions():
    """Test getting solutions."""
    print_section("Testing GET /solutions")

    try:
        response = requests.get(f"{BASE_URL}/solutions?domain=testcompany.com")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_update_solution():
    """Test updating a solution."""
    print_section("Testing PUT /solutions")

    payload = {
        "solution": {
            "Title": "Test Product",
            "Description": "Updated main test product",
            "Key_Features": ["Testing", "Automation", "New Feature"]
        }
    }

    try:
        response = requests.put(
            f"{BASE_URL}/solutions?domain=testcompany.com",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_add_competitor():
    """Test adding a competitor."""
    print_section("Testing POST /competitors")

    payload = {
        "competitor": {
            "domain": "competitor-test.com",
            "solutions": [
                {
                    "Title": "Competitor Product",
                    "Description": "Their main product"
                }
            ]
        }
    }

    try:
        response = requests.post(
            f"{BASE_URL}/competitors?domain=testcompany.com",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_competitors():
    """Test getting competitors."""
    print_section("Testing GET /competitors")

    try:
        response = requests.get(f"{BASE_URL}/competitors?domain=testcompany.com")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_category_observed():
    """Test recording a category observation."""
    print_section("Testing POST /category_observed")

    payload = {
        "category_label": "Test Category",
        "description": "A test category for testing purposes"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/category_observed?domain=testcompany.com",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_notifications():
    """Test getting notifications."""
    print_section("Testing GET /notifications")

    try:
        response = requests.get(f"{BASE_URL}/notifications?domain=testcompany.com")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  API ENDPOINT TESTING")
    print("  Base URL:", BASE_URL)
    print("="*60)

    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to the API server!")
        print("   Make sure the server is running: python backend/app.py")
        sys.exit(1)

    tests = [
        ("Health Check", test_health),
        ("Save Company Profile", test_save_company_profile),
        ("Get Company Profile", test_get_company_profile),
        ("Get Solutions", test_get_solutions),
        ("Update Solution", test_update_solution),
        ("Add Competitor", test_add_competitor),
        ("Get Competitors", test_get_competitors),
        ("Record Category Observation", test_category_observed),
        ("Get Notifications", test_get_notifications),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results.append((name, False))

    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {name}")

    print(f"\n{'='*60}")
    print(f"  Total: {passed}/{total} tests passed")
    print(f"{'='*60}\n")

    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
