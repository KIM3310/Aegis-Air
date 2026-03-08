# Aegis-Air Service-Grade SPECKIT

Last updated: 2026-03-08

## S - Scope
- 대상: local-first / air-gapped incident review engine
- baseline 목표: offline trust boundary, replay 품질, incident schema 신뢰도를 서비스 문맥으로 고정

## P - Product Thesis
- Aegis-Air는 "오프라인에서도 incident review가 가능한 엔진"이라는 메시지가 분명해야 한다.
- 빅테크 리뷰어는 air-gapped posture와 replay evidence를 바로 볼 수 있어야 한다.

## E - Execution
- local-only / air-gapped posture를 README와 runtime surface에서 명확히 유지
- replay suite, schema, eval artifact를 운영 증거로 계속 노출
- AegisOps와는 companion relationship을 유지하되 코드 경계는 보존

## C - Criteria
- `pytest`와 replay suite green
- demo 없이도 README만으로 배포 경계와 가치가 설명됨
- incident taxonomy와 report contract가 흔들리지 않음

## K - Keep
- local-first stance
- reproducible replay evidence

## I - Improve
- operator screenshots와 sample incident packet 강화
- schema diff / taxonomy migration 문서 추가

## T - Trace
- `README.md`
- `aegis_engine/`
- `scripts/run_replay_suite.py`
- `evals/`

