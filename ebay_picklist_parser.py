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
    quantity_pattern = re.compile(r"Quantity:\s*(\d+)")
    buyer_info = {}

    cards_by_buyer = defaultdict(list)
    current_buyer = None
    current_order = None

    lines = text.splitlines()
    for i, line in enumerate(lines):
        line = line.strip()
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
            # Quantity is two lines above
            qty_line = lines[i-2].strip() if i >= 2 else ""
            qty_match = quantity_pattern.search(qty_line)
            qty = int(qty_match.group(1)) if qty_match else 1
            number, name, variation = card_match.groups()
            cards_by_buyer[current_buyer].append({
                "Order": current_order,
                "Card Number": number.strip(),
                "Card Name": name.strip(),
                "Variation": variation.strip(),
                "Quantity": qty
            })

    # --- Parse Name and Shipping Address ---
    for i, line in enumerate(lines):
        if re.match(r"^\s*\d+\s*$", line):  # line with only integer
            buyer_name_line = lines[i+1].strip() if i+1 < len(lines) else "-"
            address_lines = []
            j = i+2
            while j < len(lines) and lines[j].strip() != "" and not lines[j].startswith("Pokemon"):
                address_lines.append(lines[j].strip())
                j += 1
            full_address = ", ".join(address_lines)
            buyer_info[buyer_name_line] = f"{buyer_name_line} ({full_address})"

    # --- Prepare summary dict and text ---
    summary_dict = {}
    summary_text = ""
    for buyer, cards in cards_by_buyer.items():
        grouped = Counter((c["Card Number"], c["Card Name"], c["Variation"]) for c in cards)
        summary_list = []
        for (number, name, variation), qty in grouped.items():
            summary_list.append({
                "Order": next((c["Order"] for c in cards if c["Card Number"] == number), ""),
                "Card Number": number,
                "Card Name": name,
                "Variation": variation,
                "Quantity": qty
            })
        summary_dict[buyer] = summary_list

        # Prepare plain text summary
        summary_text += f"\n👤 {buyer}\n" + "-"*40 + "\n"
        order_ids = sorted({c['Order'] for c in cards if c['Order']})
        if order_ids:
            summary_text += f"Orders: {', '.join(order_ids)}\n"
        for item in summary_list:
            summary_text += f"• {item['Card Number']} {item['Card Name']} ({item['Variation']}) ×{item['Quantity']}\n"
        summary_text += "\n"

    # --- Create final DataFrame ---
    if not summary_dict:
        return None, {}, {}, ""

    df = pd.DataFrame([{
        "Order": item["Order"],
        "Card": f"{item['Card Number']} {item['Card Name']}",
        "Variation": item["Variation"],
        "Quantity": item["Quantity"]
    } for item in [c for cards in summary_dict.values() for c in cards]])

    return df, summary_dict, buyer_info, summary_text.strip()

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
    df, summary_dict, buyer_info, summary_text = parse_picklist(picklist_text)
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
            style = ['' for _ in row]
            # Variation coloring
            var = row['Variation'].lower()
            if var == "non-holo":
                style = ['background-color: #ff9999' for _ in row]
            elif var == "holo rare":
                style = ['background-color: #add8e6' for _ in row]
            # Bold if quantity > threshold
            if row['Quantity'] > 1:
                style = [f'font-weight: bold; {s}' for s in style]
            return style

        styled_df = df.style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (expanded by default)")
    for buyer, items in summary_dict.items():
        header_info = buyer_info.get(buyer, "-")
        with st.expander(f"👤 {buyer} ({len(items)} items): {header_info}", expanded=True):
            buyer_df = pd.DataFrame([{
                "Order": item["Order"],
                "Card": f"{item['Card Number']} {item['Card Name']}",
                "Variation": item["Variation"],
                "Quantity": item["Quantity"]
            } for item in items])

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
