import json
from src.prompts.source_researcher_prompt import SOURCE_RESEARCHER_SYSTEM_PROMPT

class SourceResearcher:
    def __init__(self, llm_client=None):
        self.system_prompt = SOURCE_RESEARCHER_SYSTEM_PROMPT
        self.llm_client = llm_client

    def run(self, client_brief: dict, research_request: str = "", retrieved_material: str = "") -> dict:
        """
        Executes the Source Researcher agent and returns formatted factual research JSON.
        """
        user_message = {
            "client_brief": client_brief,
            "source_research_request": research_request,
            "retrieved_source_material": retrieved_material
        }
        
        if self.llm_client:
            raw_response = self.llm_client.generate(
                system=self.system_prompt,
                prompt=json.dumps(user_message)
            )
            return json.loads(raw_response)
        
        # Fallback response for offline testing
        return {
            "source_research": {
                "research_summary": "Sample source research summary.",
                "claims": []
            },
            "conflicting_evidence": [],
            "missing_information": []
        }