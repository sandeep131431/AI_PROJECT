from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


# 1. Get Purchase Order with line items
@router.get("/po/{po_number}")
def get_purchase_order(
    po_number: str,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            po.po_number,
            po.vendor_id,
            po.po_date,
            po.expected_delivery_date,
            po.currency,
            po.status
        FROM erp.purchase_orders po
        WHERE po.po_number = :po_number
    """)

    po = db.execute(
        query, {"po_number": po_number}
    ).mappings().first()

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    items_query = text("""
        SELECT
            li.sku_code,
            li.description,
            li.quantity,
            li.unit_price,
            li.line_total
        FROM erp.po_line_items li
        WHERE li.po_number = :po_number
    """)

    items = db.execute(
        items_query, {"po_number": po_number}
    ).mappings().all()

    return {
        "purchase_order": dict(po),
        "line_items": [dict(item) for item in items]
    }


# 2. Get Vendor
@router.get("/vendor/{vendor_id}")
def get_vendor(
    vendor_id: str,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT *
        FROM erp.vendors
        WHERE vendor_id = :vendor_id
    """)

    vendor = db.execute(
        query, {"vendor_id": vendor_id}
    ).mappings().first()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return dict(vendor)


# 3. Get SKU
@router.get("/sku/{sku_code}")
def get_sku(
    sku_code: str,
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT *
        FROM erp.sku_master
        WHERE sku_code = :sku_code
    """)

    sku = db.execute(
        query, {"sku_code": sku_code}
    ).mappings().first()

    if not sku:
        raise HTTPException(status_code=404, detail="SKU not found")

    return dict(sku)