import re
import streamlit as st
from collections import defaultdict
import pandas as pd

st.set_page_config(page_title="Picklist Parser", page_icon="🃏", layout="wide")
st.title("🃏 Picklist Parser")

picklist_text = st.text_area("Paste your picklist here", height=500)

if picklist_text:
    # --- Regex patterns ---
    order_pattern = re.compile(r"\b\d{2}-\d{5}-\d{5}\b")
    quantity_pattern = re.compile(r"Item no\.: .* Quantity: (\d+)", re.IGNORECASE)
    card_pattern = re.compile(r"Select Your Card: (\d+/\d+) (.+?) \((.+?)\)")
    # Matches a line that contains only digits, possibly with spaces/tabs
    shipping_start_pattern = re.compile(r"^[\t ]*\d+[\t ]*$")

    cards_by_buyer = defaultdict(list)
    buyer_display = {}
    shipping_info = {}

    current_order = None
    current_buyer_id = None
    last_buyer_id_seen = None
    lines = picklist_text.splitlines()

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()

        # --- Order line ---
        if order_pattern.search(line):
            current_order = line

        # --- Buyer detection ---
        elif line and not line.startswith(("Pokemon", "Item no", "Value")) and not order_pattern.search(line):
            buyer_name_line = line
            buyer_address_lines = []
            j = i + 1
            while j < len(lines):
                next_line = lines[j].strip()
                if (not next_line or order_pattern.search(next_line)
                        or next_line.startswith(("Pokemon", "Item no", "Value"))
                        or shipping_start_pattern.match(lines[j])):
                    break
                buyer_address_lines.append(next_line)
                j += 1
            buyer_id = buyer_name_line
            if buyer_address_lines:
                buyer_display[buyer_id] = f"{buyer_name_line} ({', '.join(buyer_address_lines)})"
            else:
                buyer_display[buyer_id] = buyer_name_line
            current_buyer_id = buyer_id
            last_buyer_id_seen = buyer_id
            i = j - 1

        # --- Quantity line ---
        qty_match = quantity_pattern.search(line)
        if qty_match:
            quantity = int(qty_match.group(1))
            j = i + 1
            while j < len(lines):
                card_match = card_pattern.search(lines[j])
                if card_match:
                    card_number, card_name, variation = card_match.groups()
                    target_buyer = current_buyer_id if current_buyer_id else last_buyer_id_seen
                    if target_buyer:
                        cards_by_buyer[target_buyer].append({
                            "Order": current_order,
                            "Card": f"{card_number} {card_name}",
                            "Variation": variation,
                            "Quantity": quantity
                        })
                    break
                j += 1
            i = j
            i += 1
            continue

        # --- Shipping block (tab/space tolerant) ---
        if shipping_start_pattern.match(raw_line):
            buyer_for_shipping = current_buyer_id if current_buyer_id else last_buyer_id_seen

            # Find shipping name (first non-empty line after the number)
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            shipping_name = ""
            if j < len(lines):
                shipping_name = lines[j].strip()
                j += 1

            # Collect address lines
            shipping_address_lines = []
            while j < len(lines):
                next_line = lines[j].strip()
                if (not next_line or order_pattern.search(next_line)
                        or shipping_start_pattern.match(lines[j])):
                    break
                shipping_address_lines.append(next_line)
                j += 1

            shipping_address = ", ".join(shipping_address_lines)
            if buyer_for_shipping:
                if shipping_address:
                    shipping_info[buyer_for_shipping] = f"{shipping_name} ({shipping_address})"
                else:
                    shipping_info[buyer_for_shipping] = shipping_name
            i = j
            continue

        i += 1

    # --- Render HTML table ---
    def render_table_html(df):
        df = df.copy()
        df.insert(0, "#", range(1, len(df) + 1))
        col_widths = {
            "#": "40px",
            "Order": "150px",
            "Card": "300px",
            "Variation": "150px",
            "Quantity": "80px"
        }
        html = '<table style="border-collapse: collapse; width: 100%;">'
        html += "<tr>"
        for col in df.columns:
            width = col_widths.get(col, "150px")
            html += f'<th style="border: 1px solid #444; padding: 6px; text-align: left; width:{width};">{col}</th>'
        html += "</tr>"
        for _, row in df.iterrows():
            bg_color = ""
            if str(row.get('Variation', '')).strip() == "Non-Holo":
                bg_color = "#ffcccc"
            elif str(row.get('Variation', '')).strip() == "Holo Rare":
                bg_color = "#cce6ff"
            font_weight = "bold" if int(row.get('Quantity', 0)) > 1 else "normal"
            html += f'<tr style="background-color:{bg_color}; font-weight:{font_weight};">'
            for col in df.columns:
                width = col_widths.get(col, "150px")
                html += f'<td style="border: 1px solid #ddd; padding: 6px; width:{width};">{row[col]}</td>'
            html += "</tr>"
        html += "</table>"
        return html

    # --- Display per-buyer tables with shipping info ---
    st.subheader("Parsed Picklist")
    for buyer_id, items in cards_by_buyer.items():
        df_buyer = pd.DataFrame(items)
        if df_buyer.empty:
            continue
        total_cards = int(df_buyer['Quantity'].sum())
        num_items = len(df_buyer)
        buyer_label = buyer_display.get(buyer_id, buyer_id)
        ship_label = shipping_info.get(buyer_id, "")
        expander_label = f"Buyer: {buyer_label} ({num_items} items, {total_cards} total cards)"
        if ship_label:
            expander_label += f" - {ship_label}"
        with st.expander(expander_label, expanded=True):
            st.markdown(render_table_html(df_buyer), unsafe_allow_html=True)

    # --- CSV download ---
    all_items = [item for items in cards_by_buyer.values() for item in items]
    df_all = pd.DataFrame(all_items) if all_items else pd.DataFrame()
    if not df_all.empty:
        csv = df_all.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Full CSV",
            data=csv,
            file_name="picklist_parsed.csv",
            mime="text/csv"
        )
