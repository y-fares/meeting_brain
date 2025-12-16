"""
Test script for LLM providers abstraction.
Tests both Gemini and Groq providers.
"""

import os
from dotenv import load_dotenv
from llm_providers import llm_generate, llm_generate_json, load_groq_client

# Load environment variables
load_dotenv()

def test_groq_client_loading():
    """Test loading Groq client."""
    print("=" * 60)
    print("Test 1: Loading Groq Client")
    print("=" * 60)
    
    result = load_groq_client()
    if result:
        client, model = result
        print(f"✅ Groq client loaded successfully")
        print(f"   Model: {model}")
        print(f"   Client type: {type(client).__name__}")
    else:
        print("❌ Failed to load Groq client")
        print("   Check GROQ_API_KEY in .env file")
    print()


def test_llm_generate_gemini():
    """Test text generation with Gemini."""
    print("=" * 60)
    print("Test 2: Text Generation with Gemini")
    print("=" * 60)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️  GOOGLE_API_KEY not set, skipping Gemini test")
        print()
        return
    
    prompt = "Say hello in one sentence."
    
    try:
        result = llm_generate("gemini", prompt)
        if result.startswith("Error:"):
            print(f"❌ Gemini generation failed: {result}")
        else:
            print(f"✅ Gemini generation successful")
            print(f"   Response: {result[:100]}...")
    except Exception as exc:
        print(f"❌ Exception during Gemini generation: {exc}")
    print()


def test_llm_generate_groq():
    """Test text generation with Groq."""
    print("=" * 60)
    print("Test 3: Text Generation with Groq")
    print("=" * 60)
    
    if not os.getenv("GROQ_API_KEY"):
        print("⚠️  GROQ_API_KEY not set, skipping Groq test")
        print()
        return
    
    prompt = "Say hello in one sentence."
    
    try:
        result = llm_generate("groq", prompt)
        if result.startswith("Error:"):
            print(f"❌ Groq generation failed: {result}")
        else:
            print(f"✅ Groq generation successful")
            print(f"   Response: {result[:100]}...")
    except Exception as exc:
        print(f"❌ Exception during Groq generation: {exc}")
    print()


def test_llm_generate_json():
    """Test JSON generation with both providers."""
    print("=" * 60)
    print("Test 4: JSON Generation")
    print("=" * 60)
    
    prompt = """Return a JSON object with:
- "greeting": a greeting message
- "number": the number 42"""
    
    # Test Gemini
    if os.getenv("GOOGLE_API_KEY"):
        print("Testing Gemini JSON generation...")
        try:
            result = llm_generate_json("gemini", prompt)
            if result:
                print(f"✅ Gemini JSON generation successful")
                print(f"   Result: {result}")
            else:
                print("❌ Gemini JSON generation returned empty dict")
        except Exception as exc:
            print(f"❌ Exception during Gemini JSON generation: {exc}")
    else:
        print("⚠️  GOOGLE_API_KEY not set, skipping Gemini JSON test")
    print()
    
    # Test Groq
    if os.getenv("GROQ_API_KEY"):
        print("Testing Groq JSON generation...")
        try:
            result = llm_generate_json("groq", prompt)
            if result:
                print(f"✅ Groq JSON generation successful")
                print(f"   Result: {result}")
            else:
                print("❌ Groq JSON generation returned empty dict")
        except Exception as exc:
            print(f"❌ Exception during Groq JSON generation: {exc}")
    else:
        print("⚠️  GROQ_API_KEY not set, skipping Groq JSON test")
    print()


def test_qa_engine():
    """Test Q&A engine with both providers."""
    print("=" * 60)
    print("Test 5: Q&A Engine Integration")
    print("=" * 60)
    
    try:
        from database import create_session
        from qa_engine import answer_question
        
        session = create_session()
        
        # Test with Gemini
        if os.getenv("GOOGLE_API_KEY"):
            print("Testing Q&A with Gemini...")
            try:
                result = answer_question(session, "How many meetings are in the database?", provider="gemini")
                answer = result.get("answer", "")
                if answer and not answer.startswith("Error:"):
                    print(f"✅ Q&A with Gemini successful")
                    print(f"   Answer preview: {answer[:150]}...")
                else:
                    print(f"⚠️  Q&A with Gemini: {answer}")
            except Exception as exc:
                print(f"❌ Exception during Q&A with Gemini: {exc}")
        else:
            print("⚠️  GOOGLE_API_KEY not set, skipping Gemini Q&A test")
        print()
        
        # Test with Groq
        if os.getenv("GROQ_API_KEY"):
            print("Testing Q&A with Groq...")
            try:
                result = answer_question(session, "How many meetings are in the database?", provider="groq")
                answer = result.get("answer", "")
                if answer and not answer.startswith("Error:"):
                    print(f"✅ Q&A with Groq successful")
                    print(f"   Answer preview: {answer[:150]}...")
                else:
                    print(f"⚠️  Q&A with Groq: {answer}")
            except Exception as exc:
                print(f"❌ Exception during Q&A with Groq: {exc}")
        else:
            print("⚠️  GROQ_API_KEY not set, skipping Groq Q&A test")
        
        session.close()
    except Exception as exc:
        print(f"❌ Exception during Q&A engine test: {exc}")
    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LLM Providers Test Suite")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("Environment Check:")
    print(f"  GOOGLE_API_KEY: {'✅ Set' if os.getenv('GOOGLE_API_KEY') else '❌ Not set'}")
    print(f"  GROQ_API_KEY: {'✅ Set' if os.getenv('GROQ_API_KEY') else '❌ Not set'}")
    print(f"  GEMINI_MODEL: {os.getenv('GEMINI_MODEL', 'gemini-pro (default)')}")
    print(f"  GROQ_MODEL: {os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant (default)')}")
    print()
    
    # Run tests
    test_groq_client_loading()
    test_llm_generate_gemini()
    test_llm_generate_groq()
    test_llm_generate_json()
    test_qa_engine()
    
    print("=" * 60)
    print("Test Suite Complete")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. If tests pass, try the Q&A view in Streamlit")
    print("2. Select different providers in the Q&A dropdown")
    print("3. Compare answers from Gemini vs Groq")


if __name__ == "__main__":
    main()

