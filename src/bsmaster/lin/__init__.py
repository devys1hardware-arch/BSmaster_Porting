"""LIN (ISO 17987) 프로토콜 지원 (Phase 11).

원본: `Kernel/BusmasterDriverInterface/` LIN 드라이버 인터페이스의
`STLIN_MSG` 자료형.

- `frame`: LIN 프레임, 보호 ID 패리티, 체크섬 (클래식/향상)
"""

from bsmaster.lin.frame import (
    DIAG_MASTER_REQ_ID,
    DIAG_SLAVE_RESP_ID,
    ChecksumType,
    LinFrame,
    auto_checksum_type,
    calc_checksum,
    protected_id,
    verify_parity,
)

__all__ = [
    "DIAG_MASTER_REQ_ID",
    "DIAG_SLAVE_RESP_ID",
    "ChecksumType",
    "LinFrame",
    "auto_checksum_type",
    "calc_checksum",
    "protected_id",
    "verify_parity",
]
