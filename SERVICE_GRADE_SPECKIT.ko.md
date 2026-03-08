# Aegis-Air Service-Grade SPECKIT

Last updated: 2026-03-08

## S - Scope
- 대상: local-first / air-gapped incident review engine
- 이번 iteration 목표: `runtime brief + incident schema + frontend readiness board`를 추가해 로컬 엔진의 신뢰 경계를 첫 화면에서 읽히게 만들기

## P - Product Thesis
- Aegis-Air는 "오프라인에서도 incident review가 가능한 엔진"이라는 메시지가 분명해야 한다.
- 빅테크 리뷰어는 air-gapped posture와 replay evidence를 바로 볼 수 있어야 한다.

## E - Execution
- `/api/runtime/brief`로 trust boundary, replay score, target reachability를 노출
- `/api/schema/report`로 handoff contract를 명시
- frontend에 `Local-First Readiness` 보드를 추가
- recorded demo mode에서도 같은 readiness surface를 fallback으로 유지

## C - Criteria
- `pytest`와 replay suite green
- demo 없이도 README만으로 배포 경계와 가치가 설명됨
- incident taxonomy와 report contract가 흔들리지 않음
- recorded/live 모드 모두 같은 service-grade narrative를 유지

## K - Keep
- local-first stance
- reproducible replay evidence

## I - Improve
- operator screenshots와 sample incident packet 강화
- schema diff / taxonomy migration 문서 추가
- companion `AegisOps`와 shared incident schema alignment

## T - Trace
- `README.md`
- `aegis_engine/main.py`
- `frontend/index.html`
- `frontend/app.js`
- `frontend/style.css`
- `tests/test_meta_endpoints.py`
