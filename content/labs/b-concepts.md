## 학습 목표

- 명령형과 [[declarative|선언형]] 운영의 차이를 예를 들어 설명할 수 있습니다.
- 「원하는 상태 ↔ 현재 상태」를 맞추는 **제어 루프**가 쿠버네티스의 핵심이라는 것을 압니다.
- [[control-plane|컨트롤 플레인]]과 [[node|노드]]의 구성 요소가 각각 무슨 일을 하는지 그림으로 설명할 수 있습니다.
- CoreDNS·CNI 같은 애드온이 왜 필요한지 압니다.

## 선수 지식

- 컨테이너가 무엇인지 알면 충분합니다. 부족하면 [준비 과정: 리눅스와 컨테이너 복습](#/item/prep-linux-container)을 먼저 보세요.
- 마지막 「직접 확인」은 [환경 준비](#/item/setup)를 마친 뒤 해 봅니다. 모두 읽기만 합니다.

## 개념 1: 쿠버네티스가 해결하는 문제

컨테이너 몇 개는 `docker run`으로 충분합니다. 서버 수십 대에 컨테이너 수백 개가 되면 사람이 할 수 없는 일이 생깁니다.

| 문제 | 사람이 직접 하면 | 쿠버네티스가 |
|---|---|---|
| 어느 서버에 띄울까 | 서버마다 남은 CPU·메모리를 보고 고름 | [[scheduler]]가 자동 배치 |
| 컨테이너가 죽음 | 알림 보고 다시 띄움 | 컨트롤러가 즉시 다시 만듦 |
| 서버가 죽음 | 그 위의 컨테이너를 다른 서버로 옮김 | 다른 노드에 다시 만듦 |
| 새 버전 배포 | 한 대씩 내리고 올림 | [[rolling-update|롤링 업데이트]]·[[rollout|롤백]] |
| 컨테이너 IP가 계속 바뀜 | 설정 파일을 고침 | [[service|Service]]의 고정 이름·IP |
| 트래픽이 늘어남 | 손으로 늘림 | [[hpa|HPA]]로 자동 확장 |

## 개념 2: 명령형 vs 선언형

| | 명령형 | 선언형 |
|---|---|---|
| 말하는 방식 | 「nginx 3개를 **실행해**」 | 「nginx가 3개 **있어야 한다**」 |
| 예 | `kubectl run`, `kubectl scale` | `kubectl apply -f deploy.yaml` |
| 하나가 죽으면 | 2개로 줄어든 채 그대로 | 쿠버네티스가 알아서 다시 3개로 |
| 기록·리뷰 | 명령 기록뿐 | YAML 파일을 Git에 두고 리뷰·되돌리기 |

이 과정은 처음 몇 번을 빼고 **선언형(`apply`)** 으로 진행합니다.

## 개념 3: 원하는 상태와 제어 루프

```text
           ┌──────────── 관찰 ─────────────┐
           ▼                               │
  원하는 상태 (spec: replicas 3)    현재 상태 (status: 실행 중 2)
           │                               ▲
           └─ 비교: 1개 부족 → 행동: 1개 만들기 ┘
                (이 루프를 끝없이 반복)
```

[[deployment|Deployment]] 컨트롤러, [[replicaset|ReplicaSet]] 컨트롤러, 노드 컨트롤러 … 쿠버네티스의 대부분은 이런 **작은 제어 루프들**의 모음입니다. 우리는 `spec`(원하는 상태)만 쓰고, 컨트롤러가 `status`(현재 상태)를 그쪽으로 끌고 갑니다.

## 개념 4: 클러스터 구성

```text
┌──────────────────── 컨트롤 플레인 ────────────────────┐
│  kube-apiserver ◀──── kubectl · 모든 구성 요소의 유일한 창구  │
│      │  ▲                                                  │
│      ▼  │                                                  │
│    etcd (모든 객체를 저장하는 키-값 DB)                       │
│  scheduler          (새 Pod를 어느 노드에 둘지 결정)            │
│  controller-manager (Deployment·ReplicaSet·노드 … 제어 루프들)  │
└────────────────────────────────────────────────────────┘
          ▲ API로 보고·지시 받기            ▲
┌─────── 노드 1 ───────┐           ┌─────── 노드 2 ───────┐
│ kubelet  (Pod를 실제로 띄우고 상태 보고) │  …
│ 컨테이너 런타임 (containerd → runc)  │
│ kube-proxy (Service 주소 → Pod로 전달) │
│ [Pod] [Pod] [Pod]                    │
└──────────────────────┘
```

| 구성 요소 | 어디 | 하는 일 | 고장 나면 |
|---|---|---|---|
| [[kube-apiserver]] | 컨트롤 플레인 | 모든 요청의 입구, 인증·인가·검증 후 etcd에 저장 | kubectl 명령이 모두 실패 (이미 돌던 Pod는 계속 돎) |
| [[etcd]] | 컨트롤 플레인 | 클러스터의 모든 상태 저장 | 클러스터의 기억 상실 — 백업이 가장 중요 |
| [[scheduler]] | 컨트롤 플레인 | 새 Pod를 둘 노드 선택 | 새 Pod가 `Pending`에 머묾 |
| [[controller-manager]] | 컨트롤 플레인 | 제어 루프 실행 | 죽은 Pod가 다시 안 생김 |
| [[kubelet]] | 각 노드 | 그 노드에 배정된 Pod를 런타임으로 실행·감시 | 그 노드의 Pod 관리 중단, 노드 `NotReady` |
| [[container-runtime|컨테이너 런타임]] | 각 노드 | 이미지 받기·컨테이너 실행 (containerd) | 컨테이너 시작 실패 |
| [[kube-proxy]] | 각 노드 | Service의 가상 IP를 실제 Pod로 연결 | Service 접속 실패 |

**모든 구성 요소는 서로 직접 말하지 않고 kube-apiserver를 통해서만** 정보를 주고받습니다. 그래서 「API 서버가 쿠버네티스의 중심」이라고 합니다.

## 개념 5: 애드온

| 애드온 | 하는 일 | 없으면 |
|---|---|---|
| **CoreDNS** ([[cluster-dns]]) | `web.default.svc.cluster.local` 같은 Service 이름을 IP로 | Pod가 이름으로 서로 찾지 못함 |
| **[[cni|CNI]] 플러그인** (Flannel·Calico·Cilium…) | Pod마다 IP를 주고 노드 사이 통신 연결 | Pod가 `ContainerCreating`에 머물고 노드가 `NotReady` |
| metrics-server | CPU·메모리 사용량 수집 | `kubectl top`·HPA 동작 안 함 (중급 2) |

CNI는 시리즈의 **CNI 항해도**(`/cni/`)에서 깊게 다룹니다.

## 직접 확인 (선택)

```bash shell="실습 터미널"
kubectl get nodes -o custom-columns='NAME:.metadata.name,STATUS:.status.conditions[-1].type,VERSION:.status.nodeInfo.kubeletVersion,RUNTIME:.status.nodeInfo.containerRuntimeVersion'
kubectl get pods -n kube-system --no-headers -o custom-columns='N:.metadata.name,S:.status.phase' | sed -E 's/-[a-z0-9]{8,10}-[a-z0-9]{5} / /; s/-[a-z0-9]{5} / /; s/-k8s-lab / /' | sort | awk '{printf "%-26s %s\n", $1, $2}'
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
NAME      STATUS   VERSION   RUNTIME
k8s-lab   Ready    v1.37.0   containerd://2.2.1
coredns                    Running
etcd                       Running
kindnet                    Running
kube-apiserver             Running
kube-controller-manager    Running
kube-proxy                 Running
kube-scheduler             Running
storage-provisioner        Running
```

minikube는 노드 하나가 컨트롤 플레인과 워커를 겸합니다. 컨트롤 플레인 구성 요소(etcd·apiserver·scheduler·controller-manager)도 `kube-system` 네임스페이스의 **Pod**로 돌고 있습니다. kubelet과 containerd는 Pod가 아니라 노드의 프로세스라 목록에 없습니다.

## 확인 질문

:::answer 1. kube-apiserver가 멈췄다. 이미 돌고 있던 웹 Pod는?
계속 돕니다. 다만 새 배포·스케일·자동 복구처럼 API를 거쳐야 하는 일은 멈춥니다.
:::

:::answer 2. 새로 만든 Pod가 몇 분째 Pending이다. 가장 먼저 의심할 구성 요소는?
scheduler가 둘 곳을 찾지 못한 것입니다. `kubectl describe pod`의 Events에서 이유(자원 부족, taint 등)를 봅니다.
:::
