## 요약

이 사이트의 명령어와 YAML을 **실제로 실행해 확인한 범위**와 **확인하지 못한 범위**를 기록합니다. 실습 페이지의 출력 블록은 이 기준에 따라 표시됩니다.

| 표시 | 의미 |
|---|---|
| 「검증 환경에서 실제 실행한 출력」 (초록) | 아래 검증 환경에서 그 명령을 실행해 얻은 출력을 그대로 옮긴 것 |
| 「예시 출력 · 실제 실행 결과가 아님」 (점선) | 공식 문서나 도구 동작을 바탕으로 모양을 보여 주는 예시. 실행해서 얻은 값이 아님 |

## 실행 검증 결과 (2026-10-15)

사이트에 게시된 YAML을 `tools/check_content.py --extract`로 그대로 추출하고, 실습 단계를 처음부터 다시 실행한 뒤 각 「성공 판정」 상자의 명령을 **수정 없이** 실행해 기준 정규식과 비교했습니다. 총 18개 판정 중 검증 환경의 한계로 실패가 예상된 항목을 제외하면 모두 통과했습니다.

| 판정 | 실습 | 결과 | 실제 출력 (요약) |
|---|---|---|---|
| `b1-final` | 기본 1 | 통과 | `ready=4 endpoints=4` |
| `b2-rollback` | 기본 2 | 통과 | `nginx:1.31.7-alpine 3/3 4` |
| `b2-logs` | 기본 2 | 통과 | `오류: DB_HOST 환경 변수가 설정되지 않음` 포함 |
| `bcap-state` | 기본 종합 | 통과 | `image=nginx:1.31.7-alpine ready=4/4 endpoints=4 http=200` |
| `bcap-spec` | 기본 종합 | 통과 | `guestbook 0` |
| `i1-ready` | 중급 1 | 통과 | `ready=1 notready=1` |
| `i1-liveness` | 중급 1 | 통과 | `1` |
| `i1-config` | 중급 1 | 재실행 후 통과 | 첫 실행은 롤아웃 직후 요청이 시간 초과되어 실패. 10초 뒤 재실행에서 `버전 2 maintenance`. 판정 설명에 재시도 안내를 추가함 |
| `i2-oom` | 중급 2 | 통과 | `OOMKilled 137` |
| `i2-hpa` | 중급 2 | **실패 (예상됨)** | `active=False rescaled=0` — metrics-server 없음 |
| `icap-final` | 중급 종합 | 수정 전 실패(의도), 수정 후 통과 | `api=2 worker=1 body={"status":"ok","service":"orders"}` |
| `a1-cani` | 고급 1 | 통과 | `yes yes no no` |
| `a1-token` | 고급 1 | 통과 | `system:serviceaccount:lab-a01:log-reader` |
| `a2-policy` | 고급 2 | **실패 (예상됨)** | `api=ok stranger=ok` — CNI가 정책을 집행하지 않음 |
| `a2-partner` | 고급 2 | 통과 (제한적) | `partner=ok` — 정책 집행 없이도 나오는 값이라 정책 검증으로는 의미가 없음 |
| `acap-psa` | 고급 종합 | 통과 | `violates PodSecurity "restricted:latest"` |
| `acap-final` | 고급 종합 | **실패 (예상됨)** | `web=2/2 tester=ok intruder=ok rbac=no` — intruder 차단만 미집행 |


## 검증 환경

작업 환경은 외부 컨테이너 레지스트리(Docker Hub, registry.k8s.io, quay.io 등) 접근이 막혀 있어 **minikube를 띄울 수 없었습니다.** 그래서 공식 소스로 Kubernetes를 직접 빌드해 minikube와 비슷한 단일 노드 클러스터를 구성했습니다.

| 구성 요소 | 버전·방식 |
|---|---|
| Kubernetes (kube-apiserver, kube-controller-manager, kube-scheduler, kubelet, kube-proxy, kubectl) | **v1.37.1**, 태그 커밋 `f78e722`에서 Go 1.26.8로 소스 빌드 |
| etcd | v3.7.0 서버 패키지 (Kubernetes 소스에 포함된 버전을 그대로 내장 실행) |
| 컨테이너 런타임 | containerd 2.3.6, runc 1.5.1 |
| CNI | containernetworking/plugins의 bridge·host-local·portmap·loopback (NetworkPolicy **미집행**) |
| kube-proxy 모드 | iptables (minikube 기본과 같음) |
| 클러스터 DNS | CoreDNS를 빌드할 수 없어, Service 이름의 A 레코드만 응답하는 검증용 DNS를 사용 |
| 노드 이름 | `k8s-lab` (minikube 프로필 이름과 같게 맞춤) |
| 호스트 | Linux 6.18 커널, **cgroup v1** (kubelet `failCgroupV1: false`로 실행) |

### 대체 이미지

공식 이미지를 내려받을 수 없어 Ubuntu 24.04 패키지로 대체 이미지를 만들고 **실습과 같은 태그를 붙여** 사용했습니다. 매니페스트는 바꾸지 않았습니다.

| 실습의 이미지 | 검증에 쓴 대체 이미지 | 차이 |
|---|---|---|
| `nginx:1.30.6-alpine`, `nginx:1.31.7-alpine` | Ubuntu nginx 1.24 + 공식 이미지와 같은 경로(`/etc/nginx/conf.d`, `/usr/share/nginx/html`), 로그를 표준 출력으로 연결 | nginx 버전·기본 페이지 문구가 다름. 두 태그가 같은 이미지라 업데이트 후 동작 차이는 확인 불가 |
| `busybox:1.37.0` | Ubuntu `busybox-static` 1.36.1 | 애플릿 동작은 같지만 버전이 다름 |
| `registry.k8s.io/pause:3.10.2` | Kubernetes 소스의 `pause.c`로 빌드 | 없음 |
| `registry.k8s.io/hpa-example` | 없음 (내려받지 못함) | HPA 실습 파드가 실행되지 않음 |

### 환경 차이로 조정한 점

- 이 VM은 음수 `oom_score_adj`를 설정할 권한이 없어, runc 앞에 그 값을 0으로 올리는 래퍼를 두었습니다. 파드 동작에는 영향이 없지만 노드 메모리 부족 시 퇴출 순서 실험은 할 수 없습니다.
- cgroup v1 노드에서는 메모리 초과 시 컨테이너 전체가 아니라 가장 큰 프로세스만 종료되는 것을 확인했습니다. 중급 종합 과제의 워커 명령에 `set -e`를 넣어 cgroup v1·v2 모두에서 같은 증상(OOMKilled)이 나오게 했습니다.
- `kubectl run --rm -i`처럼 바로 끝나는 명령은 연결 시점에 따라 출력이 섞여, 모든 실습에서 「대기 중인 클라이언트 파드 + `kubectl exec`」 방식으로 바꾸었습니다.

## 실습별 검증 범위

| 실습 | 실행 검증한 것 | 검증하지 못한 것 |
|---|---|---|
| 환경 준비 | 성공 판정 명령의 형식 | minikube·kubectl·Docker 설치 절차 전체 (학습자 PC 전용) |
| 기본 1 · 첫 Deployment·Service | 모든 YAML과 명령, DNS 이름 접속, port-forward, 자가 치유 | `kubectl get pods -n kube-system` 출력 (검증 환경에는 kube-system 파드 없음) |
| 기본 2 · 롤아웃·로그·이벤트 | 라벨 셀렉터, 롤링 업데이트, 태그 오타 재현, 롤백 경고, CrashLoopBackOff 로그 | 레지스트리 연결 시의 `not found` 문구 (검증 환경은 접근 차단 오류) |
| 기본 종합 과제 | 해설 매니페스트, 장애 주입·복구, 두 성공 판정 | — |
| 중급 1 · ConfigMap·Secret·Probe | Secret 디코딩, 설정 주입, Readiness 제외, Liveness 재시작, 설정 반영 시점(약 60초), rollout restart | 브라우저에서 본 한글 표시 (`<meta charset>`은 검증 뒤 추가) |
| 중급 2 · 자원·HPA | QoS 클래스, Insufficient cpu, OOMKilled 137, HPA 객체 생성, 지표가 없을 때의 HPA 상태 | metrics-server 설치·`kubectl top`·HPA 실제 확장과 축소 |
| 중급 종합 과제 | 결함 4개의 증상과 수정 후 성공 판정 | — |
| 고급 1 · RBAC | Role·RoleBinding, `auth can-i`, 실제 토큰 접속의 허용·거부, view ClusterRole 재사용 | — |
| 고급 2 · NetworkPolicy | 정책 객체 생성과 `describe` 해석, **정책을 집행하지 않는 CNI에서 무시되는 현상** | Calico 프로필 생성, 차단·허용 결과 |
| 고급 종합 과제 | Pod Security 거부 메시지, restricted 기준 앱 실행, RBAC 경계 | NetworkPolicy 차단 결과 (intruder) |

## 사이트 기능 점검

로컬 웹 서버(`python3 -m http.server`)로 연 사이트를 Playwright 1.56(Chromium, 화면 1366px·390px, 밝은·어두운 테마)으로 점검했습니다. **41/41개 통과**.

| 점검 항목 | 결과 |
|---|---|
| 홈: 수준 카드 3개 | 통과 |
| 홈: 총 예상 시간 표시 | 통과 |
| 마크다운 라이브러리 로드 | 통과 |
| 수준 선택 후 가이드 이동 | 통과 |
| 상단 수준 선택값 반영 | 통과 |
| 가이드: ①~⑤ 절 | 통과 |
| 가이드: 하루 30분·1시간·2시간 | 통과 |
| 가이드: 설치 시간 별도 표시 | 통과 |
| 가이드: 시작하기 버튼 | 통과 |
| 체크리스트 저장 유지 | 통과 |
| 가이드: 총 시간 = 공개 항목 합계 | 통과 |
| 시작하기 → 첫 실습 | 통과 |
| 실습: 지원 버전·공식 문서·검증 상태 표시 | 통과 |
| 실습: 용어 첫 등장 한영 병기 | 통과 |
| 실습: 검증 출력 표시 | 통과 |
| 코드 복사 | 통과 |
| YAML 파일 다운로드 | 통과 |
| YAML 묶음 zip 다운로드 | 통과 |
| 검증: 틀린 출력 거절 | 통과 |
| 검증: 맞는 출력 통과 | 통과 |
| 검증 진행 표시 1/3 | 통과 |
| 수동 완료 저장 유지 | 통과 |
| 수동 완료와 실행 결과 구분 표시 | 통과 |
| 이어서 학습하기: 마지막 위치 기록 | 통과 |
| 홈: 이어서 학습하기 버튼 | 통과 |
| 목록 검색: HPA | 통과 |
| 난이도 필터: 고급만 | 통과 |
| 버전 필터: 1.35에서 불가 항목과 이유 | 통과 |
| 상태 필터: 완료 | 통과 |
| 버전 1.36: 사용 불가 안내 | 통과 |
| 버전 1.37: 안내 없음 | 통과 |
| 키보드 / 로 검색창 포커스 | 통과 |
| 사이트 검색 결과 | 통과 |
| 용어집 검색 | 통과 |
| 용어집: Kubernetes 기능·외부 생태계 구분 | 통과 |
| 버전 비교 표 | 통과 |
| 검증 보고서 렌더 | 통과 |
| 진도 초기화 | 통과 |
| 콘솔·스크립트 오류 없음 | 통과 |
| 모바일 390px 가로 스크롤 없음 | 통과 |
| 예시 출력은 실제 결과가 아님을 표시 | 통과 |

게시된 아티팩트 화면에서는 브라우저 다운로드가 막혀 있어, 「YAML 받기」가 뷰어의 파일 저장 확인 창을 거쳐 zip 파일로 저장됩니다(.yaml 확장자를 직접 저장할 수 없음). 이 경로는 로컬 점검으로 확인할 수 없어 게시 후 화면에서 별도로 확인해야 합니다.

## 재현 방법

검증에 사용한 스크립트는 사이트와 함께 배포하지 않지만, 같은 방식으로 재현할 수 있습니다.

1. `python3 tools/check_content.py --extract out/`로 실습별 YAML을 파일로 추출합니다.
2. minikube `k8s-lab`에서 각 실습의 단계를 실행한 뒤, `python3 tools/check_content.py --checks`가 출력하는 성공 판정 명령을 실행하고 `expect` 정규식과 비교합니다.

## 마지막 확인

- 공식 문서·릴리스 정보 확인: 2026-10-15 (kubernetes.io Releases, v1.35~v1.37 릴리스 공지, Deprecated API Migration Guide, minikube v1.39.0 CHANGELOG·소스)
- 실행 검증: 2026-10-15
