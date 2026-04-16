import frappe
from frappe.utils import add_to_date, now


def hourly_cleanup():
	"""Trim old sync logs (best-effort)."""
	try:
		cutoff = add_to_date(now(), days=-90)
		frappe.db.sql("delete from `tabBooks Sync Log` where modified < %s", (cutoff,))
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Books hourly_cleanup")
