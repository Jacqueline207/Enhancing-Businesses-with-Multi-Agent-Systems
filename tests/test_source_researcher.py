import pytest
from src.integrations.research_tools import get_mock_source_research

def test_source_researcher_schema_keys():
    data = get_mock_source_research()
    
    # Verify top-level root keys
    assert "source_research" in data
    assert "conflicting_evidence" in data
    assert "missing_information" in data
    
    # Verify nested source_research dictionary
    sr = data["source_research"]
    assert "research_summary" in sr
    assert "claims" in sr
    assert isinstance(sr["claims"], list)

def test_source_researcher_claim_fields():
    data = get_mock_source_research()
    claims = data["source_research"]["claims"]
    
    assert len(claims) > 0
    claim = claims[0]
    
    # Verify identifier format
    assert claim["claim_id"].startswith("R-")
    
    # Verify allowed enum fields
    allowed_types = {
        "fact", "statistic", "quote", "date", 
        "study_finding", "event", "causal_claim", "attributed_opinion"
    }
    assert claim["claim_type"] in allowed_types
    assert claim["confidence"] in {"high", "medium", "low"}
    
    # Verify uncertainty and conflict fields
    assert "uncertainty_note" in claim
    assert isinstance(claim["conflicts_with"], list)