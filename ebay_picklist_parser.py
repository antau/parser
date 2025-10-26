import re
from collections import defaultdict, Counter
import pandas as pd
import streamlit as st

# --- PAGE SETUP ---
st.set_page_config(page_title="eBay Picklist Parser", page_icon="🃏", layout="wide")
st.title("🃏 eBay Picklist Parser")
st.write("Paste your eBay picklist text below to extract card variations, buyers, and quantities.")

# --- SESSION STATE ---
for key, default in {
    "picklist_text": "",
    "parsed_df": None,
    "summary_dict": {},
    "buyer_info": {},
    "highlight_threshold": 1,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

highlight_threshold = st.sidebar.number_input(
    "Highlight cards with Quantity ≥",
    1,
    value=st.session_state.highlight_threshold
)
st.session_state.highlight_threshold = highlight_threshold

# --- PARSE FUNCTION ---
def parse_picklist(text):
    lines = text.splitlines()
    order_pattern = re.compile(r"\b\d{2}-\d{5}-\d{5}\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
    card_pattern = re.compile(r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)")
    quantity_pattern = re.compile(r"Quantity:\s*(\d+)")

    cards_by_buyer = defaultdict(list)
    buyer_info = {}
    current_buyer = None
    current_order = None
    qty = 1

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Order
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(0)

        # Buyer
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line

        # Quantity line
        if line.startswith("Item no.:") and "Quantity:" in line:
            qty_match = quantity_pattern.search(line)
            qty = int(qty_match.group(1)) if qty_match else 1

        # Card line
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation = card_match.groups()
            cards_by_buyer[current_buyer].append({
                "Order": current_order,
                "Card": f"{number.strip()} {name.strip()}",
                "Variation": variation.strip(),
                "Quantity": qty
            })

        # Buyer name/address (after line with single integer)
        if re.match(r"^\t?\d+\s*$", line):
            info_lines = []
            j = i + 1
            while j < len(lines) and lines[j].strip() != "":
                info_lines.append(lines[j].strip())
                j += 1
            if info_lines:
                name = info_lines[0]
                address = ", ".join(info_lines[1:]) if len(info_lines) > 1 else "-"
                buyer_info[current_buyer] = f"{name} ({address})"
            i = j - 1  # skip parsed lines

        i += 1

    # Prepare DataFrame and summary
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
                "Quantity": qty
            })
        summary_dict[buyer] = summary_list

        # Summary text
        summary_text += f"\n👤 {buyer}\n{'-'*40}\n"
        orders = sorted({c['Order'] for c in cards if c['Order']})
        if orders:
            summary_text += f"Orders: {', '.join(orders)}\n"
        for item in summary_list:
            summary_text += f"• {item['Card']} ({item['Variation']}) ×{item['Quantity']}\n"

    df = pd.DataFrame([item for items in summary_dict.values() for item in items]) if summary_dict else None
    return df, summary_dict, buyer_info, summary_text.strip()

# --- TEXT INPUT ---
picklist_text = st.text_area(
    "Paste your picklist here:",
    value=st.session_state.picklist_text,
    height=300
)
st.session_state.picklist_text = picklist_text

if picklist_text.strip():
    df, summary_dict, buyer_info, summary_text = parse_picklist(picklist_text)
    st.session_state.parsed_df = df
    st.session_state.summary_dict = summary_dict
    st.session_state.buyer_info = buyer_info
    st.session_state.summary_text = summary_text

# --- SHOW RESULTS ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    buyer_info = st.session_state.buyer_info
    summary_text = st.session_state.summary_text

    # --- HIGHLIGHT FUNCTION ---
    def highlight_cards(row):
        color = ""
        if row['Variation'] == "Non-Holo":
            color = "#ff9999"  # red
        elif row['Variation'] == "Holo Rare":
            color = "#99ccff"  # blue
        styles = [f"background-color: {color}" if color else "" for _ in row]
        if row['Quantity'] > 1:
            styles = [s + "; font-weight: bold" if s else "font-weight: bold" for s in styles]
        return styles

    with st.expander("Parsed Data", expanded=False):
        st.dataframe(df.style.apply(highlight_cards, axis=1), use_container_width=True)

    st.subheader("Per-Buyer Packing Summary")
    for buyer, items in summary_dict.items():
        with st.expander(f"{buyer} ({len(items)} items): {buyer_info.get(buyer,'-')}", expanded=True):
            buyer_df = pd.DataFrame(items)
            st.dataframe(buyer_df.style.apply(highlight_cards, axis=1), use_container_width=True)

    # --- DOWNLOAD BUTTONS ---
    col1, col2 = st.columns(2)
    col1.download_button("⬇️ Download Parsed CSV", df.to_csv(index=False).encode("utf-8"), file_name="parsed.csv")
    col2.download_button("📋 Download Summary", summary_text.encode("utf-8"), file_name="summary.txt")

# --- CLEAR BUTTON ---
if st.button("🧹 Clear All Data"):
    st.session_state.picklist_text = ""
    st.session_state.parsed_df = None
    st.session_state.summary_dict = {}
    st.session_state.buyer_info = {}
    st.session_state.summary_text = ""
    st.experimental_rerun()
