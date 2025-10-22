import os, json
import re
import streamlit as st
from dotenv import load_dotenv
from groq import Groq

#---helper functions---
def clear_input():
    """
    this function resets the state when "clear" is pressed
    this meanings clearing:
        - search bar
        - recipes
        - and turns the surprise me mode into false
    """
    st.session_state.query = ""
    st.session_state.run_suggest = False
    st.session_state.recipes = []  # clear any stored recipes

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
    Return ONLY a JSON array. Do not include markdown, backticks, comments, or text before/after the JSON.
    Each element must match:
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
    If you cannot produce valid JSON, return [].
    """.strip()

    parts = [
        "You are ChefGPT. You output only machine-readable JSON as specified.",
        f"Create {num_recipes} distinct recipes optimized for: {query}.",
        "Prefer common ingredients and realistic steps.",
        schema,
    ]
    if constraints:
        parts.append("Constraints: " + " | ".join(constraints))
    parts.append("Your first character must be '[' and your last character must be ']'.")
    return "\n".join(parts)


def _extract_json(text: str):
    """Best-effort: grab the first JSON array or object from text."""
    text = text.strip()
    if text.startswith("[") or text.startswith("{"):
        try:
            data = json.loads(text)
            return [data] if isinstance(data, dict) else data
        except Exception:
            pass

    # try to find first JSON block using a simple bracket scan
    starts = [m.start() for m in re.finditer(r"[\[\{]", text)]
    for s in starts:
        chunk = text[s:]
        # trying progressively shorter chunks
        for e in range(len(chunk), max(len(chunk) - 8000, 200), -1):
            cand = chunk[:e].strip()
            if not (cand.endswith("]") or cand.endswith("}")):
                continue
            try:
                data = json.loads(cand)
                return [data] if isinstance(data, dict) else data
            except Exception:
                continue
    return []

def call_groq(prompt: str, model: str = "llama-3.1-8b-instant"):
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system",
             "content": "You are ChefGPT. Return ONLY JSON. First char '[' last char ']'."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1200
    )
    text = resp.choices[0].message.content or ""
    data = _extract_json(text)

    # show the raw output in an expander if parsing fails (for debug)
    if not data:
        with st.expander("Debug: model output (raw)"):
            st.code(text[:8000])

    return data[:num_recipes]


def render_recipe(r: dict):
    title = r.get("title","Untitled")
    summary = r.get("summary","")
    servings = r.get("servings","—")
    time_m = r.get("time_minutes","—")
    tags = r.get("tags", []) or []

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"<h3>{title}</h3>", unsafe_allow_html=True)
    st.markdown(f'<div class="meta">{summary}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="kv"><span>⏱ {time_m} min</span><span>👥 {servings} servings</span></div>',
        unsafe_allow_html=True
    )
    if tags:
        st.markdown('<div class="tags">' + "".join([f'<span class="tag">#{t}</span>' for t in tags]) + '</div>', unsafe_allow_html=True)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["🧾 Ingredients", "👩‍🍳 Steps", "🥗 Nutrition"])

    with t1:
        for ing in r.get("ingredients", []):
            st.write(f"- {ing}")

        # quick export list
        grocery = "\n".join(r.get("ingredients", []))
        st.download_button("🛒 Download grocery list", grocery.encode("utf-8"),
                           file_name=f"{title.replace(' ','_').lower()}_grocery.txt", use_container_width=True)

    with t2:
        for i, step in enumerate(r.get("steps", []), 1):
            st.markdown(f'<div class="step">{i}. {step}</div>', unsafe_allow_html=True)

    with t3:
        n = r.get("nutrition") or {}
        st.markdown(
            f"**Approx. per serving**  \n"
            f"- Calories: **{n.get('calories','—')}** kcal  \n"
            f"- Protein: **{n.get('protein_g','—')} g**  \n"
            f"- Carbs: **{n.get('carbs_g','—')} g**  \n"
            f"- Fat: **{n.get('fat_g','—')} g**",
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ------- setup -------
load_dotenv() #api key
st.set_page_config(page_title="ChefGPT", page_icon="🍳", layout="centered")

# --- initialize session state ---
if "query" not in st.session_state:
    st.session_state.query = ""
if "run_suggest" not in st.session_state:
    st.session_state.run_suggest = False
if "recipes" not in st.session_state:
    st.session_state.recipes = []

#CSS for streamlit elements
st.markdown("""
<style>
:root { --accent:#7C5CFF; --card:#171A24; --muted:#9aa0aa; }
div.block-container { padding-top: 2.2rem; max-width: 880px; }
.sidebar .sidebar-content { padding-top: 1rem !important; }

h1, .stMarkdown h1 { letter-spacing:.3px; }
.stButton>button {
  border-radius:12px; padding:.6rem 1rem; font-weight:600;
  border:1px solid rgba(255,255,255,.1);
}
.stButton>button:hover { border-color: var(--accent); box-shadow:0 0 0 3px rgba(124,92,255,.25); }

.card {
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
  border:1px solid rgba(255,255,255,.08); border-radius:16px;
  padding: 16px 18px; margin: 14px 0; box-shadow:0 10px 24px rgba(0,0,0,.18);
}
.card h3 { margin: 0 0 6px 0; }
.meta { color: var(--muted); font-size:.92rem; margin-bottom:.4rem; }
.kv { display:flex; gap:14px; margin:.3rem 0 0.7rem 0; }
.kv span { background:#10131a; border:1px solid rgba(255,255,255,.07); padding:.28rem .55rem; border-radius:10px; font-size:.85rem; }
.tags { margin-top:.35rem; }
.tag {
  display:inline-block; padding:.22rem .55rem; margin:.18rem .25rem 0 0;
  border:1px solid rgba(255,255,255,.1); border-radius:999px; font-size:.8rem; color:#CBD0D9;
}
h4 { margin:.8rem 0 .4rem 0; }
.step { margin:.18rem 0; line-height:1.5; }
.smallmuted { color: var(--muted); font-size:.86rem; }
.hr { height:1px; background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent); margin:10px 0; }
</style>
""", unsafe_allow_html=True)

# --------application code --------
st.title("ChefGPT")

left, right = st.columns([0.75, 0.25], vertical_alignment="center")

with left:
    st.caption("Tell me a cuisine or list your ingredients. I’ll suggest tailored recipes.")
with right:
    if st.button("Surprise me", use_container_width=True):
        # set a surprise query and trigger recipe generation
        st.session_state.query = "chef’s choice quick dinner, 20 minutes, budget"
        st.session_state.run_suggest = True
        st.rerun()


api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY. Add it to your .env or environment.")
client = Groq(api_key=api_key)

# ------- sidebar controls -------
with st.sidebar:
    st.header("Preferences")
    st.caption("Tune your results. ChefGPT adapts to your pantry & time.")
    num_recipes = st.slider("How many recipes?", 1, 5, 3)
    servings = st.slider("Servings", 1, 8, 2)
    time_cap = st.selectbox("Max cook time", ["no limit", "15 min", "30 min", "45 min", "60 min"])
    diets = st.multiselect("Dietary preferences", ["vegetarian","vegan","pescatarian","gluten-free","dairy-free","nut-free","halal","kosher","low-carb"])
    show_macros = st.toggle("Include approximate nutrition/macros", value=True)
    st.markdown('<div class="hr"></div><span class="smallmuted">Tip: add “budget” or “air fryer” to your prompt.</span>', unsafe_allow_html=True)

# === input card ===
user_input = st.text_input(
    "Your cravings or pantry items",
    key = "query",  # single source of truth
    placeholder = "e.g., chinese, italian // chicken, brussel sprouts, mushrooms, spinach",
    label_visibility = "collapsed",
)


cta1, cta2 = st.columns([1,1])
with cta1:
    btn = st.button("Suggest recipes", use_container_width=True, type="primary")
with cta2:
    clear = st.button("Clear", use_container_width=True, on_click=clear_input)


st.markdown('</div>', unsafe_allow_html=True)  # this now matches the opening


# ------- action -------
placeholder = st.empty()   # spot to show a loading card/message

if btn or st.session_state.get("run_suggest"):
    st.session_state.run_suggest = False  # clear flag after use

    if not user_input.strip():
        st.warning("Please enter a cuisine or some ingredients.")
    else:
        with placeholder.container():
            st.info("👩Preheating the pan… generating ideas...")

        try:
            recipes = call_groq(build_prompt(user_input))
        except Exception as e:
            placeholder.error(f"Groq error: {e}")
            recipes = []
        else:
            placeholder.empty()
            st.session_state.recipes = recipes 
            if st.session_state.recipes:
                for r in st.session_state.recipes:
                    render_recipe(r)
                    st.divider()


