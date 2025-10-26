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
    lines = text.splitlines()
    order_pattern = re.compile(r"\b(\d{2}-\d{5}-\d{5})\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$", re.MULTILINE)
    card_pattern = re.compile(r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)")
    quantity_pattern = re.compile(r"Quantity:\s*(\d+)")

    cards_by_buyer = defaultdict(list)
    current_buyer = None
    current_order = None

    # Parse Name + Shipping Address
    buyer_info = {}

    for i, line in enumerate(lines):
        line = line.strip()
        # Detect order number
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
            continue

        # Detect buyer
        if buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
            # Look for Name + Shipping Address after a line with just "\t<number>\t"
            buyer_info[current_buyer] = "-"
            if i+1 < len(lines):
                next_line = lines[i+1].strip()
                # Check if next line is tab + number + tab
                if re.match(r"^\t\d+\t$", next_line):
                    if i+2 < len(lines):
                        name_address_line = lines[i+2].strip()
                        buyer_info[current_buyer] = name_address_line
            continue

        # Detect card
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            # Quantity is two lines above
            qty_line = lines[i-2].strip() if i >= 2 else ""
            qty_match = quantity_pattern.search(qty_line)
            qty = int(qty_match.group(1)) if qty_match else 1

            number, name, variation = card_match.groups()
            cards_by_buyer[current_buyer].append({
                "Order": current_order or "",
                "Card": f"{number.strip()} {name.strip()}",
                "Variation": variation.strip(),
                "Quantity": qty,
            })

    # Build summary dict and DataFrame
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
        summary_text += "\n"

    if not summary_dict:
        return None, {}, ""

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

    st.subheader("📊 Parsed Data (Collapsed by Default)")
    with st.expander("Show Parsed Data", expanded=False):
        # --- HIGHLIGHT FUNCTION ---
        def highlight_cards(row):
            colors = [''] * len(row)
            var_lower = str(row.get('Variation', '')).lower()
            if var_lower == "non-holo":
                colors = ['background-color: #ff9999'] * len(row)
            elif var_lower == "holo rare":
                colors = ['background-color: #add8ff'] * len(row)
            if row.get('Quantity', 0) > 1:
                colors = [f'font-weight: bold; {c}' for c in colors]
            return colors

        styled_df = df.style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (Expanded by Default)")
    for buyer, items in summary_dict.items():
        with st.expander(f"👤 {buyer} ({len(items)} items): {buyer_info.get(buyer, '-')}", expanded=True):
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
