import re
from collections import defaultdict
import pandas as pd
import streamlit as st

# --- PAGE SETUP ---
st.set_page_config(page_title="eBay Picklist Parser v2", page_icon="🃏", layout="wide")
st.title("🃏 eBay Picklist Parser")
st.write("Paste your eBay picklist text below to extract card variations, buyers, and quantities.")

# --- SESSION STATE INIT ---
for key, default in {
    "picklist_text": "",
    "parsed_df": None,
    "summary_dict": {},
    "theme": "light",
    "highlight_threshold": 1,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- SETTINGS ---
st.sidebar.title("Settings")
theme = st.sidebar.radio("Theme:", ["Light", "Dark"])
st.session_state.theme = theme.lower()

highlight_threshold = st.sidebar.number_input(
    "Highlight cards with quantity ≥",
    min_value=1,
    value=st.session_state.highlight_threshold
)
st.session_state.highlight_threshold = highlight_threshold

# --- UPDATED PARSE FUNCTION ---
def parse_picklist(text):
    order_pattern = re.compile(r"\b(\d{2}-\d{5}-\d{5})\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$", re.MULTILINE)
    card_pattern = re.compile(
        r"Item no\.: \d+\s+Quantity: (\d+).*?Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)",
        re.DOTALL
    )

    cards_by_buyer = defaultdict(list)
    current_buyer = None
    current_order = None

    for line in text.splitlines():
        line = line.strip()
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            quantity, number, name, variation = card_match.groups()
            cards_by_buyer[current_buyer].append({
                "order": current_order,
                "number": number.strip(),
                "name": name.strip(),
                "variation": variation.strip(),
                "quantity": int(quantity)
            })

    summary_dict = {}
    summary_text = ""
    for buyer, cards in cards_by_buyer.items():
        grouped = defaultdict(int)
        for c in cards:
            key = (c["number"], c["name"], c["variation"], c["order"])
            grouped[key] += c["quantity"]

        summary_list = []
        for (number, name, variation, order), qty in grouped.items():
            summary_list.append({
                "Order": order,
                "Card Number": number,
                "Card Name": name,
                "Variation": variation,
                "Quantity": qty
            })
        summary_dict[buyer] = summary_list

        # Prepare text summary
        summary_text += f"\n👤 {buyer}\n" + "-"*40 + "\n"
        for item in summary_list:
            summary_text += f"• {item['Card Number']} {item['Card Name']} ({item['Variation']}) ×{item['Quantity']}\n"
        summary_text += "\n"

    if not summary_dict:
        return None, {}, ""

    df = pd.DataFrame([item for items in summary_dict.values() for item in items])
    return df, summary_dict, summary_text.strip()

# --- TEXT INPUT ---
picklist_text = st.text_area(
    "Paste your picklist text here:",
    height=300,
    value=st.session_state.picklist_text,
    placeholder="Paste your eBay picklist text here..."
)
st.session_state.picklist_text = picklist_text

# --- AUTO-PARSE ---
if picklist_text.strip():
    df, summary_dict, summary_text = parse_picklist(picklist_text)
    st.session_state.parsed_df = df
    st.session_state.summary_dict = summary_dict
    st.session_state.summary_text = summary_text

# --- SHOW RESULTS ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    summary_text = st.session_state.summary_text

    st.subheader("📊 Parsed Data")

    # --- HIGHLIGHT FUNCTION ---
    def highlight_cards(row):
        styles = ['' for _ in row]
        var_lower = str(row['Variation']).lower()
        if var_lower == "non-holo":
            styles = ['background-color: #add8e6' for _ in row]  # light blue
        elif var_lower == "holo rare":
            styles = ['background-color: #90ee90' for _ in row]  # light green
        elif row['Quantity'] >= highlight_threshold:
            styles = ['background-color: #ffdd99' for _ in row]  # light orange

        if row['Quantity'] > 1:
            styles = [s + '; font-weight: bold' for s in styles]

        return styles

    styled_df = df.style.apply(highlight_cards, axis=1)
    st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (Collapsible)")

    for buyer, items in summary_dict.items():
        with st.expander(f"👤 {buyer} ({len(items)} items)"):
            buyer_df = pd.DataFrame(items)
            styled_buyer_df = buyer_df.style.apply(highlight_cards, axis=1)
            st.dataframe(styled_buyer_df, use_container_width=True)

    # --- DOWNLOAD OPTIONS ---
    csv = df.to_csv(index=False).encode("utf-8")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇️ Download Parsed CSV",
            data=csv,
            file_name="parsed_picklist.csv",
            mime="text/csv"
        )
    with col2:
        st.download_button(
            label="📋 Download Summary as Text",
            data=summary_text.encode("utf-8"),
            file_name="picklist_summary.txt",
            mime="text/plain"
        )

# --- CLEAR BUTTON ---
if st.button("🧹 Clear All Data"):
    st.session_state.picklist_text = ""
    st.session_state.parsed_df = None
    st.session_state.summary_dict = {}
    st.session_state.summary_text = ""
    st.experimental_rerun()
