import streamlit as st
import streamlit.components.v1 as components
import re
import html

st.set_page_config(layout="wide")
st.title("TCGPlayer Order Summary")

raw_text = st.text_area(
    "Paste your order list here:",
    height=400
)

def clean_html(text: str) -> str:
    # Remove span tags only (keep inner text)
    text = re.sub(r"<span.*?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</span>", "", text, flags=re.IGNORECASE)
    return html.unescape(text)

def parse_orders(text: str):
    text = clean_html(text)

    pattern = re.compile(
        r"<br>\s*([^<$]+?)\s*\$(\d+\.\d{2}).*?"
        r'href="(https://store\.tcgplayer\.com/myaccount/orderhistory\?SearchString=[^"]+)"',
        re.IGNORECASE | re.DOTALL
    )

    orders = []
    for store, total, url in pattern.findall(text):
        orders.append({
            "store": store.strip(),
            "total": f"${total}",
            "url": url
        })

    return orders

def render_table(orders):
    rows_html = "".join(
        f"""
        <tr>
            <td><a href="{o['url']}" target="_blank">{o['store']}</a></td>
            <td>{o['total']}</td>
        </tr>
        """
        for o in orders
    )

    full_html = f"""
    <style>
        table {{
            font-family: Arial, sans-serif;
            font-size: 10pt;
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            border: 1px solid #cccccc;
            padding: 4px 6px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>

    <table>
        <thead>
            <tr>
                <th>Store Name</th>
                <th>Order Total</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """

    components.html(full_html, height=600, scrolling=True)

if raw_text.strip():
    orders = parse_orders(raw_text)

    if orders:
        render_table(orders)
    else:
        st.warning("No orders found. Please check the input format.")
