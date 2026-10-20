# 쿠버네티스 실습 항해도

Kubernetes 공식 문서를 근거로 기본·중급·고급 과정을 minikube 실습으로 익히는 한국어 학습 웹사이트입니다. 빌드 도구 없는 정적 사이트이며, 화면 구현(`index.html`)과 콘텐츠(`content/`)가 분리되어 있습니다.

- 기준 버전: Kubernetes 1.37 · 1.36 · 1.35 (확인일 2026-10-15)
- 실습 환경: minikube v1.39.0, docker 드라이버, 프로필 `k8s-lab` (NetworkPolicy 실습은 `k8s-lab-calico`)
- 자매 사이트(실습 항해도): [도커](https://github.com/manjae96/Docker-Hands-On-Roadmap) · [리눅스](https://github.com/manjae96/OS-Linux-Hands-On-Roadmap) · [헬름](https://github.com/manjae96/Helm-Hands-On-Roadmap) · [CNI](https://github.com/manjae96/CNI-Hands-On-Roadmap) · [모니터링](https://github.com/manjae96/Grafana-Prometheus-Hands-On-Roadmap) · [Istio·Kiali](https://github.com/manjae96/Istio-Kiali-Hands-On-Roadmap)

## 실행 방법

콘텐츠를 `fetch`로 읽기 때문에 파일을 더블클릭(`file://`)해서는 열리지 않습니다. 폴더에서 간단한 웹 서버를 띄웁니다.

```bash
cd Kubernetes-Hands-on-Roadmap
python3 -m http.server 8100
# 브라우저에서 http://localhost:8100 열기
```

- 인터넷 연결이 없으면 글꼴은 시스템 글꼴로 대체되고, 마크다운 라이브러리는 `vendor/marked.umd.js`(marked 18.0.14, MIT)를 사용합니다.
- 진도(완료 체크, 실행 결과 확인, 마지막 학습 위치, 체크리스트)는 브라우저 `localStorage`의 `k8s-hangdo-v1` 키에 저장됩니다. 페이지 아래 「진도 초기화」로 지울 수 있습니다.
- 정적 호스팅(GitHub Pages, S3, nginx 등)에 폴더째 올려도 됩니다.
- 항해도 시리즈는 사이트 포트를 겹치지 않게 나눠 씁니다: 쿠버네티스 8100 · 도커 8110 · 리눅스 8120 · 헬름 8130 · CNI 8140 · 모니터링 8150 · Istio·Kiali 8160 (모두 실습에서 쓰는 포트와 겹치지 않음)

## 폴더 구조

```text
index.html                 화면 구현 전체 (HTML·CSS·JS, 라우팅·검색·필터·진도)
vendor/marked.umd.js       마크다운 렌더러 (CDN을 쓸 수 없을 때의 대체본)
content/
  catalog.json             과정·항목 목록, 버전 정보, 시간, 검증 상태 (화면의 모든 목록과 합계의 원천)
  glossary.json            용어집
  guides/<수준>.md          수준별 「이렇게 학습하세요」 본문
  labs/<항목 id>.md         환경 준비·실습·종합 과제 본문
  pages/versions.md        버전 비교
  pages/verification.md    검증 보고서
tools/check_content.py     콘텐츠 점검·YAML 추출 도구
```

## 콘텐츠 수정 방법

### 강의·실습 추가

1. `content/labs/<id>.md`를 작성합니다.
2. `content/catalog.json`의 `items`에 항목을 추가합니다.

| 필드 | 설명 |
|---|---|
| `id`, `level` | `level`은 `prep`·`basic`·`intermediate`·`advanced`. 목록 순서 = 학습 순서 |
| `type` | `setup`·`lesson`·`lab`·`capstone` |
| `status` | `published` 또는 `planned`(예정으로 표시되고 시간 합계에서 제외) |
| `required` | `false`면 「선택 심화」 |
| `minutes` | `{concept, handson, review}` 분 단위. 가이드의 총 시간·일수가 이 값으로 자동 계산됩니다 |
| `versions`, `versionNotes` | 지원 마이너 버전 목록과, 지원하지 않는 버전별 이유 |
| `prereq`, `env`, `components`, `images`, `docs` | 실습 머리말 표에 표시 |
| `components[].kind` | `core`(Kubernetes 기능)·`addon`·`ecosystem`(외부 생태계 도구) |
| `verification` | `{status: runtime|partial|none, summary}` 검증 상태 |
| `outline`, `envNote` | 예정 항목의 계획 목차와 환경 계획 |
| `checks`, `yamlFiles` | 자동 계산 값. `python3 tools/check_content.py --write`로 갱신 |

3. `python3 tools/check_content.py --write`로 점검하고 자동 계산 값을 갱신합니다.

### 마크다운 규칙

| 쓰는 법 | 결과 |
|---|---|
| ` ```bash shell="실습 터미널" ` | 실행 셸 이름이 붙은 명령 블록과 복사 버튼 |
| ` ```yaml file=web.yaml ` | 복사·「YAML 받기」 버튼. 실습 하단 「한 번에 받기(zip)」에 포함 |
| ` ```output kind=example note="..." ` | 「예시 출력 · 실제 실행 결과가 아님」 표시 |
| ` ```output kind=verified env="..." date="..." ` | 「검증 환경에서 실제 실행한 출력」 표시. 실제로 실행한 결과에만 씁니다 |
| ` ```verify ` 블록 (`id`, `title`, `explain`, `command`, `expect`, `criteria`) | 출력을 붙여 넣어 정규식으로 판정하는 성공 판정 상자 |
| `:::note 제목` … `:::` | 콜아웃. 종류: `note`·`warn`·`danger`·`why`·`version` |
| `:::answer 제목` … `:::` | 펼쳐 보는 해설 |
| `[[pod]]`, `[[pod|파드]]` | 용어집 링크. 기본 표시는 「한국어(영어)」 |
| `- [ ] 항목` | 저장되는 체크리스트 |
| `{{roadmap}}`, `{{duration}}`, `{{cta}}` | 가이드 전용. 로드맵·기간 표·시작 버튼으로 바뀝니다 |
| 원시 `<figure class="diagram"><svg>` | 구성도. `box`·`accent`·`zone`·`line` 등 클래스로 양쪽 테마 색을 씁니다 |

### 버전 정보 갱신

1. `content/catalog.json`의 `meta.lastChecked`, `versions`(마이너·최신 패치·EOL·minikube 실습 버전)를 고칩니다. 상단 버전 선택과 홈 문구가 자동으로 바뀝니다.
2. `content/pages/versions.md`의 표를 고칩니다.
3. 새 마이너가 나오면 가장 오래된 버전을 빼고, 각 항목의 `versions`를 조정합니다.

## 검증 결과 요약

자세한 내용은 사이트의 「검증 보고서」(`content/pages/verification.md`)에 있습니다.

- 작업 환경에서는 컨테이너 레지스트리가 막혀 minikube를 띄울 수 없었습니다. 대신 Kubernetes v1.37.1을 소스에서 빌드해 단일 노드 클러스터(etcd, kube-apiserver, controller-manager, scheduler, kubelet, kube-proxy, containerd 2.3.6)를 구성하고, 사이트에 게시된 YAML과 성공 판정 명령을 그대로 실행했습니다.
- nginx·busybox는 공식 이미지를 받을 수 없어 Ubuntu 24.04 패키지로 만든 대체 이미지를 같은 태그로 사용했습니다.
- metrics-server(HPA 실제 확장)와 Calico(NetworkPolicy 차단)는 설치할 수 없어 검증하지 못했습니다.
- 사이트 기능(검색, 필터, 복사, 다운로드, 진도 저장, 실행 결과 검증, 모바일 폭)은 Playwright(Chromium)로 점검했습니다.

## 남은 작업

- 예정 콘텐츠 제작: 개념 강의 2개, 준비 과정 2개, Service 유형 심화, PV·PVC·StatefulSet, HPA scale to zero, 스케줄링, CRD·Operator, 업그레이드·복구
- 실제 minikube v1.39.0 + Docker 환경(WSL2·macOS·Linux)에서 전체 실습 재실행, 특히 HPA 확장과 Calico 차단 결과 확인 후 예시 출력을 검증 출력으로 교체
- `registry.k8s.io/hpa-example` 이미지 다이제스트 기록
- 1.38 출시(예정) 시 버전 비교 갱신, 1.35 EOL(2027-02-28) 이후 제외
