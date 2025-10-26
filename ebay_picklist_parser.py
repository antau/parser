import re
from collections import defaultdict, Counter
import pandas as pd
import streamlit as st

# --- PAGE SETUP ---
st.set_page_config(page_title="eBay Picklist Parser", page_icon="🃏", layout="wide")
st.title("🃏 eBay Picklist Parser")
st.write("Paste your eBay picklist text below to extract card variations, buyers, quantities, and shipping info.")

# --- SESSION STATE INIT ---
for key, default in {
    "picklist_text": "",
    "parsed_df": None,
    "summary_dict": {},
    "theme": "light",
    "highlight_threshold": 1,
    "buyer_info": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- THEME TOGGLE ---
st.sidebar.title("Settings")
theme = st.sidebar.radio("Theme:", ["Light", "Dark"])
st.session_state.theme = theme.lower()

highlight_threshold = st.sidebar.number_input(
    "Highlight cards with quantity ≥",
    min_value=1,
    value=st.session_state.highlight_threshold
)
st.session_state.highlight_threshold = highlight_threshold

# --- PARSE FUNCTION ---
def parse_picklist(text):
    lines = text.splitlines()
    order_pattern = re.compile(r"\b(\d{2}-\d{5}-\d{5})\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
    card_pattern = re.compile(r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)")
    qty_pattern = re.compile(r"Item no\.:\s*\d+\s+Quantity:\s*(\d+)")

    cards_by_buyer = defaultdict(list)
    buyer_info = {}
    current_buyer = None
    current_order = None

    for i, line in enumerate(lines):
        line = line.strip()
        # Detect order number
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
        # Detect buyer
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
        # Detect shipping name/address
        elif current_buyer and re.match(r"^\t\d+\t$", line):
            if i + 1 < len(lines):
                buyer_info[current_buyer] = lines[i + 1].strip()
        # Detect card quantity
        qty_match = qty_pattern.search(line)
        quantity = int(qty_match.group(1)) if qty_match else 1
        # Detect card line
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation = card_match.groups()
            cards_by_buyer[current_buyer].append({
                "order": current_order,
                "card": f"{number.strip()} {name.strip()}",
                "variation": variation.strip(),
                "quantity": quantity,
            })

    # --- Prepare summary dict and DataFrame ---
    summary_dict = {}
    for buyer, cards in cards_by_buyer.items():
        grouped = Counter((c["card"], c["variation"], c["order"]) for c in cards)
        summary_list = []
        for (card, variation, order), _ in grouped.items():
            qty = sum(c['quantity'] for c in cards if c['card'] == card and c['variation'] == variation)
            summary_list.append({
                "Order": order,
                "Card": card,
                "Variation": variation,
                "Quantity": qty,
            })
        summary_dict[buyer] = summary_list

    df = pd.DataFrame([item for items in summary_dict.values() for item in items])
    return df, summary_dict, buyer_info

# --- TEXT INPUT ---
picklist_text = st.text_area(
    "Paste your picklist text here:",
    height=300,
    value=st.session_state.picklist_text,
    placeholder="Paste your eBay picklist text here..."
)
st.session_state.picklist_text = picklist_text

# --- AUTO-PARSE WHEN TEXT CHANGES ---
if picklist_text.strip():
    df, summary_dict, buyer_info = parse_picklist(picklist_text)
    st.session_state.parsed_df = df
    st.session_state.summary_dict = summary_dict
    st.session_state.buyer_info = buyer_info

# --- SHOW RESULTS IF AVAILABLE ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    buyer_info = st.session_state.buyer_info

    st.subheader("📊 Parsed Data (Collapsed by Default)")
    with st.expander("Show Parsed Data", expanded=False):
        def highlight_cards(row):
            style = []
            if row['variation'].lower() == "non-holo":
                style = ['background-color: #ff9999']*len(row)
            elif row['variation'].lower() == "holo rare":
                style = ['background-color: #99ccff']*len(row)
            else:
                style = ['']*len(row)
            if row['quantity'] > 1:
                style = [s + '; font-weight: bold;' for s in style]
            return style

        styled_df = df.style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (Expanded by Default)")
    for buyer, items in summary_dict.items():
        header_info = f"{buyer} ({len(items)} items)"
        if buyer in buyer_info:
            header_info += f": {buyer_info[buyer]}"
        with st.expander(header_info, expanded=True):
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
        summary_text = "\n".join([f"{buyer}: {buyer_info.get(buyer,'-')}" for buyer in summary_dict.keys()])
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
    st.session_state.buyer_info = {}
    st.experimental_rerun()
