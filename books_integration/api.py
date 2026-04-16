import frappe
from frappe import _
from frappe.exceptions import AuthenticationError

from books_integration.agent_debug_log import agent_debug
from books_integration.sync.instance import upsert_instance
from books_integration.sync.settings_response import build_sync_settings_message


@frappe.whitelist(methods=["POST"])
def register_instance(instance, instance_name=None):
	"""Register a Frappe Books device (instance id) with this site."""
	# #region agent log
	agent_debug(
		"H3",
		"api.register_instance:entry",
		"register_instance invoked",
		{"has_instance_arg": bool(instance), "user": frappe.session.user},
	)
	# #endregion
	if not instance:
		frappe.throw(_("instance (device id) is required"))

	user = frappe.session.user
	if user == "Guest":
		# #region agent log
		agent_debug(
			"H1",
			"api.register_instance:guest",
			"register rejected Guest",
			{},
		)
		# #endregion
		frappe.throw(_("Authentication required"), AuthenticationError)

	upsert_instance(instance, user, instance_name)
	# #region agent log
	agent_debug(
		"H3",
		"api.register_instance:success",
		"register_instance completed",
		{"user": user},
	)
	# #endregion
	return {"success": True, "message": "Registered"}


@frappe.whitelist(methods=["GET", "POST"])
def sync_settings():
	"""Return feature flags and connector version for Frappe Books."""
	# #region agent log
	agent_debug(
		"H3",
		"api.sync_settings:entry",
		"sync_settings invoked",
		{"user": frappe.session.user},
	)
	# #endregion
	try:
		out = build_sync_settings_message()
		# #region agent log
		agent_debug(
			"H5",
			"api.sync_settings:success",
			"build_sync_settings_message ok",
			{
				"enable_sync": bool(out.get("data", {}).get("enable_sync"))
				if isinstance(out.get("data"), dict)
				else None,
			},
		)
		# #endregion
		return out
	except Exception as err:
		# #region agent log
		agent_debug(
			"H5",
			"api.sync_settings:error",
			"build_sync_settings_message failed",
			{"exc_type": type(err).__name__},
		)
		# #endregion
		raise
