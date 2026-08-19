"""Shared workflow state.

This module will define the information shared between agents.
"""


class WorkflowState:
    """Placeholder for shared agent workflow state."""

    def __init__(self):
        self.client_brief = None
        self.research_sources = []
        self.key_facts = []
        self.audience_context = []
        self.writer_draft = None
        self.critic_verdict = None
        self.critic_issues = []
        self.revision_instructions = []
        self.retry_count = 0
        self.final_status = None
