import re
from collections import defaultdict, Counter
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
    "buyer_info": {},
    "theme": "light",
    "highlight_threshold": 1,
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
    
    cards_by_buyer = defaultdict(list)
    buyer_info = {}
    current_buyer = None
    current_order = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Detect order
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
        # Detect buyer
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
        # Detect card
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            # Quantity is 2 lines above
            qty_line = lines[i-2].strip() if i >= 2 else ""
            qty_numbers = [int(s) for s in re.findall(r'\d+', qty_line)]
            qty = qty_numbers[-1] if qty_numbers else 1

            number, name, variation = card_match.groups()
            cards_by_buyer[current_buyer].append({
                "Order": current_order or "",
                "Card": f"{number.strip()} {name.strip()}",
                "Variation": variation.strip(),
                "Quantity": qty,
            })
        # Detect shipping name/address (line after a line that is just a number)
        if re.match(r"^\d+$", line) and i + 1 < len(lines):
            buyer_info[current_buyer] = lines[i + 1].strip()  # next line
        i += 1

    # Build summary_dict
    summary_dict = {}
    for buyer, cards in cards_by_buyer.items():
        grouped = Counter((c["Card"], c["Variation"]) for c in cards)
        summary_list = []
        for (card, variation), qty in grouped.items():
            order = next((c["Order"] for c in cards if c["Card"] == card), "")
            summary_list.append({
                "Order": order,
                "Card": card,
                "Variation": variation,
                "Quantity": qty,
            })
        summary_dict[buyer] = summary_list

    if not summary_dict:
        return None, {}, {}

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

    st.subheader("📊 Parsed Data")
    with st.expander("Parsed Data (Collapsed by default)", expanded=False):
        def highlight_cards(row):
            colors = [''] * len(row)
            var = str(row['Variation']).lower()
            if var == "non-holo":
                colors = ['background-color: #ff9999'] * len(row)
            elif var == "holo rare":
                colors = ['background-color: #99ccff'] * len(row)
            if row['Quantity'] > 1:
                colors = [c + "; font-weight: bold" if c else "font-weight: bold" for c in colors]
            return colors

        styled_df = df.style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (Expanded by default)")
    for buyer, items in summary_dict.items():
        header = f"👤 {buyer} ({len(items)} items): {buyer_info.get(buyer,'-')}"
        with st.expander(header, expanded=True):
            buyer_df = pd.DataFrame(items)
            styled_buyer_df = buyer_df.style.apply(highlight_cards, axis=1)
            st.dataframe(styled_buyer_df, use_container_width=True)

    # --- DOWNLOAD BUTTONS ---
    csv_data = df.to_csv(index=False).encode("utf-8")
    summary_text = ""
    for buyer, items in summary_dict.items():
        summary_text += f"\n👤 {buyer} ({len(items)} items): {buyer_info.get(buyer,'-')}\n"
        for item in items:
            summary_text += f"• {item['Card']} ({item['Variation']}) ×{item['Quantity']}\n"
    summary_bytes = summary_text.encode("utf-8")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇️ Download Parsed CSV",
            data=csv_data,
            file_name="parsed_picklist.csv",
            mime="text/csv"
        )
    with col2:
        st.download_button(
            label="📋 Download Summary Text",
            data=summary_bytes,
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
