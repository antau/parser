import re
import streamlit as st
from collections import defaultdict
import pandas as pd

st.title("Picklist Parser")

# --- Input ---
picklist_text = st.text_area("Paste your picklist here", height=500)

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

    # --- Display per-buyer tables ---
    st.subheader("Parsed Picklist")

    for buyer, items in cards_by_buyer.items():
        df_buyer = pd.DataFrame(items)
        df_buyer.insert(0, "#", range(1, len(df_buyer)+1))  # Add incremental #

        # Calculate total cards
        total_cards = df_buyer['Quantity'].sum()
        num_items = len(df_buyer)

        # Expander label
        expander_label = f"{num_items} items, {total_cards} total cards - {buyer}"

        # Highlight function
        def highlight_cards(row):
            styles = [""] * len(row)
            if row["Quantity"] > 1:
                styles = ["font-weight: bold" for _ in row]
            return styles

        with st.expander(expander_label, expanded=False):
            st.dataframe(
                df_buyer.style.apply(highlight_cards, axis=1).set_table_styles(
                    [{"selector": "th, td", "props": [("min-width", "120px"), ("max-width", "250px")]}]
                ),
                use_container_width=True
            )

    # --- Download CSV ---
    all_items = [item for items in cards_by_buyer.values() for item in items]
    df_all = pd.DataFrame(all_items)
    df_all.insert(0, "#", range(1, len(df_all)+1))
    csv = df_all.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="Download Full CSV",
        data=csv,
        file_name="picklist_parsed.csv",
        mime="text/csv"
    )
