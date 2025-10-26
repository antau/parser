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
    cards_by_buyer = defaultdict(list)
    buyer_info = {}
    current_buyer = None
    current_order = None

    order_pattern = re.compile(r"\b(\d{2}-\d{5}-\d{5})\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
    item_pattern = re.compile(r"Item no\.: .* Quantity: (\d+)")
    card_pattern = re.compile(r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)")
    buyer_info_pattern = re.compile(r"^\t\d+\t$")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Order
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)

        # Buyer
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line

        # Quantity and Card
        item_match = item_pattern.search(line)
        if item_match and current_buyer:
            qty = int(item_match.group(1))
            # Look ahead for card
            for j in range(i+1, min(i+5, len(lines))):
                card_match = card_pattern.search(lines[j])
                if card_match:
                    number, name, variation = card_match.groups()
                    cards_by_buyer[current_buyer].append({
                        "Order": current_order,
                        "Card": f"{number.strip()} {name.strip()}",
                        "Variation": variation.strip(),
                        "Quantity": qty,
                    })
                    break

        # Buyer Name + Address
        if buyer_info_pattern.match(line) and current_buyer:
            name_line_idx = i + 1
            if name_line_idx < len(lines):
                name = lines[name_line_idx].strip()
                address_lines = []
                addr_idx = name_line_idx + 1
                while addr_idx < len(lines) and lines[addr_idx].strip() != "":
                    address_lines.append(lines[addr_idx].strip())
                    addr_idx += 1
                address = ", ".join(address_lines)
                buyer_info[current_buyer] = f"{name} ({address})"
                i = addr_idx - 1  # skip processed lines

        i += 1

    # Create summary dict
    summary_dict = {}
    summary_text = ""
    for buyer, cards in cards_by_buyer.items():
        grouped = Counter((c["Card"], c["Variation"]) for c in cards)
        summary_list = []
        for (card, variation), qty in grouped.items():
            summary_list.append({
                "Order": next((c["Order"] for c in cards if c["Card"] == card), ""),
                "Card": card,
                "Variation": variation,
                "Quantity": qty,
            })
        summary_dict[buyer] = summary_list

        # Prepare plain text summary
        summary_text += f"\n👤 {buyer}\n" + "-"*40 + "\n"
        order_ids = sorted({c['Order'] for c in cards if c['Order']})
        if order_ids:
            summary_text += f"Orders: {', '.join(order_ids)}\n"
        for item in summary_list:
            summary_text += f"• {item['Card']} ({item['Variation']}) ×{item['Quantity']}\n"
        # Add shipping info if available
        if buyer in buyer_info:
            summary_text += f"Shipping: {buyer_info[buyer]}\n"
        summary_text += "\n"

    df = pd.DataFrame([item for items in summary_dict.values() for item in items]) if summary_dict else None

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

    st.subheader("📊 Parsed Data")
    def highlight_cards(row):
        v = row['Variation'].lower()
        if v == "non-holo":
            return ['background-color: #ff9999' for _ in row]  # red
        elif v == "holo rare":
            return ['background-color: #add8e6' for _ in row]  # blue
        else:
            return ['' for _ in row]  # Reverse Holo or others remain uncolored

    def bold_quantity(row):
        return ['font-weight: bold' if row['Quantity'] > 1 else '' for _ in row]

    styled_df = df.style.apply(highlight_cards, axis=1).apply(bold_quantity, axis=1)
    with st.expander("Parsed Data Table (collapsed by default)", expanded=False):
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary")
    for buyer, items in summary_dict.items():
        shipping = buyer_info.get(buyer, "-")
        with st.expander(f"👤 {buyer} ({len(items)} items): {shipping}", expanded=True):
            buyer_df = pd.DataFrame(items)
            styled_buyer_df = buyer_df.style.apply(highlight_cards, axis=1).apply(bold_quantity, axis=1)
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
