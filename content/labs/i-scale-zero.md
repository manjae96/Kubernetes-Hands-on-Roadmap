## 학습 목표

- CPU·메모리 지표만으로는 [[hpa|HPA]]가 0까지 줄일 수 없는 이유를 설명할 수 있습니다.
- Object·External 지표와 그 지표를 쿠버네티스 API로 내어 주는 **어댑터**의 역할을 압니다.
- `minReplicas: 0`인 HPA로 큐가 비면 0, 메시지가 쌓이면 다시 늘어나는 것을 확인할 수 있습니다.
- `ScaledToZero` 조건으로 「HPA가 0으로 줄였는지」, 「사람이 0으로 만들었는지」를 구분할 수 있습니다.

## 선수 지식

- [중급 2 「자원 요청·제한과 HorizontalPodAutoscaler」](#/item/i-lab02): HPA·[[metrics-server]]
- **Kubernetes 1.37 이상**: 이 기능(`HPAScaleToZero`)은 1.37에서 베타가 되어 기본으로 켜져 있습니다. 1.36 이하에서는 API 서버와 컨트롤러 매니저에 기능 게이트를 직접 켜야 합니다.
- **Helm**: 어댑터 설치에 씁니다(시리즈의 헬름 항해도 환경 준비 참고).

```bash shell="실습 터미널"
kubectl version -o json | python3 -c 'import json,sys; print("서버", json.load(sys.stdin)["serverVersion"]["gitVersion"])'
kubectl get --raw /metrics | grep 'feature_enabled{name="HPAScaleToZero"'
helm version --short | cut -d. -f1
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
서버 v1.37.0
kubernetes_feature_enabled{name="HPAScaleToZero",stage="BETA"} 1
v4
```

## 개념 1: 왜 CPU로는 0이 안 되나

HPA는 「지금 지표 ÷ 목표 × 현재 파드 수」로 원하는 파드 수를 계산합니다. CPU·메모리는 **파드가 내는 값**이라, 파드가 0개면 잴 것이 없어 다시 늘릴 근거도 사라집니다. 그래서 0까지 줄이려면 **파드 밖에 있는 지표**가 필요합니다.

| 지표 종류 | 출처 | 파드 0개일 때 | `minReplicas: 0` |
|---|---|---|---|
| Resource (CPU·메모리) | 파드 (metrics-server) | 값 없음 | 이것만으로는 불가 |
| Pods | 파드마다 낸 지표 평균 | 값 없음 | 이것만으로는 불가 |
| **Object** | 다른 쿠버네티스 객체 (예: Ingress의 요청 수) | 값 있음 | 가능 |
| **External** | 클러스터 밖 (큐 길이, 클라우드 지표) | 값 있음 | 가능 |

직접 확인합니다. CPU 지표만 둔 HPA에 `minReplicas: 0`을 주면 API 서버가 거부합니다.

```bash shell="실습 터미널"
kubectl create namespace scale0 >/dev/null && echo "scale0 준비됨"
cat <<'EOF' | kubectl apply --dry-run=server -f - 2>&1 | sed 's/.*is invalid: //'
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: cpu-zero, namespace: scale0 }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: worker }
  minReplicas: 0
  maxReplicas: 5
  metrics: [{ type: Resource, resource: { name: cpu, target: { type: Utilization, averageUtilization: 50 } } }]
EOF
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
scale0 준비됨
spec.metrics: Forbidden: must specify at least one Object or External metric to support scaling to zero replicas
```

## 개념 2: 어댑터 — 지표를 쿠버네티스 API로

HPA 컨트롤러는 Prometheus를 직접 모릅니다. `external.metrics.k8s.io`·`custom.metrics.k8s.io` 같은 **집계 API**(APIService)에 묻고, 그 뒤에서 **어댑터**가 실제 지표 저장소에 질의합니다. 어댑터는 쿠버네티스 본체가 아니라 생태계 도구라 따로 설치합니다.

```text
 큐 작업자 (예: 주문 처리)          queue_messages_ready{queue="orders"} = 25
       ▲ 늘리기/줄이기                      │ push (이 실습에서는 큐 대신 Pushgateway에 직접 기록)
 HPA 컨트롤러 ──묻기──▶ external.metrics.k8s.io ──▶ prometheus-adapter ──PromQL──▶ Prometheus ──scrape──▶ Pushgateway
```

| 어댑터 | 특징 |
|---|---|
| **prometheus-adapter** (이 실습) | Prometheus 지표를 custom·external API로. 규칙(YAML)으로 이름·라벨 대응 |
| KEDA | 큐·DB·클라우드 등 수십 가지 「스케일러」 내장. 자체적으로 0↔1을 처리하고 1 이상은 HPA를 만들어 맡김 |
| 클라우드 어댑터 | 클라우드 모니터링 지표(SQS 길이 등)를 external로 |

## 1단계: 지표 저장소와 어댑터 설치

실습용으로 Prometheus와 Pushgateway를 클러스터 안에 가장 단순하게 띄웁니다.

```yaml file=scale0/metrics.yaml
apiVersion: v1
kind: Namespace
metadata: { name: metrics-lab }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: pushgateway, namespace: metrics-lab }
spec:
  selector: { matchLabels: { app: pushgateway } }
  template:
    metadata: { labels: { app: pushgateway } }
    spec: { containers: [{ name: pushgateway, image: prom/pushgateway:v1.11.4, ports: [{ containerPort: 9091 }] }] }
---
apiVersion: v1
kind: Service
metadata: { name: pushgateway, namespace: metrics-lab }
spec: { selector: { app: pushgateway }, ports: [{ port: 9091 }] }
---
apiVersion: v1
kind: ConfigMap
metadata: { name: prometheus, namespace: metrics-lab }
data:
  prometheus.yml: |
    global: { scrape_interval: 5s }
    scrape_configs:
      - job_name: pushgateway
        honor_labels: true
        static_configs: [{ targets: ["pushgateway:9091"] }]
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: prometheus, namespace: metrics-lab }
spec:
  selector: { matchLabels: { app: prometheus } }
  template:
    metadata: { labels: { app: prometheus } }
    spec:
      containers:
        - name: prometheus
          image: prom/prometheus:v3.15.0
          args: ["--config.file=/etc/prometheus/prometheus.yml"]
          ports: [{ containerPort: 9090 }]
          volumeMounts: [{ name: config, mountPath: /etc/prometheus }]
      volumes: [{ name: config, configMap: { name: prometheus } }]
---
apiVersion: v1
kind: Service
metadata: { name: prometheus, namespace: metrics-lab }
spec: { selector: { app: prometheus }, ports: [{ port: 9090 }] }
```

어댑터 규칙: Prometheus의 `queue_messages_ready`를 External 지표 `queue_messages_ready`로 내어 주고, 지표의 `namespace` 라벨로 어느 네임스페이스의 HPA에 보일지 정합니다.

```yaml file=scale0/adapter-values.yaml
prometheus:
  url: http://prometheus.metrics-lab.svc
  port: 9090
rules:
  default: false                    # 기본 규칙(수백 개 지표)은 끄고 필요한 것만
  external:
    - seriesQuery: 'queue_messages_ready{namespace!=""}'
      resources:
        overrides:
          namespace: { resource: namespace }
      name: { as: queue_messages_ready }
      metricsQuery: 'sum(<<.Series>>{<<.LabelMatchers>>}) by (queue)'
```

```bash shell="실습 터미널" timeout=600
cd ~/k8s-lab
kubectl apply -f scale0/metrics.yaml >/dev/null
kubectl -n metrics-lab rollout status deploy/prometheus --timeout=180s | tail -1
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1; helm repo update prometheus-community >/dev/null
helm install prometheus-adapter prometheus-community/prometheus-adapter --version 5.3.0 \
  -n metrics-lab -f scale0/adapter-values.yaml --wait --timeout 5m >/dev/null && echo "어댑터 설치됨"
kubectl get apiservice v1beta1.external.metrics.k8s.io -o custom-columns='APISERVICE:.metadata.name,SERVICE:.spec.service.name,AVAILABLE:.status.conditions[0].status'
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
deployment "prometheus" successfully rolled out
어댑터 설치됨
APISERVICE                        SERVICE              AVAILABLE
v1beta1.external.metrics.k8s.io   prometheus-adapter   True
```

## 2단계: 큐 작업자와 0까지 줄이는 HPA

```yaml file=scale0/worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata: { name: worker, namespace: scale0 }
spec:
  replicas: 1
  selector: { matchLabels: { app: worker } }
  template:
    metadata: { labels: { app: worker } }
    spec: { containers: [{ name: worker, image: busybox:1.37.0, command: ["sleep", "3600"] }] }   # 큐를 처리하는 작업자 자리
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: worker, namespace: scale0 }
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: worker }
  minReplicas: 0                    # ← 0까지
  maxReplicas: 5
  metrics:
    - type: External
      external:
        metric:
          name: queue_messages_ready
          selector: { matchLabels: { queue: orders } }
        target: { type: AverageValue, averageValue: "10" }   # 작업자 하나당 메시지 10개
  behavior:
    scaleDown: { stabilizationWindowSeconds: 0 }   # 실습용: 바로 줄임 (기본 300초)
```

큐 길이를 바꾸는 도우미 함수입니다(실제로는 큐가 스스로 지표를 냄).

```bash shell="실습 터미널"
cd ~/k8s-lab
kubectl apply -f scale0/worker.yaml >/dev/null
queue() { kubectl -n metrics-lab run push-$RANDOM --rm -i --restart=Never --quiet --image=curlimages/curl:8.17.0 -- \
  sh -c "echo 'queue_messages_ready{queue=\"orders\"} $1' | curl -s --data-binary @- http://pushgateway:9091/metrics/job/queue/namespace/scale0" >/dev/null 2>&1; }
replicas() { kubectl -n scale0 get deploy worker -o jsonpath='{.spec.replicas}'; }
queue 25
until [ "$(replicas)" = 3 ]; do sleep 5; done
kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1/namespaces/scale0/queue_messages_ready?labelSelector=queue%3Dorders" \
  | python3 -c 'import json,sys; [print("External 지표:", i["metricName"], i["metricLabels"], i["value"]) for i in json.load(sys.stdin)["items"]]'
echo "메시지 25개 → 작업자 $(replicas)개 (25 ÷ 10 = 2.5 → 올림)"
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
External 지표: queue_messages_ready {'queue': 'orders'} 25
메시지 25개 → 작업자 3개 (25 ÷ 10 = 2.5 → 올림)
```

## 3단계: 큐가 비면 0, 다시 차면 깨어남

```bash shell="실습 터미널"
cd ~/k8s-lab
cond() { kubectl -n scale0 get hpa worker -o jsonpath='{range .status.conditions[?(@.type=="ScaledToZero")]}{.type}={.status} ({.reason}){end}'; }
queue 0
until [ "$(replicas)" = 0 ]; do sleep 5; done
echo "큐 0 → 작업자 $(replicas)개 · $(cond)"
queue 12
until [ "$(replicas)" = 2 ]; do sleep 5; done
echo "큐 12 → 작업자 $(replicas)개 · $(cond)"
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
큐 0 → 작업자 0개 · ScaledToZero=True (ScaledToZero)
큐 12 → 작업자 2개 · ScaledToZero=False (NotScaledToZero)
```

| 조건 | 뜻 |
|---|---|
| `ScaledToZero=True (ScaledToZero)` | **HPA가 지표를 보고** 0으로 줄였음 → 지표가 오르면 HPA가 다시 늘림 |
| `ScaledToZero=False (NotScaledToZero)` | 지금 0이 아니거나, 0이어도 HPA가 만든 0이 아님 |

## 4단계: 사람이 0으로 만들면

예전부터 `kubectl scale --replicas=0`은 「이 HPA를 잠시 멈춤」으로 쓰여 왔습니다. 이 약속을 깨지 않기 위해, HPA는 **자기가 줄인 0**(ScaledToZero=True)만 다시 늘리고, 사람이 만든 0은 그대로 둡니다.

```bash shell="실습 터미널"
cd ~/k8s-lab
kubectl -n scale0 scale deploy worker --replicas=0 >/dev/null
queue 30; sleep 40
echo "큐 30인데 작업자 $(replicas)개"
kubectl -n scale0 get hpa worker -o jsonpath='{range .status.conditions[?(@.type=="ScalingActive")]}{.type}={.status} ({.reason}){"\n"}{end}'
echo "$(cond)"
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
큐 30인데 작업자 0개
ScalingActive=False (ScalingDisabled)
ScaledToZero=False (NotScaledToZero)
```

- 사람이 0으로 만들면 `ScalingActive=False (ScalingDisabled)`가 되고 큐가 쌓여도 늘리지 않습니다. 다시 맡기려면 `kubectl scale --replicas=1`로 1 이상을 만들어 줍니다.
- 운영 중 「HPA가 왜 안 늘리지?」 하면 먼저 이 두 조건(`ScalingActive`, `ScaledToZero`)을 봅니다.

## 생각할 점

| 주제 | 내용 |
|---|---|
| 콜드 스타트 | 0에서 늘릴 때 이미지 받기·앱 시작 시간만큼 첫 처리가 늦음. 큐 작업처럼 **기다려도 되는 일**에 적합, 사용자 요청을 직접 받는 웹에는 신중히 |
| 지표 지연 | 큐 → Prometheus 수집 → 어댑터 → HPA(기본 15초 주기)까지 수십 초. 이 실습도 몇십 초씩 걸림 |
| 어댑터가 죽으면 | 지표를 못 읽어 HPA가 판단을 멈춤(`ScalingActive=False`). 0인 채로 머물 수 있으니 어댑터도 감시 대상 |
| PodDisruptionBudget | `minAvailable: 1` 같은 PDB는 0과 맞지 않음 (자발적 중단 차단) |

## 성공 판정

```verify
id: iszero-manual
title: HPA가 만든 0과 사람이 만든 0을 구분
explain: 사람이 0으로 줄인 뒤 HPA의 두 조건을 봅니다.
command: kubectl -n scale0 get hpa worker -o jsonpath='{range .status.conditions[*]}{.type}={.status} {.reason}{"\n"}{end}' | grep -E '^(ScalingActive|ScaledToZero)'
expect: ScalingActive=False ScalingDisabled\s*\nScaledToZero=False NotScaledToZero
criteria: ScalingActive=False ScalingDisabled / ScaledToZero=False NotScaledToZero
```

## 정리

```bash shell="실습 터미널"
helm uninstall prometheus-adapter -n metrics-lab >/dev/null; kubectl delete namespace scale0 metrics-lab >/dev/null && echo "정리 완료"
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
정리 완료
```
