import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from contextlib import contextmanager
from typing import Optional, Dict, List, Tuple
import os
from datetime import datetime, timedelta
import numpy as np

class DatabaseManager:
    def __init__(self):
        self.connection_params = {
            "dbname": os.getenv("DB_NAME", "shopifydb"),
            "user": os.getenv("DB_USER", "shopifyuser"),
            "password": os.getenv("DB_PASSWORD", "12345678"),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432")
        }
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = psycopg2.connect(**self.connection_params)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def authenticate_tenant(self, username: str, password: str) -> Optional[int]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM tenants WHERE username = %s AND password_hash = %s",
                (username, password)
            )
            result = cur.fetchone()
            return result[0] if result else None
    
    def get_business_overview(self, tenant_id: int) -> Dict:
        """Get comprehensive business overview metrics"""
        queries = {
            'total_orders': "SELECT COUNT(*) FROM orders WHERE tenant_id = %s",
            'total_revenue': "SELECT COALESCE(SUM(total_price), 0) FROM orders WHERE tenant_id = %s",
            'total_customers': "SELECT COUNT(DISTINCT customer_id) FROM orders WHERE tenant_id = %s",
            'total_products': "SELECT COUNT(*) FROM products WHERE tenant_id = %s",
            'avg_order_value': "SELECT COALESCE(AVG(total_price), 0) FROM orders WHERE tenant_id = %s",
            'orders_this_month': """
                SELECT COUNT(*) FROM orders 
                WHERE tenant_id = %s AND created_at >= date_trunc('month', CURRENT_DATE)
            """,
            'revenue_this_month': """
                SELECT COALESCE(SUM(total_price), 0) FROM orders 
                WHERE tenant_id = %s AND created_at >= date_trunc('month', CURRENT_DATE)
            """,
            'orders_last_month': """
                SELECT COUNT(*) FROM orders 
                WHERE tenant_id = %s 
                AND created_at >= date_trunc('month', CURRENT_DATE - interval '1 month')
                AND created_at < date_trunc('month', CURRENT_DATE)
            """,
            'revenue_last_month': """
                SELECT COALESCE(SUM(total_price), 0) FROM orders 
                WHERE tenant_id = %s 
                AND created_at >= date_trunc('month', CURRENT_DATE - interval '1 month')
                AND created_at < date_trunc('month', CURRENT_DATE)
            """
        }
        
        results = {}
        with self.get_connection() as conn:
            cur = conn.cursor()
            for key, query in queries.items():
                cur.execute(query, (tenant_id,))
                results[key] = cur.fetchone()[0]
        
        return results
    
    def get_top_customers(self, tenant_id: int, limit: int = 10) -> pd.DataFrame:
        query = """
        SELECT 
            COALESCE(c.first_name || ' ' || c.last_name, 'Unknown') AS name,
            c.email,
            COUNT(o.id) as order_count,
            SUM(o.total_price) AS total_spent,
            AVG(o.total_price) as avg_order_value,
            MAX(o.created_at) as last_order_date,
            MIN(o.created_at) as first_order_date
        FROM customers c
        JOIN orders o ON o.customer_id = c.id
        WHERE c.tenant_id = %s
        GROUP BY c.id, c.first_name, c.last_name, c.email
        ORDER BY total_spent DESC
        LIMIT %s
        """
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=(tenant_id, limit))
        
    def get_top_products(self, tenant_id: int, limit: int = 5) -> pd.DataFrame:
        query = """
        SELECT 
            p.title,
            AVG(v.price) AS avg_price
        FROM products p
        JOIN product_variants v ON v.product_id = p.id
        WHERE p.tenant_id = %s
        GROUP BY p.id, p.title
        ORDER BY avg_price DESC
        LIMIT %s
        """
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=(tenant_id, limit))
    
    def get_product_performance(self, tenant_id: int, limit: int = 10) -> pd.DataFrame:
        query = """
        SELECT 
            p.title,
            p.product_type,
            p.vendor,
            COUNT(li.id) as units_sold,
            SUM(li.price * li.quantity) as total_revenue,
            AVG(v.price) as avg_price,
            COUNT(DISTINCT o.customer_id) as unique_buyers
        FROM products p
        JOIN product_variants v ON v.product_id = p.id
        LEFT JOIN line_items li ON li.product_variant_id = v.id
        LEFT JOIN orders o ON o.id = li.order_id
        WHERE p.tenant_id = %s
        GROUP BY p.id, p.title, p.product_type, p.vendor
        ORDER BY total_revenue DESC NULLS LAST
        LIMIT %s
        """
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=(tenant_id, limit))
    
    def get_revenue_trend(self, tenant_id: int, days: int = 90) -> pd.DataFrame:
        query = """
        SELECT 
            DATE(created_at) as order_date,
            COUNT(*) as order_count,
            SUM(total_price) as revenue,
            AVG(total_price) as avg_order_value,
            COUNT(DISTINCT customer_id) as unique_customers
        FROM orders
        WHERE tenant_id = %s AND created_at >= %s
        GROUP BY order_date
        ORDER BY order_date
        """
        start_date = datetime.now() - timedelta(days=days)
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=(tenant_id, start_date))
    
    def get_customer_segments(self, tenant_id: int) -> pd.DataFrame:
        query = """
        WITH customer_stats AS (
            SELECT 
                customer_id,
                COUNT(*) as order_count,
                SUM(total_price) as total_spent,
                AVG(total_price) as avg_order_value,
                MAX(created_at) as last_order_date,
                MIN(created_at) as first_order_date
            FROM orders
            WHERE tenant_id = %s
            GROUP BY customer_id
        ),
        customer_segments AS (
            SELECT 
                customer_id,
                order_count,
                total_spent,
                avg_order_value,
                last_order_date,
                first_order_date,
                CURRENT_DATE - last_order_date::date as days_since_last_order,
                CASE 
                    WHEN order_count >= 5 AND total_spent >= 500 THEN 'VIP'
                    WHEN order_count >= 3 AND total_spent >= 200 THEN 'Loyal'
                    WHEN order_count = 2 THEN 'Returning'
                    WHEN order_count = 1 AND CURRENT_DATE - last_order_date::date <= 30 THEN 'New'
                    WHEN order_count = 1 AND CURRENT_DATE - last_order_date::date > 30 THEN 'At Risk'
                    ELSE 'Other'
                END as segment
            FROM customer_stats
        )
        SELECT 
            segment,
            COUNT(*) as customer_count,
            AVG(total_spent) as avg_lifetime_value,
            AVG(order_count) as avg_order_count,
            AVG(days_since_last_order) as avg_days_since_last_order
        FROM customer_segments
        GROUP BY segment
        ORDER BY customer_count DESC
        """
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=(tenant_id,))
    
    def get_geographical_data(self, tenant_id: int) -> pd.DataFrame:
        query = """
        SELECT 
            COALESCE(billing_address_country, 'Unknown') as country,
            COALESCE(billing_address_province, 'Unknown') as province,
            COUNT(*) as order_count,
            SUM(total_price) as total_revenue,
            AVG(total_price) as avg_order_value
        FROM orders
        WHERE tenant_id = %s
        GROUP BY billing_address_country, billing_address_province
        ORDER BY total_revenue DESC
        """
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=(tenant_id,))
    
    def get_hourly_sales_pattern(self, tenant_id: int) -> pd.DataFrame:
        query = """
        SELECT 
            EXTRACT(hour FROM created_at) as hour_of_day,
            EXTRACT(dow FROM created_at) as day_of_week,
            COUNT(*) as order_count,
            SUM(total_price) as revenue
        FROM orders
        WHERE tenant_id = %s
        GROUP BY hour_of_day, day_of_week
        ORDER BY day_of_week, hour_of_day
        """
        with self.get_connection() as conn:
            df = pd.read_sql(query, conn, params=(tenant_id,))
            # Map day numbers to names
            day_names = {0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 
                        4: 'Thursday', 5: 'Friday', 6: 'Saturday'}
            df['day_name'] = df['day_of_week'].map(day_names)
            return df
    
    def get_inventory_insights(self, tenant_id: int) -> pd.DataFrame:
        query = """
        SELECT 
            p.title,
            p.product_type,
            v.inventory_quantity,
            v.price,
            COALESCE(li.units_sold, 0) as units_sold,
            v.inventory_quantity::float / NULLIF(COALESCE(li.units_sold, 0), 0) as stock_to_sales_ratio
        FROM products p
        JOIN product_variants v ON v.product_id = p.id
        LEFT JOIN (
            SELECT 
                product_variant_id,
                SUM(quantity) as units_sold
            FROM line_items li
            JOIN orders o ON o.id = li.order_id
            WHERE o.tenant_id = %s
            GROUP BY product_variant_id
        ) li ON li.product_variant_id = v.id
        WHERE p.tenant_id = %s
        ORDER BY v.inventory_quantity DESC
        """
        with self.get_connection() as conn:
            return pd.read_sql(query, conn, params=(tenant_id, tenant_id))
