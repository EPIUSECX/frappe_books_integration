import frappe
from frappe import _

from books_integration.doc_converter import init_doc_converter
from books_integration.sync.mapping_store import upsert_mapping
from books_integration.utils import get_doctype_name, update_books_reference


def process_via_converter(instance_row: dict, record: dict) -> dict | None:
	"""Create/update ERPNext documents via DocConverter. Returns None to use legacy push."""
	doctype = record.get("doctype") or record.get("schemaName")
	conv = init_doc_converter(instance_row["name"], record, "erpn")
	if not conv:
		return None

	erp_dt = get_doctype_name(doctype, "erpn", record)
	if not erp_dt:
		return None

	books_name = record.get("name")
	if not books_name:
		frappe.throw(_("Record missing name"))

	ref = frappe.db.get_value(
		"Books Reference",
		{
			"document_type": erp_dt,
			"books_name": books_name,
			"books_instance": instance_row["name"],
		},
		"document_name",
	)

	if ref and frappe.db.exists(erp_dt, ref):
		doc = frappe.get_doc(erp_dt, ref)
		doc.update(conv.get_converted_doc())
		doc.flags.ignore_permissions = True
		doc.save()
		if record.get("submitted") or record.get("docstatus") == 1:
			if doc.docstatus == 0 and doc.meta.is_submittable:
				doc.submit()
		if record.get("cancelled") and doc.docstatus == 1:
			doc.cancel()
		_sync_maps(instance_row["name"], doctype, books_name, erp_dt, doc.name)
		return {"name": doc.name, "doctype": erp_dt}

	doc = conv.get_frappe_doc()
	if not doc:
		return None

	doc.flags.ignore_permissions = True
	doc.run_method("set_missing_values")
	doc.insert()

	if record.get("submitted") or record.get("docstatus") == 1:
		if doc.docstatus == 0 and doc.meta.is_submittable:
			doc.submit()

	update_books_reference(
		instance_row["name"],
		{"doctype": doctype, "name": doc.name, "books_name": books_name},
	)
	_sync_maps(instance_row["name"], doctype, books_name, erp_dt, doc.name)
	return {"name": doc.name, "doctype": erp_dt}


def _sync_maps(instance: str, books_doctype: str, books_name: str, erp_dt: str, erp_name: str):
	upsert_mapping(instance, books_doctype, books_name, erp_dt, erp_name)
