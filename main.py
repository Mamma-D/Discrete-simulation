"""this script simulates a sequence of pretty complex events including
consumers, companies, factories and economics decision makings"""

import mesa

class Consumer(mesa.Agent):
    """this class represents the consumers"""

    def __init__(self, model, wealth):
        super().__init__(model)
        self.wealth = wealth

class Company(mesa.Agent):
    """this class represents companies"""

    def __init__(self, model):
        super().__init__(model)

    class Factory(mesa.Agent):
        """this class represents manufacturing factories"""

        def __init__(self, model):
            super().__init__(model)
