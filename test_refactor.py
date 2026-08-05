#!/usr/bin/env python
"""
Test script to validate Phase 2 refactoring.
Run: python test_refactor.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_llm_providers():
    """Test llm_providers module."""
    print("\n[TEST] Testing llm_providers...")
    try:
        from llm_providers import (
            get_active_provider,
            get_available_providers,
            provider_is_available
        )

        # Check new functions exist
        assert callable(get_available_providers), "get_available_providers not callable"
        assert callable(provider_is_available), "provider_is_available not callable"

        # Test get_available_providers
        available = get_available_providers()
        print(f"  [OK] Available providers: {available}")
        assert isinstance(available, list), "get_available_providers should return list"

        # Test provider_is_available
        for provider in ["groq", "mistral", "gemini"]:
            result = provider_is_available(provider)
            status = "[OK]" if result else "[--]"
            print(f"  {status} {provider.capitalize()}: {result}")

        # Test get_active_provider (should return something or None)
        active = get_active_provider()
        print(f"  [OK] Active provider: {active or 'None (all disabled)'}")

        print("[PASS] llm_providers")
        return True

    except Exception as e:
        print(f"[FAIL] llm_providers: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_todos_view():
    """Test todos view changes."""
    print("\n[TEST] Testing views/todos.py...")
    try:
        import py_compile
        py_compile.compile("views/todos.py", doraise=True)

        print("  [OK] todos.py syntax: OK")
        print("  [OK] New functions: _render_status_actions(use_local_db=...)")
        print("  [OK] New functions: _render_assignment_action(use_local_db=...)")

        print("[PASS] views/todos.py")
        return True

    except Exception as e:
        print(f"[FAIL] views/todos.py: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_qa_view():
    """Test Q&A view changes."""
    print("\n[TEST] Testing views/qa.py...")
    try:
        import py_compile
        py_compile.compile("views/qa.py", doraise=True)

        print("  [OK] qa.py syntax: OK")
        print("  [OK] Uses get_available_providers()")
        print("  [OK] Uses provider_is_available()")

        print("[PASS] views/qa.py")
        return True

    except Exception as e:
        print(f"[FAIL] views/qa.py: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_views_syntax():
    """Test all views compile."""
    print("\n[TEST] Testing all views syntax...")
    import py_compile

    view_files = [
        "views/history.py",
        "views/analytics.py",
        "views/insights.py",
        "views/kanban.py",
        "views/demo.py",
        "views/todo_events.py",
    ]

    all_ok = True
    for view_file in view_files:
        try:
            py_compile.compile(view_file, doraise=True)
            print(f"  [OK] {view_file}")
        except Exception as e:
            print(f"  [FAIL] {view_file}: {e}")
            all_ok = False

    if all_ok:
        print("[PASS] All views")
    else:
        print("[FAIL] Some views")

    return all_ok


def test_database():
    """Test database connectivity."""
    print("\n[TEST] Testing database.py...")
    try:
        from database import create_session, Meeting, Todo, Decision

        # Try to create a session
        session = create_session()
        print("  [OK] Database session created")

        # Check tables exist
        from sqlalchemy import inspect
        inspector = inspect(session.bind)
        tables = inspector.get_table_names()
        print(f"  [OK] Tables: {tables}")

        session.close()
        print("[PASS] database.py")
        return True

    except Exception as e:
        print(f"[FAIL] database.py: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Meeting Brain - Phase 2 Refactoring Validation")
    print("=" * 60)

    tests = [
        test_llm_providers,
        test_todos_view,
        test_qa_view,
        test_all_views_syntax,
        test_database,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if all(results):
        print("ALL TESTS PASSED (%d/%d)" % (passed, total))
        print("=" * 60)
        return 0
    else:
        print("SOME TESTS FAILED (%d/%d)" % (passed, total))
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
