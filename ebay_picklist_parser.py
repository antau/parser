import re
import streamlit as st
from collections import defaultdict
import pandas as pd

st.set_page_config(page_title="Picklist Parser", page_icon="🃏", layout="wide")
st.title("🃏 Picklist Parser")

picklist_text = st.text_area("Paste your picklist here", height=600)

if picklist_text:
    # --- Regex patterns ---
    order_pattern = re.compile(r"\b\d{2}-\d{5}-\d{5}\b")
    quantity_pattern = re.compile(r"Item no\.: .* Quantity: (\d+)", re.IGNORECASE)
    card_pattern = re.compile(r"Select Your Card: (\d+/\d+) (.+?) \((.+?)\)")
    # Matches a line that contains only digits (with any whitespace/tabs around)
    shipping_start_pattern = re.compile(r"^[\s]*\d+[\s]*$")

    # Data structures
    cards_by_buyer = defaultdict(list)   # buyer_id -> list of cards
    buyer_display = {}                   # buyer_id -> display label (username + address)
    shipping_info = {}                   # buyer_id -> shipping name + address (for label)

    current_order = None
    current_buyer_id = None
    last_buyer_id_seen = None

    # Normalize lines but keep raw for whitespace checks
    lines = picklist_text.splitlines()
    n = len(lines)
    i = 0

    while i < n:
        raw_line = lines[i]
        # normalize line for easier checks (strip non-printing chars and whitespace ends)
        line = raw_line.strip()

        # --- Order line (keep this first) ---
        if order_pattern.search(line):
            current_order = line
            i += 1
            continue

        # --- Shipping block detection MUST come BEFORE buyer detection ---
        if shipping_start_pattern.match(raw_line) and not order_pattern.search(line):
            # Attach to most recent buyer id (prefer current, else last seen)
            buyer_for_shipping = current_buyer_id if current_buyer_id else last_buyer_id_seen

            # Find first non-empty line after the number -> shipping name
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1

            shipping_name = ""
            if j < n:
                shipping_name = lines[j].strip()
                j += 1

            # Collect address lines until blank, next order line, or next shipping-number line
            shipping_address_lines = []
            while j < n:
                next_raw = lines[j]
                next_strip = next_raw.strip()
                if (not next_strip) or order_pattern.search(next_strip) or shipping_start_pattern.match(next_raw):
                    break
                shipping_address_lines.append(next_strip)
                j += 1

            shipping_address = ", ".join(shipping_address_lines).strip()
            if buyer_for_shipping:
                if shipping_address:
                    shipping_info[buyer_for_shipping] = f"{shipping_name} ({shipping_address})"
                else:
                    shipping_info[buyer_for_shipping] = shipping_name

            # advance to the line after the shipping block
            i = j
            continue

        # --- Buyer detection (heuristic) ---
        # Only attempt buyer detection if this is not an Item/Value/Pokemon line and not empty
        if line and not line.startswith(("Pokemon", "Item no", "Value")) and not order_pattern.search(line):
            # Collect buyer address lines until blank, order line, "Pokemon", "Item no", "Value", or shipping-number
            buyer_name_line = line
            buyer_address_lines = []
            j = i + 1
            while j < n:
                next_raw = lines[j]
                next_strip = next_raw.strip()
                if (not next_strip
                        or order_pattern.search(next_strip)
                        or next_strip.startswith(("Pokemon", "Item no", "Value"))
                        or shipping_start_pattern.match(next_raw)):
                    break
                buyer_address_lines.append(next_strip)
                j += 1
            buyer_id = buyer_name_line  # stable internal id (username)
            if buyer_address_lines:
                buyer_display[buyer_id] = f"{buyer_name_line} ({', '.join(buyer_address_lines)})"
            else:
                buyer_display[buyer_id] = buyer_name_line
            current_buyer_id = buyer_id
            last_buyer_id_seen = buyer_id
            i = j
            continue

        # --- Quantity / Card lines ---
        qty_match = quantity_pattern.search(line)
        if qty_match:
            quantity = int(qty_match.group(1))
            # Look ahead for the card line (skip blank lines)
            j = i + 1
            while j < n:
                card_match = card_pattern.search(lines[j])
                if card_match:
                    card_number, card_name, variation = card_match.groups()
                    target_buyer = current_buyer_id if current_buyer_id else last_buyer_id_seen
                    if target_buyer:
                        cards_by_buyer[target_buyer].append({
                            "Order": current_order,
                            "Card": f"{card_number} {card_name}".strip(),
                            "Variation": variation.strip(),
                            "Quantity": quantity
                        })
                    break
                j += 1
            i = j + 1
            continue

        # nothing matched — advance
        i += 1

    # --- HTML table renderer (fixed column widths, row numbers, highlights, bolding only when Quantity > 1) ---
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
            var = str(row.get("Variation", "")).strip()
            if var == "Non-Holo":
                bg_color = "#ffcccc"
            elif var == "Holo Rare":
                bg_color = "#cce6ff"
            font_weight = "bold" if int(row.get("Quantity", 0)) > 1 else "normal"
            html += f'<tr style="background-color:{bg_color}; font-weight:{font_weight};">'
            for col in df.columns:
                width = col_widths.get(col, "150px")
                cell = row[col]
                html += f'<td style="border: 1px solid #ddd; padding: 6px; width:{width};">{cell}</td>'
            html += "</tr>"
        html += "</table>"
        return html

    # --- Display per-buyer tables with shipping info in the expander label ---
    st.subheader("Parsed Picklist")
    for buyer_id, items in cards_by_buyer.items():
        df_buyer = pd.DataFrame(items)
        if df_buyer.empty:
            continue
        total_cards = int(df_buyer["Quantity"].sum())
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
        csv = df_all.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Full CSV",
            data=csv,
            file_name="picklist_parsed.csv",
            mime="text/csv"
        )
