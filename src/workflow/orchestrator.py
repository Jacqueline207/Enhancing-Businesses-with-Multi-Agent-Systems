"""Workflow orchestrator."""


def run_workflow(client_brief):
    """Coordinate the Fieldstone agent workflow.

    TODO:
    1. Create workflow state.
    2. Run independent research tasks in parallel.
    3. Merge research into shared state.
    4. Run Writer.
    5. Run Critic.
    6. Route PASS toward approval/final output.
    7. Route FAIL to retry logic.
    """
    raise NotImplementedError
