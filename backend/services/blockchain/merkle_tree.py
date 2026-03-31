"""
Off-chain Merkle Tree + On-chain Root — 비용 효율적 거래 증명.

개별 신호 해시로 Merkle Tree를 오프체인에서 구성하고,
Merkle root만 Solana에 기록. 개별 신호는 Merkle proof로 검증 가능.

비용: 0.000005 SOL/Stop (TX 수수료만, 계정 rent 없음)
검증: root 대비 개별 신호의 Merkle proof 검증
"""

import hashlib
import json
import math


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def compute_leaf(signal_data: dict) -> bytes:
    """신호 데이터 → 32바이트 Merkle 리프 (SHA256)"""
    canonical = json.dumps(signal_data, sort_keys=True, separators=(",", ":"))
    return _sha256(canonical.encode())


def build_merkle_tree(leaves: list[bytes]) -> tuple[bytes, list[list[bytes]]]:
    """
    리프 목록에서 Merkle Tree를 구성.

    Returns:
        (root, layers) — root는 32바이트, layers는 각 레벨의 해시 리스트
    """
    if not leaves:
        return b"\x00" * 32, []

    n = len(leaves)
    depth = max(1, math.ceil(math.log2(n))) if n > 1 else 1
    padded_size = 2 ** depth
    padded = list(leaves) + [b"\x00" * 32] * (padded_size - n)

    layers = [padded]
    current = padded

    while len(current) > 1:
        next_layer = []
        for i in range(0, len(current), 2):
            combined = current[i] + current[i + 1]
            next_layer.append(_sha256(combined))
        layers.append(next_layer)
        current = next_layer

    return current[0], layers


def get_merkle_proof(layers: list[list[bytes]], leaf_index: int) -> list[bytes]:
    """특정 리프의 Merkle proof 생성."""
    if not layers:
        return []

    proof = []
    idx = leaf_index

    for layer in layers[:-1]:
        if idx >= len(layer):
            break
        sibling_idx = idx ^ 1
        if sibling_idx < len(layer):
            proof.append(layer[sibling_idx])
        idx //= 2

    return proof


def verify_merkle_proof(leaf: bytes, proof: list[bytes], root: bytes, leaf_index: int) -> bool:
    """Merkle proof를 검증하여 리프가 root에 포함되는지 확인."""
    current = leaf
    idx = leaf_index

    for sibling in proof:
        if idx % 2 == 0:
            current = _sha256(current + sibling)
        else:
            current = _sha256(sibling + current)
        idx //= 2

    return current == root


def build_trade_merkle(trades: list[dict]) -> dict:
    """
    거래 목록에서 Merkle Tree를 구성하고 증명 데이터를 반환.

    Returns:
        {
            "root": "hex string",
            "leaf_count": N,
            "leaves": ["hex", ...],
            "proofs": {0: ["hex", ...], 1: ["hex", ...], ...},
        }
    """
    leaves = [compute_leaf(t) for t in trades]
    root, layers = build_merkle_tree(leaves)

    proofs = {}
    for i in range(len(leaves)):
        proof = get_merkle_proof(layers, i)
        proofs[i] = [p.hex() for p in proof]

    return {
        "root": root.hex(),
        "leaf_count": len(trades),
        "leaves": [l.hex() for l in leaves],
        "proofs": proofs,
    }
