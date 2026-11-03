"""This module is the core engine and runner"""

import sympy as sp
import main
from analyze import build_figures

# -----Default values-----

shoe = {
    "population": 2,
    "market": "shoe",
    "demand_curve": sp.Eq(sp.Symbol("Q"), 500 - 5 * sp.Symbol("P")),
    "supply_curve": 0.5 * sp.Symbol("P") - 40,
    "differentiation": 4,
    "companies": [
        {"name": "Nike", "investment": 500},
        {"name": "Adidas", "investment": 800},
    ],
}


soda = {
    "population": 2,
    "market": "soda",
    "demand_curve": sp.Eq(sp.Symbol("Q"), 180 - 0.5 * sp.Symbol("P")),
    "supply_curve": 1.2 * sp.Symbol("P") - 2,
    "differentiation": 2,
    "companies": [
        {"name": "Pepsi", "investment": 500, "tech_level": 0.5},
        {"name": "CocaCola", "investment": 800, "tech_level": 0.8},
    ],
}


# -----Simulation function-----

def run_simulation(consumer_count, tick, progress=None):
    """runs the simulation tick by tick (so a progress bar can follow it) and returns the charts"""

    consumers = {
        "population": consumer_count,
        "indexes": {
            "MPC": {
                0.19: [[0.38, 0.56], [0.77, 0.95]],
                0.4: [[0.56, 0.32], [0.68, 0.77]],
                0.41: [0.32, 0.68],
            },
            "salary": {0.2: [[3679, 4500], [393, 803]], 0.8: [1000, 1000]},
        },
    }

    instance = main.TheModel(consumers, markets=[shoe, soda])

    for done in range(1, tick + 1):
        instance.run_for(1)
        if progress:
            progress(done / tick)

    company_df = instance.datacollector.get_agenttype_vars_dataframe(main.Company)
    company_df = (
        company_df.reset_index().set_index(["Step", "Name"]).drop(columns="AgentID")
    )

    consumer_df = instance.datacollector.get_agenttype_vars_dataframe(main.Consumer)

    companies = instance.agents.select(agent_type=main.Company)

    return build_figures(consumer_df, company_df, companies)