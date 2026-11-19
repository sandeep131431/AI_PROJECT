
-- Create ERP schema
CREATE SCHEMA IF NOT EXISTS erp;


-- 1. Vendors master table
CREATE TABLE IF NOT EXISTS erp.vendors (
    vendor_id VARCHAR(64) PRIMARY KEY,
    vendor_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(30),
    address TEXT,
    country VARCHAR(100),
    currency CHAR(3),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);


-- 2. SKU master table
CREATE TABLE IF NOT EXISTS erp.sku_master (
    sku_code VARCHAR(64) PRIMARY KEY,
    sku_name VARCHAR(255) NOT NULL,
    description TEXT,
    unit VARCHAR(32),
    standard_unit_price NUMERIC(14,4),
    currency CHAR(3),
    is_active BOOLEAN DEFAULT TRUE
);


-- 3. Purchase orders
CREATE TABLE IF NOT EXISTS erp.purchase_orders (
    po_number VARCHAR(64) PRIMARY KEY,
    vendor_id VARCHAR(64) NOT NULL
        REFERENCES erp.vendors(vendor_id),

    po_date DATE,
    expected_delivery_date DATE,
    currency CHAR(3),

    status VARCHAR(32) DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT now()
);


-- 4. Purchase order line items
CREATE TABLE IF NOT EXISTS erp.po_line_items (
    id BIGSERIAL PRIMARY KEY,

    po_number VARCHAR(64) NOT NULL
        REFERENCES erp.purchase_orders(po_number),

    sku_code VARCHAR(64) NOT NULL
        REFERENCES erp.sku_master(sku_code),

    description TEXT,
    quantity NUMERIC(12,3) NOT NULL,
    unit_price NUMERIC(14,4) NOT NULL,
    line_total NUMERIC(14,2),

    UNIQUE (po_number, sku_code)
);


-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_po_vendor
ON erp.purchase_orders(vendor_id);

CREATE INDEX IF NOT EXISTS idx_po_line_po
ON erp.po_line_items(po_number);

CREATE INDEX IF NOT EXISTS idx_po_line_sku
ON erp.po_line_items(sku_code);
