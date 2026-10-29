## 학습 목표

- [[requests]]와 [[limits]]가 스케줄링과 실행 중 동작에 각각 어떻게 쓰이는지 설명할 수 있습니다.
- 자원 설정에 따라 [[qos]] 클래스가 정해지는 규칙을 확인할 수 있습니다.
- 메모리 제한 초과로 인한 [[oomkilled]]와, 요청량 초과로 인한 `Pending`을 구분해 진단할 수 있습니다.
- [[metrics-server]]를 설치하고 [[hpa]]로 CPU 사용률 기준 자동 확장을 구성할 수 있습니다.
- CPU 스로틀링을 `Pending`·`OOMKilled`와 구분해 진단할 수 있습니다.
- HPA 레플리카 수와 노드에 들어가는 파드 수를 입력값·계산식으로 계산하고, 왜 실제 측정이 필요한지 설명할 수 있습니다.
- LimitRange·ResourceQuota가 기본 requests와 네임스페이스 합계를 어떻게 정하는지 확인할 수 있습니다.

## 선수 지식

- [ConfigMap·Secret과 Probe](#/item/i-lab01) 실습 수준의 매니페스트 작성
- CPU 단위: `1` = CPU 코어 1개, `100m` = 0.1코어. 메모리 단위: `Mi` = 1024²바이트, `M` = 1000²바이트

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context
kubectl get nodes
kubectl get namespace lab-i02
minikube addons list -p k8s-lab | grep metrics-server
```

`k8s-lab`, `Ready`, `NotFound`를 확인합니다. metrics-server는 `disabled`가 정상이며 5단계에서 켭니다.

## 개념: 예약은 requests, 상한은 limits

**무엇인가.** `requests`는 「이만큼은 반드시 쓸 수 있게 자리를 잡아 달라」는 **예약**이고, `limits`는 「이 이상은 쓰지 못하게 막아 달라」는 **상한**입니다.

**왜 필요한가.** 예약이 없으면 스케줄러는 노드가 얼마나 찼는지 알 수 없어 한 노드에 파드를 몰아넣습니다. 상한이 없으면 파드 하나가 메모리를 다 써서 같은 노드의 다른 파드까지 쫓겨날 수 있습니다. HPA도 「요청량 대비 몇 %를 쓰는지」로 판단하므로 requests가 없으면 동작하지 않습니다.

**어떻게 동작하나.**

| 단계 | requests | limits |
|---|---|---|
| 스케줄링 | [[scheduler]]가 노드의 남은 할당 가능량과 비교 | 고려하지 않음 |
| 실행 중 CPU | 경합 시 요청 비율대로 나눔 | 넘으면 **스로틀링**(느려짐), 종료되지 않음 |
| 실행 중 메모리 | 노드 메모리 부족 시 퇴출 우선순위에 영향 | 넘으면 커널이 **종료**(OOMKilled, 종료 코드 137) |
| HPA | 사용률 계산의 분모 | 사용하지 않음 |

QoS 클래스는 모든 컨테이너의 설정으로 자동 결정됩니다. 모든 컨테이너에 CPU·메모리의 requests와 limits가 같으면 **Guaranteed**, 하나라도 requests나 limits가 있으면 **Burstable**, 아무것도 없으면 **BestEffort**입니다. 노드 메모리가 부족하면 BestEffort부터 퇴출됩니다.

<figure class="diagram">
<svg viewBox="0 0 760 210" role="img" aria-label="metrics-server가 kubelet에서 사용량을 모으고 HPA 컨트롤러가 이를 읽어 Deployment 레플리카 수를 조정하는 흐름">
<defs><marker id="i2a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="arrowhead"/></marker></defs>
<rect class="box" x="10" y="80" width="140" height="54" rx="6"/><text x="22" y="103">kubelet</text><text class="small" x="22" y="121">파드별 CPU·메모리</text>
<rect class="box warn" x="200" y="80" width="160" height="54" rx="6"/><text x="212" y="103">metrics-server</text><text class="small" x="212" y="121">애드온 · 60초 간격 수집</text>
<rect class="box dim" x="410" y="80" width="150" height="54" rx="6"/><text x="422" y="103">metrics.k8s.io API</text><text class="small" x="422" y="121">kubectl top도 사용</text>
<rect class="box accent" x="410" y="160" width="150" height="40" rx="6"/><text x="422" y="185">HPA 컨트롤러</text>
<rect class="box accent" x="610" y="80" width="140" height="54" rx="6"/><text x="622" y="103">Deployment</text><text class="small" x="622" y="121">replicas 1 → N</text>
<path class="line" d="M152 107H198M362 107H408" marker-end="url(#i2a)"/>
<path class="line" d="M485 136V158" marker-end="url(#i2a)"/>
<path class="line" d="M562 180H680V136" marker-end="url(#i2a)"/>
<text class="small" x="10" y="30">원하는 레플리카 = ceil(현재 레플리카 × 현재 사용률 ÷ 목표 사용률)</text>
<text class="small" x="10" y="50">사용률 = 파드 CPU 사용량 ÷ 파드 CPU requests</text>
</svg>
<figcaption>HPA의 지표 경로. metrics-server는 Kubernetes에 포함되지 않은 애드온입니다.</figcaption>
</figure>

## 1단계: QoS 클래스 확인

```bash shell="실습 터미널"
kubectl create namespace lab-i02
```

`qos-pods.yaml`로 저장합니다. 자원 설정만 다른 파드 세 개입니다.

```yaml file=qos-pods.yaml
apiVersion: v1
kind: Pod
metadata:
  name: qos-besteffort
  namespace: lab-i02
spec:
  containers:
    - name: app
      image: busybox:1.37.0
      command: ["sleep", "3600"]
---
apiVersion: v1
kind: Pod
metadata:
  name: qos-burstable
  namespace: lab-i02
spec:
  containers:
    - name: app
      image: busybox:1.37.0
      command: ["sleep", "3600"]
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          memory: 128Mi
---
apiVersion: v1
kind: Pod
metadata:
  name: qos-guaranteed
  namespace: lab-i02
spec:
  containers:
    - name: app
      image: busybox:1.37.0
      command: ["sleep", "3600"]
      resources:
        requests:
          cpu: 100m
          memory: 64Mi
        limits:
          cpu: 100m
          memory: 64Mi
```

**결과를 예상한 뒤** 실행합니다.

```bash shell="실습 터미널"
kubectl apply -f qos-pods.yaml
kubectl get pods -n lab-i02 -o custom-columns=NAME:.metadata.name,QOS:.status.qosClass
kubectl describe node k8s-lab | sed -n '/Allocated resources/,/Events/p'
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드) · 노드 할당 가능량과 백분율은 환경마다 다름" date="2026-10-15"
NAME             QOS
qos-besteffort   BestEffort
qos-burstable    Burstable
qos-guaranteed   Guaranteed
Allocated resources:
  (Total limits may be over 100 percent, i.e., overcommitted.)
  Resource           Requests    Limits
  --------           --------    ------
  cpu                200m (10%)  100m (5%)
  memory             128Mi (1%)  192Mi (2%)
```

검증 환경에는 kube-system 파드가 없어 이 세 파드의 합계만 보입니다. minikube에서는 CoreDNS와 컨트롤 플레인 파드의 요청량이 더해져 이보다 크게 보입니다.

## 2단계: 요청량이 너무 커서 Pending

```yaml file=too-big.yaml
apiVersion: v1
kind: Pod
metadata:
  name: too-big
  namespace: lab-i02
spec:
  containers:
    - name: app
      image: busybox:1.37.0
      command: ["sleep", "3600"]
      resources:
        requests:
          cpu: "16"
          memory: 64Mi
```

```bash shell="실습 터미널"
kubectl apply -f too-big.yaml
kubectl get pod too-big -n lab-i02
kubectl events -n lab-i02 --for pod/too-big
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME      READY   STATUS    RESTARTS   AGE
too-big   0/1     Pending   0          5s
LAST SEEN           TYPE      REASON             OBJECT        MESSAGE
34s (x2 over 34s)   Warning   FailedScheduling   Pod/too-big   0/1 nodes are available: 1 Insufficient cpu. preemption: 0/1 nodes are available: 1 Preemption is not helpful for scheduling.
```

파드는 만들어졌지만 들어갈 노드가 없습니다. **실제로 CPU를 쓰는지와 관계없이 예약만으로 거절**된다는 점이 핵심입니다. 노드가 하나뿐인 minikube에서는 다른 파드를 밀어내도(preemption) 해결되지 않는다는 메시지도 함께 나옵니다.

```bash shell="실습 터미널"
kubectl delete pod too-big -n lab-i02
```

## 3단계: 메모리 제한 초과로 OOMKilled

64Mi 제한을 건 컨테이너에서 200MiB를 메모리에 올립니다. `head -c 200m /dev/zero | tail`은 줄바꿈 없는 200MiB를 `tail`이 한 줄로 붙잡고 있게 만드는 간단한 메모리 소비 방법입니다.

```yaml file=memory-hog.yaml
apiVersion: v1
kind: Pod
metadata:
  name: memory-hog
  namespace: lab-i02
spec:
  restartPolicy: Never
  containers:
    - name: app
      image: busybox:1.37.0
      command: ["sh", "-c", "echo '200MiB를 메모리에 올립니다'; head -c 200m /dev/zero | tail"]
      resources:
        requests:
          memory: 32Mi
        limits:
          memory: 64Mi
```

`restartPolicy: Never`는 결과를 관찰하기 쉽게 재시작하지 않도록 한 설정입니다.

```bash shell="실습 터미널"
kubectl apply -f memory-hog.yaml
kubectl get pod memory-hog -n lab-i02
kubectl logs memory-hog -n lab-i02
kubectl describe pod memory-hog -n lab-i02 | sed -n '/State:/,/Ready:/p'
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드, 대체 busybox 이미지)" date="2026-10-15"
NAME         READY   STATUS      RESTARTS   AGE
memory-hog   0/1     OOMKilled   0          96s
200MiB를 메모리에 올립니다
Killed
    State:          Terminated
      Reason:       OOMKilled
      Exit Code:    137
```

종료 코드 137은 128 + 9(SIGKILL)입니다. 앱이 정상 종료할 기회 없이 커널에 의해 즉시 종료되었다는 뜻입니다. 로그 마지막의 `Killed`는 셸이 남긴 메시지입니다.

### CPU는 상한에 걸려도 종료되지 않는다: 스로틀링

메모리와 달리 CPU limits를 넘으려는 컨테이너는 **죽지 않고 느려집니다**. 커널이 일정 주기(기본 100ms)마다 허용량을 다 쓴 컨테이너를 다음 주기까지 멈춰 세웁니다. 계속 CPU를 쓰는 반복문에 `100m` 상한을 걸어 봅니다.

```yaml file=cpu-busy.yaml
apiVersion: v1
kind: Pod
metadata:
  name: cpu-busy
  namespace: lab-i02
spec:
  containers:
    - name: app
      image: busybox:1.37.0
      command: ["sh", "-c", "while :; do :; done"]
      resources:
        requests:
          cpu: 50m
          memory: 16Mi
        limits:
          cpu: 100m
          memory: 32Mi
```

```bash shell="실습 터미널"
kubectl apply -f cpu-busy.yaml
kubectl wait --for=condition=Ready pod/cpu-busy -n lab-i02 --timeout=120s
sleep 30
kubectl get pod cpu-busy -n lab-i02
kubectl exec cpu-busy -n lab-i02 -- cat /sys/fs/cgroup/cpu.stat | awk '$1=="nr_periods"{p=$2} $1=="nr_throttled"{t=$2} END{printf "스로틀링된 구간 비율: %d%% (%d/%d)\n", t*100/p, t, p}'
```

```output kind=verified env="로컬 재현 환경 (kind · Kubernetes v1.35.0) · 구간 수와 비율은 매번 다름" date="2026-10-29"
NAME       READY   STATUS    RESTARTS   AGE
cpu-busy   1/1     Running   0          36s
스로틀링된 구간 비율: 99% (312/313)
```

`Running`·재시작 0인데 거의 모든 구간에서 멈춰 섰습니다. 그래서 스로틀링은 `kubectl get pod`로는 보이지 않고, 「응답이 느려졌다」로 나타납니다. `/sys/fs/cgroup/cpu.stat`은 cgroup v2 기준 경로입니다.

```bash shell="실습 터미널"
kubectl delete pod cpu-busy -n lab-i02
```

| 증상 | 어디서 보이나 | 원인 | 확인 명령 |
|---|---|---|---|
| `Pending` | 파드가 시작조차 안 함, 이벤트 `FailedScheduling … Insufficient cpu` | **requests** 합계가 노드의 할당 가능량을 넘음 (실제 사용량과 무관) | `kubectl events --for pod/이름`, `kubectl describe node`의 Allocated resources |
| 스로틀링 | `Running`, 재시작 없음, 느림 | 실제 CPU 사용이 **CPU limits**에 닿음 | 컨테이너의 `cpu.stat`(`nr_throttled`), `kubectl top pod`가 limits 근처 |
| `OOMKilled` | 재시작, 종료 코드 137 | 실제 메모리 사용이 **메모리 limits**를 넘음 | `kubectl describe pod`의 Last State |

## 4단계: metrics-server 애드온 설치·검증

HPA와 `kubectl top`은 [[metrics-server]]가 제공하는 지표 API가 있어야 동작합니다. metrics-server는 Kubernetes 본체가 아니라 **별도로 설치하는 애드온**입니다. minikube v1.39.0은 metrics-server v0.9.0을 애드온으로 제공합니다.

**설치**

```bash shell="실습 터미널"
minikube addons enable metrics-server -p k8s-lab
```

**검증** — 1~2분 기다린 뒤 실행합니다.

```bash shell="실습 터미널"
kubectl get deployment metrics-server -n kube-system
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top nodes
kubectl top pods -n lab-i02
```

```output kind=example note="minikube v1.39.0 기준 · 수치는 환경마다 다름"
NAME             READY   UP-TO-DATE   AVAILABLE   AGE
metrics-server   1/1     1            1           2m
NAME                     SERVICE                      AVAILABLE   AGE
v1beta1.metrics.k8s.io   kube-system/metrics-server   True        2m
NAME      CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
k8s-lab   180m         9%       900Mi           23%
```

APIService의 AVAILABLE이 `True`이고 `kubectl top nodes`가 숫자를 보여야 다음 단계로 갑니다. minikube 애드온은 60초 간격으로 지표를 수집하도록 설정되어 있어 처음에는 `metrics not available yet`이 나올 수 있습니다.

:::version 버전별 차이
metrics.k8s.io API 정의는 1.37에서 Stable(`v1`)이 되었습니다. 다만 이 실습의 metrics-server 애드온은 `v1beta1` APIService를 등록하므로 세 버전(1.35·1.36·1.37) 모두 위 명령을 그대로 씁니다. `v1beta1`은 폐기 정책에 따라 전환 기간 동안 계속 제공됩니다.
:::

## 5단계: HPA로 자동 확장

공식 「HorizontalPodAutoscaler Walkthrough」의 예제를 네임스페이스만 바꿔 사용합니다. 요청마다 CPU 계산을 하는 PHP 앱입니다.

```yaml file=php-apache.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: php-apache
  namespace: lab-i02
spec:
  selector:
    matchLabels:
      run: php-apache
  template:
    metadata:
      labels:
        run: php-apache
    spec:
      containers:
        - name: php-apache
          image: registry.k8s.io/hpa-example
          ports:
            - containerPort: 80
          resources:
            limits:
              cpu: 500m
            requests:
              cpu: 200m
---
apiVersion: v1
kind: Service
metadata:
  name: php-apache
  namespace: lab-i02
  labels:
    run: php-apache
spec:
  ports:
    - port: 80
  selector:
    run: php-apache
```

:::note 이미지 버전
`registry.k8s.io/hpa-example`은 공식 문서가 태그 없이 쓰는 예제 이미지로, 버전 태그가 따로 없습니다(`latest`로 해석). 재현성을 위해 실행 후 `kubectl get pod -n lab-i02 -l run=php-apache -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'`로 내려받은 이미지의 다이제스트를 기록해 두세요.
:::

HPA는 명령(`kubectl autoscale`) 대신 YAML로 만듭니다. kubectl 버전마다 옵션 이름이 달라질 수 있지만 `autoscaling/v2` 매니페스트는 세 버전에서 같습니다.

```yaml file=hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: php-apache
  namespace: lab-i02
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: php-apache
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 50
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 60
```

| 필드 | 의미 |
|---|---|
| `scaleTargetRef` | 레플리카 수를 조정할 대상. |
| `minReplicas`·`maxReplicas` | 조정 범위. 노드 자원을 넘지 않게 상한을 둡니다. |
| `averageUtilization: 50` | 파드 평균 CPU 사용량이 **requests의 50%**(여기서는 100m)가 되도록 맞춥니다. |
| `behavior.scaleDown.stabilizationWindowSeconds` | 줄이기 전에 지켜볼 시간. 기본 300초인데 실습 시간을 줄이려고 60초로 낮췄습니다. |

```bash shell="실습 터미널"
kubectl apply -f php-apache.yaml
kubectl rollout status deployment/php-apache -n lab-i02
kubectl apply -f hpa.yaml
kubectl get hpa php-apache -n lab-i02
```

TARGETS가 처음 1~2분은 `<unknown>/50%`였다가 `cpu: 0%/50%`로 바뀝니다. 이제 **두 번째 터미널**에서 부하를 겁니다.

```bash shell="두 번째 실습 터미널"
kubectl run load-generator -n lab-i02 --image=busybox:1.37.0 --restart=Never -- /bin/sh -c "while sleep 0.01; do wget -q -O- http://php-apache; done"
```

첫 번째 터미널에서 지켜봅니다. `Ctrl+C`로 멈출 수 있습니다.

```bash shell="실습 터미널"
kubectl get hpa php-apache -n lab-i02 --watch
```

```output kind=example note="공식 Walkthrough와 같은 흐름의 예시 · 사용률과 레플리카 수, 걸리는 시간은 PC 성능에 따라 다름"
NAME         REFERENCE               TARGETS        MINPODS   MAXPODS   REPLICAS   AGE
php-apache   Deployment/php-apache   cpu: 0%/50%    1         5         1          3m
php-apache   Deployment/php-apache   cpu: 250%/50%  1         5         1          4m
php-apache   Deployment/php-apache   cpu: 250%/50%  1         5         5          4m
php-apache   Deployment/php-apache   cpu: 62%/50%   1         5         5          5m
```

사용률 250%면 계산상 1 × 250 ÷ 50 = 5개가 필요하므로 상한 5까지 늘어납니다. 노드 CPU가 2코어뿐이라 5개가 되어도 50%까지 내려가지 않을 수 있습니다. 부하를 멈춥니다.

```bash shell="두 번째 실습 터미널"
kubectl delete pod load-generator -n lab-i02
```

1~3분 뒤(지표 수집 주기 + 안정화 60초) 레플리카가 1로 줄어드는지 확인합니다.

## 6단계: HPA가 몇 개로 늘릴지 계산하기

HPA 컨트롤러는 기본 15초마다 다음을 계산합니다([공식 문서: Algorithm details](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/#algorithm-details)).

```text
파드별 사용률    = 그 파드의 CPU 사용량 ÷ 그 파드의 CPU requests        ← requests가 분모
평균 사용률      = 대상 파드들의 파드별 사용률 평균
desiredReplicas = ceil(지금 레플리카 × 평균 사용률 ÷ 목표 사용률)
```

`averageUtilization: 50`의 「50%」는 **파드 하나하나의 사용률을 평균한 값**과 비교합니다. 파드 사용량을 모두 더한 합계를 파드 한 개의 requests로 나누면 안 됩니다(아래 응용 과제 4). 파드들의 requests가 모두 같으면 평균 사용률은 「사용량 합계 ÷ requests 합계」와 같습니다.

**requests가 분모인 이유**: 사용률은 「예약한 만큼 중 얼마나 쓰나」입니다. 그래서 requests를 실제보다 작게 적으면 같은 부하에서도 사용률이 높게 계산돼 과하게 늘어나고, 크게 적으면 늦게 늘어납니다. requests가 없으면 계산 자체를 못 합니다(흔한 오류 표의 `missing request for cpu`). 사용량은 metrics-server가 kubelet에서 모은 값이고, `kubectl top pods`가 보여 주는 숫자와 같은 출처입니다.

**계산 실습.** 입력:

- 현재 파드 2개
- 각 파드의 CPU requests 200m
- 파드별 현재 CPU 사용량 330m·350m (**파드당 평균 340m**)
- 목표 평균 사용률 50%, `maxReplicas` 5

```bash shell="실습 터미널"
awk 'BEGIN {
  n = 2; req = 200; use[1] = 330; use[2] = 350    # 입력: 파드 수, 파드 1개의 CPU requests(m), 파드별 CPU 사용량(m) — 파드당 평균 340m
  target = 50; max = 5                             # 목표 평균 사용률(%), maxReplicas
  for (i = 1; i <= n; i++) { u[i] = use[i] / req * 100; sum += u[i]; printf "파드 %d 사용률 = %d ÷ %d = %.0f%%\n", i, use[i], req, u[i] }
  avg = sum / n
  printf "평균 사용률 = (%.0f + %.0f) ÷ %d = %.0f%%\n", u[1], u[2], n, avg
  raw = n * avg / target; want = int(raw); if (want < raw) want++
  printf "desiredReplicas = ceil(%d × %.0f ÷ %d) = ceil(%.1f) = %d\n", n, avg, target, raw, want
  printf "maxReplicas %d 적용 → 최종 %d개\n", max, (want > max ? max : want)
}'
```

```output kind=verified env="계산 결과 (macOS·Ubuntu awk 동일)" date="2026-10-29"
파드 1 사용률 = 330 ÷ 200 = 165%
파드 2 사용률 = 350 ÷ 200 = 175%
평균 사용률 = (165 + 175) ÷ 2 = 170%
desiredReplicas = ceil(2 × 170 ÷ 50) = ceil(6.8) = 7
maxReplicas 5 적용 → 최종 5개
```

계산상 7개가 필요하지만 `maxReplicas` 5 때문에 최종 **5개**입니다. 이 밖에 계산 결과를 바꾸는 규칙이 셋 있습니다.

| 규칙 | 기본값 | 뜻 |
|---|---|---|
| 허용 오차(tolerance) | 0.1 | 평균 사용률 ÷ 목표가 0.9~1.1 사이면 바꾸지 않음. 예: 목표 50%에 평균 53%면 그대로 |
| 늘리기 정책 `behavior.scaleUp` | 안정화 0초, 15초마다 「100% 또는 4개 중 큰 쪽」까지 | 2개 → 15초 뒤 최대 6개. 위 예의 5개는 한 번에 도달 |
| 줄이기 정책 `behavior.scaleDown` | **안정화 300초**, 15초마다 100%까지 | 지난 300초 동안 나온 추천값 중 **가장 큰 값**을 씀 → 부하가 잠깐 줄어도 바로 줄이지 않음 (이 실습은 60초) |

정책 기본값은 [공식 문서: Default Behavior](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/#default-behavior)에 있습니다.

requests 값 자체를 사용량 기록으로 추천받는 방법은 선택 심화 [VPA로 requests 추천받기](#/item/i-vpa)에 있습니다. 같은 CPU 지표로 HPA와 VPA를 함께 쓰면 안 되는 이유도 거기서 다룹니다.

:::note 실제 값은 측정해서 정합니다
위 숫자는 계산 연습용 입력입니다. 「requests는 얼마, 목표는 몇 %」에 정답은 없습니다. 부하 시험과 `kubectl top`·모니터링으로 **평소·최대 사용량을 측정**해 requests를 정하고, 목표 사용률은 늘어나는 동안(새 파드가 뜨는 수십 초) 남은 파드가 버틸 여유를 보고 정합니다.
:::

## 7단계: 노드에 몇 개나 들어가나 — 용량 계산

스케줄러는 노드의 **Allocatable**(할당 가능량)과 이미 놓인 파드들의 **requests 합계**를 비교합니다. Allocatable은 노드 전체 용량(Capacity)에서 시스템 예약분을 뺀 값입니다([공식 문서: Reserve Compute Resources for System Daemons](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)).

```text
Allocatable = Capacity − kube-reserved − system-reserved − 축출(eviction) 임계값
```

```bash shell="실습 터미널"
kubectl get nodes -o custom-columns='NODE:.metadata.name,CPU:.status.capacity.cpu,ALLOC_CPU:.status.allocatable.cpu,MEMORY:.status.capacity.memory,ALLOC_MEMORY:.status.allocatable.memory'
kubectl describe nodes | sed -n '/Allocated resources:/,/Events:/p' | grep -E '^\s+(Resource|cpu|memory) '
```

```output kind=verified env="로컬 재현 환경 (kind · Kubernetes v1.35.0) · 노드 크기와 사용량은 환경마다 다름" date="2026-10-29"
NODE                          CPU   ALLOC_CPU   MEMORY       ALLOC_MEMORY
hangdo-verify-control-plane   15    15          16423944Ki   16423944Ki
  Resource           Requests    Limits
  cpu                950m (6%)   100m (0%)
  memory             290Mi (1%)  390Mi (2%)
```

minikube·kind 같은 실습 클러스터는 예약분을 따로 두지 않아 Capacity와 Allocatable이 같게 나옵니다. 운영 노드(kubeadm 설정·클라우드 관리형)는 예약분만큼 Allocatable이 작고, 그 값은 반드시 `kubectl describe node`로 **직접 확인**합니다.

**계산 실습.** 입력: 노드 3대, 노드 1대의 Allocatable 3800m·14336Mi, 노드마다 도는 DaemonSet requests 300m·512Mi, 앱 파드 requests 500m·1024Mi.

```bash shell="실습 터미널"
awk 'BEGIN {
  nodes = 3; alloc_cpu = 3800; alloc_mem = 14336    # 입력: 노드 수, 노드 1대의 Allocatable (CPU m, 메모리 Mi)
  ds_cpu = 300; ds_mem = 512                        # 노드마다 도는 DaemonSet(로그·모니터링 등) requests 합계
  pod_cpu = 500; pod_mem = 1024                     # 앱 파드 1개의 requests
  by_cpu = int((alloc_cpu - ds_cpu) / pod_cpu); by_mem = int((alloc_mem - ds_mem) / pod_mem)
  per = (by_cpu < by_mem ? by_cpu : by_mem)
  printf "노드 1대: CPU 기준 %d개, 메모리 기준 %d개 → %d개 (작은 쪽)\n", by_cpu, by_mem, per
  printf "노드 %d대가 모두 정상일 때 이론상 최대: %d개\n", nodes, per * nodes
  printf "노드 1대 장애(N-1) 때 이론상 최대: %d개\n", per * (nodes - 1)
}'
```

```output kind=verified env="계산 결과 (macOS·Ubuntu awk 동일)" date="2026-10-29"
노드 1대: CPU 기준 7개, 메모리 기준 13개 → 7개 (작은 쪽)
노드 3대가 모두 정상일 때 이론상 최대: 21개
노드 1대 장애(N-1) 때 이론상 최대: 14개
```

- 한 노드에 들어가는 수는 CPU·메모리 중 **작은 쪽**이 정합니다.
- **14개는 주어진 requests와 배치 조건만 고려한, 노드 1대 장애(N-1) 때의 이론상 최대 수용량입니다. 안전한 운영 권장 replica 수가 아닙니다.** 노드 하나가 빠지면 그 노드의 파드가 남은 2대로 옮겨야 하므로, 이 숫자를 넘는 `maxReplicas`는 장애 때 일부 파드가 `Pending`이 될 수 있다는 뜻일 뿐입니다.
- 실제 운영에서는 이 이론값에서 다음 여유를 **따로** 확보해야 합니다.

| 따로 남겨야 할 여유 | 왜 |
|---|---|
| 롤링 업데이트의 `maxSurge` | 업데이트 중에는 새 파드가 잠깐 더 떠 있음 |
| 시스템·애드온 증가 | kube-system 구성 요소와 애드온의 requests가 버전·설정에 따라 늘어남 |
| DaemonSet 추가 | 로그·모니터링·보안 에이전트가 늘면 노드마다 줄어듦 |
| 파드 분산·topology spread constraints | 노드·영역에 고르게 놓으라는 조건이 있으면 빈 자리가 있어도 못 쓸 수 있음 |
| CPU·메모리 사용량 변동 | requests는 예약일 뿐, 실제 사용량은 평소·최대가 다름 |
| 노드 드레인(점검·업그레이드) | 드레인하는 동안은 장애가 아니어도 노드 하나가 빠짐 |
| 클러스터 오토스케일러 반응 시간 | 노드를 새로 붙이는 데 수 분이 걸리는 동안 남은 노드가 버텨야 함 |

- requests 기준 계산은 「자리가 있느냐」만 답합니다. **실제 사용량과 응답 성능을 보장하지 않습니다.** 성능은 부하 시험과 모니터링으로 확인합니다.
- 몇 %를 남기라는 정해진 비율은 없습니다. 위 항목을 각자 환경에서 측정하거나 운영 정책으로 정합니다.

## 8단계: 네임스페이스의 기본값과 상한 — LimitRange·ResourceQuota

requests를 빠뜨린 파드는 HPA 계산도 스케줄링도 엉망이 됩니다. 관리자는 네임스페이스마다 **LimitRange**(컨테이너 기본값·최대값)와 **ResourceQuota**(네임스페이스 합계 상한)를 둡니다. 다른 단계와 섞이지 않게 별도 네임스페이스에서 합니다.

```yaml file=quota.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lab-i02-quota
---
apiVersion: v1
kind: LimitRange
metadata:
  name: defaults
  namespace: lab-i02-quota
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 100m
        memory: 64Mi
      default:
        cpu: 200m
        memory: 128Mi
      max:
        cpu: "1"
        memory: 512Mi
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-cap
  namespace: lab-i02-quota
spec:
  hard:
    requests.cpu: 300m
    requests.memory: 512Mi
    limits.cpu: "1"
    limits.memory: 1Gi
    pods: "10"
```

```bash shell="실습 터미널"
kubectl apply -f quota.yaml
kubectl create deployment web -n lab-i02-quota --image=busybox:1.37.0 --replicas=4 -- sleep 3600
sleep 15
kubectl get deployment web -n lab-i02-quota
kubectl get pod -n lab-i02-quota -o jsonpath='{.items[0].spec.containers[0].resources}{"\n"}'
kubectl describe resourcequota team-cap -n lab-i02-quota | grep -E '^(Resource|requests\.cpu|limits\.cpu|pods) '
kubectl events -n lab-i02-quota --types=Warning | grep -m1 -o 'exceeded quota: .*'
```

```output kind=verified env="로컬 재현 환경 (kind · Kubernetes v1.35.0)" date="2026-10-29"
namespace/lab-i02-quota created
limitrange/defaults created
resourcequota/team-cap created
deployment.apps/web created
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    3/4     3            3           15s
{"limits":{"cpu":"200m","memory":"128Mi"},"requests":{"cpu":"100m","memory":"64Mi"}}
Resource         Used   Hard
limits.cpu       600m   1
pods             3      10
requests.cpu     300m   300m
exceeded quota: team-cap, requested: requests.cpu=100m, used: requests.cpu=300m, limited: requests.cpu=300m
```

- `resources`를 쓰지 않은 파드에 **LimitRange가 기본 requests 100m·limits 200m를 넣었습니다.**
- 4개 중 3개만 떴습니다. 네 번째는 requests 합계가 쿼터(300m)를 넘어 **API 서버가 만들기를 거절**했습니다. 파드가 `Pending`으로 남는 것이 아니라 아예 생기지 않으므로, `kubectl get pod`가 아니라 Deployment의 READY와 이벤트(`exceeded quota`)로 찾습니다.
- HPA가 레플리카를 늘려도 쿼터를 넘는 파드는 같은 이유로 생기지 않습니다. 「HPA는 늘렸다는데 파드가 안 늘어요」의 흔한 원인입니다.

```bash shell="실습 터미널"
kubectl delete namespace lab-i02-quota
```

## 성공 판정

```verify
id: i2-oom
title: 메모리 제한 초과를 OOMKilled로 확인
explain: memory-hog 컨테이너의 종료 사유와 종료 코드를 출력합니다.
command: kubectl get pod memory-hog -n lab-i02 -o jsonpath='{.status.containerStatuses[0].state.terminated.reason} {.status.containerStatuses[0].state.terminated.exitCode}{"\n"}'
expect: ^OOMKilled 137$
criteria: OOMKilled 137
```

```verify
id: i2-hpa
title: HPA가 지표를 읽고 확장한 기록
explain: HPA의 지표 계산 가능 여부와, 지금까지 도달한 최대 레플리카 관련 이벤트 유무를 출력합니다. 부하를 건 뒤 실행하세요.
command: echo "active=$(kubectl get hpa php-apache -n lab-i02 -o jsonpath='{.status.conditions[?(@.type=="ScalingActive")].status}') rescaled=$(kubectl events -n lab-i02 --for hpa/php-apache 2>/dev/null | grep -c SuccessfulRescale)"
expect: ^active=True rescaled=[1-9][0-9]*$
criteria: active=True 이고 rescaled가 1 이상
```

:::warn 검증 범위
OOMKilled 판정은 검증 환경에서 실제로 실행해 `OOMKilled 137`을 확인했습니다. HPA 판정은 검증 환경에 metrics-server를 설치할 수 없어 **실제 확장까지 검증하지 못했습니다**. 매니페스트가 API 서버에서 정상적으로 생성되는 것과, 지표가 없을 때의 상태(아래 「흔한 오류」 표의 첫 행)만 확인했습니다.
:::

## 흔한 오류, 진단 순서, 해결 방법

HPA 진단 순서: **metrics-server 동작 → `kubectl top pods` → 대상 파드의 requests → `kubectl describe hpa`의 Conditions·Events**.

| 증상 | 확인 명령 | 원인과 해결 |
|---|---|---|
| TARGETS가 계속 `<unknown>` | `kubectl describe hpa php-apache -n lab-i02` | `FailedGetResourceMetric`이면 지표 API가 없습니다. 4단계 검증을 다시 합니다. 아래 출력은 metrics-server 없이 실행한 검증 환경의 실제 결과입니다. |
| `failed to get cpu utilization: missing request for cpu` | 파드 `resources` 확인 | 대상 파드에 CPU requests가 없습니다. 사용률의 분모가 없어 계산할 수 없습니다. |
| `kubectl top`이 `Metrics API not available` | `kubectl get apiservice v1beta1.metrics.k8s.io` | 애드온이 꺼져 있거나 아직 준비되지 않았습니다. |
| 파드가 `Pending`, `Insufficient cpu/memory` | `kubectl describe node k8s-lab`의 Allocated resources | 노드의 할당 가능량을 넘었습니다. requests를 줄이거나 maxReplicas를 낮춥니다. |
| `OOMKilled`, 종료 코드 137 | `kubectl describe pod`의 Last State | 메모리 limits가 실제 사용량보다 작습니다. 사용량을 측정해 limits를 올리거나 앱 메모리 설정(JVM 힙 등)을 맞춥니다. |
| 응답이 느리지만 재시작은 없음 | `kubectl top pods`, 컨테이너의 `cat /sys/fs/cgroup/cpu.stat` | CPU limits에 걸려 스로틀링 중입니다(`nr_throttled` 증가). 3단계의 스로틀링 실습. |
| Deployment READY가 replicas보다 적고 파드도 없음 | `kubectl events -n 네임스페이스 --types=Warning` | `exceeded quota`면 ResourceQuota 합계를 넘었습니다(8단계). 쿼터를 늘리거나 requests·replicas를 줄입니다. |

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드, metrics-server 없음)" date="2026-10-15"
NAME         REFERENCE               TARGETS              MINPODS   MAXPODS   REPLICAS   AGE
php-apache   Deployment/php-apache   cpu: <unknown>/50%   1         5         1          76s
Conditions:
  Type           Status  Reason                   Message
  ----           ------  ------                   -------
  AbleToScale    True    SucceededGetScale        the HPA controller was able to get the target's current scale
  ScalingActive  False   FailedGetResourceMetric  the HPA was unable to compute the replica count: failed to get cpu utilization: unable to get metrics for resource cpu: ...
```

## 응용 과제

**과제 1.** `qos-burstable`의 limits에 `cpu: 100m`을 추가하면 QoS가 Guaranteed가 될까요? 실행 중인 파드의 resources를 그대로 고쳐 apply할 수 있을까요?

:::answer 힌트와 해설
힌트: Guaranteed 조건은 「CPU·메모리 각각 requests와 limits가 같을 것」입니다.

해설: 메모리 requests(64Mi)와 limits(128Mi)가 달라 여전히 Burstable입니다. 또한 실행 중인 파드의 resources는 1.35부터 GA인 「In-place Pod Resize」 기능으로 `kubectl patch ... --subresource resize`를 통해 바꿀 수 있지만, QoS 클래스는 생성 시 정해지며 바뀌는 수정은 거부됩니다. 보통은 Deployment 템플릿을 고쳐 새 파드로 교체합니다.
:::

**과제 2.** `memory-hog`의 limits를 `256Mi`로 올리면 어떻게 될까요? 노드 메모리보다 큰 limits를 주면 스케줄링이 거절될까요?

:::answer 해설
200MiB를 다 올린 뒤 `tail`이 끝나며 정상 종료(Completed)합니다. 스케줄링은 requests만 보므로 limits가 노드 메모리보다 커도 거절되지 않습니다. 이것이 「limits 합계가 100%를 넘을 수 있다(overcommitted)」는 1단계 출력의 의미입니다.
:::

**과제 3.** HPA의 목표를 `averageUtilization: 80`으로 바꾸면 같은 부하에서 레플리카 수는 늘까요, 줄까요?

:::answer 해설
줄어듭니다. 원하는 레플리카 = ceil(현재 × 현재 사용률 ÷ 목표)이므로 목표가 커지면 필요한 파드 수가 줄어듭니다. 대신 파드 하나가 더 바쁘게 일합니다.
:::

**과제 4.** 6단계와 같은 조건(파드 2개, 각 requests 200m, 목표 50%, maxReplicas 5)인데, 이번에는 모니터링 화면이 「두 파드의 CPU 사용량 **합계** 340m」를 보여 줍니다. 원하는 레플리카는 몇 개일까요? 340m를 그대로 200m로 나누면 어떤 실수가 될까요?

:::answer 해설
합계 340m는 파드당 평균 170m입니다. 평균 사용률 = 170 ÷ 200 = **85%**, desiredReplicas = ceil(2 × 85 ÷ 50) = ceil(3.4) = **4개**(maxReplicas 5 이내라 그대로).
합계 340m를 파드 한 개의 requests 200m로 나누면 사용률을 170%로 잘못 계산해 7개(최종 5개)로 답하게 됩니다. HPA는 **파드별 사용률의 평균**을 쓰므로, 화면의 숫자가 파드당 값인지 합계인지 먼저 확인합니다. `kubectl top pods`는 파드마다 따로 보여 줍니다.
:::

## 정리와 재실행

이 실습은 네임스페이스와 **애드온**을 만들었으므로 둘 다 정리합니다. metrics-server를 다른 용도로 계속 쓰려면 두 번째 명령은 생략합니다.

```bash shell="실습 터미널"
kubectl delete namespace lab-i02
kubectl delete namespace lab-i02-quota --ignore-not-found
minikube addons disable metrics-server -p k8s-lab
kubectl get namespace lab-i02
kubectl get apiservice v1beta1.metrics.k8s.io
```

두 조회 명령이 모두 `NotFound`를 출력하면 정리 완료입니다. 다시 하려면 1단계부터 반복합니다.
