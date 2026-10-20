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
        self.mpc = mpc
        self.savings = 0
        self.wealth = self.save(salary)
        self.salary = salary
        self.essentials = round(250 + (self.salary * 0.25), 2)
        self.positions = {}
        self.live_utile = 0
        self.memory = {}

    def action(self):
        """this method is for putting all actions a consumer does in a DAY"""

        self.consume()
        if self.model.time % 30 == 0:
            self.get_paid(self.salary)
        if self.model.time % 2 == 0:
            self.balance_utile()

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

    def balance_utile(self):
        """this method mimics the decrease of utility over time"""

        self.live_utile = 0

        return self.live_utile

    def update_memory(self, market, company):
        """this method updates the person memory with what they bought and when they bought it distinguished by markets"""

        # logs that this consumer bought a good from the market in this time
        self.memory[market] = (self.model.time, company)

    def consume(self):
        """this method mimics spending money on goods and services"""

        # * -----Stage 1: Checking if we even want to begin consuming-----
        # Added a condition to keep consume
        while self.live_utile < 10:
            before_utile = self.live_utile

            # * -----Stage 2: Choosing a market to start-----
            all_companies = self.model.agents.select(agent_type=Company).groupby(
                "market"
            )

            # Entered the market, found the companies
            for market, companies in all_companies:

                companies_count = len(companies)

                #! -----Stage 2.2: Buying process starts here-----

                # * In the specific case of a two company market, this block happens
                if companies_count == 2:

                    chosen_company = self.duopoly_choose(companies)

                    if self.wealth >= chosen_company.price:

                        self.purchase(chosen_company)

                        self.assign_utile()

                        self.update_memory(market, chosen_company)

                    else:
                        # at any 'buying process' if a transaction fails, we should leave the consume process
                        continue

                        #! -----Buying process ends here-----
            if self.live_utile == before_utile:
                break

    def duopoly_choose(self, companies):
        """this method is for deciding which company to choose for buying"""

        if companies[0].market not in self.positions:
            pos = round(random.uniform(0.00, 1.00), 2)
            self.positions[companies[0].market] = pos

        else:
            pos = self.positions[companies[0].market]

        # * Linear city model in Game Theory to determine which company to buy from
        cost_for_firm_1 = companies[0].price + companies[0].differ * (pos) ** 2
        cost_for_firm_2 = companies[1].price + companies[1].differ * (1 - pos) ** 2

        chosen_company = (
            companies[0] if cost_for_firm_1 < cost_for_firm_2 else companies[1]
        )

        return chosen_company

    def use_savings(self):
        """this method mimics the thought process of deciding how much to use savings"""

        # todo fill this

        pass

    def purchase(self, company_seller):
        """this method mimics the purchase of a good or service from a company"""

        self.wealth = round(self.wealth - company_seller.price)
        company_seller.add_transaction(self)

        print(
            f"agent {self.unique_id} purchased from company {company_seller.name} for {company_seller.price}$"
        )

    def assign_utile(self):
        """this method calculates and adds the utility of a good or service purchased from a company"""

        U_MAX = 10
        RATE = 0.5
        quality_factor = 1

        increase = quality_factor * (RATE * (U_MAX - self.live_utile))

        self.live_utile += increase

        return self.live_utile


class Company(mesa.Agent):
    """this class represents companies"""

    def __init__(
        self,
        model,
        name,
        investment,
        tech_level,
        demand_curve,
        differ,
        market,
        marginal_cost,
    ):
        super().__init__(model)

        self.wealth = investment

        self.market = market

        self.differ = differ

        self.name = name

        self.price = 0

        self.transactions = pd.DataFrame({"consumer_id": [], "price": [], "time": []})

        self.tech_level = tech_level

        v_c, f_c = self.calculate_cost(tech_level)

        self.total_cost_function = v_c * sp.Symbol("Q") + f_c

        self.marginal_cost = marginal_cost

        self.demand_curve = demand_curve

    def action(self):
        """this method is for putting all actions a company does in a week"""

        self.set_price()

    def calculate_cost(self, tech_level):
        """this method calculates the total cost of a company based on its total cost function"""

        variable_cost_coeff = 1 - tech_level

        fixed_cost = int((1 - tech_level) * 10000)

        return (variable_cost_coeff, fixed_cost)

    def set_price(self):
        """this method sets the price of a good or service based on the company's total cost and desired profit margin"""

        all_companies = self.model.agents.select(agent_type=Company)
        companies = [a for a in all_companies if a.market == self.market]

        if len(companies) == 2:

            price = self.calculate_duopoly_price()
            self.price = price
            return price

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

    def calculate_duopoly_price(self):
        """this method is for companies to find their optimal price based on Game Theory models"""

        all_companies = self.model.agents.select(agent_type=Company)
        competitors = [
            a for a in all_companies if a != self and a.market == self.market
        ]

        competitor = competitors[0]

        m_c = self.marginal_cost
        mono_price = self.calculate_monopoly_price()
        t = self.differ

        # * These conditions must hold no matter what. i should somehow add them to the set_price method
        if competitor.price == 0:

            return mono_price

        if competitor.price < m_c:

            return 0

        if competitor.price > mono_price:

            return mono_price

        else:

            duopoly_price = round((competitor.price + t + m_c) / 2, 2)

            if duopoly_price > mono_price:
                return mono_price

            elif duopoly_price < m_c:
                return m_c

            else:
                return duopoly_price

    def calculate_monopoly_price(self):
        """this method calculates the monopoly price for a company"""

        P = sp.Symbol("P")
        marginal_cost = self.marginal_cost
        total_revenue = self.demand_curve * P
        marginal_revenue = sp.diff(total_revenue, P)

        system_eq = sp.Eq(marginal_revenue, marginal_cost)
        solution = sp.solve(system_eq, P)

        mono_price = float(self.demand_curve.subs({P: solution[0]}))

        return round(mono_price, 2)

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

    def __init__(self, consumers, markets):
        super().__init__()

        self.datacollector = mesa.DataCollector(
            agenttype_reporters={
                Consumer: {
                    "Wealth": "wealth",
                    "Savings": "savings",
                    "Salary": "salary",
                    "MPC": "mpc",
                    "LiveUtile": "live_utile",
                },
                Company: {"Name": "name", "Wealth": "wealth", "Price": "price"},
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

        for market in markets:

            for company in market["companies"]:

                company = Company(
                    self,
                    name=company["name"],
                    market=market["market"],
                    investment=company["investment"],
                    tech_level=company["tech_level"],
                    demand_curve=market["demand_curve"],
                    differ=market["differentiation"],
                    marginal_cost=int(
                        sp.solve(market["supply_curve"], sp.Symbol("P"))[0]
                    ),
                )

                self.agents.add(company)

    def step(self):

        # 1. Extract and run actions for Companies
        if self.time % 7 == 0 or self.time == 1:
            self.agents.select(agent_type=Company).shuffle_do("action")

        # 2. Extract and run actions for Consumers
        self.agents.select(agent_type=Consumer).shuffle_do("action")

        # 3. Collect data
        self.datacollector.collect(self)


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
