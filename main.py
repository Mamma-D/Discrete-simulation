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

        self.balance_utile()
        self.consume()
        if self.model.time % 4 == 0:
            self.get_paid(self.salary)

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

        self.live_utile -= 3.5
        return self.live_utile

    def consume(self):
        """this method mimics spending money on goods and services"""

        # Added a condition to keep consume
        # We check if the last transaction was successful

        # We assume consumer can shop at the beginning 
        transaction_status = True
        while transaction_status and self.live_utile < 9:


            #* -----Stage 1: Choosing a market to start-----
            #todo Add a way to have multiple markets, for now we just have one market
            # Checking available companies in the market (don't have multiple markets yet)

            # Entered the market, found the companies
            companies = self.model.agents.select(agent_type=Company)
            companies_count = len(companies)


            #! -----Stage 1.2: Buying process starts here-----

            #* In the specific case of a two company market, this block happens
            if companies_count == 2:

                pos = round(random.uniform(0.00, 1.00), 2)
                self.position["market"] = pos

                #* Linear city model in Game Theory to determine which company to buy from
                cost_for_firm_1 = (
                    companies[0].price + companies[0].differ * (pos) ** 2
                )
                cost_for_firm_2 = (
                    companies[1].price + companies[1].differ * (1 - pos) ** 2
                )

                chosen_company = companies[0] if cost_for_firm_1 < cost_for_firm_2 else companies[1]

                if self.wealth >= chosen_company.price:

                    transaction_status = True

                    self.purchase(chosen_company)

                    self.utile(chosen_company.price, pos)

                else:

                    transaction_status = False

                    #! -----Buying process ends here-----


    def purchase(self, company_seller):
        """this method mimics the purchase of a good or service from a company"""

        self.wealth = round(self.wealth - company_seller.price)
        company_seller.add_transaction(self)

        print(f"agent {self.unique_id} purchased from company {company_seller.name} for {company_seller.price}$")

    def utile(self, price, pos):
        """this method calculates and adds the utility of a good or service purchased from a company"""

        #* I'll use a simple method where the good doesn't matter and you're utility is given by you're live utile for now
        x = sp.Symbol('x')
        coefficient = 19 / (1 + ( 0.9 * sp.E**(0.4 * x) ) ) - 0.3

        utility_gotten = round(coefficient.subs(x, self.live_utile), 0)

        self.live_utile += int(utility_gotten)

class Company(mesa.Agent):
    """this class represents companies"""

    def __init__(self, model, name, investment, tech_level, demand_curve, differ, market):
        super().__init__(model)

        self.wealth = investment

        self.market = market

        self.differ = differ

        self.name = name

        self.price = 0

        self.transactions = pd.DataFrame(
            {"consumer_id": [], "price": [], "time": []}
        )

        self.tech_level = tech_level

        v_c, f_c = self.calculate_cost(tech_level)

        self.total_cost_function =  v_c * sp.Symbol("Q") + f_c

        self.marginal_cost = v_c

        self.demand_curve = demand_curve


    def action(self):
        """this method is for putting all actions a company does in a week"""

        self.set_price()

    def calculate_cost(self, tech_level):
        """this method calculates the total cost of a company based on its total cost function"""

        variable_cost_coeff = (1 - tech_level)

        fixed_cost = int((1 - tech_level) * 10000)

        return (variable_cost_coeff, fixed_cost)

    def set_price(self):
        """this method sets the price of a good or service based on the company's total cost and desired profit margin"""

        companies = self.model.agents.select(agent_type=Company)

        if len(companies) == 2:

            price = self.find_duopoly_price()
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

    def find_duopoly_price(self):
        """this method is for companies to find their optimal price based on Game Theory models"""

        competitors = self.model.agents.select(agent_type=Company, filter_func=lambda x: x != self)
        competitor = competitors[0]

        m_c = self.marginal_cost
        mono_price = self.calculate_monopoly_price()
        t = self.differ

        #* These conditions must hold no matter what. i should somehow add them to the set_price method
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
                Consumer: {"Wealth": "wealth", "Savings": "savings", "Salary": "salary", "MPC": "mpc", "LiveUtile": "live_utile"},
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

        for market in markets:

            for company in market['companies']:

                company = Company(
                    self, 
                    name=company["name"],
                    market=market["market"],
                    investment=company["investment"],
                    tech_level=company["tech_level"],
                    demand_curve=market["demand_curve"],
                    differ=market["differentiation"]
                )

                self.agents.add(company)

    def step(self):
        # 1. Collect data first
        
        # 2. Extract and run actions for Companies
        self.agents.select(agent_type=Company).shuffle_do("action")
        
        # 3. Extract and run actions for Consumers
        self.agents.select(agent_type=Consumer).shuffle_do("action")

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
