import re
from collections import defaultdict, Counter
import pandas as pd
import streamlit as st

# --- PAGE SETUP ---
st.set_page_config(page_title="eBay Picklist Parser", page_icon="🃏", layout="wide")
st.title("🃏 eBay Picklist Parser")
st.write("Paste your eBay picklist text below to extract card variations, buyers, quantities, and shipping info.")

# --- SESSION STATE ---
for key, default in {
    "picklist_text": "",
    "parsed_df": None,
    "summary_dict": {},
    "buyer_info": {},
    "theme": "light",
    "highlight_threshold": 1
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- THEME ---
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
    buyer_info_pattern = re.compile(r"^\t\d+\t$")  # Line with tab, number, tab

    cards_by_buyer = defaultdict(list)
    buyer_info = {}
    current_buyer = None
    current_order = None
    lines = text.splitlines()
    current_qty = 1

    for i, line in enumerate(lines):
        line = line.strip()
        # Detect order
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
        # Detect buyer
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
        # Detect buyer shipping info
        elif buyer_info_pattern.match(line) and i + 1 < len(lines):
            name_address = lines[i + 1].strip()
            buyer_info[current_buyer] = name_address
        # Detect quantity
        if "Item no.:" in line:
            qty_match = quantity_pattern.search(line)
            current_qty = int(qty_match.group(1)) if qty_match else 1
        # Detect card
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation = card_match.groups()
            cards_by_buyer[current_buyer].append({
                "order": current_order,
                "card": f"{number.strip()} {name.strip()}",
                "variation": variation.strip(),
                "quantity": current_qty
            })

    # Build summary
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
                "Quantity": qty
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
        return None, {}, {}, ""

    df = pd.DataFrame([item for items in summary_dict.values() for item in items])
    return df, summary_dict, buyer_info, summary_text.strip()

# --- TEXT INPUT ---
picklist_text = st.text_area(
    "Paste your picklist text here:",
    height=300,
    value=st.session_state.picklist_text,
    placeholder="Paste your eBay picklist text here..."
)
st.session_state.picklist_text = picklist_text

# --- AUTO-PARSE ---
if picklist_text.strip():
    df, summary_dict, buyer_info, summary_text = parse_picklist(picklist_text)
    st.session_state.parsed_df = df
    st.session_state.summary_dict = summary_dict
    st.session_state.buyer_info = buyer_info
    st.session_state.summary_text = summary_text

# --- DISPLAY RESULTS ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    buyer_info = st.session_state.buyer_info
    summary_text = st.session_state.summary_text

    st.subheader("📊 Parsed Data")
    def highlight_cards(row):
        styles = ['']*len(row)
        var_lower = str(row['Variation']).lower()
        if var_lower == "non-holo":
            styles = ['background-color: #ff9999' for _ in row]  # red
        elif var_lower == "holo rare":
            styles = ['background-color: #99ccff' for _ in row]  # blue
        if row['Quantity'] > 1:
            styles = [s + '; font-weight: bold' for s in styles]
        return styles

    with st.expander("Parsed Data Table (collapsed)", expanded=False):
        st.dataframe(df.style.apply(highlight_cards, axis=1), use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary")
    for buyer, items in summary_dict.items():
        buyer_header = f"👤 {buyer} ({len(items)} items): {buyer_info.get(buyer,'-')}"
        with st.expander(buyer_header, expanded=True):
            buyer_df = pd.DataFrame(items)
            st.dataframe(buyer_df.style.apply(highlight_cards, axis=1), use_container_width=True)

    # --- DOWNLOAD ---
    csv = df.to_csv(index=False).encode("utf-8")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("⬇️ Download Parsed CSV", csv, "parsed_picklist.csv", "text/csv")
    with col2:
        st.download_button("📋 Download Summary as Text", summary_text.encode("utf-8"), "picklist_summary.txt", "text/plain")

# --- CLEAR ---
if st.button("🧹 Clear All Data"):
    st.session_state.picklist_text = ""
    st.session_state.parsed_df = None
    st.session_state.summary_dict = {}
    st.session_state.buyer_info = {}
    st.session_state.summary_text = ""
    st.experimental_rerun()
