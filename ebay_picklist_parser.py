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
    quantity_pattern = re.compile(r"(\d+)\s*$")  # last integer on line

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
            continue

        # Detect buyer username
        if buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
            continue

        # Detect shipping info (line after tab + integer line)
        if current_buyer and re.match(r"^\t\d+\t$", line):
            if i+1 < len(lines):
                shipping_line = lines[i+1].strip()
                buyer_info[current_buyer] = shipping_line
            continue

        # Detect card line
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            # Quantity is found two lines above "Select Your Card:"
            qty_line = lines[i-2].strip() if i >= 2 else ""
            qty_match = quantity_pattern.search(qty_line)
            qty = int(qty_match.group(1)) if qty_match else 1

            number, name, variation = card_match.groups()
            cards_by_buyer[current_buyer].append({
                "Order": current_order,
                "Card": f"{number.strip()} {name.strip()}",
                "Variation": variation.strip(),
                "Quantity": qty
            })

    # Build summary dict and text
    summary_dict = {}
    summary_text = ""
    for buyer, items in cards_by_buyer.items():
        grouped = Counter((c["Card"], c["Variation"]) for c in items)
        summary_list = []
        for (card, variation), qty in grouped.items():
            order = next((c["Order"] for c in items if c["Card"] == card), "")
            summary_list.append({
                "Order": order,
                "Card": card,
                "Variation": variation,
                "Quantity": qty
            })
        summary_dict[buyer] = summary_list

        # Prepare text summary
        summary_text += f"\n👤 {buyer}\n" + "-"*40 + "\n"
        order_ids = sorted({c['Order'] for c in items if c['Order']})
        if order_ids:
            summary_text += f"Orders: {', '.join(order_ids)}\n"
        for item in summary_list:
            summary_text += f"• {item['Card']} ({item['Variation']}) ×{item['Quantity']}\n"
        if buyer in buyer_info:
            summary_text += f"Shipping: {buyer_info[buyer]}\n"
        summary_text += "\n"

    # Create DataFrame
    df = pd.DataFrame([item for items in summary_dict.values() for item in items])
    return df if not df.empty else None, summary_dict, summary_text.strip(), buyer_info

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

    st.subheader("📊 Parsed Data")
    with st.expander("Parsed Data Table (collapsed by default)", expanded=False):
        def highlight_cards(row):
            var = str(row['Variation']).lower()
            if var == "non-holo":
                colors = ['background-color: #ff9999'] * len(row)  # red
            elif var == "holo rare":
                colors = ['background-color: #99ccff'] * len(row)  # blue
            else:
                colors = [''] * len(row)

            # Bold rows if Quantity > 1
            if row['Quantity'] > 1:
                colors = [c + "; font-weight: bold" if c else "font-weight: bold" for c in colors]
            return colors

        styled_df = df.style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (expanded by default)")
    for buyer, items in summary_dict.items():
        shipping = buyer_info.get(buyer, "-")
        with st.expander(f"👤 {buyer} ({len(items)} items): {shipping}", expanded=True):
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
    st.session_state.buyer_info = {}
    st.experimental_rerun()
