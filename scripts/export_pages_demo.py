"""Export a deterministic, database-free InvoiceCraft demo for GitHub Pages."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from functools import partial
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace as NS
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# These modules have no application startup, environment or database side effects.
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.i18n import catalog, translate
from app.models import compute_totals, precision
from app.services.invoicing import (
    CURRENCIES,
    client_data,
    default_form,
    issuer_data,
    make_document,
)

TODAY = date(2026, 10, 28)
NOTICE = "完整应用功能 / Available in the full app"
SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£", "CNY": "¥", "JPY": "¥"}


def money(value, currency="USD"):
    amount = Decimal(str(value)).quantize(precision(currency), rounding=ROUND_HALF_UP)
    digits = 0 if currency == "JPY" else 2
    return f"{SYMBOLS.get(currency, currency + ' ')}{amount:,.{digits}f}"


def overdue(invoice):
    return invoice.status == "sent" and invoice.due_date and invoice.due_date < TODAY


class DemoURL:
    def __init__(self, path):
        self.path = urlsplit(path).path
        self.query = urlsplit(path).query

    def include_query_params(self, **kwargs):
        values = dict(parse_qsl(self.query))
        values.update(kwargs)
        return self.path + "?" + urlencode(values)

    def __str__(self):
        return self.path + ("?" + self.query if self.query else "")


def sample_data():
    user = NS(
        id=1,
        name="Orbit Studio",
        email="hello@orbit.example",
        language="zh-CN",
        issuer_name="Orbit Studio / 轨道设计",
        issuer_email="billing@orbit.example",
        issuer_address="88 Example Lane\nDemo City · Fictional address",
        payment_instructions="演示付款说明 · 请勿转账\nDemo payment instructions — do not send money.",
        default_currency="USD",
        default_tax_rate="6",
        document_language="zh-CN",
        is_pro=True,
    )
    client_specs = [
        (
            "林舟",
            "Northstar Labs",
            "lin@northstar.example",
            "12 Example Street\nDemo City",
        ),
        (
            "Maya Chen",
            "Paper Moon Press",
            "maya@papermoon.example",
            "24 Sample Avenue\nDemo City",
        ),
        (
            "高橋 凛",
            "Hikari Works",
            "rin@hikari.example",
            "36 Fictional Road\nDemo City",
        ),
        (
            "Alex Rivera",
            "Field Notes Co.",
            "alex@fieldnotes.example",
            "48 Placeholder Way\nDemo City",
        ),
    ]
    clients = [
        NS(
            id=i,
            user_id=1,
            name=n,
            company=c,
            email=e,
            address=a,
            notes="合成客户资料 / Synthetic client profile",
            created_at=datetime(2026, 1, i, tzinfo=UTC),
        )
        for i, (n, c, e, a) in enumerate(client_specs, 1)
    ]
    specs = [
        (
            1,
            1,
            "sent",
            "USD",
            "6",
            "2026-10-12",
            "2026-10-26",
            "zh-CN",
            [
                ("品牌策略与视觉系统 / Brand identity", "1", "2400"),
                ("设计工作坊 / Design workshop", "2.5", "180"),
            ],
        ),
        (
            2,
            2,
            "paid",
            "EUR",
            "0",
            "2026-09-18",
            "2026-10-18",
            "en",
            [
                ("Editorial design · Autumn issue", "1", "1850"),
                ("Print preparation", "3", "85.50"),
            ],
        ),
        (
            3,
            3,
            "sent",
            "JPY",
            "10",
            "2026-10-20",
            "2026-11-19",
            "en",
            [
                ("Packaging design", "1", "120000"),
                ("Production consultation", "2.5", "6500"),
            ],
        ),
        (
            4,
            1,
            "draft",
            "CNY",
            "6",
            "2026-10-28",
            "2026-11-11",
            "zh-CN",
            [("产品界面设计", "8", "680"), ("交互原型", "1", "1800.125")],
        ),
        (
            5,
            4,
            "paid",
            "USD",
            "8.25",
            "2026-09-02",
            "2026-10-02",
            "en",
            [("Website direction", "1", "3200"), ("Content session", "2", "175")],
        ),
        (
            6,
            2,
            "draft",
            "USD",
            "5",
            "2026-10-27",
            "2026-11-10",
            "en",
            [
                ("Winter campaign concept", "1.25", "950.125"),
                ("Asset preparation", "3", "110.50"),
            ],
        ),
    ]
    invoices, all_items = [], {}
    for ident, client_id, status, currency, tax, issued, due, lang, rows in specs:
        invoice = NS(
            id=ident,
            user_id=1,
            client_id=client_id,
            number=f"INV-2026-{ident:03d}",
            status=status,
            currency=currency,
            tax_rate_decimal=tax,
            tax_rate=float(tax),
            document_language=lang,
            issue_date=date.fromisoformat(issued),
            due_date=date.fromisoformat(due),
            notes="感谢合作，期待下一次创作。\nThank you for the collaboration.",
            payment_instructions=user.payment_instructions,
            share_token=f"demo-{ident}",
            created_at=datetime.fromisoformat(issued).replace(tzinfo=UTC),
        )
        invoices.append(invoice)
        all_items[ident] = [
            NS(
                description=d,
                quantity_decimal=q,
                unit_price_decimal=p,
                quantity=q,
                unit_price=p,
            )
            for d, q, p in rows
        ]
    return user, clients, invoices, all_items


def summaries(rows):
    grouped = {}
    for row in rows:
        invoice = row["invoice"]
        group = grouped.setdefault(
            invoice.currency,
            {
                "currency": invoice.currency,
                "outstanding": Decimal(0),
                "overdue": Decimal(0),
                "paid": Decimal(0),
            },
        )
        if invoice.status == "paid":
            group["paid"] += row["totals"]["total"]
        if invoice.status == "sent":
            group["outstanding"] += row["totals"]["total"]
            if overdue(invoice):
                group["overdue"] += row["totals"]["total"]
    return [grouped[key] for key in sorted(grouped)]


class StaticHTML(HTMLParser):
    """Rewrite URLs and render every backend mutation inert even without JavaScript."""

    def __init__(self, base_path, page, invoice_tokens):
        super().__init__(convert_charrefs=False)
        self.base = base_path
        self.page = page
        self.tokens = invoice_tokens
        self.output = []
        self.form = None
        self.read_only = False

    def url(self, value):
        parts = urlsplit(value)
        if parts.scheme or parts.netloc or not parts.path.startswith("/"):
            return value
        path = parts.path
        if path.startswith(self.base) and self.base != "/":
            path = "/" + path[len(self.base) :]
        if path.startswith("/i/"):
            path = f"/invoices/{self.tokens[path.rsplit('/', 1)[1]]}"
        query = [
            (key, self.url(val) if key == "return_to" else val)
            for key, val in parse_qsl(parts.query, keep_blank_values=True)
        ]
        if not path.startswith("/static/") and not path.endswith("/"):
            path += "/"
        return urlunsplit(
            ("", "", self.base + path.lstrip("/"), urlencode(query), parts.fragment)
        )

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.form = attrs.get("method", "get").lower()
            self.read_only = "settings-form" in attrs.get(
                "class", ""
            ) or "client-form" in attrs.get("class", "")
            if self.form == "post":
                attrs.update(
                    method="dialog",
                    action="#demo-banner",
                    onsubmit="return false",
                    **{"data-demo-form": ""},
                )
        for key in ("href", "src", "action"):
            if key in attrs:
                value = attrs[key]
                if key == "href" and (
                    re.search(r"/invoices/\d+/pdf$", urlsplit(value).path)
                    or value in ("/login", "/signup")
                ):
                    attrs.update(
                        href="#demo-banner",
                        **{
                            "aria-disabled": "true",
                            "data-demo-disabled": "",
                            "title": NOTICE,
                        },
                    )
                else:
                    attrs[key] = self.url(value)
        if "data-copy" in attrs:
            attrs["data-copy"] = self.url(self.page)
            attrs["data-demo-copy"] = ""
        if tag == "input" and attrs.get("name") == "return_to":
            attrs["value"] = self.url(attrs.get("value", "/invoices"))
        if (
            tag == "button"
            and self.form == "post"
            and attrs.get("type", "submit") == "submit"
        ):
            attrs.update(
                type="button", disabled=None, title=NOTICE, **{"data-demo-disabled": ""}
            )
        if tag == "button" and "data-open-dialog" in attrs:
            attrs.update(disabled=None, title=NOTICE, **{"data-demo-disabled": ""})
        if self.read_only and tag in ("input", "textarea"):
            attrs["readonly"] = None
        if self.read_only and tag == "select":
            attrs["disabled"] = None
        self.output.append(
            "<"
            + tag
            + "".join(
                " "
                + key
                + (
                    f'="{html.escape(str(value), quote=True)}"'
                    if value is not None
                    else ""
                )
                for key, value in attrs.items()
            )
            + ">"
        )

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.output.append(f"</{tag}>")
        if tag == "form":
            self.form, self.read_only = None, False

    def handle_data(self, data):
        self.output.append(data)

    def handle_entityref(self, name):
        self.output.append(f"&{name};")

    def handle_charref(self, name):
        self.output.append(f"&#{name};")

    def handle_decl(self, decl):
        self.output.append(f"<!{decl}>")

    def handle_comment(self, data):
        self.output.append(f"<!--{data}-->")


def export(output, base_path):
    user, clients, invoices, items = sample_data()
    by_id = {client.id: client for client in clients}
    rows = [
        {
            "invoice": invoice,
            "client": by_id[invoice.client_id],
            "totals": compute_totals(
                items[invoice.id], invoice.tax_rate_decimal, invoice.currency
            ),
        }
        for invoice in reversed(invoices)
    ]
    demo_data = {
        "basePath": base_path,
        "today": TODAY.isoformat(),
        "catalogs": {lang: catalog(lang) for lang in ("zh-CN", "en")},
        "issuer": issuer_data(user),
        "paymentInstructions": user.payment_instructions,
        "clients": [dict(id=c.id, **client_data(c)) for c in clients],
        "invoices": [
            {
                "id": i.id,
                "clientId": i.client_id,
                "currency": i.currency,
                "status": "overdue" if overdue(i) else i.status,
                "issueDate": str(i.issue_date),
                "dueDate": str(i.due_date),
            }
            for i in invoices
        ],
    }
    env = Environment(
        loader=FileSystemLoader(ROOT / "app/templates"),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["money"] = money
    env.globals.update(
        app_name="InvoiceCraft",
        currencies=CURRENCIES,
        translate=translate,
        is_overdue=overdue,
    )
    common = {
        "user": user,
        "prefs": user,
        "lang": "zh-CN",
        "t": partial(translate, lang="zh-CN"),
        "ui_strings": catalog("zh-CN"),
        "errors": {},
        "error": None,
        "flashes": [],
        "demo_mode": True,
        "demo_data": demo_data,
        "base_url": "",
        "return_to": "/invoices",
        "page": 1,
        "pages": 1,
        "total": len(rows),
        "q": "",
        "invoice": None,
        "client": None,
    }
    pages = []
    stats = NS(
        invoice_count=len(invoices),
        draft_count=sum(i.status == "draft" for i in invoices),
        overdue_count=sum(bool(overdue(i)) for i in invoices),
    )
    dashboard = {
        "stats": stats,
        "summaries": summaries(rows),
        "recent": rows,
        "attention": [
            r for r in rows if r["invoice"].status == "draft" or overdue(r["invoice"])
        ],
    }
    pages += [
        ("/", "dashboard.html", dashboard),
        ("/dashboard", "dashboard.html", dashboard),
    ]
    counts = dict(
        all=len(rows),
        **{
            s: sum(("overdue" if overdue(i) else i.status) == s for i in invoices)
            for s in ("draft", "sent", "overdue", "paid")
        },
    )
    pages.append(
        (
            "/invoices",
            "invoices/list.html",
            {
                "rows": rows,
                "clients": by_id,
                "counts": counts,
                "filters": NS(
                    status="all", q="", currency="", client_id="", sort="newest"
                ),
            },
        )
    )
    for invoice in invoices:
        doc = make_document(
            invoice,
            items[invoice.id],
            issuer_data(user),
            client_data(by_id[invoice.client_id]),
        )
        context = {"invoice": invoice, "client": by_id[invoice.client_id], "doc": doc}
        pages.append((f"/invoices/{invoice.id}", "invoices/detail.html", context))
        pages.append(
            (
                f"/invoices/{invoice.id}/edit",
                "invoices/edit.html",
                dict(
                    context,
                    clients=clients,
                    form=default_form(user, invoice, items[invoice.id]),
                ),
            )
        )
    new_form = default_form(user)
    new_form["issue_date"] = TODAY.isoformat()
    new_form["due_date"] = date(2026, 11, 11).isoformat()
    new_form["items"] = [
        {
            "description": "示例设计服务 / Sample design services",
            "quantity": "1",
            "unit_price": "500",
        }
    ]
    pages.append(
        ("/invoices/new", "invoices/new.html", {"form": new_form, "clients": clients})
    )
    client_rows = [
        {"client": c, "invoice_count": sum(i.client_id == c.id for i in invoices)}
        for c in clients
    ]
    pages.append(
        ("/clients", "clients/list.html", {"rows": client_rows, "total": len(clients)})
    )
    pages.append(("/clients/new", "clients/new.html", {}))
    for client in clients:
        related = [r for r in rows if r["invoice"].client_id == client.id]
        pages.append(
            (
                f"/clients/{client.id}",
                "clients/detail.html",
                {"client": client, "rows": related, "summaries": summaries(related)},
            )
        )
        pages.append(
            (f"/clients/{client.id}/edit", "clients/edit.html", {"client": client})
        )
    pages.append(("/settings", "settings.html", {}))
    output.mkdir(parents=True, exist_ok=True)
    for path, template, extra in pages:
        context = dict(common, request=NS(url=DemoURL(path)))
        context.update(extra)
        markup = env.get_template(template).render(**context)
        parser = StaticHTML(base_path, path, {i.share_token: i.id for i in invoices})
        parser.feed(markup)
        destination = output / path.strip("/") / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        rendered = re.sub(r"(?m)^[ \t]+$", "", "".join(parser.output))
        destination.write_text(rendered, encoding="utf-8")
    static = output / "static"
    static.mkdir(exist_ok=True)
    for name in (
        "style.css",
        "pages.css",
        "demo.css",
        "demo.js",
        "cassette.js",
        "favicon.svg",
    ):
        text = (ROOT / "app/static" / name).read_text()
        if name.endswith(".css"):
            text = text.replace("url('/static/", "url('./").replace(
                'url("/static/', 'url("./'
            )
        (static / name).write_text(text)
    # Only browser UI fonts and their source/license notices; omit the PDF CJK font.
    for folder, names in {
        "fonts": [
            "IBMPlexMono-Regular.ttf",
            "IBMPlexMono-SemiBold.ttf",
            "VT323-Regular.ttf",
            "OFL-IBM-Plex.txt",
            "OFL-VT323.txt",
            "IBM-PLEX-SOURCE.md",
            "VT323-SOURCE.md",
        ],
        "hardware": ["dial-face.webp", "fastener.webp", "README.md"],
        "textures": ["cassette-shell.webp", "README.md"],
    }.items():
        (static / folder).mkdir(exist_ok=True)
        for name in names:
            shutil.copyfile(ROOT / "app/static" / folder / name, static / folder / name)
    (output / ".nojekyll").write_text("")
    print(f"Exported {len(pages)} static pages to {output}; base path {base_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="docs/demo",
        help="Output directory (relative to repository root)",
    )
    parser.add_argument(
        "--base-path",
        default="/invoicecraft/",
        help="Deployment path, including leading/trailing slash",
    )
    args = parser.parse_args()
    base_path = (
        "/" + args.base_path.strip("/") + "/" if args.base_path.strip("/") else "/"
    )
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    export(output, base_path)


if __name__ == "__main__":
    main()
