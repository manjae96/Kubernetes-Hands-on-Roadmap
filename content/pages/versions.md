## 지원 중인 버전 한눈에 보기

Kubernetes 프로젝트는 최근 3개 마이너 버전의 릴리스 브랜치를 유지하며, 1.19 이후 버전은 약 1년 동안 패치를 받습니다. 아래는 2026-10-15에 공식 릴리스 페이지에서 확인한 값입니다.

| 마이너 | 릴리스명 | 출시일 | 최신 패치 (2026-10-15) | 지원 종료(EOL) | 이 사이트의 minikube 실습 버전 |
|---|---|---|---|---|---|
| **1.37** | Garhwal | 2026-08-26 | 1.37.1 (2026-09-15) | 2027-10-28 | v1.37.0 (minikube v1.39.0 기본값) |
| **1.36** | ハル (Haru) | 2026-04-22 | 1.36.5 (2026-09-15) | 2027-06-28 | v1.36.4 |
| **1.35** | Timbernetes | 2025-12-17 | 1.35.9 (2026-09-15) | 2027-02-28 | v1.35.8 |

minikube v1.39.0(2026-09-01)이 검증 목록에 넣은 각 마이너의 최신 패치가 위 「실습 버전」입니다. 그 뒤에 나온 패치(1.37.1, 1.36.5, 1.35.9)도 `--kubernetes-version`으로 지정할 수 있지만 minikube가 경고를 표시할 수 있습니다.

:::warn 1.34는 곧 지원 종료
1.34의 마지막 지원일은 **2026-10-27**입니다. 이 사이트는 1.34를 비교 대상에서 뺐습니다. 1.34 클러스터를 운영 중이라면 1.35 이상으로 올릴 계획을 세우세요. 1.33은 2026-06-28에 이미 지원이 끝났습니다.
:::

상단의 「Kubernetes」 선택에서 버전을 바꾸면, 그 버전에서 진행할 수 없는 실습에 이유가 표시됩니다. 현재 공개된 실습은 세 버전에서 모두 같은 YAML로 동작하며, 버전에 따라 다른 것은 「HPA로 0까지 축소하기」(예정, 1.37 전용)입니다.

## 기능 성숙도 읽는 법

| 단계 | 기본 상태 | 의미 |
|---|---|---|
| Alpha | 꺼짐 | 실험 단계. 다음 버전에서 바뀌거나 사라질 수 있어 운영 환경에 쓰지 않습니다. |
| Beta | 대개 켜짐 (예외 있음) | 충분히 시험됨. 세부 동작은 바뀔 수 있습니다. |
| Stable (GA) | 항상 켜짐 | 이후 버전에서 호환성을 유지합니다. 기능 게이트가 기본값으로 잠깁니다. |

[[feature-gate]]와 [[stability]]도 참고하세요.

## 학습 내용과 관련 있는 기능의 버전별 상태

Kubernetes v1.37.1 소스의 기능 게이트 이력(`pkg/features/kube_features.go`)과 각 릴리스 공지로 확인했습니다.

| 기능 (KEP) | 1.35 | 1.36 | 1.37 | 관련 과정 |
|---|---|---|---|---|
| 파드 자원 제자리 변경 In-place Pod Resize ([1287](https://kep.k8s.io/1287)) | **Stable** | Stable | Stable | 중급 · 자원 |
| HPA 허용 오차 설정 ([4951](https://kep.k8s.io/4951)) | Beta | Beta | **Stable** | 중급 · HPA |
| HPA 0까지 축소 ([2021](https://kep.k8s.io/2021)) | Alpha (꺼짐) | Alpha (꺼짐) | **Beta (켜짐)** | 중급 · 선택 심화 |
| metrics.k8s.io API 정의 ([5207](https://kep.k8s.io/5207)) | Beta (`v1beta1`) | Beta | **Stable (`v1`)** | 중급 · HPA |
| StatefulSet `maxUnavailable` | Beta (꺼짐) | Beta (꺼짐) | Beta (**켜짐**) | 중급 · StatefulSet |
| 스토리지 버전 마이그레이션 내장 ([4192](https://kep.k8s.io/4192)) | Beta (꺼짐) | Beta (꺼짐) | **Stable** | 고급 · 업그레이드 |
| 사용자 네임스페이스 User Namespaces ([127](https://kep.k8s.io/127)) | Beta (켜짐) | **Stable** | Stable | 고급 · 보안 |
| 변경 어드미션 정책 Mutating Admission Policy ([3962](https://kep.k8s.io/3962)) | Beta (꺼짐) | **Stable** | Stable | 고급 · 확장 |
| kubelet API 세분화 인가 ([2862](https://kep.k8s.io/2862)) | Beta (켜짐) | **Stable** | Stable | 고급 · RBAC |
| 파드 인증서 Pod Certificates ([4317](https://kep.k8s.io/4317)) | Beta (꺼짐) | Beta (꺼짐) | **Stable** | 고급 · 보안 |
| 노드 기능 선언 Node Declared Features ([5328](https://kep.k8s.io/5328)) | Alpha | Beta | **Stable** | 고급 · 스케줄링 |
| KYAML 출력 ([5295](https://kep.k8s.io/5295)) | Beta | Beta | **Stable** (`kubectl get -o kyaml`) | 준비 · YAML |

「꺼짐/켜짐」은 해당 버전의 기본값입니다. Beta라도 기본으로 꺼진 기능은 클러스터 설정에서 켜야 쓸 수 있으며, minikube에서는 `--feature-gates` 옵션으로 켭니다.

## 버전별 주요 변경

### 1.37 (2026-08-26) · 67개 개선: Stable 16 · Beta 23 · Alpha 27

- **Stable**: 견고한 watch 캐시 초기화 — API 서버가 재시작·복구 중 과도한 요청을 HTTP 429로 거절합니다. 직접 만든 컨트롤러는 `Retry-After`와 지수 백오프로 429를 처리해야 합니다.
- **Stable**: KYAML, metrics.k8s.io API, Pod Certificates·ClusterTrustBundle, Node Declared Features, 스토리지 버전 마이그레이터, HPA 허용 오차, DRA 일부 기능
- **Beta**: HPA scale to zero(기본 켜짐), 매니페스트 기반 어드미션 설정, 갱 스케줄링, Memory QoS(cgroup v2), 파드 수준 자원 관리자, PVC 마지막 사용 시각
- **Alpha**: StatefulSet `Recreate` 전략, 파드 수준 체크포인트·복원, in-place resize를 위한 스케줄러 선점
- 기타: StatefulSet `maxUnavailable` 기본 재활성화, kube-proxy nftables 성능 개선
- 공식 공지: [Kubernetes v1.37: Garhwal](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/)

### 1.36 (2026-04-22) · Stable 18

- **Stable**: kubelet API 세분화 인가, User Namespaces, Mutating Admission Policies, Volume Group Snapshot, ServiceAccount 토큰 외부 서명 API, Node log query, cgroup v2 기반 PSI, OCI 아티팩트·이미지 볼륨
- **Beta**: 컨트롤러 상태 지연(staleness) 완화, IP/CIDR 검증 강화, kubectl 사용자 설정(kuberc) 분리
- **Alpha**: HPA scale to zero의 사용자 지정 지표 지원 진전, 워크로드 인지 스케줄링(WAS)
- 공식 공지: [Kubernetes v1.36: ハル (Haru)](https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/)

### 1.35 (2025-12-17) · Stable 15

- **Stable**: In-place Pod Resize, Pod Generation(`.metadata.generation`으로 파드 갱신 추적), PreferSameNode 트래픽 분산, Job managed-by, SPDY → WebSocket 전환
- **Beta**: Pod Certificates, 네이티브 스토리지 버전 마이그레이션, StatefulSet `maxUnavailable`, KYAML, HPA 허용 오차 설정, User Namespaces
- **Alpha**: 갱 스케줄링, Node Declared Features, 제한된 사칭(constrained impersonation)
- 공식 공지: [Kubernetes v1.35: Timbernetes](https://kubernetes.io/blog/2025/12/17/kubernetes-v1-35-release/)

## 폐기 예정·제거 기능과 일정

| 대상 | 발표 | 현재 상태 | 이후 일정 | 대응 |
|---|---|---|---|---|
| cgroup v1 노드 지원 | 1.35 | 1.35부터 kubelet `failCgroupV1` 기본값 `true` (cgroup v1 노드에서 시작 실패) | 이후 버전에서 완전 제거 예정 | 노드 OS를 cgroup v2로 전환. 임시로 `failCgroupV1: false` |
| containerd 1.x | 1.35 | 1.35가 containerd 1.x를 지원하는 마지막 버전 | 1.36부터 containerd 2.0 이상 필요 | 업그레이드 전 런타임 확인 (`kubelet_cri_losing_support` 지표) |
| kube-proxy `ipvs` 모드 | 1.35 | 시작 시 경고 | 1.40쯤 기본 비활성, 1.43쯤 제거 예정 | `nftables` 모드로 전환 |
| Service `.spec.externalIPs` | 1.36 | 사용 시 경고 | 1.43 제거 예정 | LoadBalancer, NodePort, Gateway API |
| `gitRepo` 볼륨 | 1.11 폐기 | **1.36에서 영구 비활성화** | — | init 컨테이너 또는 git-sync 류 도구 |
| kube-dns | 1.37 | 폐기 예정 | 1.40 이후 새 패키지 없음 | CoreDNS로 이전 |
| `kubectl run --filename/-f` | 1.37 | 폐기 예정 | — | `kubectl apply -f` 사용 |
| 스태틱 파드의 Secret·ConfigMap 참조 | 1.37 | **금지** (`PreventStaticPodAPIReferences` 게이트 제거) | — | 스태틱 파드에서 API 객체 참조 제거 |
| Ingress NGINX 컨트롤러 (외부 생태계) | 2025-11 | 2026년 3월까지 최선 노력 유지보수 후 보관(archive) | — | Gateway API 구현체로 이전 |

## 제거된 API 버전과 마이그레이션

공식 「Deprecated API Migration Guide」(2026-10-14 갱신본) 기준으로, **1.33부터 1.37 사이에 제공이 중단된 REST API 버전은 없습니다.** 가장 최근의 제거는 1.32입니다.

| 제거 버전 | 자원 | 제거된 API | 대체 API |
|---|---|---|---|
| 1.32 | FlowSchema, PriorityLevelConfiguration | `flowcontrol.apiserver.k8s.io/v1beta3` | `flowcontrol.apiserver.k8s.io/v1` (1.29부터 제공) |
| 1.29 | FlowSchema, PriorityLevelConfiguration | `flowcontrol.apiserver.k8s.io/v1beta2` | `flowcontrol.apiserver.k8s.io/v1` |
| 1.27 | CSIStorageCapacity | `storage.k8s.io/v1beta1` | `storage.k8s.io/v1` |
| 1.26 | HorizontalPodAutoscaler | `autoscaling/v2beta2` | `autoscaling/v2` |
| 1.25 | CronJob, PodDisruptionBudget 등 | `batch/v1beta1`, `policy/v1beta1` 등 | `batch/v1`, `policy/v1` |

1.37에서 metrics.k8s.io가 `v1`으로 Stable이 되었지만 `v1beta1`은 폐기 정책에 따라 전환 기간 동안 계속 제공됩니다. HPA 실습에서 쓰는 `autoscaling/v2`는 1.23부터 Stable입니다.

### 마이그레이션 방법

1. **사용 중인 폐기 API 찾기** — 폐기된 API를 호출하면 kubectl이 경고를 출력합니다. API 서버의 `apiserver_requested_deprecated_apis` 지표와 감사 로그로도 확인할 수 있습니다.
2. **제거를 미리 시험하기** — 시험용 API 서버에 `--runtime-config=<group>/<version>=false`를 주어 해당 버전을 끈 상태로 매니페스트와 도구를 돌려 봅니다.
3. **매니페스트 변환하기** — `kubectl convert` 플러그인(별도 설치)으로 변환한 뒤 기본값이 달라진 필드를 검토합니다.

```bash shell="실습 터미널"
kubectl convert -f ./my-deployment.yaml --output-version apps/v1
```

4. **API 클라이언트와 컨트롤러 갱신** — 직접 만든 도구가 폐기 API를 쓰고 있다면 클라이언트 라이브러리를 올리고 새 API로 바꿉니다.

## Kubernetes 기능과 외부 생태계 도구의 구분

이 사이트는 각 실습의 「사용 구성 요소」에 둘을 구분해 적습니다.

| 구분 | 이 과정에서 쓰는 것 | 버전이 결정되는 곳 |
|---|---|---|
| Kubernetes 기능 | Pod, Deployment, Service, ConfigMap, Secret, Probe, HPA, RBAC, NetworkPolicy, Pod Security Admission | 클러스터의 Kubernetes 버전 |
| 애드온·외부 구성 요소 | CoreDNS, metrics-server v0.9.0 | minikube 애드온 매니페스트 |
| 외부 생태계 도구 | minikube v1.39.0, Docker, containerd, Calico v3.32.2, Gateway API 구현체 | 각 프로젝트의 릴리스 |

예를 들어 NetworkPolicy는 Kubernetes API이지만 실제 차단은 Calico 같은 CNI가 하므로, 같은 Kubernetes 버전이라도 CNI에 따라 결과가 달라집니다.

## 근거 문서

- [Releases](https://kubernetes.io/releases/) — 지원 버전, 최신 패치, EOL (확인 2026-10-15)
- [Version Skew Policy](https://kubernetes.io/releases/version-skew-policy/)
- [Deprecated API Migration Guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)
- [Kubernetes Deprecation Policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Feature Gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)
- [minikube CHANGELOG v1.39.0](https://github.com/kubernetes/minikube/blob/master/CHANGELOG.md)
