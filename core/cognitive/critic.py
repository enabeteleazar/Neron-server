"""Critic engine skeleton.

Responsible for evaluating candidate plans or actions.

TODO:
- Provide scoring interface
- Connect to DecisionEngine
"""

class Critic:
    """Simple critic that can score plans.

    Methods are placeholders and must not perform destructive actions.
    """

    def __init__(self):
        pass

    def score(self, plan, context=None):
        """Return a numeric score for a plan. Higher is better.

        Current implementation returns 0.0 (neutral).
        """
        return 0.0
