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
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$", re.MULTILINE)
    card_pattern = re.compile(r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)")

    cards_by_buyer = defaultdict(list)
    buyer_info_dict = {}
    current_buyer = None
    current_order = None

    for i, line in enumerate(lines):
        line = line.strip()

        # --- Detect order number ---
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
            continue

        # --- Detect buyer username ---
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
            continue

        # --- Detect Name & Shipping Address ---
        if current_buyer:
            # Line with only a number preceded by tab
            if re.match(r"^\t\d+$", line):
                name_addr_line = lines[i+1].strip() if i+1 < len(lines) else "-"
                buyer_info_dict[current_buyer] = name_addr_line
                continue

        # --- Detect card lines ---
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation = card_match.groups()

            # Look up to 5 lines above for Quantity
            qty = 1
            for k in range(i-1, max(i-6, -1), -1):
                qty_line = lines[k].strip()
                qty_match = re.match(r"Item no\.\s*\d+\s+Quantity:\s*(\d+)", qty_line)
                if qty_match:
                    qty = int(qty_match.group(1))
                    break

            cards_by_buyer[current_buyer].append({
                "order": current_order,
                "card": f"{number.strip()} {name.strip()}",
                "variation": variation.strip(),
                "quantity": qty
            })

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

        # Prepare plain text summary
        summary_text += f"\n👤 {buyer}\n" + "-"*40 + "\n"
        order_ids = sorted({c['order'] for c in cards if c['order']})
        if order_ids:
            summary_text += f"Orders: {', '.join(order_ids)}\n"
        for item in summary_list:
            summary_text += f"• {item['Card']} ({item['Variation']}) ×{item['Quantity']}\n"
        # Include Name & Shipping if available
        if buyer in buyer_info_dict:
            summary_text += f"Name & Shipping: {buyer_info_dict[buyer]}\n"
        summary_text += "\n"

    if not summary_dict:
        return None, {}, "", {}

    df = pd.DataFrame([item for items in summary_dict.values() for item in items])
    return df, summary_dict, summary_text.strip(), buyer_info_dict

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
    df, summary_dict, summary_text, buyer_info_dict = parse_picklist(picklist_text)
    st.session_state.parsed_df = df
    st.session_state.summary_dict = summary_dict
    st.session_state.summary_text = summary_text
    st.session_state.buyer_info_dict = buyer_info_dict

# --- SHOW RESULTS IF AVAILABLE ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    summary_text = st.session_state.summary_text
    buyer_info_dict = st.session_state.buyer_info_dict

    st.subheader("📊 Parsed Data (collapsed by default)")
    with st.expander("Show Parsed Data", expanded=False):
        # --- HIGHLIGHT FUNCTION BASED ON VARIATION & QUANTITY ---
        def highlight_cards(row):
            style = ['']*len(row)
            if row['Variation'].lower() == "holo rare":
                style = ['background-color: #add8e6']*len(row)  # blue
            elif row['Variation'].lower() == "non-holo":
                style = ['background-color: #ff9999']*len(row)  # red
            if row['Quantity'] >= highlight_threshold:
                style = ['font-weight: bold' if s=='' else s+'; font-weight: bold' for s in style]
            return style

        # --- Reorder columns ---
        df = df[['Order', 'Card', 'Variation', 'Quantity']]

        styled_df = df.style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (expanded by default)")
    for buyer, items in summary_dict.items():
        header = f"👤 {buyer} ({len(items)} items)"
        if buyer in buyer_info_dict:
            header += f": {buyer_info_dict[buyer]}"
        with st.expander(header, expanded=True):
            buyer_df = pd.DataFrame(items)
            buyer_df = buyer_df[['Order', 'Card', 'Variation', 'Quantity']]
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
    st.session_state.buyer_info_dict = {}
    st.experimental_rerun()
