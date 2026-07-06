from __future__ import annotations

import re

from xtrakt.parsers import PARSERS, parser_for
from xtrakt.parsers.asmjit_json import _layout_from_opstring


def test_manifest_banks_have_registered_parsers():
    text = open("BANKS.yaml", encoding="utf-8").read()
    bank_ids = re.findall(r'^- id: "([^"]+)"', text, re.M)

    missing = [bank_id for bank_id in bank_ids if bank_id not in PARSERS]
    fallbacks = [
        bank_id for bank_id in bank_ids
        if parser_for(bank_id).__name__ == "NotImplementedParser"
    ]

    assert missing == []
    assert fallbacks == []


def test_asmjit_slice_tokens_preserve_layout_width():
    layout = _layout_from_opstring("0|relS[1:0]|10000|relS[20:2]|Rd", 5)
    assert sum(segment.width for segment in layout) == 32
