## Books Integration

Frappe app **`books_integration`** connects **Frappe Books** (desktop) to **ERPNext**. The Books client calls a fixed set of authenticated API methods under `books_integration.api` and `books_integration.api.sync`. This app implements those endpoints, maps documents between Books and ERPNext, and queues outbound updates so accounting data stays aligned on both sides.

### What it does

- **Registration & settings** — Registers each Books instance (`device_id`) against a site user and company, and exposes sync options (what to push, pull, or sync both ways).
- **Pull** — Serves pending ERPNext changes (and optional master data) for Books to import.
- **Push** — Accepts submitted documents from Books (for example sales invoices and payments), converts them to ERPNext doctypes, and returns success or structured failure for each record.
- **Status** — Receives acknowledgements and name mappings after Books applies pulled documents.

ERPNext-side changes that should appear in Books are recorded via **Books Sync Queue** using `doc_events` in `hooks.py`.

### Requirements

- **ERPNext** is required (`required_apps` lists `erpnext`).

### Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app /path/to/books_integration --branch version-16
bench --site your.site migrate
bench --site your.site install-app books_integration
```

### Site configuration

1. Open **Books Sync Settings** (Single): enable sync, set **Default Company** if needed, and choose per-entity directions (push / pull / bidirectional).
2. Create a **User** dedicated to Books with access to the target **Company** and the roles your flows need.
3. Create **API Key** and **API Secret** for that user (User → API Access).
4. In **Frappe Books** → ERPNext sync: set the **API base URL** to `https://your.site` (no trailing slash), set the token as `api_key:api_secret`, enable ERPNext sync in Accounting Settings, and complete instance registration.

### Security

- Endpoints use standard Frappe **token** authentication (`Authorization: token …`).
- **Books Instance** links a Books `device_id` to a **User** and **Company**; restrict the API user to the companies and doctypes they need.
- Use **Books Sync Log** (and server error logs) to audit failed pushes.

### API surface

| Method | Role |
|--------|------|
| `books_integration.api.register_instance` | Register or refresh a Books instance (`device_id` → Books Instance) |
| `books_integration.api.sync_settings` | Return connector version and sync flags |
| `books_integration.api.sync.get_pending_docs` | Pull: queued docs and optional master bundle |
| `books_integration.api.sync.sync_transactions` | Push: transactional documents from Books |
| `books_integration.api.sync.update_status` | Acknowledge pulls and record name mappings |

### Contributing

Formatting and linting use **pre-commit** (Ruff and related hooks):

```bash
cd apps/books_integration
pre-commit install
pre-commit run --all-files
```

### License

MIT
