# 변경 기록 — 쿠버네티스 실습 항해도

형식: [SemVer](https://semver.org/lang/ko/) · 릴리스는 허브의 `tools/release.py`로 만듭니다.

## v1.9.4 — 2026-11-07

공통 화면 틀 feedback 2.5.0

- 도움·의견·dock 템플릿 feedback 2.5.0: 자기 배치 화면의 바닥글 표시(data-hd-foot) 지원 — 이 항해도 화면의 동작은 2.4.0과 같음
- 항해도 id·항목 id·저장 키·URL·콘텐츠 그대로

공통 템플릿: deep-drawer v1.5.0 · hub-search v1.3.2 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.9.3 — 2026-11-07

공통 화면 틀 feedback 2.4.0

- 공통 도움·의견·dock 템플릿 feedback 2.4.0: 항해도 바닥글(.site-foot)과 허브 공통 바닥글(footer.hd-foot)을 같은 방식으로 처리 — 이 항해도 화면의 동작은 2.3.1과 같음(바닥글 아래 빈 공간 0)
- 항해도 id·항목 id·저장 키·URL·콘텐츠 그대로 (index.html의 공통 템플릿 구간만)

공통 템플릿: deep-drawer v1.5.0 · hub-search v1.3.2 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.9.2 — 2026-11-07

맨 아래로 내렸을 때 바닥글 아래 빈 공간 제거

- 공통 화면 틀의 도움·의견·dock 템플릿 feedback 2.3.1: 단추 회피 여백을 바닥글 뒤가 아니라 본문 끝·바닥글 안쪽에 둠 — 맨 아래에서 바닥글이 화면 끝에 닿고 빈 공간 0
- 바닥글 글자·본문 마지막 줄은 떠 있는 단추(도움·의견·테마·맨 위로·허브 홈)에 가리지 않음 — 실제 단추 위치를 재서 바닥글 아래·오른쪽 여백을 정함
- 항해도 id·항목 id·저장 키·URL·콘텐츠 그대로 (index.html의 공통 템플릿 구간만)

공통 템플릿: deep-drawer v1.5.0 · hub-search v1.3.2 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.9.1 — 2026-11-07

i-lab02 회차별 학습 지도·단계 번호 정정, Vault 설명 정리

- i-lab02: 회차별 학습 지도(성공 판정·HPA 이벤트 1시간 주의), metrics-server는 4단계(5단계 아님), 정리 안내 「세 번째 명령」
- a-vault: init·unseal 짧은 뜻과 심화 노트 연결, 재시작 봉인·audit HMAC 설명 정리, root 토큰 폐기는 7단계(6단계 아님)
- 항해도 id·항목 id·저장 키·URL 그대로, 실습 명령·검증 출력은 바꾸지 않음

공통 템플릿: deep-drawer v1.5.0 · hub-search v1.3.2 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.9.0 — 2026-11-07

응용 과제 힌트·해설 2층, 공통 완료 규칙·화면 틀 갱신

- 공통 완료 규칙으로 목차·진도·학습 현황 계산, 「배지 받으러 가기」 — 허브 templates/completion.js 1.0.0 · app-ui 2.2.0 · progress-sync 2.1.0
- 초기화·되돌리기 알림을 받은 열린 탭은 첫 화면(#/)으로 다시 열고 한 줄 안내 — 허브 templates/progress-sync.html 2.1.0
- 공통 화면 틀: 맨 아래 여백을 필요한 만큼만·허브 홈 아래·맨 위로 위, 목차 맨 아래 버전, 지금 묶음도 접기, 힌트·해설 문법 — 허브 templates feedback 2.3.0 · app-ui 2.2.0 · deep-drawer 1.5.0 · return-to 1.0.3
- 그림에 height 속성 — 받기 전에도 자리를 잡아 스크롤 위치가 밀리지 않게 (허브 tools/visuals.py)
- 응용 과제: 과제 → 스스로 해 볼 시간 → 힌트(접힘) → 해설(접힘)으로 나눔 — 허브 docs/HINTS.md
- 항해도 id·항목 id·저장 키·URL 그대로, D1 마이그레이션 없음

공통 템플릿: deep-drawer v1.5.0 · hub-search v1.3.2 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.8.5 — 2026-11-06

README 자매 사이트·포트 안내에 자격증 준비 항해도 3개

- 허브 v1.29.0의 자격증 준비 영역(CKA·CKAD·CKS) 추가에 맞춘 README 갱신 — 화면·콘텐츠 변경 없음

공통 템플릿: deep-drawer v1.4.0 · hub-search v1.3.2 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.8.4 — 2026-11-06

CSP 강제 준비 — 인라인 스타일을 클래스로

- CSP 강제 준비: style="" 속성을 클래스로(허브 tools/csp_inline.py) — 화면은 그대로(바꾸기 전·후 픽셀 비교 동일), 항해도 화면 CSP 위반 0
- a-lab02 그림의 SVG style도 클래스로(레벨테스트 근거 절 해시는 그대로)
- 공통 화면 틀 app-ui 2.1.0: 수준 카드의 「총 예상 시간·진도」와 「먼저 볼 곳」 카드를 같은 줄끼리 정렬
- 오른쪽 아래 「허브 홈」·「맨 위로」(도움·의견과 같은 dock 안 별도 줄, feedback 2.2.0) · 「이전 실습으로 돌아가기」 안내가 dock과 겹치지 않게(return-to 1.0.2)
- URL·#/item/<id>·항목 id·storageKey·진도·포트·Docker·단독 실행 그대로

공통 템플릿: deep-drawer v1.4.0 · hub-search v1.3.2 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.8.3 — 2026-11-05

공통 화면 틀 2.0 — 망분리 항해도와 같은 화면 구조·토큰·글꼴

- 공통 화면 틀 2.0(허브 app-ui 2.0.0, docs/UI-SHELL.md): 망분리 항해도와 같은 상단 바·왼쪽 전체 과정 목차·가운데 본문·오른쪽 「이 페이지」·홈 대시보드·공통 토큰(밝게/어둡게)
- 글꼴: 허브 Pretendard(UI·본문), 코드만 고정폭 — 외부 글꼴(Google Fonts) 링크 제거, 외부 출처 0
- 접근성: 건너뛰기 링크, aria-current·aria-expanded·aria-controls, 좁은 화면 서랍(초점 가두기·ESC로 닫고 단추로 복귀)
- URL·#/item/<id>·항목 id·storageKey·진도·시험·배지·포트·Docker 그대로, 앱 기능 그대로(상단 메뉴는 왼쪽 목차로)

공통 템플릿: deep-drawer v1.4.0 · hub-search v1.3.2 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.8.2 — 2026-11-05

공통 템플릿 갱신 — 계정별 진도 동기화 2.0 · 읽기 배치 · 화면 밀림 수정

- 공통 템플릿: 진도 동기화 2.0(계정 진도가 기준·자동 병합 없음·오래된 탭 차단) · 진도 영역 1.3.0 · 도움·의견 2.1.0 · 읽기 배치 app-ui 1.0.2(정보표 「항목 | 내용」·목차 접기·화면 밀림 수정) · 통합 검색 1.3.2

공통 템플릿: deep-drawer v1.4.0 · hub-search v1.3.2 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.8.1 — 2026-11-04

공통 템플릿과 성능 측정 연결

- 0으로 줄이기(i-scale-zero) 「생각할 점」: HPA를 TPS·정상 상태로 확인 — Locust i-tps 연결
- 모든 화면 오른쪽 아래 「도움·의견」 버튼 — 건의사항·질문·버그 신고 (feedback v2.0.0)
- 진도 영역 1.2.0: 사용 안내·실습 환경 선택도 사람·이용권별로 분리

공통 템플릿: deep-drawer v1.4.0 · hub-search v1.3.0 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.8.0 — 2026-11-03

선택 심화 과정 6개(MetalLB·Vault·kubeadm·Kubespray·k8gb·KubeVirt)와 접근 가능한 SVG

- MetalLB L2로 베어메탈 LoadBalancer (a-metallb, 부분 검증)
- Vault와 Kubernetes ServiceAccount 인증 (a-vault, 부분 검증)
- kubeadm 구조 보기와 패치 업그레이드 (a-kubeadm, 부분 검증)
- Kubespray 인벤토리와 플레이북 검사 (a-kubespray, 정적 검증)
- k8gb로 두 클러스터 DNS 장애 전환 (a-k8gb, 부분 검증)
- KubeVirt 설치와 KVM 없는 노드의 한계 (a-kubevirt, 부분 검증)
- 텍스트 그림을 접근 가능한 SVG로 (원래 텍스트는 「글로 보기」로 유지)
- b-service-types에서 MetalLB 실습으로 짧은 링크

공통 템플릿: deep-drawer v1.4.0 · hub-search v1.3.0 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.7.1 — 2026-11-02

공통 템플릿: favicon·lang·CSP 대응·레벨테스트 결과 사람별 분리

- 공통 favicon 링크와 html lang=ko
- CSP 대응: 인라인 이벤트·style 속성 제거, marked 자체 호스팅
- 진도 영역 1.1.0: 레벨테스트 결과를 사람·이용권별로 분리

공통 템플릿: deep-drawer v1.3.0 · hub-search v1.3.0 · theme-toggle v1.0.0 · deploy v1.1.0

## v1.7.0 — 2026-10-30

VPA 추천 과정과 자원 계획 보강

- 게스트 진도 영역 보호(오래된 탭 쓰기 차단)
- 이전 실습으로 돌아가기
- 과정별 피드백 양식
- 중급: VPA로 requests 추천받기(i-vpa, 실행 검증) 추가
- 자원 계획·HPA 계산 과정 보강
- 준비: minikube containerd 런타임 명시

공통 템플릿: deep-drawer v1.3.0 · hub-search v1.3.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.6.2 — 2026-10-28

공통 템플릿 갱신: 통합 검색 1.3.0

- 공통 템플릿: 통합 검색 hub-search 1.3.0 — 바뀌기 전 이름(aliases)으로도 검색, 항해도·학습 트랙 항목 추가, 학습 가이드 가중치 누락 수정
- 자매 사이트 이름 갱신: Jenkins CI/CD · Terraform IaC · DNS·HTTPS · Harbor·Nexus 레지스트리

공통 템플릿: deep-drawer v1.3.0 · hub-search v1.3.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.6.1 — 2026-10-28

상황 문장 다듬기

- 고급 종합 과제 상황의 주어(플랫폼 팀) 정리

공통 템플릿: deep-drawer v1.3.0 · hub-search v1.2.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.6.0 — 2026-10-28

교육 중심 정리

- 미공개 계획 항목을 사이트에서 빼고 docs/backlog.json으로 옮김, 「예정·준비 중」 문구 정리
- 단계 목표 정리, HPA 0까지 축소 링크 연결
- 공통 템플릿: 용어 미리보기·클릭 동작 정리(deep-drawer 1.3.0), 권한별 진도 저장(progress-sync 1.2.0), 검색에 학습 가이드(hub-search 1.2.0)

공통 템플릿: deep-drawer v1.3.0 · hub-search v1.2.0 · theme-toggle v1.0.0 · deploy v1.0.0

## v1.5.0 — 2026-10-26

중급 예정 항목 공개 (2차)

- 중급: HPA로 0까지 축소 — External 지표·prometheus-adapter·ScaledToZero 조건 (i-scale-zero, Kubernetes 1.37 베타)

공통 템플릿: deep-drawer v1.2.0 · hub-search v1.1.0 · theme-toggle v1.0.0 · deploy v1.0.0

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
