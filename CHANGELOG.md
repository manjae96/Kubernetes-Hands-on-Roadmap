# 변경 기록 — 쿠버네티스 실습 항해도

형식: [SemVer](https://semver.org/lang/ko/) · 릴리스는 허브의 `tools/release.py`로 만듭니다.

## v1.4.0 — 2026-10-26

준비·기본 과정 예정 항목 공개

- 준비: 리눅스·컨테이너 복습 (prep-linux-container)
- 준비: YAML과 매니페스트 읽기 (prep-yaml)
- 기본: 쿠버네티스 개념과 클러스터 구성 (b-concepts)
- 기본: Service 유형 심화 (b-service-types)

공통 템플릿: deep-drawer v1.2.0 · hub-search v1.1.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.3.3 — 2026-10-25

진도 동기화 템플릿 v1.1.0

- progress-sync v1.1.0: 관리자에게 가입 요청 대기 수, 게스트에게 이용 범위(준비·기본) 표시

공통 템플릿: deep-drawer v1.2.0 · hub-search v1.1.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.3.2 — 2026-10-25

진도 동기화 템플릿 설치

- progress-sync v1.0.0: 클라우드 허브에서 로그인한 계정별로 진도를 서버(D1)에 저장·다른 기기와 합침, 열람 기록. 로컬 허브·단독 실행에서는 동작하지 않음

공통 템플릿: deep-drawer v1.2.0 · hub-search v1.1.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.3.1 — 2026-10-25

자매 사이트 목록 갱신

- 자매 사이트 목록·시리즈 포트 안내를 22개 기준으로 갱신

공통 템플릿: deep-drawer v1.2.0 · hub-search v1.1.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.3.0 — 2026-10-24

중급 3 「PV·PVC와 StatefulSet」 공개

- 예정이던 중급 3 공개: emptyDir 유실 → PVC 동적 프로비저닝 → StatefulSet 고정 이름·파드별 볼륨·Headless Service → 회수 정책
- PV·PVC 실습 항해도로 이어지는 「더 깊이」 연결

공통 템플릿: deep-drawer v1.2.0 · hub-search v1.1.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.2.0 — 2026-10-23

읽을거리 「버전의 역사」 추가

- 새 페이지 #/history: 1.0(2015)~1.37(2026) 마이너 38개를 시대 6개로 — 버전별 강조·사라짐·바뀜, 사라진 것 모아 보기(사용 중단→제거), 지원 기간(EOS) 표, 실습과의 연결
- 근거: 버전별 kubernetes.io 릴리스 발표 글, GitHub 릴리스, website data/releases(eol·schedule), Deprecated API Migration Guide — 날짜 32개 자동 대조
- 표 칸 줄바꿈 수정(짧은 값이 한 글자씩 꺾이던 문제), 통합 검색 hub-search v1.1.0

공통 템플릿: deep-drawer v1.2.0 · hub-search v1.1.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.1.1 — 2026-10-23

시리즈 목록 갱신 (Ingress 항해도 추가)

- README 자매 사이트·포트 목록에 Ingress(8260) 추가

공통 템플릿: deep-drawer v1.2.0 · hub-search v1.0.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.1.0 — 2026-10-22

테마 바꾸기, 서랍에서 흐름 그림 표시

- 테마 바꾸기 theme-toggle v1.0.0: 왼쪽 아래 버튼으로 자동·밝게·어둡게, 허브 전체가 같은 선택을 따름
- 심화 노트 서랍 deep-drawer v1.2.0: 노트의 흐름 그림(예: 파드가 만들어지기까지)을 서랍 폭에 맞춰 타임라인으로 표시

공통 템플릿: deep-drawer v1.2.0 · hub-search v1.0.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.0.2 — 2026-10-22

시리즈 목록 갱신, 심화 노트 서랍 v1.1.0

- README 자매 사이트·포트 목록에 vi 편집(8250)·CI/CD(8190) 추가
- 심화 노트 서랍 deep-drawer v1.1.0: 노트의 roadmaps에 이 항해도가 있을 때만 용어에 노트 연결, 노트 안 링크는 노트 제목으로 표시

공통 템플릿: deep-drawer v1.1.0 · hub-search v1.0.0 · deploy v1.0.0

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
