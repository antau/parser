import re
import streamlit as st
from collections import defaultdict
import pandas as pd

st.title("Picklist Parser")

# --- Input text area ---
picklist_text = st.text_area("Paste your picklist here", height=500)

# --- Highlight threshold ---
highlight_threshold = st.sidebar.number_input("Highlight cards with Quantity ≥", min_value=1, value=1)

if picklist_text:
    # --- Regex patterns ---
    order_pattern = re.compile(r"\b\d{2}-\d{5}-\d{5}\b")
    quantity_pattern = re.compile(r"Item no\.: .* Quantity: (\d+)", re.IGNORECASE)
    card_pattern = re.compile(r"Select Your Card: (\d+/\d+) (.+?) \((.+?)\)")
    
    cards_by_buyer = defaultdict(list)
    current_order = None
    current_buyer = None
    lines = picklist_text.splitlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect order line
        if order_pattern.match(line):
            current_order = line

        # Detect buyer (heuristic)
        elif line and not line.startswith(("Pokemon", "Item no", "Value")) and not order_pattern.match(line):
            buyer_name_line = line
            buyer_address_lines = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line or order_pattern.match(next_line) or next_line.startswith(("Pokemon", "Item no", "Value")):
                    break
                buyer_address_lines.append(next_line)
                j += 1
            if buyer_address_lines:
                current_buyer = f"{buyer_name_line} ({', '.join(buyer_address_lines)})"
            else:
                current_buyer = buyer_name_line
            i = j - 1

        # Detect Quantity line
        qty_match = quantity_pattern.search(line)
        if qty_match:
            quantity = int(qty_match.group(1))

            # Look ahead for card line
            j = i + 1
            while j < len(lines):
                card_match = card_pattern.search(lines[j])
                if card_match:
                    card_number, card_name, variation = card_match.groups()
                    if current_buyer:
                        cards_by_buyer[current_buyer].append({
                            "Order": current_order,
                            "Card": f"{card_number} {card_name}",
                            "Variation": variation,
                            "Quantity": quantity
                        })
                    break
                j += 1
            i = j  # skip to card line after processing

        i += 1

    # --- Highlight function ---
    def highlight_cards(row):
        color = ""
        if row['Variation'] == "Non-Holo":
            color = "#ffcccc"  # light red
        elif row['Variation'] == "Holo Rare":
            color = "#cce5ff"  # light blue
        styles = [f"background-color: {color}" if color else "" for _ in row]
        if row['Quantity'] >= highlight_threshold:
            styles = [s + "; font-weight: bold" if s else "font-weight: bold" for s in styles]
        return styles

    # --- Display per-buyer tables ---
    st.subheader("Parsed Picklist")
    all_summary_text = ""
    for buyer, items in cards_by_buyer.items():
        with st.expander(f"Buyer: {buyer} ({len(items)} items)", expanded=True):
            df_buyer = pd.DataFrame(items)
            st.dataframe(df_buyer.style.apply(highlight_cards, axis=1), use_container_width=True)

            # Prepare summary text
            buyer_summary = f"👤 {buyer}\n{'-'*40}\n"
            orders = sorted({c['Order'] for c in items if c['Order']})
            if orders:
                buyer_summary += f"Orders: {', '.join(orders)}\n"
            for c in items:
                buyer_summary += f"• {c['Card']} ({c['Variation']}) ×{c['Quantity']}\n"
            all_summary_text += buyer_summary + "\n"

    # --- CSV download ---
    all_items = [item for items in cards_by_buyer.values() for item in items]
    df_all = pd.DataFrame(all_items)
    csv_data = df_all.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Full CSV",
        data=csv_data,
        file_name="picklist_parsed.csv",
        mime="text/csv"
    )

    # --- Summary text download ---
    st.download_button(
        label="📋 Download Per-Buyer Summary",
        data=all_summary_text.encode('utf-8'),
        file_name="picklist_summary.txt",
        mime="text/plain"
    )
