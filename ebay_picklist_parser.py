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

    # Use buyer_id (stable) -> list of cards, and buyer_display mapping for UI labels
    cards_by_buyer = defaultdict(list)   # buyer_id -> list of card dicts
    buyer_display = {}                   # buyer_id -> "Display Name (addr1, addr2)"
    shipping_info = {}                   # buyer_id -> "Shipping Name (addr1, addr2)"

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

        # --- Buyer detection (heuristic) ---
        # Buyer id is the first buyer_name_line (likely username), address lines follow
        elif line and not line.startswith(("Pokemon", "Item no", "Value")) and not order_pattern.search(line):
            # collect buyer address lines (until blank, order line, "Pokemon", "Item no", "Value", or shipping-number line)
            buyer_name_line = line
            buyer_address_lines = []
            j = i + 1
            while j < len(lines):
                next_raw = lines[j]
                next_strip = next_raw.strip()
                # stop on blank, order line, labels, or shipping-number line
                if (not next_strip
                    or order_pattern.search(next_strip)
                    or next_strip.startswith(("Pokemon", "Item no", "Value"))
                    or shipping_start_pattern.match(next_raw)):
                    break
                buyer_address_lines.append(next_strip)
                j += 1
            # stable internal id
            buyer_id = buyer_name_line  # keep it simple and stable
            # display label includes address if present
            if buyer_address_lines:
                buyer_display[buyer_id] = f"{buyer_name_line} ({', '.join(buyer_address_lines)})"
            else:
                buyer_display[buyer_id] = buyer_name_line
            current_buyer_id = buyer_id
            last_buyer_id_seen = buyer_id
            # jump to last processed line
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
            i = j  # move to the card line index (or end)
            i += 1
            continue  # already moved i, skip bottom increment

        # --- Shipping block detection (number line with tabs/spaces) ---
        if shipping_start_pattern.match(raw_line):
            # attach shipping block to the most recent buyer id seen
            buyer_for_shipping = current_buyer_id if current_buyer_id else last_buyer_id_seen
            # find first non-empty line after the number line -> shipping name
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            shipping_name = ""
            if j < len(lines):
                shipping_name = lines[j].strip()
                j += 1
            # collect shipping address lines until blank, next order line, or next shipping-number line
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
                if shipping_address:
                    shipping_info[buyer_for_shipping] = f"{shipping_name} ({shipping_address})"
                else:
                    shipping_info[buyer_for_shipping] = shipping_name
            # jump past shipping block
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

    # --- Display per-buyer tables with shipping in expander label ---
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
