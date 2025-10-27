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
    # Matches a line that contains only digits, possibly surrounded by spaces/tabs
    shipping_start_pattern = re.compile(r"^[\t ]*\d+[\t ]*$")

    cards_by_buyer = defaultdict(list)
    shipping_info = {}              # maps buyer_key -> "Name (addr1, addr2, ...)"
    current_order = None
    current_buyer = None
    last_buyer_seen = None          # fallback if current_buyer is None when shipping block appears
    lines = picklist_text.splitlines()

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()

        # --- Order line ---
        if order_pattern.search(line):
            current_order = line

        # --- Buyer detection (heuristic) ---
        elif line and not line.startswith(("Pokemon", "Item no", "Value")) and not order_pattern.search(line):
            # collect buyer address lines (until blank, order line, "Pokemon", "Item no", "Value", or a shipping-number line)
            buyer_name_line = line
            buyer_address_lines = []
            j = i + 1
            while j < len(lines):
                next_raw = lines[j]
                next_strip = next_raw.strip()
                if (not next_strip
                    or order_pattern.search(next_strip)
                    or next_strip.startswith(("Pokemon", "Item no", "Value"))
                    or shipping_start_pattern.match(next_raw)):
                    break
                buyer_address_lines.append(next_strip)
                j += 1
            if buyer_address_lines:
                buyer_key = f"{buyer_name_line} ({', '.join(buyer_address_lines)})"
            else:
                buyer_key = buyer_name_line
            current_buyer = buyer_key
            last_buyer_seen = current_buyer
            i = j - 1

        # --- Quantity / Card lines ---
        qty_match = quantity_pattern.search(line)
        if qty_match:
            quantity = int(qty_match.group(1))
            # Look ahead for card line (skip blank lines)
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
                    else:
                        # If we haven't found a buyer for this block, attach to last_buyer_seen if available
                        if last_buyer_seen:
                            cards_by_buyer[last_buyer_seen].append({
                                "Order": current_order,
                                "Card": f"{card_number} {card_name}",
                                "Variation": variation,
                                "Quantity": quantity
                            })
                    break
                j += 1
            i = j  # jump to card line (or end)
            i += 1
            continue  # skip increment at bottom because we've already moved i

        # --- Shipping block detection (a line that only contains a number possibly with tabs/spaces) ---
        if shipping_start_pattern.match(raw_line):
            # Associate to current_buyer if set, otherwise to last_buyer_seen
            buyer_for_shipping = current_buyer if current_buyer else last_buyer_seen

            # Find first non-empty line after the number line -> shipping name
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            shipping_name = ""
            if j < len(lines):
                shipping_name = lines[j].strip()
                j += 1

            # Collect shipping address lines until blank line or next order line or next shipping-number line
            shipping_address_lines = []
            while j < len(lines):
                next_raw = lines[j]
                next_strip = next_raw.strip()
                if (not next_strip) or order_pattern.search(next_strip) or shipping_start_pattern.match(next_raw):
                    break
                shipping_address_lines.append(next_strip)
                j += 1

            shipping_address = ", ".join(shipping_address_lines) if shipping_address_lines else ""
            if buyer_for_shipping:
                # format as "Name (addr1, addr2)" for the expander label
                if shipping_address:
                    shipping_info[buyer_for_shipping] = f"{shipping_name} ({shipping_address})"
                else:
                    shipping_info[buyer_for_shipping] = shipping_name

            # advance i to the last processed line
            i = j
            continue

        i += 1

    # --- Render HTML table helper ---
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
        # header
        html += "<tr>"
        for col in df.columns:
            width = col_widths.get(col, "150px")
            html += f'<th style="border: 1px solid #444; padding: 6px; text-align: left; width:{width};">{col}</th>'
        html += "</tr>"
        # rows
        for _, row in df.iterrows():
            bg_color = ""
            if str(row.get('Variation','')).strip() == "Non-Holo":
                bg_color = "#ffcccc"
            elif str(row.get('Variation','')).strip() == "Holo Rare":
                bg_color = "#cce6ff"
            font_weight = "bold" if int(row.get('Quantity', 0)) > 1 else "normal"
            html += f'<tr style="background-color:{bg_color}; font-weight:{font_weight};">'
            for col in df.columns:
                width = col_widths.get(col, "150px")
                html += f'<td style="border: 1px solid #ddd; padding: 6px; width:{width};">{row[col]}</td>'
            html += "</tr>"
        html += "</table>"
        return html

    # --- Display per-buyer tables with shipping info in expander label ---
    st.subheader("Parsed Picklist")
    for buyer, items in cards_by_buyer.items():
        df_buyer = pd.DataFrame(items)
        if df_buyer.empty:
            continue
        total_cards = int(df_buyer['Quantity'].sum())
        num_items = len(df_buyer)
        ship_label = shipping_info.get(buyer, "")
        expander_label = f"Buyer: {buyer} ({num_items} items, {total_cards} total cards)"
        if ship_label:
            expander_label += f" - {ship_label}"
        # expanded True so you can see full table by default
        with st.expander(expander_label, expanded=True):
            st.markdown(render_table_html(df_buyer), unsafe_allow_html=True)

    # --- Full CSV download ---
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
