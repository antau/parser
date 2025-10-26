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
    "buyer_info": {},
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
    order_pattern = re.compile(r"\b(\d{2}-\d{5}-\d{5})\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$", re.MULTILINE)
    card_pattern = re.compile(r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)")
    quantity_pattern = re.compile(r"Quantity:\s*(\d+)")

    cards_by_buyer = defaultdict(list)
    buyer_info = {}
    current_buyer = None
    current_order = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
        elif re.fullmatch(r"\s*\d+", line) and current_buyer:
            # Line with tab+integer precedes Name+Address
            name_line = lines[i + 1].strip()
            address_lines = []
            j = i + 2
            while j < len(lines) and lines[j].strip():
                address_lines.append(lines[j].strip())
                j += 1
            buyer_info[current_buyer] = {
                "Name": name_line,
                "Address": " ".join(address_lines)
            }
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation = card_match.groups()
            qty_line = lines[i - 2].strip() if i >= 2 else "Quantity: 1"
            qty_match = quantity_pattern.search(qty_line)
            quantity = int(qty_match.group(1)) if qty_match else 1
            cards_by_buyer[current_buyer].append({
                "order": current_order,
                "card": f"{number.strip()} {name.strip()}",
                "variation": variation.strip(),
                "quantity": quantity
            })
        i += 1

    summary_dict = {}
    summary_text = ""
    for buyer, cards in cards_by_buyer.items():
        grouped = Counter((c["card"], c["variation"]) for c in cards)
        summary_list = []
        for (card, variation), qty in grouped.items():
            summary_list.append({
                "Order": next((c["order"] for c in cards if c["card"] == card), ""),
                "Card": card,
                "Variation": variation,
                "Quantity": qty,
            })
        summary_dict[buyer] = summary_list

        # Plain text summary
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
    # Reorder columns: Order, Card, Variation, Quantity
    df = df[["Order", "Card", "Variation", "Quantity"]]
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
    st.session_state.buyer_info = buyer_info
    st.session_state.summary_text = summary_text

# --- SHOW RESULTS IF AVAILABLE ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    summary_text = st.session_state.summary_text
    buyer_info = st.session_state.buyer_info

    st.subheader("📊 Parsed Data")
    # Collapsed by default
    with st.expander("View Parsed Data (collapsed by default)", expanded=False):
        # --- HIGHLIGHT FUNCTION BASED ON VARIATION ---
        def highlight_cards(row):
            var_lower = str(row['Variation']).lower()
            styles = [''] * len(row)
            if var_lower == "non-holo":
                styles = ['background-color: #ff9999' for _ in row]  # red
            elif var_lower == "holo rare":
                styles = ['background-color: #add8e6' for _ in row]  # blue
            if row['Quantity'] >= highlight_threshold:
                styles = ['font-weight: bold'] * len(row)
            return styles

        styled_df = df.style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary")
    # Uncollapsed by default
    for buyer, items in summary_dict.items():
        info = buyer_info.get(buyer, {"Name": "", "Address": ""})
        with st.expander(f"👤 {buyer} ({len(items)} items): {info['Name']} - {info['Address']}", expanded=True):
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
    st.session_state.buyer_info = {}
    st.session_state.summary_text = ""
    st.experimental_rerun()
