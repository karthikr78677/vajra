import os
import pytest
from knowledge_base.ingest import ingest_all, chunk_text, collection as ingest_collection
from knowledge_base.retrieve import search_knowledge_base, format_for_prompt

def test_ingest_populates_db():
    # Run the ingestion process
    ingest_all()
    
    # Check that chunks were populated in ChromaDB
    count = ingest_collection.count()
    assert count > 0, "ChromaDB collection should have more than 0 chunks after ingestion."

def test_search_compressor_query():
    query = "How to safely restart the compressor and check vibration?"
    results = search_knowledge_base(query, k=1)
    
    assert len(results) > 0, "Should return at least 1 result."
    assert "SOP_Compressor_Restart.txt" in results[0]["source"], \
        f"Expected SOP_Compressor_Restart.txt, but got {results[0]['source']}"

def test_search_valve_query():
    query = "What kind of grease should be used for rising stem gate valves?"
    results = search_knowledge_base(query, k=1)
    
    assert len(results) > 0, "Should return at least 1 result."
    assert "Manual_Valve_Maintenance.txt" in results[0]["source"], \
        f"Expected Manual_Valve_Maintenance.txt, but got {results[0]['source']}"

def test_search_vendor_approval_query():
    query = "Which vendor is approved for high-pressure spiral wound gaskets in 2024?"
    results = search_knowledge_base(query, k=1)
    
    assert len(results) > 0, "Should return at least 1 result."
    assert "Correspondence_Vendor_Approval_2024.txt" in results[0]["source"], \
        f"Expected Correspondence_Vendor_Approval_2024.txt, but got {results[0]['source']}"

def test_nonsense_query_does_not_crash():
    query = "lkjsdflkjsdflkjsdfoi1234908usdf"
    results = search_knowledge_base(query, k=3)
    
    # It should not crash, and it will return some closest vector (even if not highly relevant)
    assert isinstance(results, list), "Should return a list"
    
    formatted = format_for_prompt(results)
    assert isinstance(formatted, str), "Should format to a string successfully"

def test_chunking_logic():
    # Quick unit test for chunk_text
    dummy_text = "word " * 450
    chunks = chunk_text(dummy_text, chunk_size=100, overlap=20)
    
    assert len(chunks) > 1
    # Check that chunks have roughly the correct word count
    assert len(chunks[0].split()) == 100
