import frappe
from frappe import _
from frappe.model.document import Document


class BooksInstance(Document):
	def validate(self):
		if self.device_id and frappe.db.exists(
			"Books Instance", {"device_id": self.device_id, "name": ["!=", self.name]}
		):
			frappe.throw(_("Device ID must be unique"))
