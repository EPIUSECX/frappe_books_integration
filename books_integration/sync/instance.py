import frappe
from frappe import _


def get_instance_by_device(device_id: str) -> dict | None:
	if not device_id:
		return None
	return frappe.db.get_value(
		"Books Instance",
		{"device_id": device_id},
		["name", "device_id", "user", "company", "status"],
		as_dict=True,
	)


def get_company_for_instance(instance: dict | None, fallback_user: str | None = None) -> str | None:
	if instance and instance.get("company"):
		return instance["company"]
	settings = frappe.get_single("Books Sync Settings")
	if settings.default_company:
		return settings.default_company
	if fallback_user:
		c = frappe.defaults.get_user_default("Company", user=fallback_user)
		if c:
			return c
	companies = frappe.get_all("Company", pluck="name", limit=1)
	return companies[0] if companies else None


def upsert_instance(device_id: str, user: str, instance_name: str | None = None) -> dict:
	company = get_company_for_instance(None, user)
	if not company:
		frappe.throw(_("No Company found. Set Default Company or Books Sync Settings.default_company."))

	existing = get_instance_by_device(device_id)
	if existing:
		doc = frappe.get_doc("Books Instance", existing.name)
		if instance_name:
			doc.instance_name = instance_name
		doc.user = user
		doc.company = company
		doc.status = "Active"
		doc.save(ignore_permissions=True)
		return doc.as_dict()

	doc = frappe.get_doc(
		{
			"doctype": "Books Instance",
			"device_id": device_id,
			"user": user,
			"company": company,
			"instance_name": instance_name or "",
			"status": "Active",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.as_dict()
