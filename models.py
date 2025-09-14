from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, BigInteger, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    shop_name = Column(String, unique=True, index=True)
    access_token = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    customers = relationship("Customer", back_populates="tenant")
    products = relationship("Product", back_populates="tenant")
    orders = relationship("Order", back_populates="tenant")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    shopify_customer_id = Column(BigInteger, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String)
    phone = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    tenant = relationship("Tenant", back_populates="customers")
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    shopify_product_id = Column(BigInteger, unique=True, index=True)
    title = Column(String)
    vendor = Column(String)
    product_type = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    tenant = relationship("Tenant", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product")

class ProductVariant(Base):
    __tablename__ = "product_variants"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    shopify_variant_id = Column(BigInteger, unique=True, index=True)
    title = Column(String)
    price = Column(DECIMAL(10, 2))
    sku = Column(String)
    weight = Column(DECIMAL(10, 2))
    weight_unit = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    product = relationship("Product", back_populates="variants")
    order_items = relationship("OrderLineItem", back_populates="variant")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    customer_id = Column(Integer, ForeignKey("customers.id"))
    shopify_order_id = Column(BigInteger, unique=True, index=True)
    total_price = Column(DECIMAL(10, 2))
    currency = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    tenant = relationship("Tenant", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    line_items = relationship("OrderLineItem", back_populates="order")

class OrderLineItem(Base):
    __tablename__ = "order_line_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"))
    quantity = Column(Integer)
    price = Column(DECIMAL(10, 2))
    created_at = Column(DateTime, server_default=func.now())
    order = relationship("Order", back_populates="line_items")
    variant = relationship("ProductVariant", back_populates="order_items")