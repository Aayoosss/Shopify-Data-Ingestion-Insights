import streamlit as st
import psycopg2
import pandas as pd

# Database connection (you can also use sqlalchemy)
def get_connection():
    return psycopg2.connect(
        dbname="shopifydb",
        user="shopifyuser",
        password="12345678",
        host="localhost",
        port="5432"
    )

# Simple login (for tenants)
def login(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants WHERE shop_name=%s AND access_token=%s", (username, password))
    tenant = cur.fetchone()
    conn.close()
    return tenant[0] if tenant else None


# ---------------- STREAMLIT APP ----------------

st.title("🛍 Shopify Insights Dashboard")

# Session state to persist login
if "tenant_id" not in st.session_state:
    st.session_state["tenant_id"] = None

# Login form
if st.session_state["tenant_id"] is None:
    st.subheader("Login")
    username = st.text_input("Shop Name (myshop.myshopify.com)")
    password = st.text_input("API Token", type="password")
    if st.button("Login"):
        tenant_id = login(username, password)
        if tenant_id:
            st.session_state["tenant_id"] = tenant_id
            st.success("Login successful ✅")
        else:
            st.error("Invalid credentials ❌")
else:
    st.success(f"Logged in as Tenant ID {st.session_state['tenant_id']}")

    # Insights Page
    st.header("📊 Insights")

    # Connect DB
    conn = get_connection()

    # Top 5 Customers
    df_customers = df_customers = pd.read_sql(
    f"""
    SELECT c.first_name || ' ' || c.last_name AS name,
           SUM(o.total_price) AS total_spent
    FROM customers c
    JOIN orders o ON o.customer_id = c.id
    WHERE c.tenant_id={st.session_state['tenant_id']}
    GROUP BY c.id
    ORDER BY total_spent DESC
    LIMIT 5
    """,
    conn
)

    st.subheader("Top 5 Customers by Spend")
    st.bar_chart(df_customers.set_index("name"))

        # Top 5 Products
    df_products = pd.read_sql(
        f"""
        SELECT p.title, AVG(v.price) AS avg_price
        FROM products p
        JOIN product_variants v ON v.product_id = p.id
        WHERE p.tenant_id={st.session_state['tenant_id']}
        GROUP BY p.id
        ORDER BY avg_price DESC
        LIMIT 5
        """,
        conn
    )

    st.subheader("Top 5 Products by Price")
    st.bar_chart(df_products.set_index("title"))

    # Orders Trend
    df_orders = pd.read_sql(
        f"SELECT DATE(created_at) as order_date, SUM(total_price) as revenue FROM orders WHERE tenant_id={st.session_state['tenant_id']} GROUP BY order_date ORDER BY order_date",
        conn
    )
    st.subheader("Revenue Trend")
    st.line_chart(df_orders.set_index("order_date"))

    conn.close()

    # Logout
    if st.button("Logout"):
        st.session_state["tenant_id"] = None
