"""
Test script to verify the FAISS-based RAG system works correctly.
Run this after installation to verify everything is set up properly.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test 1: Verify all imports work"""
    logger.info("=" * 70)
    logger.info("TEST 1: Checking imports...")
    logger.info("=" * 70)
    
    try:
        from app.services.claude_chat_rag import (
            medicine_chat_rag,
            knowledge_base,
            llm_provider,
            add_to_knowledge_base,
            process_prescription_for_kb
        )
        logger.info("✅ All imports successful!")
        return True
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during import: {e}")
        return False


def test_knowledge_base():
    """Test 2: Verify knowledge base initialization"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Checking knowledge base initialization...")
    logger.info("=" * 70)
    
    try:
        from app.services.claude_chat_rag import knowledge_base
        
        if knowledge_base.vector_store is None:
            logger.error("❌ Vector store not initialized")
            return False
        
        logger.info("✅ Vector store initialized!")
        
        # Test retrieval
        logger.info("Testing context retrieval...")
        context = knowledge_base.retrieve("What does BD mean in prescriptions?", k=2)
        
        if context and len(context) > 0:
            logger.info(f"✅ Retrieved {len(context)} characters of context")
            logger.info(f"Sample: {context[:200]}...")
            return True
        else:
            logger.warning("⚠️ Retrieved empty context (this might be OK on first run)")
            return True
    
    except Exception as e:
        logger.error(f"❌ Knowledge base test failed: {e}", exc_info=True)
        return False


def test_llm_providers():
    """Test 3: Verify LLM providers are configured"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Checking LLM providers...")
    logger.info("=" * 70)
    
    try:
        from app.services.claude_chat_rag import llm_provider
        
        if not llm_provider.providers:
            logger.error("❌ No LLM providers configured!")
            logger.error("   Please set at least one in .env:")
            logger.error("   - ANTHROPIC_API_KEY=sk-ant-...")
            logger.error("   - GROQ_API_KEY=gsk_...")
            logger.error("   - OPENROUTER_API_KEY=sk-or-...")
            return False
        
        logger.info(f"✅ Found {len(llm_provider.providers)} provider(s):")
        for provider in llm_provider.providers:
            logger.info(f"   - {provider['name']} (priority: {provider['priority']})")
        
        # Test getting LLM
        llm, provider_name = llm_provider.get_llm()
        logger.info(f"✅ Using primary provider: {provider_name}")
        return True
    
    except RuntimeError as e:
        logger.error(f"❌ LLM provider check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return False


def test_medical_chat_rag():
    """Test 4: Verify medicine_chat_rag function works"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 4: Testing medicine_chat_rag function...")
    logger.info("=" * 70)
    
    try:
        from app.services.claude_chat_rag import medicine_chat_rag
        
        logger.info("Sending test question: 'What does BD mean in prescriptions?'")
        
        result = medicine_chat_rag(
            question="What does BD mean in prescriptions?",
            chat_history=[]
        )
        
        if result.get("status") != "success":
            logger.error(f"❌ Chat failed with status: {result.get('status')}")
            return False
        
        logger.info(f"✅ Chat successful!")
        logger.info(f"Provider used: {result.get('provider_used')}")
        logger.info(f"Processing time: {result.get('metadata', {}).get('processing_time_ms')} ms")
        logger.info(f"\nAnswer (first 300 chars):")
        logger.info("-" * 70)
        answer = result.get('answer', '').split('\n\n')[0]  # Get first paragraph
        logger.info(answer[:300] + "...")
        logger.info("-" * 70)
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Chat test failed: {e}", exc_info=True)
        return False


def test_knowledge_base_add():
    """Test 5: Verify adding documents to knowledge base"""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 5: Testing knowledge base document addition...")
    logger.info("=" * 70)
    
    try:
        from app.services.claude_chat_rag import add_to_knowledge_base
        
        test_content = """
        Test Medicine Information:
        - Medicine: Test Drug
        - Dosage: 100 mg
        - Frequency: Once daily
        - Side effects: None known in this test
        """
        
        success = add_to_knowledge_base(test_content, metadata={"source": "test"})
        
        if success:
            logger.info("✅ Successfully added test document to knowledge base")
            return True
        else:
            logger.warning("⚠️ Failed to add document (this might indicate an issue)")
            return False
    
    except Exception as e:
        logger.error(f"❌ Knowledge base add test failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests"""
    logger.info("\n")
    logger.info("╔" + "=" * 68 + "╗")
    logger.info("║" + " FAISS-based RAG System - Verification Tests ".center(68) + "║")
    logger.info("╚" + "=" * 68 + "╝")
    
    tests = [
        ("Imports", test_imports),
        ("Knowledge Base", test_knowledge_base),
        ("LLM Providers", test_llm_providers),
        ("Medicine Chat RAG", test_medical_chat_rag),
        ("Knowledge Base Add", test_knowledge_base_add),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' crashed: {e}", exc_info=True)
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("=" * 70)
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n🎉 All tests passed! RAG system is ready to use!")
        logger.info("\nNext steps:")
        logger.info("1. Start your app: uvicorn app.main:app --reload")
        logger.info("2. Test the endpoint: POST /chat/medicine-chat")
        logger.info("3. Example question: 'What does BD mean in prescriptions?'")
        return 0
    else:
        logger.warning(f"\n⚠️ {total - passed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
