def get_mock_source_research():
    """Provides mock source research conforming to the revised schema."""
    return {
        "source_research": {
            "research_summary": "Verified revenue and market growth data from internal and third-party reports.",
            "claims": [
                {
                    "claim_id": "R-001",
                    "claim_type": "statistic",
                    "claim": "Company revenue grew 12 percent year-over-year in Q3.",
                    "evidence": "Q3 Financial Performance Summary, Section 2.1.",
                    "source_title": "Q3 Financial Performance Summary",
                    "source_publisher": "Fieldstone Analytics",
                    "source_url_or_reference": "https://internal.fieldstone.com/reports/q3",
                    "source_date": "2026-08-01",
                    "confidence": "high",
                    "uncertainty_note": "",
                    "conflicts_with": []
                },
                {
                    "claim_id": "R-002",
                    "claim_type": "statistic",
                    "claim": "Market share expanded by 3 percent.",
                    "evidence": "Preliminary industry assessment indicates a 3% shift.",
                    "source_title": "Industry Benchmark Report",
                    "source_publisher": "Market Insights Group",
                    "source_url_or_reference": "https://marketinsights.com/2026-benchmarks",
                    "source_date": "2026-07-15",
                    "confidence": "medium",
                    "uncertainty_note": "Preliminary figure subject to final quarterly audit.",
                    "conflicts_with": []
                }
            ]
        },
        "conflicting_evidence": [],
        "missing_information": []
    }