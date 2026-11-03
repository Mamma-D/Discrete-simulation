# 📈 Oligopoly Market & Economic Simulator

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://discrete-simulation.streamlit.app/)

An Agent-Based Model (ABM) exploring Game Theory, Consumer Utility, and Supply Chain Volatility — powered by Python, Mesa, and Streamlit.

## 📌 Overview

This project is a discrete-time economic simulation built using Object-Oriented Python. It models a closed market ecosystem where autonomous corporate agents compete for market share, while consumer agents make purchasing decisions based on utility, income, savings, and brand loyalty.

The simulation incorporates **Hotelling's Linear City Model** to represent consumer preferences and strategic competition between firms. It also introduces stochastic economic shocks to investigate how supply chain disruptions and changes in living costs affect corporate profitability and consumer wealth.

The project comes with an interactive **Streamlit dashboard**, allowing users to configure simulation parameters, execute the model, and explore its results through interactive Plotly visualizations — without having to interact directly with the underlying Python code.

## 🖥️ Simulation Dashboard

![Simulation Dashboard](<img width="1919" height="872" alt="Screenshot 2026-11-03 115046" src="https://github.com/user-attachments/assets/fb1ef0e1-0145-4d2a-97ea-f99699bb13a5" />)

## ⚙️ Core Mechanics

- **🧠 Corporate Agents (Game Theory):** Companies dynamically determine their selling prices based on marginal costs and competitive conditions. The pricing mechanism incorporates symbolic optimization for monopoly pricing and strategic price responses in duopoly markets.

- **🛒 Autonomous Consumers:** Consumer agents receive salaries, account for essential living expenses, and allocate their income between consumption and savings according to their Marginal Propensity to Consume (MPC). Their purchasing decisions are influenced by affordability, utility, and brand proximity.

- **⚡ Stochastic Economic Shocks:** The model periodically introduces random economic disturbances, including fluctuations in companies' marginal costs and consumers' essential living expenses. These shocks allow us to observe how the market responds to unexpected economic changes.

- **📊 Interactive Analytics:** Simulation data is collected and processed using Pandas. An independent analytics module generates interactive Plotly visualizations, which are displayed directly in the Streamlit dashboard.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| [Python](https://www.python.org/) | Core programming language and simulation logic |
| [Mesa](https://mesa.readthedocs.io/) | Agent-Based Modeling framework |
| [SymPy](https://www.sympy.org/) | Symbolic mathematics and pricing calculations |
| [Pandas](https://pandas.pydata.org/) | Data collection, manipulation, and analysis |
| [Plotly](https://plotly.com/python/) | Interactive data visualization |
| [Streamlit](https://streamlit.io/) | Interactive dashboard and user interface |

## 🗂️ Project Structure

```text
Discrete-simulation/
│
├── dashboard.py          # Streamlit dashboard and user interface
├── engine.py             # Simulation runner and market configuration
├── main.py               # Core ABM: Consumer, Company, and TheModel
├── analyze.py            # Analytics and Plotly visualization module
├── configuration.ipynb   # Jupyter Notebook for manual configuration
└── README.md
```

## 🚀 Installation & Usage

### 1. Clone the repository

```bash
git clone https://github.com/Mamma-D/Discrete-simulation.git
cd Discrete-simulation
```

### 2. Install dependencies

```bash
pip install mesa pandas plotly sympy streamlit
```

### 3. Launch the dashboard

Run the following command from the project directory:

```bash
streamlit run dashboard.py
```

Streamlit will launch the application in your default web browser.

### 4. Configure and run a simulation

Inside the dashboard, you can:

1. **Set the consumer population:** Choose the number of consumers participating in the market (5–500).
2. **Set the simulation duration:** Choose the number of time steps (1–1000), where each tick represents one simulated day.
3. **Run the simulation:** Start the engine and monitor its execution through the progress bar.
4. **Explore the results:** Examine the generated interactive Plotly charts directly in the dashboard.

No manual configuration or Jupyter Notebook execution is required for the standard dashboard workflow.

## 📓 Alternative: Jupyter Notebook

The `configuration.ipynb` notebook is also available for users who want to experiment with the underlying model, modify market parameters, or inspect simulation data directly.

## ⚠️ Disclaimer

This project is an educational simulation developed to explore concepts in Agent-Based Modeling, Game Theory, Operations Research, Microeconomics, and Data Science.

Its assumptions and mechanisms are simplified representations of real-world economic behavior. The results should not be interpreted as financial forecasts or investment recommendations.
