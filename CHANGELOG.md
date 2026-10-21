# 변경 기록 — 쿠버네티스 실습 항해도

형식: [SemVer](https://semver.org/lang/ko/) · 릴리스는 허브의 `tools/release.py`로 만듭니다.

## v1.0.1 — 2026-10-22

자매 사이트·포트 안내에 도메인 항해도 추가

- README 자매 사이트 목록과 시리즈 포트 안내(도메인 8240) 갱신

공통 템플릿: deep-drawer v1.0.0 · hub-search v1.0.0 · deploy v1.0.0

## v1.0.0 — 2026-10-21

형상관리 기준선

- VERSION·CHANGELOG·태그 도입 (이전 기록은 CHANGELOG 「이전 기록」)
- 공통 템플릿 버전 표시: deploy v1.0.0 · deep-drawer v1.0.0 · hub-search v1.0.0
- 컨테이너가 버전을 알림: <경로>/VERSION, /healthz의 version

공통 템플릿: deep-drawer v1.0.0 · hub-search v1.0.0 · deploy v1.0.0

## 이전 기록 (버전 관리 전)

| 날짜 | 커밋 | 내용 |
|---|---|---|
| 2026-10-21 | `83294b7` | feat: 통합 검색 ⌘K (항해도 11개 · 용어 · 심화 노트) |
| 2026-10-21 | `c393f6b` | feat: 심화 노트 서랍 (용어 미리보기 · 서랍 · 📌 고정 · 노트 이동 · 요약부터 보기) |
| 2026-10-21 | `70c15db` | build: 실습 항해도 공통 배포 규칙 적용 (deploy/Dockerfile) |
| 2026-10-21 | `437bcb8` | docs: 자매 사이트·포트 안내에 PV·PVC, Harbor·Nexus, Locust 항해도 추가 |
| 2026-10-20 | `e7a2937` | docs: 자매 사이트·포트 안내에 Falco 항해도 추가 |
| 2026-10-20 | `461f9b0` | feat: 허브 포털에서 열었을 때 '← 전체 항해도' 링크 표시 |
| 2026-10-20 | `bc679ca` | docs: 자매 사이트 링크 정리, 사이트 포트 81xx로 분리 |
| 2026-10-15 | `a3c8d8f` | 쿠버네티스 실습 항해도 첫 버전 |
