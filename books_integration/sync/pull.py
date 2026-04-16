import json

import frappe
from frappe.utils import cint, flt


def get_item_rates() -> dict:
	if not frappe.db.exists("Books Item Settings", "Books Item Settings"):
		return {}
	pl = frappe.db.get_single_value("Books Item Settings", "price_list")
	if not pl:
		return {}
	rates = {}
	for row in frappe.get_all(
		"Item Price",
		filters={"price_list": pl},
		fields=["item_code", "price_list_rate"],
	):
		rates[row.item_code] = flt(row.price_list_rate)
	return rates


def queue_row_to_books_payload(row: dict) -> dict:
	data = json.loads(row.get("document_json") or "{}")
	if not data.get("doctype"):
		data["doctype"] = row.get("books_doctype")
	data.setdefault("erpnextDocName", data.get("name"))
	data.setdefault("fbooksDocName", data.get("name"))
	return data


def build_initial_master_docs(company: str, limit: int = 200) -> list[dict]:
	out: list[dict] = []
	rates = get_item_rates()
	items = frappe.get_all(
		"Item",
		filters={"disabled": 0},
		fields=["name", "item_code", "item_name", "stock_uom", "item_group", "description"],
		limit=limit,
	)
	for it in items:
		out.append(item_row_to_books(it, rates))

	customers = frappe.get_all(
		"Customer",
		filters={"disabled": 0},
		fields=["name", "customer_name"],
		limit=min(limit, 100),
	)
	for cu in customers:
		out.append(customer_to_party_books(cu))

	return out


def item_row_to_books(it: dict, rates: dict | None = None) -> dict:
	code = it.get("name") or it.get("item_code")
	rates = rates if rates is not None else get_item_rates()
	rate = flt(rates.get(code) or rates.get(it.get("item_code")) or 0)
	return {
		"doctype": "Item",
		"name": code,
		"itemCode": it.get("item_code") or code,
		"itemGroup": it.get("item_group") or "All Item Groups",
		"unit": it.get("stock_uom") or "Nos",
		"for": "Both",
		"itemType": "Product",
		"description": it.get("description") or "",
		"rate": rate,
		"datafromErp": True,
		"erpnextDocName": code,
		"fbooksDocName": code,
	}


def customer_to_party_books(cu: dict) -> dict:
	name = cu.get("name")
	return {
		"doctype": "Party",
		"name": name,
		"role": "Customer",
		"erpnextDocName": name,
		"fbooksDocName": name,
	}


def sales_invoice_to_books(si_name: str) -> dict | None:
	if not frappe.db.exists("Sales Invoice", si_name):
		return None
	si = frappe.get_doc("Sales Invoice", si_name)
	items = []
	for row in si.items:
		items.append(
			{
				"item": row.item_code,
				"quantity": flt(row.qty),
				"rate": flt(row.rate),
				"amount": flt(row.amount),
				"unit": row.uom,
				"account": row.income_account,
			}
		)
	return {
		"doctype": "SalesInvoice",
		"name": si.name,
		"party": si.customer,
		"date": str(si.posting_date),
		"items": items,
		"submitted": cint(si.docstatus) == 1,
		"docstatus": si.docstatus,
		"erpnextDocName": si.name,
		"fbooksDocName": si.name,
	}
