"""this script simulates a sequence of pretty complex events including
consumers, companies, factories and economics decision makings"""

import random
import mesa
import pandas as pd
import sympy as sp


class Consumer(mesa.Agent):
    """this class represents the consumers"""

    def __init__(self, model, salary, mpc):
        super().__init__(model)
        self.wealth = salary
        self.salary = salary
        self.mpc = mpc
        self.essentials = round(250 + (self.salary * 0.25), 2)
        self.savings = 0
        self.position = {}
        self.live_utile = 0

    def action(self):
        """this method is for putting all actions a consumer does in a week"""

        if self.model.time % 4 == 0:
            self.get_paid(self.salary)

    def coefficient(self, x):
        """this method calculates the coefficient for the utility function based on the consumer's current utility"""

        return lambda x: -0.07 * x + 0.8

    def get_paid(self, salary):
        """this method adds the monthly payment to the consumer's wealth"""

        print(f"{self.unique_id} got paid {salary}$")

        takehome_salary = salary - self.essentials
        print(f"{self.unique_id} spent {self.essentials}$ on essentials")

        remaining_salary = self.save(takehome_salary)

        self.wealth += remaining_salary
        print(f"{self.unique_id}'s wealth increased by {remaining_salary}$")

    def save(self, received_salary):
        """this method mimics saving money in an account"""

        saving = round((1 - self.mpc) * received_salary, 2)

        self.savings += saving
        print(f"{self.unique_id} saved {saving}$")

        return round((received_salary - saving), 2)

    def consume(self):
        """this method mimics spending money on goods and services"""

        # todo Need a way to check if the person has enough money to even begin the consume process (i thought of checking with the
        # cheapest item being sold but that takes long)
        # maybe it doesn't even need a check because the consumer will just not be able to buy anything if they don't have enough money

        # Added a condition to keep consume
        while self.live_utile < 9:

            # Checking available companies in the market (don't have multiple markets yet)

            companies = self.model.agents.get_type(Company)
            companies_count = len(companies)

            # * If it's a two company market, the consumer will choose the company with the lowest cost for them to buy from
            if companies_count > 0:

                # * In the specific case of a two company market, this block happens
                if companies_count == 2:

                    pos = round(random.uniform(0.00, 1.00), 2)
                    self.position["market"] = pos

                    # * Linear city model in Game Theory to determine which company to buy from
                    cost_for_firm_1 = (
                        companies[0].price + companies[0].differ * (pos) ** 2
                    )
                    cost_for_firm_2 = (
                        companies[1].price + companies[1].differ * (1 - pos) ** 2
                    )

                    if (
                        cost_for_firm_1 < cost_for_firm_2
                        and self.wealth >= cost_for_firm_1
                    ):

                        chosen_company = companies[0]

                        self.purchase(chosen_company)

                        self.utile(chosen_company, pos)

                    else:
                        break

    def purchase(self, company_seller):
        """this method mimics the purchase of a good or service from a company"""

        self.wealth -= company_seller.price
        company_seller.add_transaction(self)

    def utile(self, company_seller, pos):
        """this method calculates and adds the utility of a good or service purchased from a company"""

        price = company_seller.price

        good_utility = int(round(pos * price, 0))

        coefficient = self.coefficient(self.live_utile)

        self.live_utile += good_utility * coefficient

    def __repr__(self) -> str:
        return f"Consumer(id={self.unique_id}, wealth={self.wealth}, MPC={self.mpc}, salary={self.salary})"


class Company(mesa.Agent):
    """this class represents companies"""

    def __init__(self, model, given_differ):
        super().__init__(model)

        # todo Need a way to determine a companies starting wealth, maybe just pass in a random amount
        # todo of starting investment
        self.wealth = 0

        self.differ = given_differ

        # todo Need to make a "set_price" method that sets price based on other companies...
        self.price = 0

        self.transactions = pd.DataFrame(
            {"consumer_id": [], "price": [], "time": []}
        )

        # todo We need a way to determine the total cost function of a company
        self.total_cost = sp.Function("C")(
            sp.symbols("FC"), sp.Symbol("Q"), sp.symbols("b")
        )

        self.marginal_cost = sp.diff(self.total_cost, sp.Symbol("Q"))

        self.demand_curve = sp.Function("Q")(
            sp.Symbol("a"), sp.Symbol("p"), sp.Symbol("b")
        )

    def action(self):
        """this method is for putting all actions a company does in a week"""

        self.set_price()

    def set_price(self):
        """this method sets the price of a good or service based on the company's total cost and desired profit margin"""

        companies = self.model.agents.get_type(Company)

        if len(companies) == 2:

            self.price = self.find_duopoly_price()

    def add_transaction(self, consumer):
        """this method adds the transaction to the company's wealth"""

        self.wealth += self.price
        self.transactions = pd.concat(
            [
                self.transactions,
                pd.DataFrame(
                    [
                        {
                            "consumer_id": consumer.unique_id,
                            "price": self.price,
                            "time": self.model.time,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    def find_duopoly_price(self):
        """this method is for companies to find their optimal price based on Game Theory models"""

        competitor = next(
            iter(
                agent for agent in self.model.agents.get_type(Company) if agent != self
            )
        )
        mrc = self.marginal_cost
        mono_price = self.calculate_monopoly_price()
        t = self.differ

        if not competitor.price:

            self.price = mono_price
        elif competitor.price:

            best_response = (competitor.price + t + mrc) / 2

            if best_response > mono_price:
                br = mono_price

            elif best_response < mrc:
                br = mrc

            else:
                br = best_response

            return br

    def calculate_monopoly_price(self):
        """this method calculates the monopoly price for a company"""

        q = sp.Symbol("Q")
        marginal_cost = self.marginal_cost
        total_revenue = self.demand_curve * q
        marginal_revenue = sp.diff(total_revenue, q)

        system_eq = sp.Eq(marginal_revenue, marginal_cost)
        solution = sp.solve(system_eq, q)

        mono_price = self.demand_curve.subs({q: solution[0]})

        return mono_price

    def R_D(self):
        """this method is for companies to invest in research and development"""

        # todo Need to implement a way for companies to invest in R&D and how it affects their production and costs

        pass

    # todo Need to work on factory class, maybe even abandon it for now, for simplicity
    class Factory(mesa.Agent):
        """this class represents manufacturing factories"""

        def __init__(self, model):
            super().__init__(model)


class TheModel(mesa.Model):
    """this class is a initial model"""

    def __init__(self, consumers, companies):
        super().__init__()

        self.datacollector = mesa.DataCollector(
            agenttype_reporters={
                Consumer: {"Wealth": "wealth", "Savings": "savings"},
                Company: {"Wealth": "wealth", "Price": "price"},
            }
        )

        # * Creating the consumers in the model
        generators = {}
        for index_name in consumers["indexes"].keys():

            index_generator = generate_number(consumers, index_name)

            generators[index_name] = index_generator

        for _ in range(consumers["population"]):

            person = Consumer(
                self, salary=next(generators["salary"]), mpc=next(generators["MPC"])
            )

            self.agents.add(person)

        # * Creating the companies in the model

        for _ in range(companies["population"]):

            company = Company(
                self, given_differ=companies["indexes"]["differentiation"]
            )

            self.agents.add(company)

    def step(self):

        self.datacollector.collect(self)
        self.agents.get_type(Company).shuffle_do("action")
        self.agents.get_type(Consumer).shuffle_do("action")


def generate_number(category: dict, index: str):

    while True:
        for proportion, ranges in category["indexes"][index].items():

            percentage = proportion / len(ranges) if len(ranges) > 0 else proportion

            this_many = int(category["population"] * percentage)

            if isinstance(ranges[0], (int, float)):

                for _ in range(this_many):
                    yield round(random.uniform(ranges[0], ranges[1]), 2)

            else:

                for spec_range in ranges:

                    for _ in range(this_many):
                        yield round(random.uniform(spec_range[0], spec_range[1]), 2)
