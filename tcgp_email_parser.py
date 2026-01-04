import streamlit as st
import pandas as pd
import re
import html

st.set_page_config(layout="wide")
st.title("TCGPlayer Orders")

raw_text = st.text_area(
    "Paste order list:",
    height=400
)

def normalize_text(text: str) -> str:
    # Decode HTML entities
    text = html.unescape(text)

    # Remove span tags but keep content
    text = re.sub(r"</?span[^>]*>", "", text, flags=re.IGNORECASE)

    # Convert <br> to newline
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Remove all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    return text

def parse_orders(text: str):
    clean = normalize_text(text)

    orders = []
    lines = [l.strip() for l in clean.splitlines() if l.strip()]

    for i, line in enumerate(lines):
        # Match: Store Name $12.34
        m = re.match(r"(.+?)\s+\$(\d+\.\d{2})$", line)
        if not m:
            continue

        store, total = m.groups()

        # Look ahead for Order Number
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

        orders.append({
            "Store Name": f"[{store}]({url})",
            "Order Total": f"${total}"
        })

    return orders

if raw_text.strip():
    data = parse_orders(raw_text)

    if data:
        df = pd.DataFrame(data)

        # Font styling
        st.markdown(
            """
            <style>
            div[data-testid="stDataFrame"] * {
                font-family: Arial, sans-serif;
                font-size: 10pt;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No orders detected.")
