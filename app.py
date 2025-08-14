import streamlit as st

st.set_page_config(page_title="ChefGPT", page_icon="🍳")
st.title("ChefGPT 🍳")
st.caption("tell me a cuisine or list your ingredients. i'll be happy to suggest recipes.")

user_input = st.text_input("your cravings or pantry items:", placeholder="e.g., chinese // chicken, brussel sprouts, mushrooms, spinach")

if st.button("suggest recipes"):
    if not user_input.strip():
        st.warning("please enter a cuisine or some ingredients.")
    else:
        st.write("your recipes will appear here <placeholder>!")
