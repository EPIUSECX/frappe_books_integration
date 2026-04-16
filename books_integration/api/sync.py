import json

import frappe
from frappe import _

from books_integration.sync.instance import get_company_for_instance, get_instance_by_device
from books_integration.sync.pull import build_initial_master_docs, queue_row_to_books_payload
from books_integration.sync.push import process_record
from books_integration.utils import pretty_json, update_books_reference


@frappe.whitelist(methods=["GET"])
def get_pending_docs():
	instance_id = frappe.form_dict.get("instance") or frappe.request.args.get("instance")
	all_docs = frappe.form_dict.get("all_docs") or frappe.request.args.get("all_docs")
	all_docs_flag = str(all_docs).lower() in ("1", "true", "yes")

	if not instance_id:
		return _pending_response(False, _("instance is required"), [])

	inst = get_instance_by_device(instance_id)
	if not inst:
		return _pending_response(False, _("Unknown instance — register first"), [])

	company = get_company_for_instance(inst)
	data: list = []

	rows = frappe.get_all(
		"Books Sync Queue",
		filters={"instance": inst.name, "status": "Pending"},
		fields=["name", "books_doctype", "document_json", "priority"],
		order_by="priority asc, creation asc",
		limit=100,
	)
	for row in rows:
		try:
			data.append(queue_row_to_books_payload(row))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Books Sync Queue parse error")

	if all_docs_flag and company:
		try:
			data.extend(build_initial_master_docs(company))
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Books initial sync masters")

	return _pending_response(True, "", data)


def _pending_response(success: bool, message: str, data: list):
	return {
		"status": "ok" if success else "error",
		"success": success,
		"message": message or "",
		"data": data,
	}


@frappe.whitelist(methods=["POST"])
def sync_transactions():
	payload = _get_json_body()
	instance_id = payload.get("instance")
	records = payload.get("records") or []

	if not instance_id:
		frappe.throw(_("instance is required"))

	inst = get_instance_by_device(instance_id)
	if not inst:
		frappe.throw(_("Unknown instance — register first"))

	success_log = []
	failed_log = []

	for rec in records:
		dt = rec.get("doctype") or rec.get("schemaName") or "?"
		name = rec.get("name") or ""
		try:
			result = process_record(inst, rec)
			success_log.append({"name": result.get("name"), "doctype": result.get("doctype")})
			_log_sync(
				inst.name, "push", True, "", json.dumps({"record": name, "doctype": dt, "result": result})
			)
		except Exception as e:
			tb = frappe.get_traceback()
			frappe.log_error(tb, f"Books push failed {dt} {name}")
			_log_books_error(inst.name, rec, tb)
			failed_log.append({"name": name, "doctype": dt})
			_log_sync(inst.name, "push", False, str(e), tb)

	return {"success": len(failed_log) == 0, "success_log": success_log, "failed_log": failed_log}


@frappe.whitelist(methods=["POST"])
def update_status():
	payload = _get_json_body()
	instance_id = payload.get("instance")
	data = payload.get("data") or {}

	if not instance_id:
		frappe.throw(_("instance is required"))

	inst = get_instance_by_device(instance_id)
	if not inst:
		frappe.throw(_("Unknown instance"))

	doctype = data.get("doctype")
	name_in_erp = data.get("nameInERPNext")
	name_in_books = data.get("nameInFBooks")

	if doctype and name_in_erp and name_in_books:
		from books_integration.sync.mapping_store import upsert_mapping

		erp_dt = None
		if doctype == "SalesInvoice":
			erp_dt = "Sales Invoice"
		elif doctype == "Payment":
			erp_dt = "Payment Entry"
		if erp_dt:
			upsert_mapping(inst.name, doctype, name_in_books, erp_dt, name_in_erp)
			update_books_reference(
				inst.name,
				{"doctype": doctype, "name": name_in_erp, "books_name": name_in_books},
			)

	if name_in_books:
		for qname in frappe.get_all(
			"Books Sync Queue",
			filters={"instance": inst.name, "status": "Pending"},
			pluck="name",
		):
			q = frappe.get_doc("Books Sync Queue", qname)
			try:
				j = json.loads(q.document_json or "{}")
			except Exception:
				continue
			if j.get("name") == name_in_books:
				q.status = "Synced"
				q.save(ignore_permissions=True)

	return {"success": True, "message": "ok"}


def _get_json_body() -> dict:
	req = getattr(frappe.local, "request", None)
	if not req:
		return dict(frappe.form_dict) if frappe.form_dict else {}
	try:
		if getattr(req, "data", None):
			return json.loads(req.get_data(as_text=True))
	except Exception:
		pass
	try:
		if req.is_json and req.json:
			return req.json
	except Exception:
		pass
	return dict(frappe.form_dict) if frappe.form_dict else {}


def _log_sync(instance_name: str, operation: str, success: bool, message: str, details: str):
	try:
		frappe.get_doc(
			{
				"doctype": "Books Sync Log",
				"instance": instance_name,
				"operation": operation,
				"success": 1 if success else 0,
				"message": (message or "")[:140],
				"details": details[:10000] if details else None,
			}
		).insert(ignore_permissions=True)
	except Exception:
		pass


def _log_books_error(instance_name: str, record: dict, err_tb: str):
	try:
		frappe.get_doc(
			{
				"doctype": "Books Error Log",
				"books_instance": instance_name,
				"document_type": record.get("doctype") or record.get("schemaName") or "?",
				"data": (pretty_json(record) or "")[:120000],
				"error": (err_tb or "")[:120000],
			}
		).insert(ignore_permissions=True)
	except Exception:
		pass
