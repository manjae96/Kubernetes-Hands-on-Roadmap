## 과제 소개

주문 API를 Kubernetes로 옮기던 동료가 휴가를 떠났습니다. 남긴 매니페스트를 배포하면 「주문 API에 연결이 안 된다」는 문의가 들어옵니다. 매니페스트에는 **결함이 네 개** 숨어 있습니다. 증상에서 출발해 근거를 찾고, 하나씩 고쳐 정상 상태로 만드세요.

정답을 바로 찾기보다 **진단 과정을 기록하는 것**이 이 과제의 목표입니다. 결함마다 「증상 → 확인한 명령 → 근거가 된 출력 → 원인 → 수정」을 한 줄씩 적어 보세요.

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context
kubectl get namespace cap-inter
```

`k8s-lab`과 `NotFound`를 확인합니다.

## 과제 매니페스트

아래 파일을 `order-broken.yaml`로 저장해 그대로 배포합니다. **파일을 먼저 읽고 결함을 찾지 말고**, 배포 후 증상부터 확인하세요.

```yaml file=order-broken.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: order-api-config
  namespace: cap-inter
data:
  APP_MODE: "production"
  index.html: |
    {"status":"ok","service":"orders"}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-api
  namespace: cap-inter
  labels:
    app.kubernetes.io/name: orders-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: orders-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: orders-api
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.6-alpine
          ports:
            - name: http
              containerPort: 80
          env:
            - name: APP_MODE
              valueFrom:
                configMapKeyRef:
                  name: order-api-config
                  key: API_MODE
          volumeMounts:
            - name: content
              mountPath: /usr/share/nginx/html
              readOnly: true
          readinessProbe:
            httpGet:
              path: /
              port: 8080
            periodSeconds: 5
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              memory: 64Mi
      volumes:
        - name: content
          configMap:
            name: order-api-config
            items:
              - key: index.html
                path: index.html
---
apiVersion: v1
kind: Service
metadata:
  name: order-api
  namespace: cap-inter
spec:
  selector:
    app.kubernetes.io/name: order-api
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-worker
  namespace: cap-inter
  labels:
    app.kubernetes.io/name: order-worker
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: order-worker
  template:
    metadata:
      labels:
        app.kubernetes.io/name: order-worker
    spec:
      containers:
        - name: worker
          image: busybox:1.37.0
          command: ["sh", "-c", "set -e; echo '주문 캐시 적재 (약 50MiB)'; head -c 50m /dev/zero | tail; echo '적재 완료, 대기'; sleep 3600"]
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              memory: 32Mi
```

```bash shell="실습 터미널"
kubectl create namespace cap-inter
kubectl apply -f order-broken.yaml
kubectl run client -n cap-inter --image=busybox:1.37.0 --restart=Never -- sleep 3600
```

1분쯤 기다린 뒤 사용자 입장에서 확인합니다.

```bash shell="실습 터미널"
kubectl exec client -n cap-inter -- wget -qO- -T 5 http://order-api
kubectl get pods -n cap-inter
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME                            READY   STATUS                       RESTARTS      AGE
client                          1/1     Running                      0             46s
order-api-f484b6597-h5hfw       0/1     CreateContainerConfigError   0             46s
order-api-f484b6597-xxkxq       0/1     CreateContainerConfigError   0             46s
order-worker-f7b88fc54-r4nvm    0/1     OOMKilled                    3 (32s ago)   50s
```

## 권장 진단 순서

중급 과정에서 익힌 순서를 그대로 적용합니다. 결함은 하나를 고쳐야 다음 것이 드러나기도 합니다.

1. `kubectl get pods`의 STATUS·READY·RESTARTS로 어느 워크로드가 문제인지 고릅니다.
2. `kubectl describe pod` 또는 `kubectl events --types=Warning`으로 이유를 읽습니다.
3. 컨테이너가 시작했다면 `kubectl logs`(필요하면 `--previous`)를 봅니다.
4. 파드가 모두 Ready인데도 연결이 안 되면 `kubectl get endpointslices`와 `--show-labels`로 Service와 파드의 연결을 확인합니다.
5. 고친 뒤에는 파일을 수정해 `kubectl apply -f`로 반영합니다.

## 성공 판정

```verify
id: icap-final
title: API 2개·워커 1개 준비, 주문 API가 정상 응답
explain: 두 Deployment의 준비된 레플리카 수와 client 파드에서 받은 응답 본문을 한 줄로 출력합니다.
command: echo "api=$(kubectl get deploy order-api -n cap-inter -o jsonpath='{.status.readyReplicas}') worker=$(kubectl get deploy order-worker -n cap-inter -o jsonpath='{.status.readyReplicas}') body=$(kubectl exec client -n cap-inter -- wget -qO- -T 5 http://order-api)"
expect: ^api=2 worker=1 body=\{"status":"ok","service":"orders"\}$
criteria: api=2 worker=1 body={"status":"ok","service":"orders"}
```

검증 환경에서 해설의 수정본으로 실행한 실제 출력은 `api=2 worker=1 body={"status":"ok","service":"orders"}`였습니다.

## 스스로 점검

- [ ] 네 결함 각각에 대해 근거가 된 출력 한 줄을 적었다
- [ ] `CreateContainerConfigError`와 `CrashLoopBackOff`가 어느 단계의 실패인지 구분할 수 있다
- [ ] 파드가 모두 Ready인데 Service가 안 될 때 가장 먼저 볼 명령을 안다
- [ ] OOMKilled를 limits만 올려 해결해도 되는 경우와 아닌 경우를 설명할 수 있다

## 해설

:::answer 결함 1: 존재하지 않는 ConfigMap 키
**증상** `order-api` 파드가 `CreateContainerConfigError`.

**근거** `kubectl events -n cap-inter --types=Warning`

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
LAST SEEN          TYPE      REASON   OBJECT                          MESSAGE
7s (x5 over 45s)   Warning   Failed   Pod/order-api-f484b6597-xxkxq   Error: couldn't find key API_MODE in ConfigMap cap-inter/order-api-config
```

**원인과 수정** ConfigMap에는 `APP_MODE`가 있는데 Deployment는 `API_MODE`를 찾습니다. `configMapKeyRef.key`를 `APP_MODE`로 고칩니다. 키가 선택 사항이라면 `optional: true`를 줄 수도 있지만, 필수 설정은 지금처럼 시작을 막는 편이 안전합니다.
:::

:::answer 결함 2: 프로브 포트가 틀림
**증상** 결함 1을 고치면 파드는 `Running`이지만 READY가 `0/1`에 머물고, 롤아웃이 끝나지 않습니다.

**근거** Warning 이벤트

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
Warning   Unhealthy   Pod/order-api-6c4659fff8-bdqdq   Readiness probe failed: Get "http://10.244.0.94:8080/": dial tcp 10.244.0.94:8080: connect: connection refused
```

**원인과 수정** nginx는 80번 포트에서 듣는데 readinessProbe가 8080을 검사합니다. `port: http`(컨테이너 포트 이름)로 고칩니다. 포트를 숫자로 적으면 컨테이너 포트를 바꿀 때 프로브를 함께 고치는 것을 잊기 쉽습니다.
:::

:::answer 결함 3: Service 셀렉터 오타
**증상** 파드가 모두 `1/1 Running`인데도 `wget`이 실패합니다.

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME              ADDRESSTYPE   PORTS     ENDPOINTS   AGE
order-api-5rg9d   IPv4          <unset>   <unset>     2m31s
wget: can't connect to remote host (10.96.232.53): Connection refused
command terminated with exit code 1
```

**근거** `kubectl get svc order-api -n cap-inter -o jsonpath='{.spec.selector}'`는 `{"app.kubernetes.io/name":"order-api"}`인데, `kubectl get pods -n cap-inter --show-labels`의 파드 라벨은 `app.kubernetes.io/name=orders-api`입니다.

**원인과 수정** Service 셀렉터를 `orders-api`로 고칩니다. Deployment 이름(`order-api`)과 라벨 값(`orders-api`)이 달라 생긴 전형적인 실수입니다. 이름과 라벨 규칙을 팀에서 정해 두면 예방할 수 있습니다.
:::

:::answer 결함 4: 워커 메모리 제한 부족
**증상** `order-worker`가 `OOMKilled`와 `CrashLoopBackOff`를 오가며 RESTARTS가 계속 늘어납니다.

**근거** `kubectl get pod -n cap-inter -l app.kubernetes.io/name=order-worker -o jsonpath='{.items[0].status.containerStatuses[0].lastState.terminated.reason} {.items[0].status.containerStatuses[0].lastState.terminated.exitCode}'` → `OOMKilled 137`. 로그 첫 줄에 「약 50MiB」를 적재한다고 나옵니다.

**원인과 수정** 약 50MiB를 메모리에 올리는데 limits가 32Mi입니다. 실제 필요량에 여유를 더해 `128Mi`로 올립니다. 필요량을 모르는 앱이라면 metrics-server의 `kubectl top pods`로 측정한 뒤 정합니다. 메모리 사용이 시간에 따라 계속 늘어난다면 limits를 올리는 것은 임시방편이고 누수를 고쳐야 합니다.

명령 맨 앞의 `set -e`는 메모리를 쓰는 하위 프로세스가 강제 종료되면 셸도 바로 끝나게 합니다. cgroup v2 노드에서는 kubelet이 OOM 발생 시 컨테이너 전체를 종료하지만, 검증 환경(cgroup v1)에서는 하위 프로세스만 종료되고 셸은 계속 실행되는 것을 확인했습니다. 환경에 관계없이 같은 증상이 나오도록 넣은 줄입니다.
:::

:::answer 수정 요약 (diff)
```text
39c39  key: API_MODE                        →  key: APP_MODE
47c47  port: 8080                           →  port: http
70c70  app.kubernetes.io/name: order-api    →  app.kubernetes.io/name: orders-api   (Service 셀렉터)
102c102 memory: 32Mi                        →  memory: 128Mi                         (order-worker limits)
```

```bash shell="실습 터미널"
kubectl apply -f order-broken.yaml
kubectl rollout status deployment/order-api -n cap-inter
kubectl rollout status deployment/order-worker -n cap-inter
```

수정한 파일 이름을 그대로 둔 채 apply해도 됩니다. 검증 환경에서는 결함을 하나씩 고쳐 apply하며 위 증상들을 차례로 확인했습니다.
:::

## 정리와 재실행

```bash shell="실습 터미널"
kubectl delete namespace cap-inter
kubectl get namespace cap-inter
```

`NotFound`면 정리 완료입니다. 다시 도전하려면 「YAML 받기」로 결함이 있는 원본을 새로 받아 시작합니다.
