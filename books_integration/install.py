import frappe

from books_integration import __version__


def after_install():
	ensure_books_sync_settings()
	ensure_books_item_settings()


def ensure_books_sync_settings():
	if frappe.db.exists("Books Sync Settings", "Books Sync Settings"):
		return
	doc = frappe.get_doc(
		{
			"doctype": "Books Sync Settings",
			"enable_sync": 1,
			"sync_dependant_masters": 1,
			"sync_interval": "60",
			"sync_item": 1,
			"item_sync_type": "Bidirectional",
			"sync_customer": 1,
			"customer_sync_type": "Bidirectional",
			"sync_supplier": 1,
			"supplier_sync_type": "Bidirectional",
			"sync_sales_invoice": 1,
			"sales_invoice_sync_type": "Bidirectional",
			"sync_sales_payment": 1,
			"sales_payment_sync_type": "Bidirectional",
			"sync_stock": 1,
			"stock_sync_type": "Pull",
			"sync_price_list": 1,
			"price_list_sync_type": "Bidirectional",
			"sync_serial_number": 0,
			"serial_number_sync_type": "Pull",
			"sync_batches": 1,
			"batch_sync_type": "Bidirectional",
			"sync_delivery_note": 1,
			"delivery_note_sync_type": "Bidirectional",
			"app_version": __version__,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()


def ensure_books_item_settings():
	if frappe.db.exists("Books Item Settings", "Books Item Settings"):
		return
	frappe.get_doc({"doctype": "Books Item Settings"}).insert(ignore_permissions=True)
	frappe.db.commit()
