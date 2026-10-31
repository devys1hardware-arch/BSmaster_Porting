# BSmaster_Porting

BUSMASTER([rbei-etas/busmaster](https://github.com/rbei-etas/busmaster), 오픈소스 CAN/LIN 버스 분석기)의 Python 포팅 프로젝트.

- **언어**: Python 3.11+
- **GUI**: PySide6 (Qt for Python)
- **방식**: 원본(약 42.9만 줄, C++/MFC)의 핵심 모듈부터 단계별로 포팅. 전체 1:1 이식이 아니라, 실제로 쓸모 있는 코어 → GUI 순서로 재구성한다.

## 실행 방법

```bash
pip install -r requirements.txt
python -m bsmaster        # GUI 실행
# 또는
bsmaster                  # 설치 후 실행
```

## 테스트

```bash
pytest
```

## 단계별 계획

자세한 모듈 매핑과 단계는 [docs/PORTING_PLAN.md](docs/PORTING_PLAN.md)를 참고.

1. **Phase 0** — 저장소/프로젝트 뼈대 (현재 단계)
2. **Phase 1** — 핵심 데이터 타입 (`STCAN_MSG` 등)
3. **Phase 2** — DBC 파싱 + 시그널 인코딩/디코딩
4. **Phase 3** — 로그 포맷 컨버터 (ASC/BLF)
5. **Phase 4** — PySide6 메인 윈도우 틀
6. **Phase 5+** — 기능 모듈 점진적 이식 (Tx/Rx, 필터, NodeSim …)

## 라이선스

원본 BUSMASTER는 LGPL v3를 따른다. 이 포팅 프로젝트도 동일하게 LGPL v3를 따른다.
