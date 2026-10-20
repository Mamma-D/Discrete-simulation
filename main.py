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

        if self.live_utile >= 3.5:
            self.live_utile -= 3.5

        else:
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
        while self.live_utile <= 10:
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

                    if self.wealth < chosen_company.price:

                        if self.use_savings(chosen_company.price - self.wealth):
                            self.buying_process(chosen_company, market)

                    else:
                        self.buying_process(chosen_company, market)                          

                        #! -----Buying process ends here-----

            if self.live_utile == before_utile:
                break

    def buying_process(self, chosen_company, market):
        """this method mimics the process of buying a good or service from a company"""

        self.purchase(chosen_company)

        self.assign_utile()

        self.update_memory(market, chosen_company)

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

    def use_savings(self, needed):
        """this method mimics the thought process of deciding how much to use savings"""
        # todo fill this

        if self.savings > needed:

            self.wealth += needed
            self.savings -= needed

            return True

        return False

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

        self.tech_level = 0

        self.marginal_cost = marginal_cost

        self.demand_curve = demand_curve

    def action(self):
        """this method is for putting all actions a company does in a week"""

        self.set_price()

    def factor_mc(self, P):
        """this is a factor for determining a price. its core goal is to price based on the company's marginal cost."""

        result = P >= self.marginal_cost

        return result

    def factor_compet(self, P):
        """this is a factor for determining a price. its core goal is to price based on competitors."""

        all_companies = self.model.agents.select(agent_type=Company)
        companies = [a for a in all_companies if a.market == self.market]
        market_structure = 'mono' if len(companies) == 1 else 'duo' if len(companies) == 2 else 'pc'

        if market_structure == 'duo':

            result = P <= self.calculate_duopoly_price(companies)

        if market_structure == 'mono':

            result = P <= self.calculate_monopoly_price()

        if market_structure == 'pc':

            result = P <= self.marginal_cost

        return result

    def set_price(self):
        """this method sets the price of a good or service based on the company's total cost and desired profit margin"""

        P = sp.Symbol("P")

        key_factors = {
            1: self.factor_mc,
            2: self.factor_compet
        }

        limits = {}

        for prioritize, procedure in key_factors.items():
            
            inequation = procedure(P)

            limits[prioritize] = inequation

        feasible_range = sp.reduce_inequalities(limits, P)
        
        if feasible_range:

            price = feasible_range.as_set().sup

        else:

            base = limits[1]

            price = base.as_set().sup

        return price

    def add_transaction(self, consumer):
        """this method adds the transaction to the company's wealth"""

        # gaining the revenue from selling the good or service
        self.wealth += self.price
        # paying the cost of producing the good or service
        self.wealth -= self.marginal_cost

        # adding the transaction to the company's transaction history
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

    def calculate_duopoly_price(self, companies):
        """this method is for companies to find their optimal price based on Game Theory models"""

        competitors = [
            a for a in companies if a != self and a.market == self.market
        ]

        competitor = competitors[0]

        m_c = self.marginal_cost
        t = self.differ

        duopoly_price = round((competitor.price + t + m_c) / 2, 2)

        return duopoly_price

    def calculate_monopoly_price(self):
        """this method calculates the monopoly price for a company"""

        P = sp.Symbol("P")
        Q = sp.Symbol("Q")

        inverse_demand = sp.solve(self.demand_curve, P)[0]
        total_revenue = inverse_demand * Q
        marginal_revenue = total_revenue.diff(Q)
        equation = sp.Eq(marginal_revenue, self.marginal_cost)

        solution = sp.solve(equation, Q)[0]
        if solution <= 0:
            raise ValueError(
            f"{self.name} ({self.market}): marginal cost {self.marginal_cost} is above the "
            f"highest price buyers will pay ({float(inverse_demand.subs(Q, 0))}), "
            f"so there is no profitable output."
            )
        mono_price = round(float(inverse_demand.subs(Q, solution).evalf()), 2)

        return mono_price

    def R_D(self):
        """this method is for companies to invest in research and development"""

        # todo Need to implement a way for companies to invest in R&D and how it affects their production and costs

        N = sp.Symbol("N")
        RATE = 30 / ( 0.5 * N ** 2 + 5 )
        COST = 1000


        if self.wealth < COST:
            return False

        self.wealth -= COST
        growth = round(RATE.subs(N, self.tech_level).evalf(), 2)

        self.marginal_cost = self.marginal_cost - (growth/100 * self.marginal_cost)

        self.tech_level += 1

        return self.marginal_cost

    def spend_on_RD(self):
        """this method is for companies to decide whether to spend on R&D or not based on the potential benefits of investing"""
        # todo companies forecast a simple demand curve based on historical transactions and decide whether to invest or not
        



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
