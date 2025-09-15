import streamlit as st
import psycopg2
import pandas as pd
from contextlib import contextmanager
from typing import Optional
import os
from datetime import datetime, timedelta
from databasemanager import DatabaseManager

class ShopifyDashboard:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        if "tenant_id" not in st.session_state:
            st.session_state.tenant_id = None
        if "shop_name" not in st.session_state:
            st.session_state.shop_name = None
    
    def render_login_form(self):
        st.subheader("🔐 Login")
        
        with st.form("login_form"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                username = st.text_input(
                    "Username",
                    placeholder="myshop from myshop.myshopify.com",
                    help="Enter your Shopify store name"
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    help="Enter your Shopify Password"
                )
            
            submit_button = st.form_submit_button("Login", use_container_width=True)
            
            if submit_button:
                if not username or not password:
                    st.error("Please enter both shop name and API token")
                else:
                    self._handle_login(username, password)
    
    def _handle_login(self, username: str, password: str):
        try:
            tenant_id = self.db_manager.authenticate_tenant(username, password)
            if tenant_id:
                st.session_state.tenant_id = tenant_id
                st.session_state.shop_name = username
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid credentials. Please check your shop name and API token.")
        except Exception as e:
            st.error(f"❌ Database connection error: {str(e)}")
    
    def render_header(self):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.success(f"📊 Dashboard for: **{st.session_state.shop_name}**")
        
        with col2:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.tenant_id = None
                st.session_state.shop_name = None
                st.rerun()
    
    def render_metrics_cards(self):
        try:
            df_customers = self.db_manager.get_top_customers(st.session_state.tenant_id)
            df_products = self.db_manager.get_top_products(st.session_state.tenant_id)
            df_revenue = self.db_manager.get_revenue_trend(st.session_state.tenant_id)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_customers = len(df_customers)
                st.metric("Top Customers", total_customers, delta=None)
            
            with col2:
                total_products = len(df_products)
                st.metric("Top Products", total_products, delta=None)
            
            with col3:
                total_revenue = df_revenue['revenue'].sum() if not df_revenue.empty else 0
                st.metric("Revenue (30d)", f"₹{total_revenue:,.2f}", delta=None)
                
        except Exception as e:
            st.error(f"Error loading metrics: {str(e)}")
    
    def render_charts(self):
        st.header("📈 Analytics")
        
        tab1, tab2, tab3 = st.tabs(["💳 Top Customers", "🛍️ Top Products", "📊 Revenue Trend"])
        
        with tab1:
            self._render_top_customers_chart()
        
        with tab2:
            self._render_top_products_chart()
        
        with tab3:
            self._render_revenue_trend_chart()
            

    
    def _render_top_customers_chart(self):
        try:
            df_customers = self.db_manager.get_top_customers(st.session_state.tenant_id)
            
            if df_customers.empty:
                st.info("No customer data available")
                return
            
            st.subheader("Top 5 Customers by Total Spend")
            st.bar_chart(
                df_customers.set_index("name")["total_spent"],
                use_container_width=True
            )
            
            with st.expander("View Customer Details"):
                df_customers["total_spent"] = df_customers["total_spent"].apply(
                    lambda x: f"₹{x:,.2f}"
                )
                st.dataframe(df_customers, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error loading customer data: {str(e)}")
    
    def _render_top_products_chart(self):
        try:
            df_products = self.db_manager.get_top_products(st.session_state.tenant_id)
            
            if df_products.empty:
                st.info("No product data available")
                return
            
            st.subheader("Top 5 Products by Average Price")
            st.bar_chart(
                df_products.set_index("title")["avg_price"],
                use_container_width=True
            )
            
            with st.expander("View Product Details"):
                df_products["avg_price"] = df_products["avg_price"].apply(
                    lambda x: f"₹{x:,.2f}"
                )
                st.dataframe(df_products, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error loading product data: {str(e)}")
    
    def _render_revenue_trend_chart(self):
        try:
            df_revenue = self.db_manager.get_revenue_trend(st.session_state.tenant_id)
            
            if df_revenue.empty:
                st.info("No revenue data available for the last 30 days")
                return
            
            st.subheader("Revenue Trend (Last 30 Days)")
            st.line_chart(
                df_revenue.set_index("order_date")["revenue"],
                use_container_width=True
            )
            
            with st.expander("View Revenue Details"):
                df_revenue["revenue"] = df_revenue["revenue"].apply(
                    lambda x: f"₹{x:,.2f}"
                )
                st.dataframe(df_revenue, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error loading revenue data: {str(e)}")
    
    def run(self):
        st.set_page_config(
            page_title="Shopify Insights Dashboard",
            page_icon="🛍️",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
        st.title("🛍️ Shopify Insights Dashboard")
        st.markdown("---")
        
        if st.session_state.tenant_id is None:
            self.render_login_form()
        else:
            self.render_header()
            st.markdown("---")
            self.render_metrics_cards()
            st.markdown("---")
            self.render_charts()


if __name__ == "__main__":
    dashboard = ShopifyDashboard()
    dashboard.run()

# import streamlit as st
# import psycopg2
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
# from contextlib import contextmanager
# from typing import Optional, Dict, List, Tuple
# import os
# from datetime import datetime, timedelta
# import numpy as np
# from databasemanager import DatabaseManager

# class ShopifyDashboard:
#     def __init__(self):
#         self.db_manager = DatabaseManager()
#         self._initialize_session_state()
    
#     def _initialize_session_state(self):
#         if "tenant_id" not in st.session_state:
#             st.session_state.tenant_id = None
#         if "shop_name" not in st.session_state:
#             st.session_state.shop_name = None
    
#     def render_login_form(self):
#         st.subheader("🔐 Login")
        
#         with st.form("login_form"):
#             col1, col2 = st.columns([2, 1])
            
#             with col1:
#                 username = st.text_input(
#                     "Username",
#                     placeholder="myshop from myshop.myshopify.com",
#                     help="Enter your Shopify store name"
#                 )
#                 password = st.text_input(
#                     "Password",
#                     type="password",
#                     help="Enter your Shopify Password"
#                 )
            
#             submit_button = st.form_submit_button("Login", use_container_width=True)
            
#             if submit_button:
#                 if not username or not password:
#                     st.error("Please enter both shop name and API token")
#                 else:
#                     self._handle_login(username, password)
    
#     def _handle_login(self, username: str, password: str):
#         try:
#             tenant_id = self.db_manager.authenticate_tenant(username, password)
#             if tenant_id:
#                 st.session_state.tenant_id = tenant_id
#                 st.session_state.shop_name = username
#                 st.success("✅ Login successful!")
#                 st.rerun()
#             else:
#                 st.error("❌ Invalid credentials. Please check your shop name and API token.")
#         except Exception as e:
#             st.error(f"❌ Database connection error: {str(e)}")
    
#     def render_header(self):
#         col1, col2 = st.columns([3, 1])
        
#         with col1:
#             st.success(f"📊 Dashboard for: **{st.session_state.shop_name}**")
        
#         with col2:
#             if st.button("🚪 Logout", use_container_width=True):
#                 st.session_state.tenant_id = None
#                 st.session_state.shop_name = None
#                 st.rerun()
    
#     def render_kpi_dashboard(self):
#         """Render comprehensive KPI dashboard"""
#         try:
#             overview = self.db_manager.get_business_overview(st.session_state.tenant_id)
            
#             st.header("📈 Key Performance Indicators")
            
#             # Main KPIs
#             col1, col2, col3, col4, col5 = st.columns(5)
            
#             with col1:
#                 st.metric(
#                     "Total Revenue", 
#                     f"₹{overview['total_revenue']:,.2f}",
#                     delta=None
#                 )
            
#             with col2:
#                 st.metric(
#                     "Total Orders", 
#                     f"{overview['total_orders']:,}",
#                     delta=None
#                 )
            
#             with col3:
#                 st.metric(
#                     "Customers", 
#                     f"{overview['total_customers']:,}",
#                     delta=None
#                 )
            
#             with col4:
#                 st.metric(
#                     "Products", 
#                     f"{overview['total_products']:,}",
#                     delta=None
#                 )
            
#             with col5:
#                 st.metric(
#                     "Avg Order Value", 
#                     f"₹{overview['avg_order_value']:.2f}",
#                     delta=None
#                 )
            
#             # Monthly comparison
#             st.subheader("📅 Monthly Performance")
#             col1, col2, col3, col4 = st.columns(4)
            
#             # Calculate month-over-month changes
#             orders_change = overview['orders_this_month'] - overview['orders_last_month']
#             revenue_change = overview['revenue_this_month'] - overview['revenue_last_month']
            
#             with col1:
#                 st.metric(
#                     "Orders This Month",
#                     f"{overview['orders_this_month']:,}",
#                     delta=f"{orders_change:+,} vs last month"
#                 )
            
#             with col2:
#                 st.metric(
#                     "Revenue This Month",
#                     f"₹{overview['revenue_this_month']:,.2f}",
#                     delta=f"₹{revenue_change:+,.2f} vs last month"
#                 )
            
#             with col3:
#                 growth_rate = (revenue_change / overview['revenue_last_month'] * 100) if overview['revenue_last_month'] > 0 else 0
#                 st.metric(
#                     "Revenue Growth",
#                     f"{growth_rate:.1f}%",
#                     delta=f"{'📈' if growth_rate > 0 else '📉'}"
#                 )
            
#             with col4:
#                 customer_acquisition = overview['total_customers'] / max(overview['total_orders'], 1) * 100
#                 st.metric(
#                     "Customer Conversion",
#                     f"{customer_acquisition:.1f}%",
#                     delta="New vs Returning"
#                 )
                
#         except Exception as e:
#             st.error(f"Error loading KPIs: {str(e)}")
    
#     def render_advanced_analytics(self):
#         """Render advanced analytics with interactive charts"""
#         st.header("🎯 Advanced Analytics")
        
#         # Revenue trend with enhanced visualization
#         self._render_enhanced_revenue_trend()
        
#         # Customer segmentation
#         self._render_customer_segmentation()
        
#         # Product performance matrix
#         self._render_product_performance()
        
#         # Sales patterns
#         self._render_sales_patterns()
    
#     def _render_enhanced_revenue_trend(self):
#         try:
#             df_revenue = self.db_manager.get_revenue_trend(st.session_state.tenant_id, days=90)
            
#             if df_revenue.empty:
#                 st.info("No revenue data available")
#                 return
            
#             st.subheader("💰 Revenue Analytics (90 Days)")
            
#             # Create subplots
#             fig = make_subplots(
#                 rows=2, cols=2,
#                 subplot_titles=('Revenue Trend', 'Order Count', 'Average Order Value', 'Unique Customers'),
#                 specs=[[{"secondary_y": True}, {"secondary_y": False}],
#                        [{"secondary_y": False}, {"secondary_y": False}]]
#             )
            
#             # Revenue trend
#             fig.add_trace(
#                 go.Scatter(x=df_revenue['order_date'], y=df_revenue['revenue'],
#                           mode='lines+markers', name='Revenue', line=dict(color='#1f77b4')),
#                 row=1, col=1
#             )
            
#             # Order count
#             fig.add_trace(
#                 go.Bar(x=df_revenue['order_date'], y=df_revenue['order_count'],
#                       name='Orders', marker_color='#ff7f0e'),
#                 row=1, col=2
#             )
            
#             # Average order value
#             fig.add_trace(
#                 go.Scatter(x=df_revenue['order_date'], y=df_revenue['avg_order_value'],
#                           mode='lines+markers', name='AOV', line=dict(color='#2ca02c')),
#                 row=2, col=1
#             )
            
#             # Unique customers
#             fig.add_trace(
#                 go.Bar(x=df_revenue['order_date'], y=df_revenue['unique_customers'],
#                       name='Customers', marker_color='#d62728'),
#                 row=2, col=2
#             )
            
#             fig.update_layout(height=600, showlegend=False)
#             st.plotly_chart(fig, use_container_width=True)
            
#             # Summary statistics
#             col1, col2, col3 = st.columns(3)
#             with col1:
#                 st.metric("Avg Daily Revenue", f"₹{df_revenue['revenue'].mean():.2f}")
#             with col2:
#                 st.metric("Avg Daily Orders", f"{df_revenue['order_count'].mean():.1f}")
#             with col3:
#                 st.metric("Peak Day Revenue", f"₹{df_revenue['revenue'].max():,.2f}")
                
#         except Exception as e:
#             st.error(f"Error loading revenue analytics: {str(e)}")
    
#     def _render_customer_segmentation(self):
#         try:
#             df_segments = self.db_manager.get_customer_segments(st.session_state.tenant_id)
            
#             if df_segments.empty:
#                 st.info("No customer segmentation data available")
#                 return
            
#             st.subheader("👥 Customer Segmentation")
            
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 # Customer segment pie chart
#                 fig_pie = px.pie(
#                     df_segments, 
#                     values='customer_count', 
#                     names='segment',
#                     title="Customer Distribution by Segment"
#                 )
#                 st.plotly_chart(fig_pie, use_container_width=True)
            
#             with col2:
#                 # Segment value chart
#                 fig_bar = px.bar(
#                     df_segments,
#                     x='segment',
#                     y='avg_lifetime_value',
#                     title="Average Lifetime Value by Segment",
#                     color='avg_lifetime_value',
#                     color_continuous_scale='viridis'
#                 )
#                 st.plotly_chart(fig_bar, use_container_width=True)
            
#             # Detailed segment table
#             with st.expander("Detailed Segment Analysis"):
#                 st.dataframe(
#                     df_segments.style.format({
#                         'avg_lifetime_value': '₹{:.2f}',
#                         'avg_order_count': '{:.1f}',
#                         'avg_days_since_last_order': '{:.0f} days'
#                     }),
#                     use_container_width=True
#                 )
                
#         except Exception as e:
#             st.error(f"Error loading customer segmentation: {str(e)}")
    
#     def _render_product_performance(self):
#         try:
#             df_products = self.db_manager.get_product_performance(st.session_state.tenant_id, limit=20)
            
#             if df_products.empty:
#                 st.info("No product performance data available")
#                 return
            
#             st.subheader("🛍️ Product Performance Matrix")
            
#             # Filter out products with zero sales for better visualization
#             df_products_filtered = df_products[df_products['total_revenue'].fillna(0) > 0]
            
#             if not df_products_filtered.empty:
#                 # Bubble chart: Revenue vs Units Sold
#                 fig_bubble = px.scatter(
#                     df_products_filtered,
#                     x='units_sold',
#                     y='total_revenue',
#                     size='unique_buyers',
#                     color='avg_price',
#                     hover_name='title',
#                     title="Product Performance: Revenue vs Units Sold (Size = Unique Buyers)",
#                     labels={'units_sold': 'Units Sold', 'total_revenue': 'Total Revenue (₹)'}
#                 )
#                 st.plotly_chart(fig_bubble, use_container_width=True)
            
#             # Top products by different metrics
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 top_revenue = df_products.nlargest(10, 'total_revenue')
#                 fig_revenue = px.bar(
#                     top_revenue,
#                     x='total_revenue',
#                     y='title',
#                     orientation='h',
#                     title="Top 10 Products by Revenue"
#                 )
#                 fig_revenue.update_yaxis(title=None)
#                 st.plotly_chart(fig_revenue, use_container_width=True)
            
#             with col2:
#                 top_units = df_products.nlargest(10, 'units_sold')
#                 fig_units = px.bar(
#                     top_units,
#                     x='units_sold',
#                     y='title',
#                     orientation='h',
#                     title="Top 10 Products by Units Sold",
#                     color='units_sold',
#                     color_continuous_scale='blues'
#                 )
#                 fig_units.update_yaxis(title=None)
#                 st.plotly_chart(fig_units, use_container_width=True)
                
#         except Exception as e:
#             st.error(f"Error loading product performance: {str(e)}")
    
#     def _render_sales_patterns(self):
#         try:
#             df_hourly = self.db_manager.get_hourly_sales_pattern(st.session_state.tenant_id)
            
#             if df_hourly.empty:
#                 st.info("No sales pattern data available")
#                 return
            
#             st.subheader("⏰ Sales Patterns & Timing")
            
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 # Hourly sales heatmap
#                 pivot_revenue = df_hourly.pivot(index='day_name', columns='hour_of_day', values='revenue').fillna(0)
#                 fig_heatmap = px.imshow(
#                     pivot_revenue,
#                     title="Sales Revenue Heatmap (Day vs Hour)",
#                     labels=dict(x="Hour of Day", y="Day of Week", color="Revenue (₹)"),
#                     aspect="auto",
#                     color_continuous_scale="blues"
#                 )
#                 st.plotly_chart(fig_heatmap, use_container_width=True)
            
#             with col2:
#                 # Daily sales pattern
#                 daily_totals = df_hourly.groupby('day_name').agg({
#                     'order_count': 'sum',
#                     'revenue': 'sum'
#                 }).reset_index()
                
#                 # Order days properly
#                 day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
#                 daily_totals['day_name'] = pd.Categorical(daily_totals['day_name'], categories=day_order, ordered=True)
#                 daily_totals = daily_totals.sort_values('day_name')
                
#                 fig_daily = px.bar(
#                     daily_totals,
#                     x='day_name',
#                     y='revenue',
#                     title="Revenue by Day of Week"
#                 )
#                 st.plotly_chart(fig_daily, use_container_width=True)
                
#         except Exception as e:
#             st.error(f"Error loading sales patterns: {str(e)}")
    
#     def render_detailed_insights(self):
#         """Render detailed insights and recommendations"""
#         st.header("🧠 Business Insights & Recommendations")
        
#         tab1, tab2, tab3, tab4 = st.tabs(["🏆 Top Customers", "🌍 Geography", "📦 Inventory", "💡 Recommendations"])
        
#         with tab1:
#             self._render_customer_insights()
        
#         with tab2:
#             self._render_geographical_insights()
        
#         with tab3:
#             self._render_inventory_insights()
        
#         with tab4:
#             self._render_recommendations()
    
#     def _render_customer_insights(self):
#         try:
#             df_customers = self.db_manager.get_top_customers(st.session_state.tenant_id, limit=20)
            
#             if df_customers.empty:
#                 st.info("No customer data available")
#                 return
            
#             st.subheader("🏆 Customer Insights")
            
#             # Customer value distribution
#             fig_scatter = px.scatter(
#                 df_customers,
#                 x='order_count',
#                 y='total_spent',
#                 size='avg_order_value',
#                 hover_name='name',
#                 title="Customer Value Analysis",
#                 labels={'order_count': 'Number of Orders', 'total_spent': 'Total Spent (₹)'}
#             )
#             st.plotly_chart(fig_scatter, use_container_width=True)
            
#             # Customer lifetime analysis
#             df_customers['customer_lifetime_days'] = (
#                 pd.to_datetime(df_customers['last_order_date']) - 
#                 pd.to_datetime(df_customers['first_order_date'])
#             ).dt.days
            
#             # Detailed customer table
#             display_df = df_customers.copy()
#             display_df['total_spent'] = display_df['total_spent'].apply(lambda x: f"₹{x:,.2f}")
#             display_df['avg_order_value'] = display_df['avg_order_value'].apply(lambda x: f"₹{x:.2f}")
#             display_df['last_order_date'] = pd.to_datetime(display_df['last_order_date']).dt.strftime('%Y-%m-%d')
            
#             st.dataframe(
#                 display_df[['name', 'email', 'order_count', 'total_spent', 'avg_order_value', 'last_order_date']],
#                 use_container_width=True
#             )
            
#         except Exception as e:
#             st.error(f"Error loading customer insights: {str(e)}")
    
#     def _render_geographical_insights(self):
#         try:
#             df_geo = self.db_manager.get_geographical_data(st.session_state.tenant_id)
            
#             if df_geo.empty:
#                 st.info("No geographical data available")
#                 return
            
#             st.subheader("🌍 Geographical Performance")
            
#             # Country performance
#             country_summary = df_geo.groupby('country').agg({
#                 'order_count': 'sum',
#                 'total_revenue': 'sum',
#                 'avg_order_value': 'mean'
#             }).reset_index().sort_values('total_revenue', ascending=False)
            
#             col1, col2 = st.columns(2)
            
#             with col1:
#                 fig_country_revenue = px.bar(
#                     country_summary.head(10),
#                     x='total_revenue',
#                     y='country',
#                     orientation='h',
#                     title="Top Countries by Revenue"
#                 )
#                 st.plotly_chart(fig_country_revenue, use_container_width=True)
            
#             with col2:
#                 fig_country_orders = px.pie(
#                     country_summary.head(8),
#                     values='order_count',
#                     names='country',
#                     title="Order Distribution by Country"
#                 )
#                 st.plotly_chart(fig_country_orders, use_container_width=True)
            
#             # Detailed geographical table
#             with st.expander("Detailed Geographical Breakdown"):
#                 display_geo = df_geo.copy()
#                 display_geo['total_revenue'] = display_geo['total_revenue'].apply(lambda x: f"₹{x:,.2f}")
#                 display_geo['avg_order_value'] = display_geo['avg_order_value'].apply(lambda x: f"₹{x:.2f}")
#                 st.dataframe(display_geo, use_container_width=True)
                
#         except Exception as e:
#             st.error(f"Error loading geographical insights: {str(e)}")
    
#     def _render_inventory_insights(self):
#         try:
#             df_inventory = self.db_manager.get_inventory_insights(st.session_state.tenant_id)
            
#             if df_inventory.empty:
#                 st.info("No inventory data available")
#                 return
            
#             st.subheader("📦 Inventory Analysis")
            
#             # Inventory alerts
#             low_stock = df_inventory[df_inventory['inventory_quantity'] < 10]
#             overstocked = df_inventory[df_inventory['stock_to_sales_ratio'] > 10]
#             fast_movers = df_inventory[df_inventory['units_sold'] > df_inventory['units_sold'].quantile(0.8)]
            
#             col1, col2, col3 = st.columns(3)
            
#             with col1:
#                 st.metric("Low Stock Items", len(low_stock), delta="⚠️ Need Restock")
            
#             with col2:
#                 st.metric("Overstocked Items", len(overstocked), delta="💰 Reduce Orders")
            
#             with col3:
#                 st.metric("Fast Moving Items", len(fast_movers), delta="🚀 High Demand")
            
#             # Inventory performance chart
#             df_inventory_clean = df_inventory[df_inventory['units_sold'] > 0].copy()
#             if not df_inventory_clean.empty:
#                 fig_inventory = px.scatter(
#                     df_inventory_clean,
#                     x='inventory_quantity',
#                     y='units_sold',
#                     size='price',
#                     color='product_type',
#                     hover_name='title',
#                     title="Inventory vs Sales Performance",
#                     labels={'inventory_quantity': 'Current Inventory', 'units_sold': 'Units Sold'}
#                 )
#                 st.plotly_chart(fig_inventory, use_container_width=True)
            
#             # Inventory alerts tables
#             if not low_stock.empty:
#                 st.warning("⚠️ Low Stock Alerts")
#                 st.dataframe(low_stock[['title', 'product_type', 'inventory_quantity', 'units_sold']], use_container_width=True)
            
#             if not overstocked.empty:
#                 st.info("💰 Overstocked Items")
#                 st.dataframe(overstocked[['title', 'product_type', 'inventory_quantity', 'units_sold', 'stock_to_sales_ratio']], use_container_width=True)
                
#         except Exception as e:
#             st.error(f"Error loading inventory insights: {str(e)}")
    
#     def _render_recommendations(self):
#         """Generate AI-powered business recommendations"""
#         try:
#             overview = self.db_manager.get_business_overview(st.session_state.tenant_id)
#             df_segments = self.db_manager.get_customer_segments(st.session_state.tenant_id)
#             df_revenue = self.db_manager.get_revenue_trend(st.session_state.tenant_id, days=30)
            
#             st.subheader("💡 AI-Powered Recommendations")
            
#             recommendations = []
            
#             # Revenue growth recommendations
#             if not df_revenue.empty:
#                 recent_revenue = df_revenue['revenue'].tail(7).mean()
#                 older_revenue = df_revenue['revenue'].head(7).mean()
                
#                 if recent_revenue < older_revenue * 0.9:
#                     recommendations.append({
#                         'type': '📉 Revenue Decline',
#                         'priority': 'High',
#                         'recommendation': 'Revenue has declined by more than 10% recently. Consider running promotional campaigns or analyzing customer feedback.',
#                         'action': 'Launch targeted marketing campaign within 7 days'
#                     })
#                 elif recent_revenue > older_revenue * 1.1:
#                     recommendations.append({
#                         'type': '📈 Revenue Growth',
#                         'priority': 'Medium',
#                         'recommendation': 'Revenue is growing! Scale your successful strategies and consider expanding inventory for high-performing products.',
#                         'action': 'Analyze top-performing products and increase marketing budget'
#                     })
            
#             # Customer segmentation recommendations
#             if not df_segments.empty:
#                 vip_customers = df_segments[df_segments['segment'] == 'VIP']['customer_count'].iloc[0] if 'VIP' in df_segments['segment'].values else 0
#                 at_risk_customers = df_segments[df_segments['segment'] == 'At Risk']['customer_count'].iloc[0] if 'At Risk' in df_segments['segment'].values else 0
                
#                 if at_risk_customers > vip_customers:
#                     recommendations.append({
#                         'type': '⚠️ Customer Retention',
#                         'priority': 'High',
#                         'recommendation': f'You have {at_risk_customers} at-risk customers vs {vip_customers} VIP customers. Implement win-back campaigns.',
#                         'action': 'Create personalized email campaigns for at-risk customers'
#                     })
                
#                 if vip_customers > 0:
#                     recommendations.append({
#                         'type': '👑 VIP Engagement',
#                         'priority': 'Medium',
#                         'recommendation': f'You have {vip_customers} VIP customers. Create exclusive offers and loyalty programs to maintain their engagement.',
#                         'action': 'Develop VIP-only products or early access programs'
#                     })
            
#             # AOV recommendations
#             if overview['avg_order_value'] < 50:
#                 recommendations.append({
#                     'type': '💰 Average Order Value',
#                     'priority': 'Medium',
#                     'recommendation': f'Your AOV is ₹{overview["avg_order_value"]:.2f}. Consider implementing upselling, cross-selling, or minimum order incentives.',
#                     'action': 'Add product bundles and free shipping thresholds'
#                 })
            
#             # Display recommendations
#             for i, rec in enumerate(recommendations):
#                 priority_color = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}
                
#                 with st.container():
#                     st.markdown(f"""
#                     **{rec['type']}** {priority_color[rec['priority']]} {rec['priority']} Priority
                    
#                     {rec['recommendation']}
                    
#                     **Suggested Action:** {rec['action']}
#                     """)
#                     st.markdown("---")
            
#             if not recommendations:
#                 st.success("🎉 Your store is performing well! Keep monitoring key metrics and maintain current strategies.")
                
#         except Exception as e:
#             st.error(f"Error generating recommendations: {str(e)}")
    
#     def render_export_options(self):
#         """Render data export options"""
#         st.sidebar.header("📊 Export Data")
        
#         export_options = st.sidebar.multiselect(
#             "Select data to export:",
#             ["Top Customers", "Product Performance", "Revenue Trend", "Customer Segments"]
#         )
        
#         if st.sidebar.button("📥 Export Selected Data"):
#             if export_options:
#                 # This would typically generate CSV/Excel files
#                 st.sidebar.success("Export functionality would be implemented here!")
#             else:
#                 st.sidebar.warning("Please select data to export")
    
#     def run(self):
#         st.set_page_config(
#             page_title="Shopify Insights Dashboard",
#             page_icon="🛍️",
#             layout="wide",
#             initial_sidebar_state="expanded"
#         )
        
#         # Custom CSS for better styling
#         st.markdown("""
#         <style>
#         .metric-card {
#             background-color: #f0f2f6;
#             padding: 1rem;
#             border-radius: 0.5rem;
#             border-left: 4px solid #1f77b4;
#         }
#         .stTabs [data-baseweb="tab-list"] {
#             gap: 2px;
#         }
#         .stTabs [data-baseweb="tab"] {
#             height: 50px;
#             padding-left: 20px;
#             padding-right: 20px;
#         }
#         </style>
#         """, unsafe_allow_html=True)
        
#         st.title("🛍️ Shopify Advanced Analytics Dashboard")
#         st.markdown("*Comprehensive business intelligence for data-driven decisions*")
#         st.markdown("---")
        
#         if st.session_state.tenant_id is None:
#             self.render_login_form()
#         else:
#             self.render_header()
            
#             # Sidebar navigation
#             st.sidebar.title("🧭 Navigation")
#             page = st.sidebar.radio(
#                 "Select Dashboard View:",
#                 ["📈 Overview", "🎯 Advanced Analytics", "🧠 Detailed Insights"]
#             )
            
#             # Time range selector
#             st.sidebar.subheader("📅 Time Range")
#             time_range = st.sidebar.selectbox(
#                 "Analysis Period:",
#                 ["Last 30 days", "Last 90 days", "Last 6 months", "Last year"]
#             )
            
#             # Render export options
#             self.render_export_options()
            
#             # Main content based on selected page
#             if page == "📈 Overview":
#                 self.render_kpi_dashboard()
#                 st.markdown("---")
                
#                 # Quick insights
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     try:
#                         df_customers = self.db_manager.get_top_customers(st.session_state.tenant_id, limit=5)
#                         if not df_customers.empty:
#                             st.subheader("🏆 Top 5 Customers")
#                             for idx, row in df_customers.iterrows():
#                                 st.write(f"**{row['name']}** - ₹{row['total_spent']:,.2f} ({row['order_count']} orders)")
#                     except Exception as e:
#                         st.error(f"Error loading top customers: {str(e)}")
                
#                 with col2:
#                     try:
#                         df_products = self.db_manager.get_product_performance(st.session_state.tenant_id, limit=5)
#                         if not df_products.empty:
#                             st.subheader("🎯 Top 5 Products")
#                             for idx, row in df_products.iterrows():
#                                 revenue = row['total_revenue'] if pd.notna(row['total_revenue']) else 0
#                                 st.write(f"**{row['title']}** - ₹{revenue:,.2f} revenue")
#                     except Exception as e:
#                         st.error(f"Error loading top products: {str(e)}")
            
#             elif page == "🎯 Advanced Analytics":
#                 self.render_advanced_analytics()
            
#             elif page == "🧠 Detailed Insights":
#                 self.render_detailed_insights()
            
#             # Footer with last update time
#             st.sidebar.markdown("---")
#             st.sidebar.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# if __name__ == "__main__":
#     dashboard = ShopifyDashboard()
#     dashboard.run()