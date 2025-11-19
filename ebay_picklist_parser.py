import re
import streamlit as st
from collections import defaultdict
import pandas as pd

st.set_page_config(page_title="Picklist Parser", page_icon="🃏", layout="wide")
st.title("🃏 Picklist Parser")

# --- Future-proof card title patterns (Option A: skip these lines) ---
CARD_TITLE_PATTERNS = [
    "Pokemon 151 Singles - Complete Your Set - Reverse Holo, Holo, and Regular TCG",
    "Pokemon 151 Holo Rare & Non-Holo Singles - Up to 20% off! Complete your set! NM"
]

# --- Input ---
picklist_text = st.text_area("Paste your picklist here", height=700)

if picklist_text:
    # --- Regex patterns ---
    order_pattern = re.compile(r"\b\d{2}-\d{5}-\d{5}\b")
    quantity_pattern = re.compile(r"Item no\.: .* Quantity: (\d+)", re.IGNORECASE)
    # Accept both "Select Your Card:" and "Card:" forms
    card_pattern = re.compile(r"(?:Select Your Card:|Card:)\s*(\d+/\d+)\s+(.+?)\s*\((.+?)\)")
    # lines that contain just a number (with optional spaces/tabs) indicate shipping block start
    shipping_start_pattern = re.compile(r"^[\s]*\d+[\s]*$")

    # Data structures
    cards_by_buyer = defaultdict(list)   # buyer_id -> list of item dicts
    buyer_display = {}                  # buyer_id -> "BuyerName (address lines, ...)" or just name
    shipping_info = {}                  # buyer_id -> "Shipping Name (full address comma-joined)" or name
    last_buyer_id_seen = None
    current_buyer_id = None
    current_order = None

    lines = picklist_text.splitlines()
    n = len(lines)
    i = 0

    while i < n:
        raw_line = lines[i]
        line = raw_line.strip()

        # --- Skip explicit card-title lines (future-proof) ---
        if any(pattern in line for pattern in CARD_TITLE_PATTERNS):
            i += 1
            continue

        # --- Order line ---
        if order_pattern.search(line):
            current_order = line
            i += 1
            continue

        # --- Shipping block detection (line with only integer, possibly tabs/spaces) ---
        if shipping_start_pattern.match(raw_line) and not order_pattern.search(line):
            # shipping belongs to current_buyer if set; otherwise last_buyer_id_seen
            buyer_for_shipping = current_buyer_id if current_buyer_id else last_buyer_id_seen
            j = i + 1

            # skip purely blank lines (there may be one after the number)
            while j < n and not lines[j].strip():
                j += 1

            shipping_name = ""
            if j < n:
                shipping_name = lines[j].strip()
                j += 1

            shipping_address_lines = []
            # collect address lines until blank line or next buyer/order/shipping start
            while j < n:
                next_raw = lines[j]
                next_strip = next_raw.strip()
                if (not next_strip) or order_pattern.search(next_strip) or shipping_start_pattern.match(next_raw):
                    break
                # stop if next line looks like the start of a buyer block (heuristic)
                if next_strip.startswith(("Pokemon", "Item no", "Value")):
                    break
                shipping_address_lines.append(next_strip)
                j += 1

            shipping_address = ", ".join(shipping_address_lines).strip()
            if buyer_for_shipping:
                if shipping_address:
                    shipping_info[buyer_for_shipping] = f"{shipping_name} ({shipping_address})"
                else:
                    shipping_info[buyer_for_shipping] = shipping_name

            # advance i to the line we stopped at
            i = j
            continue

        # --- Buyer detection ---
        # Heuristic: non-empty line that doesn't start with the product text
        if line and not line.startswith(("Pokemon", "Item no", "Value")) and not order_pattern.search(line):
            # Collect subsequent lines as buyer address lines until we hit blank/order/product/shipping-start
            buyer_name_line = line
            buyer_address_lines = []
            j = i + 1
            while j < n:
                next_raw = lines[j]
                next_strip = next_raw.strip()
                # stop when blank, order, product title, item no, value, or shipping number line encountered
                if (not next_strip
                        or order_pattern.search(next_strip)
                        or next_strip.startswith(("Pokemon", "Item no", "Value"))
                        or shipping_start_pattern.match(next_raw)):
                    break
                buyer_address_lines.append(next_strip)
                j += 1

            buyer_id = buyer_name_line
            if buyer_address_lines:
                buyer_display[buyer_id] = f"{buyer_name_line} ({', '.join(buyer_address_lines)})"
            else:
                buyer_display[buyer_id] = buyer_name_line
            current_buyer_id = buyer_id
            last_buyer_id_seen = buyer_id

            i = j
            continue

        # --- Quantity and following Card detection ---
        qty_match = quantity_pattern.search(line)
        if qty_match:
            # quantity found
            quantity = int(qty_match.group(1))
            # look ahead for a card line (skip blank lines)
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            # Now search forward until we find a card line or we hit something that indicates the block ended
            while j < n:
                next_line = lines[j].strip()
                # If next_line is a card pattern, parse it
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
                # If we encounter an explicit product title or an order line or a shipping start, stop searching
                if any(pattern in next_line for pattern in CARD_TITLE_PATTERNS) or order_pattern.search(next_line) or shipping_start_pattern.match(lines[j]):
                    break
                j += 1
            # move outer pointer to j (we handled up through card or stopped)
            i = j + 1
            continue

        # otherwise move to next line
        i += 1

    # --- Helper: render HTML table for a buyer (fixed column widths, # column, colors, bold quantity>1) ---
    def render_table_html(df_in):
        df = df_in.copy().reset_index(drop=True)
        df.insert(0, "#", range(1, len(df) + 1))
        # force column order and widths
        col_widths = {
            "#": "40px",
            "Order": "150px",
            "Card": "420px",
            "Variation": "150px",
            "Quantity": "80px"
        }
        # start table
        html = '<table style="border-collapse: collapse; width: 100%;">'
        # header
        html += "<tr>"
        for col in df.columns:
            width = col_widths.get(col, "150px")
            html += f'<th style="border: 1px solid #444; padding: 6px; text-align: left; width:{width}; background:#f2f2f2;">{col}</th>'
        html += "</tr>"
        # rows
        for _, row in df.iterrows():
            var = str(row.get("Variation", "")).strip()
            bg_color = ""
            if var == "Non-Holo":
                bg_color = "#ffcccc"  # light red
            elif var == "Holo Rare":
                bg_color = "#cce6ff"  # light blue
            font_weight = "bold" if int(row.get("Quantity", 0)) > 1 else "normal"
            html += f'<tr style="background-color:{bg_color}; font-weight:{font_weight};">'
            for col in df.columns:
                cell = row[col]
                html += f'<td style="border: 1px solid #ddd; padding: 6px; vertical-align: top;">{cell}</td>'
            html += "</tr>"
        html += "</table>"
        return html

    # --- Display per-buyer tables and build summary rows ---
    st.subheader("Parsed Picklist")
    summary_rows = []
    # iterate in stable order (the order buyers were discovered)
    for buyer_id, items in cards_by_buyer.items():
        df_buyer = pd.DataFrame(items)
        if df_buyer.empty:
            continue

        # totals & counts
        total_cards = int(df_buyer["Quantity"].sum())
        num_items = len(df_buyer)
        buyer_label = buyer_display.get(buyer_id, buyer_id)
        ship_label = shipping_info.get(buyer_id, "")

        # counts of variations
        number_reverse_holo = int(df_buyer.loc[df_buyer["Variation"].str.lower().str.contains("reverse", na=False), "Quantity"].sum()) if "Variation" in df_buyer else 0
        number_holo_rare = int(df_buyer.loc[df_buyer["Variation"].str.lower() == "holo rare", "Quantity"].sum()) if "Variation" in df_buyer else 0
        number_non_holo = int(df_buyer.loc[df_buyer["Variation"].str.lower() == "non-holo", "Quantity"].sum()) if "Variation" in df_buyer else 0

        # Build expander label (plain-text): include counts at end as requested
        expander_label = f"Buyer: {buyer_label} ({num_items} items, {total_cards} total cards) - {number_reverse_holo} Reverse Holo, {number_holo_rare} Holo Rare, {number_non_holo} Non-Holo"
        if ship_label:
            expander_label = f"{expander_label} - {ship_label}"

        # Show expander (expanded by default)
        with st.expander(expander_label, expanded=True):
            # Show a small styled summary line (colored/bold counts) inside the expander for clarity
            holo_rare_html = f'<b style="color:blue;">{number_holo_rare} Holo Rare</b>' if number_holo_rare > 0 else f'{number_holo_rare} Holo Rare'
            non_holo_html = f'<b style="color:red;">{number_non_holo} Non-Holo</b>' if number_non_holo > 0 else f'{number_non_holo} Non-Holo'
            reverse_html = f'{number_reverse_holo} Reverse Holo'
            st.markdown(f"**Variation totals:** {reverse_html} — {holo_rare_html} — {non_holo_html}", unsafe_allow_html=True)

            # Render the table (shipping info removed from the table rows)
            st.markdown(render_table_html(df_buyer), unsafe_allow_html=True)

        # Build summary row (shipping name + full shipping address)
        shipping_name = ""
        shipping_address_full = ""
        if ship_label:
            # ship_label is either "Name (addr1, addr2, ...)" or just "Name"
            m = re.match(r"^(.*?)\s*\((.*)\)$", ship_label)
            if m:
                shipping_name = m.group(1).strip()
                shipping_address_full = m.group(2).strip()
            else:
                shipping_name = ship_label
                shipping_address_full = ""

        card_list = list(df_buyer["Card"].values)[:3]
        while len(card_list) < 3:
            card_list.append("")

        summary_rows.append({
            "Shipping Name": shipping_name,
            "Shipping Address": shipping_address_full,
            "# of Items": num_items,
            "Total Cards": total_cards,
            "Card 1": card_list[0],
            "Card 2": card_list[1],
            "Card 3": card_list[2]
        })

    # --- Buyer summary table (with # column, no unnamed index) ---
    if summary_rows:
        st.subheader("Buyer Summary Table")
        df_summary = pd.DataFrame(summary_rows)
        df_summary.insert(0, "#", range(1, len(df_summary) + 1))
        # ensure the DataFrame doesn't show the pandas index column; dataframe will show our # column
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        # CSV download for buyer summary
        csv_summary = df_summary.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Buyer Summary CSV",
            data=csv_summary,
            file_name="buyer_summary.csv",
            mime="text/csv"
        )

    # --- Full picklist CSV download ---
    all_items = [item for items in cards_by_buyer.values() for item in items]
    df_all = pd.DataFrame(all_items) if all_items else pd.DataFrame()
    if not df_all.empty:
        csv = df_all.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Full Picklist CSV",
            data=csv,
            file_name="picklist_parsed.csv",
            mime="text/csv"
        )

else:
    st.info("Paste your picklist into the text area above to parse it.")
