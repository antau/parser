import streamlit as st
import pandas as pd
import re
import html

st.title("TCGPlayer Orders")

raw_text = st.text_area("Paste input:", height=400)

def parse_orders(text: str):
    # Decode HTML entities
    text = html.unescape(text)

    # Normalize breaks
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Remove all remaining HTML
    text = re.sub(r"<[^>]+>", "", text)

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    rows = []
    i = 0
    while i < len(lines):
        # Match: Store Name $12.34
        m = re.match(r"(.+?)\s+\$(\d+\.\d{2})$", lines[i])
        if not m:
            i += 1
            continue

        store, total = m.groups()

        # Find order number in following lines
        order_id = None
        for j in range(i + 1, min(i + 4, len(lines))):
            oid = re.search(r"Order Number:\s*([A-Z0-9\-]+)", lines[j])
            if oid:
                order_id = oid.group(1)
                break

        if order_id:
            link = (
                "https://store.tcgplayer.com/myaccount/orderhistory"
                f"?SearchString={order_id}"
            )
            store_display = f"[{store}]({link})"
        else:
            store_display = store

        rows.append({
            "Store Name": store_display,
            "Order Total": f"${total}"
        })

        i += 1

    return rows

if raw_text.strip():
    data = parse_orders(raw_text)

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No orders found.")
