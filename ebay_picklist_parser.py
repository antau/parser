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
    "highlight_threshold": 1,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- SETTINGS ---
st.sidebar.title("Settings")
highlight_threshold = st.sidebar.number_input(
    "Highlight cards with quantity ≥",
    min_value=1,
    value=st.session_state.highlight_threshold
)
st.session_state.highlight_threshold = highlight_threshold

# --- PARSE FUNCTION ---
def parse_picklist(text):
    lines = text.splitlines()
    order_pattern = re.compile(r"\b\d{2}-\d{5}-\d{5}\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
    card_pattern = re.compile(r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)")
    qty_pattern = re.compile(r"Quantity:\s*(\d+)")

    cards_by_buyer = defaultdict(list)
    buyer_info = {}
    current_buyer = None
    current_order = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Detect order
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(0)
            i += 1
            continue

        # Detect buyer
        if buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
            i += 1
            continue

        # Detect buyer's Name & Address
        if line.startswith("\t") and line.strip().isdigit() and current_buyer:
            addr_lines = []
            j = i + 1
            while j < len(lines) and lines[j].strip():
                addr_lines.append(lines[j].strip())
                j += 1
            buyer_info[current_buyer] = " | ".join(addr_lines) if addr_lines else "-"
            i = j
            continue

        # Detect card
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            # Look backwards for nearest "Item no." line to get Quantity
            qty = 1
            for j in range(i-1, -1, -1):
                prev_line = lines[j].strip()
                if prev_line.startswith("Item no.:"):
                    qty_match = qty_pattern.search(prev_line)
                    if qty_match:
                        qty = int(qty_match.group(1))
                    break
            number, name, variation = card_match.groups()
            cards_by_buyer[current_buyer].append({
                "Order": current_order,
                "Card": f"{number.strip()} {name.strip()}",
                "Variation": variation.strip(),
                "Quantity": qty
            })
        i += 1

    # Build summary_dict
    summary_dict = {}
    summary_text = ""
    for buyer, cards in cards_by_buyer.items():
        summary_dict[buyer] = cards
        summary_text += f"\n👤 {buyer}\n" + "-"*40 + "\n"
        for item in cards:
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

# --- HIGHLIGHT FUNCTION ---
def highlight_cards(row):
    colors = [""] * len(row)
    variation = row["Variation"].lower()
    if variation == "non-holo":
        colors = ["background-color: red"] * len(row)
    elif variation == "holo rare":
        colors = ["background-color: lightblue"] * len(row)
    # Bold if quantity > highlight threshold
    if row["Quantity"] > 1:
        colors = [f"{c}; font-weight: bold" if c else "font-weight: bold" for c in colors]
    return colors

# --- DISPLAY RESULTS ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    summary_text = st.session_state.summary_text
    buyer_info = st.session_state.buyer_info

    st.subheader("📊 Parsed Data (Collapsed by Default)")
    with st.expander("Show Parsed Data", expanded=False):
        styled_df = df.style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (Expanded by Default)")
    for buyer, items in summary_dict.items():
        header_text = f"👤 {buyer} ({len(items)} items)"
        if buyer in buyer_info:
            header_text += f": {buyer_info[buyer]}"
        with st.expander(header_text, expanded=True):
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
