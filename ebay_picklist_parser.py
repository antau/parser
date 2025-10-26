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

    cards_by_buyer = defaultdict(list)
    buyer_info = {}  # Store name & shipping
    current_buyer = None
    current_order = None
    previous_lines = []

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        previous_lines.append(line)
        if len(previous_lines) > 3:
            previous_lines.pop(0)

        # Detect order number
        order_match = order_pattern.search(line)
        if order_match:
            current_order = order_match.group(1)

        # Detect buyer
        elif buyer_pattern.match(line) and not line.startswith("Pokemon"):
            current_buyer = line

        # Detect single integer line (for Name + Shipping)
        elif re.fullmatch(r"\d+", line) and current_buyer:
            # Next line is Name
            name_line = lines[i+1].strip() if i+1 < len(lines) else ""
            # Following lines until empty line or another marker are shipping address
            addr_lines = []
            j = i+2
            while j < len(lines) and lines[j].strip():
                addr_lines.append(lines[j].strip())
                j += 1
            buyer_info[current_buyer] = {
                "name": name_line,
                "address": ", ".join(addr_lines)
            }

        # Detect card
        card_match = card_pattern.search(line)
        if card_match and current_buyer:
            number, name, variation = card_match.groups()
            # Quantity is 2 lines before "Select Your Card:"
            quantity_line = previous_lines[-3] if len(previous_lines) >= 3 else ""
            quantity_match = re.search(r"Quantity:\s*(\d+)", quantity_line)
            quantity = int(quantity_match.group(1)) if quantity_match else 1
            cards_by_buyer[current_buyer].append({
                "order": current_order,
                "number": number.strip(),
                "name": name.strip(),
                "variation": variation.strip(),
                "quantity": quantity,
            })

        i += 1

    # --- Build summary dict ---
    summary_dict = {}
    summary_text = ""
    for buyer, cards in cards_by_buyer.items():
        grouped = Counter((c["number"], c["name"], c["variation"]) for c in cards)
        summary_list = []
        for (number, name, variation), qty in grouped.items():
            order_val = next((c["order"] for c in cards if c["number"] == number), "")
            summary_list.append({
                "Order": order_val,
                "Card": f"{number} {name.strip()}",
                "Variation": variation.strip(),
                "Quantity": qty,
            })
        summary_dict[buyer] = summary_list

        # Prepare text summary
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

# --- HIGHLIGHT FUNCTION ---
def highlight_cards(row):
    var_lower = str(row['Variation']).lower()
    styles = ['']*len(row)
    if var_lower == "non-holo":
        styles = ['background-color: #ff9999' for _ in row]  # red
    elif var_lower == "holo rare":
        styles = ['background-color: #99ccff' for _ in row]  # blue
    if row['Quantity'] > 1:
        styles = [s+'; font-weight: bold' if s else 'font-weight: bold' for s in styles]
    return styles

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
    st.session_state.buyer_info = buyer_info
    st.session_state.summary_text = summary_text

# --- SHOW RESULTS IF AVAILABLE ---
if st.session_state.parsed_df is not None:
    df = st.session_state.parsed_df
    summary_dict = st.session_state.summary_dict
    buyer_info = st.session_state.buyer_info
    summary_text = st.session_state.summary_text

    st.subheader("📊 Parsed Data (Collapsed by Default)")
    with st.expander("Show Parsed Data", expanded=False):
        styled_df = df[['Order', 'Card', 'Variation', 'Quantity']].style.apply(highlight_cards, axis=1)
        st.dataframe(styled_df, use_container_width=True)

    st.subheader("📦 Per-Buyer Packing Summary (Expanded by Default)")
    for buyer, items in summary_dict.items():
        info = buyer_info.get(buyer, {})
        name = info.get("name", "")
        address = info.get("address", "")
        header_text = f"👤 {buyer} ({len(items)} items): Name: {name}, Shipping: {address}"
        with st.expander(header_text, expanded=True):
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
    st.session_state.buyer_info = {}
    st.session_state.summary_text = ""
    st.experimental_rerun()
