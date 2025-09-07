import os, json
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

# ------- setup -------
load_dotenv()
st.set_page_config(page_title="ChefGPT", page_icon="🍳", layout="centered")
st.title("ChefGPT 🍳")
st.caption("Tell me a cuisine or list your ingredients. I’ll suggest tailored recipes.")

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("Missing GROQ_API_KEY. Add it to your .env or environment.")
client = Groq(api_key=api_key)

# ------- sidebar controls -------
with st.sidebar:
    st.subheader("Preferences")
    num_recipes = st.slider("How many recipes?", 1, 5, 3)
    servings = st.slider("Servings", 1, 8, 2)
    time_cap = st.selectbox("Max cook time", ["no limit", "15 min", "30 min", "45 min", "60 min"])
    diets = st.multiselect(
        "Dietary preferences (optional)",
        ["vegetarian", "vegan", "pescatarian", "gluten-free", "dairy-free", "nut-free", "halal", "kosher", "low-carb"]
    )
    show_macros = st.checkbox("Include approximate nutrition/macros", value=True)

user_input = st.text_input(
    "Your cravings or pantry items:",
    placeholder="e.g., chinese // chicken, brussel sprouts, mushrooms, spinach"
)
btn = st.button("Suggest recipes")


# ------- helpers -------
def build_prompt(query: str) -> str:
    constraints = []
    if diets:
        constraints.append(f"Dietary: {', '.join(diets)}")
    if time_cap != "no limit":
        constraints.append(f"Max time: {time_cap}")
    constraints.append(f"Servings: {servings}")
    if show_macros:
        constraints.append("Include rough calories & macros.")

    schema = """
    Return ONLY a JSON array. Each recipe must match:
    {
    "title": str,
    "summary": str,
    "servings": int,
    "time_minutes": int,
    "ingredients": [str, ...],
    "steps": [str, ...],
    "tags": [str, ...],
    "nutrition": {"calories": int, "protein_g": int, "carbs_g": int, "fat_g": int}
    }
    """
    
    parts = [
        f"Create {num_recipes} recipes for: {query}.",
        "Prefer common ingredients and realistic steps.",
        schema.strip(),
        "Reply with a strict JSON array only."
    ]
    if constraints:
        parts.append("Constraints: " + " | ".join(constraints))
    return "\n".join(parts)


def call_groq(prompt: str, model: str = "llama-3.1-8b-instant"):
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are ChefGPT."},
                  {"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=1000
    )
    text = resp.choices[0].message.content.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return [data]
        return data
    except Exception:
        return []


def render_recipe(card: dict):
    st.markdown(f"### {card.get('title', 'Untitled')}")
    st.write(card.get("summary", ""))
    cols = st.columns(3)
    with cols[0]:
        st.write(f"**Servings:** {card.get('servings', servings)}")
    with cols[1]:
        st.write(f"**Time:** {card.get('time_minutes', '—')} min")
    with cols[2]:
        if card.get("tags"):
            st.write("**Tags:** " + ", ".join(card["tags"]))
    st.markdown("**Ingredients**")
    for ing in card.get("ingredients", []):
        st.write(f"- {ing}")
    st.markdown("**Steps**")
    for i, step in enumerate(card.get("steps", []), 1):
        st.write(f"{i}. {step}")
    if show_macros and isinstance(card.get("nutrition"), dict):
        n = card["nutrition"]
        st.markdown(
            f"**Approx. Nutrition (per serving)** — "
            f"{n.get('calories', '—')} kcal · "
            f"{n.get('protein_g', '—')}g protein · "
            f"{n.get('carbs_g', '—')}g carbs · "
            f"{n.get('fat_g', '—')}g fat"
        )


# ------- action -------
if btn:
    if not user_input.strip():
        st.warning("Please enter a cuisine or some ingredients.")
    else:
        with st.spinner("Cooking up ideas..."):
            try:
                recipes = call_groq(build_prompt(user_input))
            except Exception as e:
                st.error(f"Groq error: {e}")
                recipes = []

            if not recipes:
                st.warning("I couldn’t parse recipe ideas this time. Try again.")
            else:
                for r in recipes:
                    render_recipe(r)
                    st.divider()
