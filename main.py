"""this script simulates a sequence of pretty complex events including
consumers, companies, factories and economics decision makings"""

import mesa
import random
class Consumer(mesa.Agent):
    """this class represents the consumers"""

    def __init__(self, model, salary, mpc):
        super().__init__(model)
        self.wealth = salary
        self.salary = salary
        self.mpc = mpc

    def action(self):
        """this method is for putting all actions a consumer does in a week"""

        if self.model.time % 4 == 0:
            self.get_paid(self.salary)

    def get_paid(self, salary):
        """this method adds the monthly payment to the consumer's wealth"""

        self.wealth += salary

    def __repr__(self) -> str:
        return f"Consumer(id={self.unique_id}, wealth={self.wealth}, MPC={self.mpc}, salary={self.salary})"
class Company(mesa.Agent):
    """this class represents companies"""

    def __init__(self, model):
        super().__init__(model)

    class Factory(mesa.Agent):
        """this class represents manufacturing factories"""

        def __init__(self, model):
            super().__init__(model)

class TheModel(mesa.Model):
    """this class is a initial model"""

    def __init__(self, consumers, companies):
        super().__init__()

        generators = {}
        for index_name in consumers['indexes'].keys():

            index_generator = generate_number(consumers, index_name)

            generators[index_name] = index_generator

        for _ in range(consumers['population']):

            person = Consumer(
                self,
                salary=next(generators['salary']),
                mpc=next(generators['MPC'])
                )

            self.agents.add(person)

    def step(self):

        self.agents.shuffle_do("action")


def generate_number(category: dict, index: str):

    for proportion, ranges in category['indexes'][index].items():

        percentage = proportion / len(ranges) if len(ranges) > 0 else proportion

        this_many = int(category['population'] * percentage)

        if isinstance(ranges[0], (int, float)):

            for _ in range(this_many):
                yield random.uniform(ranges[0], ranges[1])

        else:

            for spec_range in ranges:

                for _ in range(this_many):
                    yield  random.uniform(spec_range[0], spec_range[1])
