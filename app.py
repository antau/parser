# app.py
# Version: v1.7 (Streamlit-version-safe)

import re
import pandas as pd
import streamlit as st

# -----------------------
# Page config
# -----------------------
st.set_page_config(layout="wide")
st.caption("App version: v1.7")

# -----------------------
# Global CSS
# -----------------------
st.markdown(
    """
    <style>
    * {
        font-family: Arial, sans-serif;
        font-size: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# Input
# -----------------------
raw_text = st.text_area(
    "Paste order list here:",
    height=300,
)

# -----------------------
# Parser
# -----------------------
def parse_orders(text: str) -> pd.DataFrame:
    rows = []

    pattern = re.compile(
        r"<br>\s*([^<$]+?)\s*\$(\d+\.\d{2}).*?"
        r"SearchString=([A-Z0-9-]+)",
        re.DOTALL,
    )

    for store, total, order_id in pattern.findall(text):
        url = (
            "https://store.tcgplayer.com/myaccount/orderhistory"
            f"?SearchString={order_id}"
        )

        rows.append(
            {
                "Store Name": url,   # URL goes here
                "Display Name": store.strip(),
                "Order Total": f"${total}",
            }
        )

    return pd.DataFrame(rows)


# -----------------------
# Output
# -----------------------
if raw_text.strip():
    df = parse_orders(raw_text)

    if df.empty:
        st.error("No orders detected. Check input format.")
    else:
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Store Name": st.column_config.LinkColumn(
                    "Store Name",
                    display_text="Display Name",
                ),
                "Display Name": None,  # hide helper column
                "Order Total": "Order Total",
            },
        )
