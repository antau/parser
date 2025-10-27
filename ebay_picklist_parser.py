import re
import streamlit as st
from collections import defaultdict

st.title("Picklist Parser")

picklist_text = st.text_area("Paste your picklist here", height=500)

if picklist_text:
    # Regex patterns
    item_pattern = re.compile(r"Item no\.: .* Quantity: (\d+)", re.IGNORECASE)
    card_pattern = re.compile(r"Select Your Card: (\d+/\d+) (.+?) \((.+?)\)")
    
    cards_by_buyer = defaultdict(list)
    buyer_name = None
    buyer_address_lines = []
    current_order = None
    
    lines = picklist_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect order lines
        if re.match(r"\d{2}-\d{5}-\d{5}", line):
            current_order = line

        # Detect Quantity line
        qty_match = item_pattern.search(line)
        if qty_match:
            quantity = int(qty_match.group(1))

            # Look ahead for the card line (skip blank lines)
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                card_match = card_pattern.search(lines[j])
                if card_match and buyer_name:
                    card_number, card_name, variation = card_match.groups()
                    cards_by_buyer[buyer_name].append({
                        "Order": current_order,
                        "Card": f"{card_number} {card_name}",
                        "Variation": variation,
                        "Quantity": quantity
                    })
            i = j  # skip to card line after processing

        # Detect Buyer Name and Address block
        elif line and not line.startswith("Pokemon") and not line.startswith("Item no") and not line.startswith("Value") and not re.match(r"\d{2}-\d{5}-\d{5}", line):
            buyer_name_line = line
            buyer_address_lines = []
            k = i + 1
            while k < len(lines) and lines[k].strip() and not re.match(r"\d{2}-\d{5}-\d{5}", lines[k].strip()):
                if re.match(r"\d+\s*$", lines[k].strip()):
                    k += 1
                    continue
                buyer_address_lines.append(lines[k].strip())
                k += 1
            if buyer_address_lines:
                buyer_name = f"{buyer_name_line} ({', '.join(buyer_address_lines)})"
            i = k - 1

        i += 1

    # Display results
    for buyer, items in cards_by_buyer.items():
        st.subheader(f"Buyer: {buyer}")
        st.table([{
            "Order": item["Order"],
            "Card": item["Card"],
            "Variation": item["Variation"],
            "Quantity": item["Quantity"]
        } for item in items])
