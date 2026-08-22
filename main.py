"""this script simulates a sequence of pretty complex events including
consumers, companies, factories and economics decision makings"""

import mesa

class Consumer(mesa.Agent):
    """this class represents the consumers"""

    def __init__(self, model, salary, mcp):
        super().__init__(model)
        self.wealth = salary
        self.salary = salary
        self.mcp = mcp

    def step(self):
        """this method is for putting all actions a consumer does in a week"""

        if self.model.time % 4:
            self.get_paid(self.salary)

    def get_paid(self, salary):
        """this method adds the monthly payment to the consumer's wealth"""

        self.wealth += salary
class Company(mesa.Agent):
    """this class represents companies"""

    def __init__(self, model):
        super().__init__(model)

    class Factory(mesa.Agent):
        """this class represents manufacturing factories"""

        def __init__(self, model):
            super().__init__(model)
