import re
import streamlit as st
from collections import defaultdict
import pandas as pd

st.set_page_config(page_title="Picklist Parser", page_icon="🃏", layout="wide")
st.title("🃏 Picklist Parser")

# --- Input ---
picklist_text = st.text_area("Paste your picklist here", height=500)

if picklist_text:
    # --- Regex patterns ---
    order_pattern = re.compile(r"\b\d{2}-\d{5}-\d{5}\b")
    quantity_pattern = re.compile(r"Item no\.: .* Quantity: (\d+)", re.IGNORECASE)
    card_pattern = re.compile(r"Select Your Card: (\d+/\d+) (.+?) \((.+?)\)")
    shipping_start_pattern = re.compile(r"^[\t ]*\d+[\t ]*$")  # Number line with tabs/spaces

    cards_by_buyer = defaultdict(list)
    shipping_info = {}
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
                if not next_line or order_pattern.match(next_line) or next_line.startswith(("Pokemon", "Item no", "Value")) or shipping_start_pattern.match(lines[j]):
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

            # Look ahead for the card line
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

        # Detect shipping info (number line → name + address)
        elif shipping_start_pattern.match(line):
            shipping_name = ""
            shipping_address_lines = []
            j = i + 1

            # Find shipping name
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                shipping_name = lines[j].strip()
                j += 1

            # Find shipping address (until blank or next order)
            while j < len(lines):
                next_line = lines[j].strip()
                if not next_line or order_pattern.match(next_line):
                    break
                shipping_address_lines.append(next_line)
                j += 1

            shipping_address = ", ".join(shipping_address_lines)
            if current_buyer:
                shipping_info[current_buyer] = f"{shipping_name}, {shipping_address}"
            i = j - 1

        i += 1

    # --- Function to render HTML table with highlights, fixed column widths, and row numbers ---
    def render_table_html(df):
        df.insert(0, "#", range(1, len(df) + 1))
        col_widths = {
            "#": "40px",
            "Order": "150px",
            "Card": "250px",
            "Variation": "150px",
            "Quantity": "80px"
        }
        html = '<table style="border-collapse: collapse; width: 100%;">'
        html += "<tr>"
        for col in df.columns:
            width = col_widths.get(col, "150px")
            html += f'<th style="border: 1px solid black; padding: 4px; text-align: left; width:{width};">{col}</th>'
        html += "</tr>"
        for _, row in df.iterrows():
            bg_color = ""
            if row['Variation'] == "Non-Holo":
                bg_color = "#ff9999"
            elif row['Variation'] == "Holo Rare":
                bg_color = "#99ccff"
            font_weight = "bold" if row['Quantity'] > 1 else "normal"
            html += f'<tr style="background-color:{bg_color}; font-weight:{font_weight};">'
            for col in df.columns:
                width = col_widths.get(col, "150px")
                html += f'<td style="border: 1px solid black; padding: 4px; width:{width};">{row[col]}</td>'
            html += "</tr>"
        html += "</table>"
        return html

    # --- Display per-buyer tables ---
    st.subheader("Parsed Picklist")
    for buyer, items in cards_by_buyer.items():
        df_buyer = pd.DataFrame(items)
        total_cards = int(df_buyer['Quantity'].sum())
        num_items = len(df_buyer)
        shipping_label = shipping_info.get(buyer, "").strip(", ")
        expander_label = f"Buyer: {buyer} ({num_items} items, {total_cards} total cards)"
        if shipping_label:
            expander_label += f" – {shipping_label}"
        with st.expander(expander_label, expanded=True):
            st.markdown(render_table_html(df_buyer), unsafe_allow_html=True)

    # --- Full CSV download ---
    all_items = [item for items in cards_by_buyer.values() for item in items]
    df_all = pd.DataFrame(all_items)
    csv = df_all.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Download Full CSV",
        data=csv,
        file_name="picklist_parsed.csv",
        mime="text/csv"
    )
