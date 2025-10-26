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
    order_pattern = re.compile(r"\b(\d{2}-\d{5}-\d{5})\b")
    buyer_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")
    card_pattern = re.compile(r"Select Your Card:\s*([\d/]+)\s+([^(]+)\(([^)]+)\)")

    cards_by_buyer = defaultdict(list)
    buyer_info = {}
    current_buyer = None
    current_order = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line
        elif re.fullmatch(r"\s*\d+", line) and current_buyer:
            # Line with number (tabs/spaces) precedes Name + Address
            if i + 1 < len(lines):
                name_line = lines[i + 1].strip()
            else:
                name_line = "-"
            address_lines = []
            j = i + 2
            while j < len(lines) and lines[j].strip():  # keep reading until blank line
                address_lines.append(lines[j].strip())
                j += 1
            buyer_info[current_buyer] = {
                "Name": name_line,
                "Address": " ".join(address_lines) if address_lines else "-"
            }
            i = j - 1  # skip processed lines
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation = card_match.groups()
            # Look two lines back for Quantity
            qty = 1
            if i >= 2:
                qty_line = lines[i - 2].strip()
                qty_match = re.match(r"Quantity:\s*(\d+)", qty_line)
                if qty_match:
                    qty = int(qty_match.group(1))
            cards_by_buyer[current_buyer].append({
                "order": current_order,
                "number": number.strip(),
                "name": name.strip(),
                "variation": variation.strip(),
                "quantity": qty
            })
        i += 1

    summary_dict = {}
    summary_text = ""
    for buyer, cards in cards_by_buyer.items():
        grouped = Counter((c["number"], c["name"], c["variation"]) for c in cards)
        summary_list = []
        for (number, name, variation), qty in grouped.items():
            summary_list.append({
                "Order": next((c["order"] for c in cards if c["number"] == number), ""),
                "Card": f"{number} {name.strip()}",
                "Variation": variation.strip(),
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
    with st.expander("Show Parsed Data (collapsed by default)", expanded=False):
        def highlight_cards(row):
            var_lower = str(row['Variation']).lower()
            if var_lower == "non-holo":
                return ['background-color: #ff9999' for _ in row]  # red
            elif var_lower == "holo rare":
                return ['background-color: #add8e6' for _ in row]  # blue
            elif row['Quantity'] >= highlight_threshold:
                return ['background-color: #ffdd99' for _ in row]  # light orange
            else:
                return ['' for _ in row]

        styled_df = df.style.apply(highlight_cards, axis=1).format({"Quantity": "{:.0f}"})
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (uncollapsed by default)")
    for buyer, items in summary_dict.items():
        buyer_name = buyer_info.get(buyer, {}).get("Name", "-")
        buyer_address = buyer_info.get(buyer, {}).get("Address", "-")
        with st.expander(f"👤 {buyer} ({len(items)} items): {buyer_name}, {buyer_address}", expanded=True):
            buyer_df = pd.DataFrame(items)
            styled_buyer_df = buyer_df.style.apply(highlight_cards, axis=1).format({"Quantity": "{:.0f}"})
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
