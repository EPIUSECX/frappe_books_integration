import frappe

from books_integration import __version__


def build_sync_settings_message() -> dict:
	doc = frappe.get_single("Books Sync Settings")
	out = {
		"name": doc.name,
		"owner": doc.owner,
		"modified": str(doc.modified),
		"modified_by": doc.modified_by,
		"docstatus": bool(doc.docstatus),
		"idx": str(doc.idx or 0),
		"enable_sync": bool(doc.enable_sync),
		"sync_dependant_masters": bool(doc.sync_dependant_masters),
		"sync_interval": doc.sync_interval or "60",
		"sync_item": bool(doc.sync_item),
		"item_sync_type": doc.item_sync_type or "Bidirectional",
		"sync_customer": bool(doc.sync_customer),
		"customer_sync_type": doc.customer_sync_type or "Bidirectional",
		"sync_supplier": bool(doc.sync_supplier),
		"supplier_sync_type": doc.supplier_sync_type or "Bidirectional",
		"sync_sales_invoice": bool(doc.sync_sales_invoice),
		"sales_invoice_sync_type": doc.sales_invoice_sync_type or "Bidirectional",
		"sync_sales_payment": bool(doc.sync_sales_payment),
		"sales_payment_sync_type": doc.sales_payment_sync_type or "Bidirectional",
		"sync_stock": bool(doc.sync_stock),
		"stock_sync_type": doc.stock_sync_type or "Pull",
		"sync_price_list": bool(doc.sync_price_list),
		"price_list_sync_type": doc.price_list_sync_type or "Bidirectional",
		"sync_serial_number": bool(doc.sync_serial_number),
		"serial_number_sync_type": doc.serial_number_sync_type or "Pull",
		"sync_batches": bool(doc.sync_batches),
		"batch_sync_type": doc.batch_sync_type or "Bidirectional",
		"sync_delivery_note": bool(doc.sync_delivery_note),
		"delivery_note_sync_type": doc.delivery_note_sync_type or "Bidirectional",
		"sync_item_as_non_inventory": bool(getattr(doc, "sync_item_as_non_inventory", False)),
		"doctype": "Books Sync Settings",
	}
	return {
		"success": True,
		"app_version": doc.app_version or __version__,
		"message": "",
		"data": out,
	}
