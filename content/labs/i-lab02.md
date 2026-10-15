## 학습 목표

- [[requests]]와 [[limits]]가 스케줄링과 실행 중 동작에 각각 어떻게 쓰이는지 설명할 수 있습니다.
- 자원 설정에 따라 [[qos]] 클래스가 정해지는 규칙을 확인할 수 있습니다.
- 메모리 제한 초과로 인한 [[oomkilled]]와, 요청량 초과로 인한 `Pending`을 구분해 진단할 수 있습니다.
- [[metrics-server]]를 설치하고 [[hpa]]로 CPU 사용률 기준 자동 확장을 구성할 수 있습니다.

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
| 응답이 느리지만 재시작은 없음 | `kubectl top pods` | CPU limits에 걸려 스로틀링 중일 수 있습니다. |

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

## 정리와 재실행

이 실습은 네임스페이스와 **애드온**을 만들었으므로 둘 다 정리합니다. metrics-server를 다른 용도로 계속 쓰려면 두 번째 명령은 생략합니다.

```bash shell="실습 터미널"
kubectl delete namespace lab-i02
minikube addons disable metrics-server -p k8s-lab
kubectl get namespace lab-i02
kubectl get apiservice v1beta1.metrics.k8s.io
```

두 조회 명령이 모두 `NotFound`를 출력하면 정리 완료입니다. 다시 하려면 1단계부터 반복합니다.
