import streamlit as st

st.set_page_config(page_title="ChefGPT", page_icon="🍳")
st.title("ChefGPT 🍳")
st.caption("tell me a cuisine or list your ingredients. i'll be happy to suggest recipes.")

user_input = st.text_input("Your craving or pantry:", placeholder="e.g., Thai // chicken, mushrooms, spinach")

if st.button("Suggest recipes"):
    if not user_input.strip():
        st.warning("Please enter a cuisine or some ingredients.")
    else:
        st.write("Here’s where your recipes will appear!")
