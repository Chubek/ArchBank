"""L3/CIR value-object invariants: BitVec identity, canonical doc round-trip."""
from __future__ import annotations

from xtrakt.cir import BitVec, InstructionRecord, bv, ones, is_bv


def test_bitvec_identity_width_value():
    assert BitVec(8, 0x73) == BitVec(8, 0x73)
    assert BitVec(8, 0x73) != BitVec(16, 0x73)
    assert BitVec(8, 0x173).value == 0x73   # masked to width


def test_bitvec_hex_round_trip():
    for w, v in [(8, 0x73), (13, 0x1fff), (32, 0xDEADBEEF), (0, 0)]:
        b = BitVec(w, v)
        assert BitVec.from_doc(b.to_doc()) == b


def test_bitvec_from_bin_preserves_width():
    assert BitVec.from_bin("10111") == BitVec(5, 0x17)


def test_ones_and_is_bv():
    assert ones(4) == 0xF and ones(0) == 0
    assert is_bv(bv(4, 0xA)) and not is_bv(4)


def test_record_doc_round_trip_preserves_bitvecs():
    r = InstructionRecord(
        arch="riscv", mnemonic="addi", isa_ext="i", encoding_class="I",
        encoding_function="(define-encoding (addi) 32 (cat (const #x17) (field)))",
        decode_mask=bv(32, 0x707F), decode_match=bv(32, 0x13),
        fields={"imm": bv(12, 0xFFF), "rd": 5, "rs1": 6},
        source_banks=["riscv-opcodes"],
    )
    assert InstructionRecord.from_doc(r.to_doc()) == r


def test_record_operand_signature_stable():
    r = InstructionRecord(arch="a", mnemonic="m", isa_ext="", encoding_class="c",
                          encoding_function="", fields={"x": bv(4, 1), "y": 2})
    sig = r.operand_signature
    assert sig == r.operand_signature          # deterministic
    assert "x:bv4" in sig and "y:int" in sig


def test_record_key_is_dedup_key():
    r1 = InstructionRecord(arch="a", mnemonic="m", isa_ext="i", encoding_class="c",
                           encoding_function="", fields={"x": bv(4, 1)})
    r2 = r1.clone()
    assert r1.key == r2.key
