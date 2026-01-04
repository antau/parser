import streamlit as st
import streamlit.components.v1 as components

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
