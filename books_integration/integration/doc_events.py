import frappe

from books_integration.integration.outbound import enqueue_for_books


def on_sales_invoice_change(doc, method=None):
	try:
		enqueue_for_books("Sales Invoice", doc.name)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Books outbound Sales Invoice")


def on_payment_entry_change(doc, method=None):
	# Payment Entry → Books payload can be added alongside pull serializers
	try:
		pass
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Books outbound Payment Entry")


def on_item_change(doc, method=None):
	try:
		s = frappe.get_single("Books Sync Settings")
		if not s.enable_sync or not s.sync_item or s.item_sync_type == "Push":
			return
		from books_integration.sync.pull import item_row_to_books

		payload = item_row_to_books(
			{
				"name": doc.name,
				"item_code": doc.item_code,
				"item_name": doc.item_name,
				"stock_uom": doc.stock_uom,
				"item_group": doc.item_group,
				"description": doc.description,
			}
		)
		for row in frappe.get_all("Books Instance", filters={"status": "Active"}, fields=["name"]):
			import json

			frappe.get_doc(
				{
					"doctype": "Books Sync Queue",
					"instance": row.name,
					"books_doctype": "Item",
					"document_json": json.dumps(payload),
					"status": "Pending",
					"priority": 40,
				}
			).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Books outbound Item")


def on_customer_change(doc, method=None):
	try:
		s = frappe.get_single("Books Sync Settings")
		if not s.enable_sync or not s.sync_customer or s.customer_sync_type == "Push":
			return
		from books_integration.sync.pull import customer_to_party_books

		payload = customer_to_party_books({"name": doc.name, "customer_name": doc.customer_name})
		for row in frappe.get_all("Books Instance", filters={"status": "Active"}, fields=["name"]):
			import json

			frappe.get_doc(
				{
					"doctype": "Books Sync Queue",
					"instance": row.name,
					"books_doctype": "Party",
					"document_json": json.dumps(payload),
					"status": "Pending",
					"priority": 40,
				}
			).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Books outbound Customer")


def on_supplier_change(doc, method=None):
	try:
		s = frappe.get_single("Books Sync Settings")
		if not s.enable_sync or not s.sync_supplier or s.supplier_sync_type == "Push":
			return
		name = doc.name
		payload = {
			"doctype": "Party",
			"name": name,
			"role": "Supplier",
			"erpnextDocName": name,
			"fbooksDocName": name,
		}
		for row in frappe.get_all("Books Instance", filters={"status": "Active"}, fields=["name"]):
			import json

			frappe.get_doc(
				{
					"doctype": "Books Sync Queue",
					"instance": row.name,
					"books_doctype": "Party",
					"document_json": json.dumps(payload),
					"status": "Pending",
					"priority": 40,
				}
			).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Books outbound Supplier")


def on_delivery_note_change(doc, method=None):
	try:
		pass
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Books outbound Delivery Note")
