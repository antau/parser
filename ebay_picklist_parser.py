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
    "summary_text": "",
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
    order_pattern = re.compile(r"\b(\d{2}-\d{5}-\d{5})\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$", re.MULTILINE)
    card_pattern = re.compile(r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)")

    cards_by_buyer = defaultdict(list)
    buyer_info = {}
    current_buyer = None
    current_order = None
    lines = text.splitlines()

    for i, line in enumerate(lines):
        line = line.strip()

        # Detect order number
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)

        # Detect buyer username
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line

        # Detect card lines
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation = card_match.groups()

            # Quantity is 2 lines above "Select Your Card:"
            quantity = 1
            if i >= 2:
                qty_line = lines[i - 2].strip()
                qty_match = re.search(r"Quantity:\s*(\d+)", qty_line)
                if qty_match:
                    quantity = int(qty_match.group(1))

            cards_by_buyer[current_buyer].append({
                "order": current_order,
                "card": f"{number.strip()} {name.strip()}",  # combine number + name
                "variation": variation.strip(),
                "quantity": quantity
            })

        # Detect Name + Shipping Address (line after single integer)
        if current_buyer and re.match(r"^\d+$", line.strip()):
            if i + 1 < len(lines):
                buyer_info[current_buyer] = lines[i + 1].strip()

    summary_dict = {}
    summary_text = ""
    for buyer, cards in cards_by_buyer.items():
        grouped = Counter((c["card"], c["variation"], c["order"], c["quantity"]) for c in cards)
        summary_list = []
        for (card, variation, order, quantity), _ in grouped.items():
            summary_list.append({
                "Order": order,
                "Card": card,
                "Variation": variation,
                "Quantity": quantity
            })
        summary_dict[buyer] = summary_list

        # Prepare plain text summary
        summary_text += f"\n👤 {buyer}\n" + "-"*40 + "\n"
        order_ids = sorted({c['order'] for c in cards if c['order']})
        if order_ids:
            summary_text += f"Orders: {', '.join(order_ids)}\n"
        for item in summary_list:
            summary_text += f"• {item['Card']} ({item['Variation']}) ×{item['Quantity']}\n"
        summary_text += "\n"

    if not summary_dict:
        return None, {}, "", {}

    df = pd.DataFrame([item for items in summary_dict.values() for item in items])
    return df, summary_dict, summary_text.strip(), buyer_info

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
    df, summary_dict, summary_text, buyer_info = parse_picklist(picklist_text)
    st.session_state.parsed_df = df
    st.session_state.summary_dict = summary_dict
    st.session_state.summary_text = summary_text
    st.session_state.buyer_info = buyer_info

# --- SHOW RESULTS IF AVAILABLE ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    summary_text = st.session_state.summary_text
    buyer_info = st.session_state.buyer_info

    st.subheader("📊 Parsed Data (collapsed by default)")
    with st.expander("Show Parsed Data", expanded=False):
        # Highlight function
        def highlight_cards(row):
            colors = ['' for _ in row]
            var_lower = str(row['Variation']).lower()
            if var_lower == "non-holo":
                colors = ['background-color: #ff9999' for _ in row]  # red
            elif var_lower == "holo rare":
                colors = ['background-color: #add8e6' for _ in row]  # blue
            # Bold if quantity > 1
            if row['Quantity'] > 1:
                colors = [f'{c}; font-weight: bold' if c else 'font-weight: bold' for c in colors]
            return colors

        # Reorder columns: Order, Card, Variation, Quantity
        df = df[['Order', 'Card', 'Variation', 'Quantity']]
        styled_df = df.style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (uncollapsed by default)")
    for buyer, items in summary_dict.items():
        header_info = buyer_info.get(buyer, '-')
        with st.expander(f"👤 {buyer} ({len(items)} items): {header_info}", expanded=True):
            buyer_df = pd.DataFrame(items)[['Order', 'Card', 'Variation', 'Quantity']]
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
    st.session_state.buyer_info = {}
    st.experimental_rerun()
