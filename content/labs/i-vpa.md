## 학습 목표

- [[vpa|VerticalPodAutoscaler(VPA)]]가 [[hpa|HPA]]와 무엇이 다른지(개수가 아니라 **크기**를 바꿈) 설명할 수 있습니다.
- VPA의 세 구성 요소(recommender·updater·admission controller)와 갱신 모드 `Off`·`Initial`·`Recreate`(옛 `Auto`)·`InPlaceOrRecreate`를 구분할 수 있습니다.
- **추천만 받는(`Off`) 모드**로 실제 사용량에 맞는 requests 추천값을 읽을 수 있습니다.
- VPA가 requests를 바꾸면 파드가 **새로 만들어진다**는 점과, 같은 지표로 HPA와 함께 쓰면 안 되는 이유를 압니다.

## 선수 지식

- [중급 2 「자원 요청·제한과 HorizontalPodAutoscaler」](#/item/i-lab02): requests·limits, [[metrics-server]], HPA 계산(6단계)
- 이 과정은 **선택 심화**입니다. VPA는 쿠버네티스 본체가 아니라 [kubernetes/autoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler) 저장소의 **애드온**이라, 설치·버전 관리를 직접 합니다.

:::note 검증 범위
**Kubernetes v1.37.0 + VPA 1.8.1** 조합에서 설치 → 추천(`Off`) → `Initial` 반영 → 정리까지 실제로 실행했고, 출력 블록은 그 결과입니다(2026-10-30, minikube v1.38.1). Kubernetes **1.36**은 VPA 1.8.1의 호환 범위지만 실행하지 않았고, **1.35용 VPA 1.7.3**도 실행하지 않았습니다 — 명령은 같지만 출력·기본값이 다를 수 있습니다. 추천 숫자는 PC 성능과 측정 시간에 따라 달라집니다.
:::

## 개념: 개수(HPA)가 아니라 크기(VPA)

**무엇인가.** HPA는 파드 **개수**를 바꾸고, VPA는 파드 하나의 **requests(크기)** 를 바꿉니다. 「requests를 얼마로 적어야 하지?」라는 질문에, 실제 사용량 기록을 보고 답을 추천해 주는 도구입니다.

**왜 필요한가.** [중급 2](#/item/i-lab02)에서 본 것처럼 requests는 스케줄링과 HPA 계산의 기준인데, 처음 적는 값은 대개 짐작입니다. 너무 크면 노드 자리가 낭비되고, 너무 작으면 노드가 붐빌 때 밀리거나(CPU) 쫓겨납니다(메모리).

**어떻게 동작하나.**

| 구성 요소 | 하는 일 |
|---|---|
| recommender | metrics-server의 사용량을 1분마다 모아 컨테이너별 추천값(target·lowerBound·upperBound)을 계산해 VPA 객체의 `status`에 씀. 기록은 반감기 24시간으로 오래된 것의 무게를 줄임 |
| updater | 추천과 지금 requests가 크게 다른 파드를 골라 **축출**(재생성)하거나 제자리에서 크기 변경 (모드에 따라) |
| admission controller | 파드가 **만들어질 때** requests를 추천값으로 바꿔 넣는 웹훅 |

| `updateMode` | 새 파드 만들 때 | 실행 중 파드 | 쓰는 때 |
|---|---|---|---|
| `Off` | 바꾸지 않음 | 바꾸지 않음 | **추천만 받기** — 처음 도입할 때 가장 안전 |
| `Initial` | 추천값으로 | 바꾸지 않음 | 다음 배포·재시작 때만 반영 |
| `Recreate` (기본값) | 추천값으로 | 크게 다르면 **축출해 다시 만듦** (PDB 존중) | 재시작이 괜찮은 워크로드 |
| `InPlaceOrRecreate` | 추천값으로 | 제자리 크기 변경, 안 되면 축출 | in-place 리사이즈를 쓰는 환경 |
| `Auto` | — | — | **폐기 예정.** 지금은 `Recreate`와 같음 → 명시적 모드를 씀 |

이 밖에 축출 없이 제자리 변경만 하는 `InPlace` 모드가 있습니다(기능 게이트 필요). 모드 이름과 기본값은 VPA 버전마다 바뀌어 왔으니 쓰는 버전의 `docs/quickstart.md`를 확인합니다.

## 버전 고정

| 쿠버네티스(이 시리즈) | VPA | 근거 |
|---|---|---|
| 1.37 · 1.36 | **1.8.1** | VPA 1.8.x 호환 표: Kubernetes 1.36 – 1.38 |
| 1.35 | **1.7.3** | VPA 1.7.x 호환 표: Kubernetes 1.35 – 1.37 |

이미지 태그(`registry.k8s.io/autoscaling/vpa-recommender:1.8.1` 등)는 저장소의 같은 태그에 들어 있는 `deploy/*.yaml`에 고정되어 있습니다.

## 1단계: metrics-server와 VPA 설치

recommender는 metrics-server의 지표를 씁니다([중급 2의 4단계](#/item/i-lab02)와 같음).

```bash shell="실습 터미널" run=skip
minikube addons enable metrics-server -p k8s-lab
kubectl top nodes                      # 숫자가 나올 때까지 1~2분 기다림
```

공식 설치 방법은 저장소를 해당 태그로 받아 `hack/vpa-up.sh`를 실행하는 것입니다. 스크립트가 CRD·RBAC·세 구성 요소를 `kube-system`에 만들고, admission controller용 인증서를 openssl로 만듭니다(openssl 1.1.1 이상). `master` 브랜치가 아니라 **버전 태그**를 받고, 실행 전에 `hack/vpa-up.sh`와 `deploy/*.yaml`을 한 번 읽어 보세요. autoscaler 저장소는 크므로 VPA 폴더만 받는 부분 복제(sparse checkout, git 2.25 이상)를 씁니다.

```bash shell="실습 터미널" run=skip
VPA_TAG=vertical-pod-autoscaler-1.8.1          # Kubernetes 1.35라면 vertical-pod-autoscaler-1.7.3
git clone --depth 1 --filter=blob:none --sparse --branch "$VPA_TAG" https://github.com/kubernetes/autoscaler.git ~/vpa-src
git -C ~/vpa-src sparse-checkout set vertical-pod-autoscaler   # 큰 저장소에서 VPA 폴더만 받음
cd ~/vpa-src/vertical-pod-autoscaler && ./hack/vpa-up.sh
kubectl -n kube-system get deploy vpa-recommender vpa-updater vpa-admission-controller
kubectl get crd verticalpodautoscalers.autoscaling.k8s.io
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · docker 런타임 · VPA 1.8.1)" date="2026-10-30"
NAME                       READY   UP-TO-DATE   AVAILABLE   AGE
vpa-recommender            1/1     1            1           14s
vpa-updater                1/1     1            1           14s
vpa-admission-controller   1/1     1            1           14s
NAME                                        CREATED AT
verticalpodautoscalers.autoscaling.k8s.io   2026-10-29T20:24:07Z
```

- `vpa-up.sh`는 맨 앞에서 `git switch --detach vertical-pod-autoscaler-1.8.1`로 태그를 다시 확인하고(`HEAD is now at de59752 …`), CRD 2개·RBAC·세 Deployment·웹훅용 Service를 만듭니다. 웹훅 인증서는 `/tmp/vpa-certs`에서 만들어 Secret `vpa-tls-certs`로 올린 뒤 임시 폴더를 지웁니다.
- 스크립트 안의 `kubectl apply`는 실패해도 `|| true`로 넘어가므로, 위처럼 **세 Deployment가 1/1인지 직접** 확인합니다.
- admission controller는 시작하고 약 10초 뒤 스스로 웹훅을 등록합니다. `kubectl get mutatingwebhookconfiguration vpa-webhook-config`가 바로 NotFound여도 잠시 뒤 다시 보면 생깁니다.

## 2단계: 추천만 받기 (`updateMode: "Off"`)

requests를 일부러 작게(CPU 50m) 적고 CPU를 꾸준히 쓰는 앱입니다. VPA는 `Off`라 아무것도 바꾸지 않고 추천만 계산합니다.

```yaml file=vpa-demo.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lab-vpa
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vpa-demo
  namespace: lab-vpa
spec:
  replicas: 2
  selector:
    matchLabels: { app: vpa-demo }
  template:
    metadata:
      labels: { app: vpa-demo }
    spec:
      containers:
        - name: app
          image: busybox:1.37.0
          # 0.5초 일하고 0.5초 쉼 → 대략 CPU 절반 정도를 꾸준히 씀
          command: ["sh", "-c", "while true; do timeout 0.5 sh -c 'while :; do :; done'; sleep 0.5; done"]
          resources:
            requests: { cpu: 50m, memory: 16Mi }
            limits: { cpu: "1", memory: 64Mi }
---
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: vpa-demo
  namespace: lab-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vpa-demo
  updatePolicy:
    updateMode: "Off"
```

```bash shell="실습 터미널" run=skip
kubectl apply -f vpa-demo.yaml
sleep 180                                   # recommender는 1분마다 계산 — 첫 추천까지 몇 분
kubectl get vpa vpa-demo -n lab-vpa
kubectl get vpa vpa-demo -n lab-vpa -o jsonpath='{range .status.recommendation.containerRecommendations[*]}{.containerName}: target={.target} lower={.lowerBound} upper={.upperBound} uncapped={.uncappedTarget}{"\n"}{end}'
kubectl get pod -n lab-vpa -l app=vpa-demo -o jsonpath='{.items[0].spec.containers[0].resources.requests}{"\n"}'
kubectl top pod -n lab-vpa --no-headers
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · docker 런타임 · VPA 1.8.1)" date="2026-10-30"
NAME       MODE   CPU    MEM     PROVIDED   AGE
vpa-demo   Off    587m   250Mi   True       3m13s
app: target={"cpu":"587m","memory":"250Mi"} lower={"cpu":"198m","memory":"250Mi"} upper={"cpu":"423227m","memory":"8291500000"} uncapped={"cpu":"587m","memory":"250Mi"}
{"cpu":"50m","memory":"16Mi"}
vpa-demo-7b8fbcc49c-8dwx5   498m   2Mi
vpa-demo-7b8fbcc49c-xz269   502m   3Mi
```

- **대기 시간**: 검증 환경에서는 파드가 뜬 뒤 **약 30초** 만에 첫 추천이 생겼습니다(recommender가 1분 주기로 계산). 환경에 따라 몇 분 걸릴 수 있어 `sleep 180`을 둡니다.
- **target**이 추천값입니다. 실제 사용량(`kubectl top`, 파드당 약 500m)보다 약간 높게 잡혔습니다. **uncappedTarget**은 `resourcePolicy`의 최소·최대 제한을 적용하기 전 값으로, 제한이 없는 지금은 target과 같습니다.
- **lowerBound·upperBound**는 범위입니다. 기록이 몇 분뿐인 지금은 upperBound가 CPU 423코어·메모리 약 8GB처럼 **터무니없이 넓습니다** — 기록이 짧을수록 신뢰도를 낮게 잡아 범위를 넓히기 때문이고, 며칠 동안 기록이 쌓이면 좁아집니다. 이 숫자로 판단하지 않습니다.
- 메모리 추천은 파드당 최솟값(기본 250MB)보다 작아지지 않습니다. 그래서 메모리를 거의 안 쓰는 이 앱(2~3Mi)도 `250Mi`가 추천됩니다. 최솟값은 recommender 옵션(`--pod-recommendation-min-memory-mb`)입니다.
- 실행 중 파드의 requests는 여전히 `50m`입니다. 3분 동안 파드 이름·재시작 수·requests 모두 그대로였습니다 — `Off`는 **읽기만** 합니다.

## 3단계: 만들 때만 반영 (`Initial`) — requests 변경은 파드 재생성

모드를 `Initial`로 바꾸고, 실행 중인 파드가 그대로인지 봅니다.

```bash shell="실습 터미널" run=skip
kubectl patch vpa vpa-demo -n lab-vpa --type=merge -p '{"spec":{"updatePolicy":{"updateMode":"Initial"}}}'
kubectl get pod -n lab-vpa -l app=vpa-demo -o custom-columns='NAME:.metadata.name,CPU:.spec.containers[0].resources.requests.cpu'
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · docker 런타임 · VPA 1.8.1)" date="2026-10-30"
verticalpodautoscaler.autoscaling.k8s.io/vpa-demo patched
NAME                        CPU
vpa-demo-7b8fbcc49c-8dwx5   50m
vpa-demo-7b8fbcc49c-xz269   50m
```

파드를 다시 만들게 합니다(배포·재시작과 같은 상황).

```bash shell="실습 터미널" run=skip
kubectl rollout restart deployment/vpa-demo -n lab-vpa && kubectl rollout status deployment/vpa-demo -n lab-vpa | tail -1
sleep 35                                    # 옛 파드의 종료 유예(30초)가 끝날 때까지
kubectl get pod -n lab-vpa -l app=vpa-demo -o custom-columns='NAME:.metadata.name,CPU:.spec.containers[0].resources.requests.cpu,LIMIT:.spec.containers[0].resources.limits.cpu'
kubectl get deploy vpa-demo -n lab-vpa -o jsonpath='Deployment 템플릿: {.spec.template.spec.containers[0].resources.requests}{"\n"}'
kubectl get pod -n lab-vpa -l app=vpa-demo -o jsonpath='{.items[0].metadata.annotations.vpaUpdates}{"\n"}'
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · docker 런타임 · VPA 1.8.1)" date="2026-10-30"
deployment.apps/vpa-demo restarted
deployment "vpa-demo" successfully rolled out
NAME                       CPU    LIMIT
vpa-demo-566bdbfb9-949mq   587m   11740m
vpa-demo-566bdbfb9-t8l9q   587m   11740m
Deployment 템플릿: {"cpu":"50m","memory":"16Mi"}
Pod resources updated by vpa-demo: container 0: cpu request, memory request, cpu limit, memory limit
```

- 모드를 바꿔도 **실행 중인 파드는 그대로**입니다. 새로 만들어진 파드에만 admission controller가 추천값을 넣었고, 파드 주석 `vpaUpdates`에 그 기록이 남습니다. Deployment 템플릿(`50m`)은 바뀌지 않았습니다 — 값은 파드가 만들어지는 순간 웹훅이 바꿉니다.
- limits도 원래 비율(requests 50m : limits 1 = 1:20)을 지키며 함께 커졌습니다(`controlledValues: RequestsAndLimits`가 기본). 비율이 큰 limits는 이렇게 노드 크기를 넘어설 수 있어, `resourcePolicy`로 최대값(`maxAllowed`)을 두는 것이 안전합니다.
- 검증 때 `sleep 35` 없이 바로 조회하면 종료 중인 옛 파드(50m) 2개가 함께 보였습니다. 새 파드(587m)와 옛 파드가 섞여 보여도 정상입니다.
- `Recreate`(기본값)로 두면 updater가 1분마다 보고, 추천과 크게 다른 파드를 **축출**해 같은 방식으로 다시 만들게 합니다. VPA 1.8.1 기본 설정(`--min-replicas=2`)에서는 복제본이 2개 미만인 워크로드를 축출하지 않습니다. 이 과정은 `Recreate` 축출을 실행해 보지는 않았습니다.

## 4단계: HPA와 함께 쓸 때

| 조합 | 결과 |
|---|---|
| HPA(CPU 사용률) + VPA(CPU) | **쓰면 안 됨.** HPA는 사용량 ÷ **requests**로 개수를 정하는데, VPA가 requests를 바꾸면 사용률이 흔들려 두 컨트롤러가 서로 반대로 움직일 수 있음 (공식 Known limitations) |
| HPA(CPU) + VPA(메모리만) | 가능 — VPA의 `controlledResources: ["memory"]` |
| HPA(사용자 정의·외부 지표) + VPA | 가능 — 서로 다른 신호 |
| VPA `Off` + 사람이 판단 | 가장 흔한 시작점 — 추천을 보고 YAML의 requests를 고침 |

HPA가 CPU로 개수를 정할 때 VPA는 메모리만 관리하게 하는 설정입니다. API 서버가 이 필드를 받아들이는지 저장하지 않고(`--dry-run=server`) 확인합니다.

```bash shell="실습 터미널" run=skip
kubectl apply --dry-run=server -f - <<'YAML'
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: vpa-memory-only
  namespace: lab-vpa
spec:
  targetRef: {apiVersion: apps/v1, kind: Deployment, name: vpa-demo}
  updatePolicy: {updateMode: "Off"}
  resourcePolicy:
    containerPolicies:
      - containerName: "*"
        controlledResources: ["memory"]
        maxAllowed: {memory: 1Gi}
YAML
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · docker 런타임 · VPA 1.8.1)" date="2026-10-30"
verticalpodautoscaler.autoscaling.k8s.io/vpa-memory-only created (server dry run)
```

## 적용하면 안 되는 상황

| 상황 | 이유 |
|---|---|
| 재시작이 곧 장애인 단일 복제본 서비스에 `Recreate` | 크기를 바꾸려면 파드를 다시 만듦 (축출) |
| 같은 지표로 HPA가 이미 있음 | 위의 충돌 |
| 짧게 돌고 끝나는 Job | 추천이 쌓이기 전에 끝남 |
| 부하가 몇 분 단위로 크게 출렁임 | 추천이 따라가지 못함 → HPA가 맞음 |
| 노드보다 큰 추천이 나올 수 있는 워크로드에 `maxAllowed` 없음 | 다시 만든 파드가 `Pending` (공식 Known limitations) |
| 컨트롤러 없이 만든 단독 파드 | VPA가 갱신하지 않음 |

## 환경의 한계

- 이 실습 클러스터(노드 1대·몇 분 측정)의 추천은 **동작 확인용**입니다. 운영에서는 평소·최대 부하를 포함한 며칠치 기록을 보고 판단합니다.
- recommender는 기본으로 메모리에 기록을 쌓아, 다시 시작하면 기록이 비고 처음부터 다시 쌓습니다(Prometheus 기록을 쓰는 설정은 공식 문서 참고).
- 추천은 「자리를 얼마나 잡을지」이고 성능 보장이 아닙니다. 성능은 부하 시험으로 확인합니다([중급 2의 6·7단계](#/item/i-lab02)).

## 성공 판정

```verify
id: vpa-recommend
title: VPA가 컨테이너 CPU 추천값을 계산함
explain: vpa-demo VPA의 첫 컨테이너 추천 target CPU를 출력합니다. 2단계 후 몇 분 기다린 뒤 실행하세요.
command: kubectl get vpa vpa-demo -n lab-vpa -o jsonpath='{.status.recommendation.containerRecommendations[0].target.cpu}{"\n"}'
expect: ^[0-9]+m?$
criteria: 숫자(예: 587m)가 출력됨
```

## 정리

```bash shell="실습 터미널" run=skip
kubectl delete namespace lab-vpa
cd ~/vpa-src/vertical-pod-autoscaler && ./hack/vpa-down.sh
cd ~ && rm -rf ~/vpa-src
kubectl get crd verticalpodautoscalers.autoscaling.k8s.io       # NotFound면 VPA 제거 완료
minikube addons disable metrics-server -p k8s-lab               # 다른 실습에서 계속 쓰면 생략
```

검증 때는 별도 프로필에서 실행했고, `vpa-down.sh`가 지우는 RBAC 줄 수십 개는 줄였습니다. `Error from server (NotFound)`가 **정상** 결과입니다.

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · docker 런타임 · VPA 1.8.1)" date="2026-10-30"
namespace "lab-vpa" deleted
customresourcedefinition.apiextensions.k8s.io "verticalpodautoscalercheckpoints.autoscaling.k8s.io" deleted
customresourcedefinition.apiextensions.k8s.io "verticalpodautoscalers.autoscaling.k8s.io" deleted
…
Deleting VPA Admission Controller certs.
secret "vpa-tls-certs" deleted from kube-system namespace
Unregistering VPA admission controller webhook
mutatingwebhookconfiguration.admissionregistration.k8s.io "vpa-webhook-config" deleted
service "vpa-webhook" deleted from kube-system namespace
deployment.apps "vpa-admission-controller" deleted from kube-system namespace
Error from server (NotFound): customresourcedefinitions.apiextensions.k8s.io "verticalpodautoscalers.autoscaling.k8s.io" not found
```
