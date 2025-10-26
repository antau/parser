import re
from collections import defaultdict
import pandas as pd
import streamlit as st

# --- PAGE SETUP ---
st.set_page_config(page_title="eBay Picklist Parser", page_icon="🃏", layout="wide")

st.title("🃏 eBay Picklist Parser")
st.write("Paste your eBay picklist text below to extract card variations, buyers, and quantities.")

# --- SESSION STATE INIT ---
for key, default in {
    "picklist_text": "",
    "parsed_df": None,
    "summary_dict": {},
    "highlight_threshold": 1,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

highlight_threshold = st.sidebar.number_input(
    "Highlight cards with quantity ≥",
    min_value=1,
    value=st.session_state.highlight_threshold
)
st.session_state.highlight_threshold = highlight_threshold

# --- PARSE FUNCTION ---
def parse_picklist(text):
    order_pattern = re.compile(r"\b(\d{2}-\d{5}-\d{5})\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$", re.MULTILINE)
    card_pattern = re.compile(
        r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\).*?Quantity[:\s]+(\d+)",
        re.IGNORECASE
    )

    cards_by_buyer = defaultdict(list)
    current_buyer = None
    current_order = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
            continue

        if buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
            continue

        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation, quantity = card_match.groups()
            quantity = int(quantity)
            cards_by_buyer[current_buyer].append({
                "Order": current_order or "",
                "Card Number": number.strip(),
                "Card Name": name.strip(),
                "Variation": variation.strip(),
                "Quantity": quantity
            })

    summary_dict = {}
    for buyer, cards in cards_by_buyer.items():
        groupe
