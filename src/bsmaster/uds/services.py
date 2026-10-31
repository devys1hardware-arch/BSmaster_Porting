"""UDS 서비스 ID 및 네거티브 응답 코드 (Phase 7).

ISO 14229-1 (UDS) 기준. 원본 BUSMASTER의 `UDS_Protocol` 모듈이
다루는 진단 서비스를 Python 자료형으로 포팅.

- 요청 SID에 0x40을 더하면 긍정 응답 SID.
- 0x7F로 시작하면 부정 응답: [0x7F, 요청SID, NRC].
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ServiceId(Enum):
    """UDS 서비스 ID (ISO 14229-1)."""

    DIAGNOSTIC_SESSION_CONTROL = 0x10
    ECU_RESET = 0x11
    CLEAR_DIAGNOSTIC_INFORMATION = 0x14
    READ_DTC_INFORMATION = 0x19
    READ_DATA_BY_IDENTIFIER = 0x22
    READ_MEMORY_BY_ADDRESS = 0x23
    READ_SCALING_DATA_BY_IDENTIFIER = 0x24
    SECURITY_ACCESS = 0x27
    COMMUNICATION_CONTROL = 0x28
    READ_DATA_BY_PERIODIC_IDENTIFIER = 0x2A
    DYNAMICALLY_DEFINE_DATA_IDENTIFIER = 0x2C
    WRITE_DATA_BY_IDENTIFIER = 0x2E
    INPUT_OUTPUT_CONTROL_BY_IDENTIFIER = 0x2F
    ROUTINE_CONTROL = 0x31
    REQUEST_DOWNLOAD = 0x34
    REQUEST_UPLOAD = 0x35
    TRANSFER_DATA = 0x36
    REQUEST_TRANSFER_EXIT = 0x37
    TESTER_PRESENT = 0x3E
    ACCESS_TIMING_PARAMETER = 0x83
    SECURED_DATA_TRANSMISSION = 0x84
    CONTROL_DTC_SETTING = 0x85
    RESPONSE_ON_EVENT = 0x86
    LINK_CONTROL = 0x87


class NegativeResponseCode(Enum):
    """부정 응답 코드 (NRC, ISO 14229-1 Annex A)."""

    GENERAL_REJECT = 0x10
    SERVICE_NOT_SUPPORTED = 0x11
    SUB_FUNCTION_NOT_SUPPORTED = 0x12
    INCORRECT_MESSAGE_LENGTH_OR_INVALID_FORMAT = 0x13
    RESPONSE_TOO_LONG = 0x14
    BUSY_REPEAT_REQUEST = 0x21
    CONDITIONS_NOT_CORRECT = 0x22
    REQUEST_SEQUENCE_ERROR = 0x24
    FAILURE_PREVENTS_EXECUTION = 0x26
    REQUEST_OUT_OF_RANGE = 0x31
    SECURITY_ACCESS_DENIED = 0x33
    INVALID_KEY = 0x35
    EXCEED_NUMBER_OF_ATTEMPTS = 0x36
    REQUIRED_TIME_DELAY_NOT_EXPIRED = 0x37
    UPLOAD_DOWNLOAD_NOT_ACCEPTED = 0x70
    TRANSFER_DATA_SUSPENDED = 0x71
    GENERAL_PROGRAMMING_FAILURE = 0x72
    WRONG_BLOCK_SEQUENCE_COUNTER = 0x73
    REQUEST_CORRECTLY_RECEIVED_RESPONSE_PENDING = 0x78
    SUB_FUNCTION_NOT_SUPPORTED_IN_ACTIVE_SESSION = 0x7E
    SERVICE_NOT_SUPPORTED_IN_ACTIVE_SESSION = 0x7F
    RPM_TOO_HIGH = 0x81
    RPM_TOO_LOW = 0x82
    ENGINE_IS_RUNNING = 0x83
    ENGINE_IS_NOT_RUNNING = 0x84
    VEHICLE_SPEED_TOO_HIGH = 0x88
    VEHICLE_SPEED_TOO_LOW = 0x89
    VOLTAGE_TOO_HIGH = 0x92
    VOLTAGE_TOO_LOW = 0x93


POSITIVE_RESPONSE_OFFSET = 0x40
NEGATIVE_RESPONSE_SID = 0x7F


def positive_response_sid(request_sid: int) -> int:
    """요청 SID → 긍정 응답 SID."""
    return (request_sid + POSITIVE_RESPONSE_OFFSET) & 0xFF


@dataclass(frozen=True)
class UdsResponse:
    """파싱된 UDS 응답."""

    service_id: int          # 요청 SID (긍정 응답이면 -0x40 한 값)
    positive: bool
    data: bytes = b""        # 긍정 응답의 SID 이후 바이트
    nrc: NegativeResponseCode | None = None


def parse_response(payload: bytes) -> UdsResponse:
    """UDS 응답 페이로드를 파싱. ISO-TP 재조립 이후의 바이트를 입력."""
    if not payload:
        raise ValueError("빈 UDS 페이로드")
    sid = payload[0]
    if sid == NEGATIVE_RESPONSE_SID:
        if len(payload) < 3:
            raise ValueError("부정 응답 길이가 짧습니다")
        req_sid = payload[1]
        try:
            nrc = NegativeResponseCode(payload[2])
        except ValueError:
            nrc = None
        return UdsResponse(service_id=req_sid, positive=False, nrc=nrc)
    if sid & 0x40:
        return UdsResponse(service_id=sid - POSITIVE_RESPONSE_OFFSET,
                           positive=True, data=payload[1:])
    raise ValueError(f"알 수 없는 응답 SID: {sid:#x}")


def build_request(service: ServiceId | int, params: bytes = b"") -> bytes:
    """UDS 요청 페이로드 조립 (SID + 파라미터)."""
    sid = service.value if isinstance(service, ServiceId) else service
    return bytes([sid]) + params
