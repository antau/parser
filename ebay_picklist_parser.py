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
    buyers_info = {}
    current_buyer = None
    current_order = None

    lines = text.splitlines()

    for i, line in enumerate(lines):
        line = line.strip()
        # Check for order
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
        # Check for buyer
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
        # Capture shipping info: a line with only an integer number precedes name & address
        elif current_buyer and line.isdigit() and i+1 < len(lines):
            name_address_lines = []
            for j in range(i+1, len(lines)):
                next_line = lines[j].strip()
                if not next_line:
                    break
                name_address_lines.append(next_line)
            buyers_info[current_buyer] = " ".join(name_address_lines)

        # Check for card line
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation = card_match.groups()
            # Look up to 5 lines above for Quantity
            qty = 1
            for k in range(i-1, max(i-6, -1), -1):
                qty_line = lines[k].strip()
                qty_match = re.match(r"Item no\.: \d+\s+Quantity:\s*(\d+)", qty_line)
                if qty_match:
                    qty = int(qty_match.group(1))
                    break
            cards_by_buyer[current_buyer].append({
                "order": current_order,
                "card": f"{number.strip()} {name.strip()}",
                "variation": variation.strip(),
                "quantity": qty,
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
        summary_text += "\n"

    if not summary_dict:
        return None, {}, ""

    df = pd.DataFrame([item for items in summary_dict.values() for item in items])
    return df, summary_dict, summary_text.strip(), buyers_info

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
    df, summary_dict, summary_text, buyers_info = parse_picklist(picklist_text)
    st.session_state.parsed_df = df
    st.session_state.summary_dict = summary_dict
    st.session_state.summary_text = summary_text
    st.session_state.buyers_info = buyers_info

# --- SHOW RESULTS IF AVAILABLE ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    summary_text = st.session_state.summary_text
    buyers_info = st.session_state.buyers_info

    st.subheader("📊 Parsed Data")
    with st.expander("View Parsed Data", expanded=False):
        def highlight_cards(row):
            styles = ['']*len(row)
            if row['Variation'].lower() == "non-holo":
                styles = ['background-color: #ff9999']*len(row)  # red
            elif row['Variation'].lower() == "holo rare":
                styles = ['background-color: #add8ff']*len(row)  # blue
            elif row['Quantity'] >= highlight_threshold:
                styles = ['background-color: #ffdd99']*len(row)  # orange
            if row['Quantity'] > 1:
                styles = [f"{s}; font-weight: bold" if s else "font-weight: bold" for s in styles]
            return styles

        st.dataframe(df.style.apply(highlight_cards, axis=1), use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary")
    for buyer, items in summary_dict.items():
        header_info = buyers_info.get(buyer, "-")
        with st.expander(f"👤 {buyer} ({len(items)} items): {header_info}", expanded=True):
            buyer_df = pd.DataFrame(items)
            st.dataframe(buyer_df.style.apply(highlight_cards, axis=1), use_container_width=True)

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
    st.session_state.buyers_info = {}
    st.experimental_rerun()
