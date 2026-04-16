import frappe
from frappe import _
from frappe.exceptions import AuthenticationError

from books_integration.sync.instance import upsert_instance
from books_integration.sync.settings_response import build_sync_settings_message


@frappe.whitelist(methods=["POST"])
def register_instance(instance, instance_name=None):
	"""Register a Frappe Books device (instance id) with this site."""
	if not instance:
		frappe.throw(_("instance (device id) is required"))

	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Authentication required"), AuthenticationError)

	upsert_instance(instance, user, instance_name)
	return {"success": True, "message": "Registered"}


@frappe.whitelist(methods=["GET"])
def sync_settings():
	"""Return feature flags and connector version for Frappe Books."""
	return build_sync_settings_message()
