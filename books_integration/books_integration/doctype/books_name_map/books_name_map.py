import frappe
from frappe import _
from frappe.model.document import Document


class BooksNameMap(Document):
	def validate(self):
		exists = frappe.db.exists(
			"Books Name Map",
			{
				"instance": self.instance,
				"books_doctype": self.books_doctype,
				"books_name": self.books_name,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(_("Mapping for this Books document already exists"))
