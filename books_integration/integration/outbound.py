import json

import frappe

from books_integration.sync.pull import sales_invoice_to_books


def enqueue_for_books(erpnext_doctype: str, erpnext_name: str):
	"""Queue ERPNext documents for pull by connected Frappe Books instances."""
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return

	settings = frappe.get_single("Books Sync Settings")
	if not settings.enable_sync:
		return
	if erpnext_doctype == "Sales Invoice" and (
		not settings.sync_sales_invoice or settings.sales_invoice_sync_type == "Push"
	):
		return

	payload = _serialize(erpnext_doctype, erpnext_name)
	if not payload:
		return

	for row in frappe.get_all("Books Instance", filters={"status": "Active"}, fields=["name"]):
		frappe.get_doc(
			{
				"doctype": "Books Sync Queue",
				"instance": row.name,
				"books_doctype": payload.get("doctype"),
				"document_json": json.dumps(payload),
				"status": "Pending",
				"priority": 50,
			}
		).insert(ignore_permissions=True)


def _serialize(erpnext_doctype: str, erpnext_name: str) -> dict | None:
	if erpnext_doctype == "Sales Invoice":
		return sales_invoice_to_books(erpnext_name)
	# Masters: enqueue Item / Party via dedicated flows when expanding scope
	return None
