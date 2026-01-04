import streamlit as st
import pandas as pd
import re
import html

st.set_page_config(layout="wide")
st.title("TCGPlayer Orders")

raw_text = st.text_area("Paste order list:", height=400)

def parse_orders(text: str):
    text = html.unescape(text)

    # Normalize <br> into newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Remove span tags but keep text
    text = re.sub(r"</?span[^>]*>", "", text, flags=re.IGNORECASE)

    # Remove remaining HTML
    text = re.sub(r"<[^>]+>", "", text)

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    rows = []
    i = 0
    while i < len(lines):
        m = re.match(r"(.+?)\s+\$(\d+\.\d{2})$", lines[i])
        if not m:
            i += 1
            continue

        store, total = m.groups()

        order_id = None
        for j in range(i + 1, min(i + 4, len(lines))):
            oid = re.search(r"Order Number:\s*([A-Z0-9\-]+)", lines[j])
            if oid:
                order_id = oid.group(1)
                break

        if order_id:
            url = (
                "https://store.tcgplayer.com/myaccount/orderhistory"
                f"?SearchString={order_id}"
            )
        else:
            url = ""

        rows.append({
            "Store Name": store,
            "Order URL": url,
            "Order Total": f"${total}"
        })

        i += 1

    return rows

if raw_text.strip():
    data = parse_orders(raw_text)

    if data:
        df = pd.DataFrame(data)

        st.dataframe(
            df,
            hide_index=True,  # ✅ removes 0,1,2 column
            use_container_width=True,
            column_config={
                "Order URL": st.column_config.LinkColumn(
                    "Store Name",
                    display_text="Open Order"
                )
            }
        )
    else:
        st.warning("No orders found.")
