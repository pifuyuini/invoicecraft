"""Verify text survives in the delivered PDF, not just in an HTML response."""

import re
import zlib
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.pdf import render_invoice_pdf, settings


def _document(language="zh-CN", currency="CNY"):
    return {
        "number": "INV-0100", "language": language, "currency": currency,
        "status": "draft", "issue_date": date(2026, 9, 22), "due_date": None,
        "issuer": {"name": "拾光工作室", "email": "studio@example.com", "address": "上海市静安区"},
        "client": {"name": "陈晓", "company": "青山文化", "email": "client@example.com", "address": "杭州市西湖区"},
        "items": [{"description": "设计服务", "quantity": Decimal(2), "unit_price": Decimal("100.25"), "amount": Decimal("200.50")}],
        "totals": {"subtotal": Decimal("200.50"), "tax": Decimal("12.03"), "total": Decimal("212.53")},
        "tax_rate": Decimal(6), "notes": "谢谢信任。", "payment_instructions": "付款时请注明账单编号。",
    }


def _pdf_text(pdf):
    """Read the embedded Unicode map and text streams using the standard library."""
    streams = []
    for match in re.finditer(rb"<<(.*?)>>\s*stream\r?\n(.*?)\r?\nendstream", pdf, re.DOTALL):
        header, stream = match.groups()
        streams.append(zlib.decompress(stream) if b"/FlateDecode" in header else stream)
    cmap = {}
    for stream in streams:
        if b"beginbfchar" in stream:
            for source, target in re.findall(rb"<([0-9A-F]+)>\s+<([0-9A-F]+)>", stream):
                cmap[int(source, 16)] = bytes.fromhex(target.decode()).decode("utf-16-be")
    text = []
    escapes = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}
    for stream in streams:
        if b"BT" not in stream or b"Tj" not in stream:
            continue
        for literal in re.findall(rb"\(((?:\\.|[^\\)])*)\)\s*Tj", stream, re.DOTALL):
            def unescape(match):
                code = match.group(1)
                return bytes([int(code, 8)]) if code[:1].isdigit() else escapes.get(code, code)
            raw = re.sub(rb"\\([0-7]{1,3}|.)", unescape, literal, flags=re.DOTALL)
            text.append("".join(cmap.get(int.from_bytes(raw[i:i + 2], "big"), "") for i in range(0, len(raw), 2)))
    return "\n".join(text)


def _render(doc):
    return render_invoice_pdf(None, [], SimpleNamespace(is_pro=False), None, {}, doc=doc)


@pytest.mark.parametrize("language,title", [("zh-CN", "账单"), ("en", "INVOICE")])
def test_pdf_embeds_chinese_and_uses_document_snapshot(monkeypatch, language, title):
    monkeypatch.setattr(settings, "billing_enabled", False)
    document = _document(language)
    pdf = _render(document)
    text = _pdf_text(pdf)
    assert pdf.startswith(b"%PDF-") and b"/FontFile2" in pdf
    for expected in (title, "拾光工作室", "陈晓", "设计服务", "付款时请注明账单编号。", "CNY 212.53"):
        assert expected in text
    assert "Created with InvoiceCraft" not in text
    assert "使用 InvoiceCraft 制作" not in text
    # The document, not any stale model or client data, drives the export.
    document["issuer"]["name"] = "归档时的开票方"
    document["items"][0]["amount"] = Decimal("199.99")
    text = _pdf_text(_render(document))
    assert "归档时的开票方" in text and "199.99" in text
    assert "200.50" in text  # supplied subtotal remains authoritative


def test_pdf_jpy_has_no_fractional_digits(monkeypatch):
    monkeypatch.setattr(settings, "billing_enabled", False)
    doc = _document("en", "JPY")
    doc["items"][0].update(unit_price=Decimal(125), amount=Decimal(250))
    doc["totals"].update(subtotal=Decimal(250), tax=Decimal(15), total=Decimal(265))
    text = _pdf_text(_render(doc))
    assert "JPY 265" in text and "265.00" not in text and "125.00" not in text


def test_pdf_long_description_notes_and_headers_survive_page_breaks(monkeypatch):
    monkeypatch.setattr(settings, "billing_enabled", False)
    doc = _document()
    doc["items"][0]["description"] = "完整的中文项目描述与 English detail。" * 420 + "DescriptionWithoutAnySpaces" * 50 + "描述结尾标记"
    doc["items"].extend([
        {"description": f"第 {index} 个项目", "quantity": 1, "unit_price": 10, "amount": 10}
        for index in range(45)
    ])
    doc["notes"] = "逐项验收后交付所有源文件，保留完整备注。\n" * 120 + "备注结尾标记"
    pdf = _render(doc)
    text = _pdf_text(pdf)
    compact = text.replace("\n", "")
    assert "描述结尾标记" in compact and "备注结尾标记" in compact
    # Ignore repeated running furniture when rejoining a word across pages.
    body = "".join(
        line for line in text.splitlines()
        if line not in {"INVOICECRAFT", "INV-0100", "项目描述", "数量", "单价", "金额"}
        and not re.fullmatch(r"页 \d+", line)
    )
    assert body.count("DescriptionWithoutAnySpaces") == 50
    assert "第 44 个项目" in text
    assert "付款时请注明账单编号。" in text
    assert text.count("项目描述") > 2
    assert len(re.findall(rb"/Type /Page\b", pdf)) > 3


def test_pdf_optional_paid_feature_watermark(monkeypatch):
    monkeypatch.setattr(settings, "billing_enabled", True)
    assert "Created with InvoiceCraft" in _pdf_text(_render(_document("en")))
