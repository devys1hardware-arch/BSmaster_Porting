# 포팅 계획 (PORTING PLAN)

원본: [rbei-etas/busmaster](https://github.com/rbei-etas/busmaster) (C++/MFC, 약 50.8만 줄, Sources/ 실측)
목표: Python 3.11+ + PySide6 로 핵심부터 단계별 포팅.

> 상세 구조·클래스·메소드 분석: [ARCHITECTURE.md](ARCHITECTURE.md)

> 원칙: 전체 1:1 이식은 하지 않는다. Windows MFC GUI와 벤더 하드웨어
> 드라이버 DLL은 이식 대상에서 제외하고, 포터블한 코어와 Qt 기반 GUI를
> 새로 구성한다.

## 진행 현황

- **2026-10-31 — Phase 0 완료**: 프로젝트 뼈대, 패키지 구조, `CanFrame`/`CanError` 포팅, DBC/logconv 스켈레톤, PySide6 메인 윈도우 틀, 테스트 9개 통과 + GUI 스모크 테스트 통과. `main` 브랜치에 푸시됨.
- **2026-10-31 — Phase 1 완료**: `sSIGNALS`/`sMESSAGE`/`SMSGENTRY` → `DbSignal`/`DbMessage`/`MessageDatabase`, 시그널 인코딩(`vSetSignalValue`/`un64GetBitMask`) → `encode_signal`/`decode_signal` 포팅. 테스트 23개 통과 (인코딩 벡터·퍼즈 라운드트립 포함).
- **2026-10-31 — Phase 2 완료**: DBC 파서 (`BO_`/`SG_`/`VAL_`/`SIG_VALTYPE_`/`CM_`/`BU_`, Motorola 시작비트 변환 포함) → `DbcDatabase`. 파싱→인코딩 통합 테스트 포함, 34개 테스트 통과.
- **2026-10-31 — Phase 3 완료**: 로그 컨버터 — ASC 리더/라이터, BLF 리더/라이터 (원본 `BlfFormat.h` 구조체 레이아웃·zlib 컨테이너·CAN_MESSAGE 그대로 재현). 41개 테스트 통과.
- **2026-10-31 — Phase 4 완료**: PySide6 GUI 확장 — 메시지 윈도우 도크, DBC 시그널 해석 도크, Tx 전송 패널, DBC/로그 열기 메뉴, 가상 시뮬레이션. 48개 테스트 통과 (오프스크린).
- **2026-10-31 — Phase 5 필터 완료**: `SFILTER_CAN`/`bDoesFrameOccur` → `bsmaster/core/filters.py` (단일 ID/ID 범위 + 채널/방향/ID타입/RTR, Pass/Stop FilterSet), 메시지 도크에 필터 바 연동. 59개 테스트 통과.

## 단계

| 단계 | 내용 | 상태 |
|------|------|------|
| Phase 0 | 저장소/프로젝트 뼈대, 패키지 구조, 테스트 틀 | 완료 (2026-10-31) |
| Phase 1 | 핵심 데이터 타입 (`STCAN_MSG` → `CanFrame` 등, `DataTypes/`, `Include/Struct_CAN_.h`) | 완료 (2026-10-31) |
| Phase 2 | DBC 파싱 + 시그널 인코딩/디코딩 (`Format Converter/DBC2DBFConverter`) | 완료 (2026-10-31) |
| Phase 3 | 로그 포맷 컨버터 (ASC/BLF/LogToExcel, `Format Converter/`) | 완료 (2026-10-31) |
| Phase 4 | PySide6 메인 윈도우 틀 (메뉴/도킹/상태표시줄, `Application/`) | 완료 (2026-10-31) |
| Phase 5+ | 기능 모듈 점진적 이식: Tx/Rx 창, 필터(`Filter/`), NodeSim(`NodeSimEx/`), J1939/UDS | 진행 중 (필터 완료, 2026-10-31) |

## 모듈 매핑 (원본 → 포팅)

| 원본 (C++) | 포팅 (Python) | 비고 |
|------------|---------------|------|
| `Include/Struct_CAN_.h` (`STCAN_MSG`, `SCAN_ERR`) | `bsmaster/core/datatypes.py` | Phase 1, 진행 중 |
| `DataTypes/MsgSignal_Datatypes.*` | `bsmaster/core/datatypes.py` | Phase 1 |
| `DataTypes/J1939_DataTypes.*`, `UDS_DataTypes.*` | `bsmaster/core/` | Phase 5+ |
| `Format Converter/DBC2DBFConverter` | `bsmaster/dbc/parser.py` | Phase 2 |
| `Format Converter/AscLogConverter`, `BlfLogConverter` | `bsmaster/logconv/` | Phase 3 |
| `Application/` (MFC 메인 프레임) | `bsmaster/gui/main_window.py` (PySide6) | Phase 4 |
| `CAN_*`, `LIN_*` (벤더 드라이버 DLL) | 이식 제외 | Windows 전용 바이너리 |
| `DIL_Interface/` | 인터페이스 정의만 참고 | Phase 5+ 에서 검토 |

## GUI 전략 (PySide6)

- MFC의 MDI/도킹 구조를 Qt의 `QMainWindow` + Dock Widgets로 재구성한다.
- MFC 코드를 직접 번역하지 않고, 화면 단위로 새로 설계한다.
- 하드웨어 연결 없이 동작하는 "시뮬레이션 모드"를 우선 목표로 한다.
