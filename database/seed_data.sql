
BEGIN;

-- 1. Insert Vendors
INSERT INTO erp.vendors
(vendor_id, vendor_name, email, country, currency)
VALUES
('V001', 'ABC Logistics Pvt Ltd', 'abc@example.com', 'India', 'INR'),
('V002', 'Global Transport Ltd', 'global@example.com', 'India', 'INR')
ON CONFLICT (vendor_id) DO NOTHING;


-- 2. Insert SKU Master
INSERT INTO erp.sku_master
(sku_code, sku_name, description, unit, standard_unit_price, currency)
VALUES
('SKU001', 'Packaging Box', 'Standard packaging box', 'piece', 100.00, 'INR'),
('SKU002', 'Shipping Tape', 'Industrial shipping tape', 'roll', 50.00, 'INR'),
('SKU003', 'Packing Material', 'Protective packing material', 'kg', 200.00, 'INR')
ON CONFLICT (sku_code) DO NOTHING;


-- 3. Insert Purchase Orders
INSERT INTO erp.purchase_orders
(po_number, vendor_id, po_date, currency, total_amount, status)
SELECT
    'PO1001',
    'V001',
    '2026-11-10',
    'INR',
    350.00,
    'open'
WHERE EXISTS (
    SELECT 1 FROM erp.vendors
    WHERE vendor_id = 'V001'
)
ON CONFLICT (po_number) DO NOTHING;


-- 4. Insert PO Line Items
INSERT INTO erp.po_line_items
(po_id, item_code, description, quantity, unit_price, line_total)
SELECT
    po.po_id,
    data.item_code,
    sku.sku_name,
    data.quantity,
    data.unit_price,
    data.quantity * data.unit_price
FROM (
    VALUES
    ('SKU001', 2::NUMERIC, 100::NUMERIC),
    ('SKU002', 3::NUMERIC, 50::NUMERIC)
) AS data(item_code, quantity, unit_price)

JOIN erp.purchase_orders po
    ON po.po_number = 'PO1001'

JOIN erp.sku_master sku
    ON sku.sku_code = data.item_code

WHERE NOT EXISTS (
    SELECT 1
    FROM erp.po_line_items existing
    WHERE existing.po_id = po.po_id
      AND existing.item_code = data.item_code
);

COMMIT;
