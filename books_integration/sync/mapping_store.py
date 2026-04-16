import frappe


def get_mapping(instance_name: str, books_doctype: str, books_name: str) -> frappe._dict | None:
	name = frappe.db.get_value(
		"Books Name Map",
		{
			"instance": instance_name,
			"books_doctype": books_doctype,
			"books_name": books_name,
		},
		["name", "erpnext_doctype", "erpnext_name"],
		as_dict=True,
	)
	return name


def upsert_mapping(
	instance_name: str,
	books_doctype: str,
	books_name: str,
	erpnext_doctype: str,
	erpnext_name: str,
):
	existing = frappe.db.exists(
		"Books Name Map",
		{
			"instance": instance_name,
			"books_doctype": books_doctype,
			"books_name": books_name,
		},
	)
	if existing:
		doc = frappe.get_doc("Books Name Map", existing)
		doc.erpnext_doctype = erpnext_doctype
		doc.erpnext_name = erpnext_name
		doc.save(ignore_permissions=True)
		return doc

	doc = frappe.get_doc(
		{
			"doctype": "Books Name Map",
			"instance": instance_name,
			"books_doctype": books_doctype,
			"books_name": books_name,
			"erpnext_doctype": erpnext_doctype,
			"erpnext_name": erpnext_name,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc
