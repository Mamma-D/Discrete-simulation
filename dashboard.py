"""Streamlit dashboard for the economic simulation."""

import streamlit as st
from engine import run_simulation

# -----Streamlit UI-----

st.set_page_config(page_title="Economic Simulator", page_icon="📊", layout="centered")

st.markdown(
    "<h1 style='text-align: center;'>Economic Simulator 💱</h1>", unsafe_allow_html=True
)
st.space("small")


with st.container(border=True):

    consumer_population = st.number_input(
        "Enter the consumer's population", min_value=5, max_value=500, value=50, step=1
    )
    st.caption("Choose the population for people in the simulation (Maximum 500)")

    tick = st.number_input(
        "Enter the number of ticks to simulate",
        min_value=1,
        max_value=1000,
        value=100,
        step=1,
    )
    st.caption(
        "Choose the number of ticks you wanna simulate, each tick equals one day (Maximum 1000)"
    )

    if not tick or not consumer_population:
        st.warning(
            "Please enter both the consumer's population and the number of ticks to simulate."
        )
        st.stop()
    st.success("Click the Run Simulation button to start the simulation.")

if st.button("Run Simulation"):

    bar = st.progress(0.0, text="Simulating...")

    figures = run_simulation(
        consumer_population,
        tick,
        progress=lambda done: bar.progress(done, text=f"Simulating... {done:.0%}"),
    )

    bar.empty()

    figures.pop(0)

    with st.container(width="stretch"):
        for figure in figures:
            st.plotly_chart(figure, width="stretch")
