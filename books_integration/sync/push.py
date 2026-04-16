import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate, today

from books_integration.sync.instance import get_company_for_instance
from books_integration.sync.mapping_store import get_mapping, upsert_mapping


def process_record(instance_row: dict, record: dict) -> dict:
	from books_integration.sync.converter_process import process_via_converter

	converted = process_via_converter(instance_row, record)
	if converted is not None:
		return converted

	doctype = record.get("doctype") or record.get("schemaName")
	if not doctype:
		frappe.throw(_("Record missing doctype"))

	if doctype == "SalesInvoice":
		return push_sales_invoice(instance_row, record)
	if doctype == "Payment":
		return push_payment(instance_row, record)
	if doctype in ("Shipment", "POSOpeningShift", "POSClosingShift"):
		frappe.throw(
			_("DocType {0} is not supported yet in this connector").format(doctype),
			title=_("Unsupported"),
		)

	frappe.throw(_("Unsupported doctype: {0}").format(doctype))


def push_sales_invoice(instance_row: dict, record: dict) -> dict:
	company = get_company_for_instance(instance_row)
	if not company:
		frappe.throw(_("Company not configured for this Books instance"))

	books_name = record.get("name")
	if not books_name:
		frappe.throw(_("Sales Invoice missing name"))

	mapped = get_mapping(instance_row["name"], "SalesInvoice", books_name)
	if mapped and frappe.db.exists("Sales Invoice", mapped["erpnext_name"]):
		return {"name": mapped["erpnext_name"], "doctype": "Sales Invoice"}

	customer = resolve_party_to_customer(instance_row, record.get("party"), company)
	posting_date = getdate(get_datetime(record.get("date"))) if record.get("date") else today()

	si = frappe.new_doc("Sales Invoice")
	si.company = company
	si.customer = customer
	si.posting_date = posting_date
	si.due_date = posting_date

	items = record.get("items") or []
	if not items:
		frappe.throw(_("Sales Invoice has no items"))

	for row in items:
		item_code = row.get("item")
		if not item_code:
			frappe.throw(_("Item row missing item link"))
		ensure_item_exists(item_code, company)
		qty = flt(row.get("quantity") or row.get("transferQuantity") or 1)
		rate = flt(row.get("rate") or 0)
		income_account = row.get("account") or get_income_account(item_code, company)
		si.append(
			"items",
			{
				"item_code": item_code,
				"qty": qty,
				"rate": rate,
				"income_account": income_account,
				"uom": frappe.db.get_value("Item", item_code, "stock_uom") or "Nos",
			},
		)

	si.set_missing_values()
	si.insert(ignore_permissions=True)

	if record.get("submitted") or record.get("docstatus") == 1:
		si.submit()

	upsert_mapping(instance_row["name"], "SalesInvoice", books_name, "Sales Invoice", si.name)
	return {"name": si.name, "doctype": "Sales Invoice"}


def get_income_account(item_code: str, company: str) -> str:
	acc = frappe.db.get_value(
		"Item Default",
		{"parent": item_code, "company": company},
		"income_account",
	)
	if acc:
		return acc
	return frappe.db.get_value("Company", company, "default_income_account")


def ensure_item_exists(item_code: str, company: str):
	if frappe.db.exists("Item", item_code):
		return
	it = frappe.new_doc("Item")
	it.item_code = item_code
	it.item_name = item_code
	ig = frappe.get_all("Item Group", fields=["name"], limit=1)
	it.item_group = ig[0].name if ig else "All Item Groups"
	it.stock_uom = "Nos"
	it.is_stock_item = 0
	it.insert(ignore_permissions=True)


def resolve_party_to_customer(instance_row: dict, party_name: str | None, company: str) -> str:
	if not party_name:
		frappe.throw(_("Missing party on document"))

	m = get_mapping(instance_row["name"], "Party", party_name)
	if m and frappe.db.exists("Customer", m["erpnext_name"]):
		return m["erpnext_name"]

	if frappe.db.exists("Customer", party_name):
		upsert_mapping(instance_row["name"], "Party", party_name, "Customer", party_name)
		return party_name

	cust = frappe.new_doc("Customer")
	cust.customer_name = party_name
	cust.customer_type = "Company"
	cg = frappe.get_all("Customer Group", fields=["name"], limit=1)
	cust.customer_group = cg[0].name if cg else "All Customer Groups"
	terr = frappe.get_all("Territory", fields=["name"], limit=1)
	cust.territory = terr[0].name if terr else "All Territories"
	cust.insert(ignore_permissions=True)
	upsert_mapping(instance_row["name"], "Party", party_name, "Customer", cust.name)
	return cust.name


def push_payment(instance_row: dict, record: dict) -> dict:
	company = get_company_for_instance(instance_row)
	if not company:
		frappe.throw(_("Company not configured for this Books instance"))

	books_name = record.get("name")
	if not books_name:
		frappe.throw(_("Payment missing name"))

	mapped = get_mapping(instance_row["name"], "Payment", books_name)
	if mapped and frappe.db.exists("Payment Entry", mapped["erpnext_name"]):
		return {"name": mapped["erpnext_name"], "doctype": "Payment Entry"}

	party_name = record.get("party")
	payment_type = record.get("paymentType") or "Receive"
	amount = flt(record.get("amount") or 0)
	if amount <= 0:
		frappe.throw(_("Payment amount must be positive"))

	posting_date = getdate(get_datetime(record.get("date"))) if record.get("date") else today()

	party_type, party = resolve_party_type(instance_row, party_name, company)

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = payment_type
	pe.company = company
	pe.posting_date = posting_date
	pe.party_type = party_type
	pe.party = party

	from erpnext.accounts.party import get_party_account

	party_account = get_party_account(party_type, party, company)

	bank_account = record.get("account") or get_default_company_cash_or_bank_account(company)
	if not bank_account:
		frappe.throw(_("Set a Bank or Cash account on the Company or map accounts in Books"))

	if payment_type == "Receive":
		pe.paid_from = party_account
		pe.paid_to = bank_account
	else:
		pe.paid_from = bank_account
		pe.paid_to = party_account

	pe.paid_amount = amount
	pe.received_amount = amount
	pe.reference_no = record.get("referenceId") or books_name
	pe.reference_date = posting_date

	pe.set_missing_values()
	pe.setup_party_account_field()
	pe.set_missing_values()

	pe.insert(ignore_permissions=True)
	if record.get("submitted") or record.get("docstatus") == 1:
		pe.submit()

	upsert_mapping(instance_row["name"], "Payment", books_name, "Payment Entry", pe.name)
	return {"name": pe.name, "doctype": "Payment Entry"}


def resolve_party_type(instance_row: dict, party_name: str | None, company: str):
	if not party_name:
		frappe.throw(_("Missing party"))

	if frappe.db.exists("Customer", party_name):
		return "Customer", party_name
	if frappe.db.exists("Supplier", party_name):
		return "Supplier", party_name

	m = get_mapping(instance_row["name"], "Party", party_name)
	if m:
		if m["erpnext_doctype"] == "Customer" and frappe.db.exists("Customer", m["erpnext_name"]):
			return "Customer", m["erpnext_name"]
		if m["erpnext_doctype"] == "Supplier" and frappe.db.exists("Supplier", m["erpnext_name"]):
			return "Supplier", m["erpnext_name"]

	cust_name = resolve_party_to_customer(instance_row, party_name, company)
	return "Customer", cust_name


def get_default_company_cash_or_bank_account(company: str) -> str | None:
	for acc_type in ("Cash", "Bank"):
		rows = frappe.get_all(
			"Account",
			filters={"company": company, "account_type": acc_type, "is_group": 0},
			pluck="name",
			order_by="creation asc",
			limit=1,
		)
		if rows:
			return rows[0]
	return None
