## 과제 소개

사내 방명록 서비스의 프런트엔드를 Kubernetes로 옮기는 일을 맡았습니다. 아래 **요구 사항**만 보고 매니페스트를 직접 작성해 배포하고, 이어지는 운영 상황에 대응하세요. 단계별 명령은 주지 않습니다. 막히면 [첫 Deployment·Service](#/item/b-lab01)와 [롤링 업데이트·로그·이벤트](#/item/b-lab02)를 다시 보거나, 맨 아래 해설을 펼칩니다.

이 과제를 마치면 기본 과정의 목표인 배포·노출·확장·업데이트·진단을 안내 없이 해낼 수 있는지 스스로 확인할 수 있습니다.

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context
kubectl get namespace cap-basic
```

`k8s-lab`이어야 하고, 두 번째 명령은 `NotFound`가 정상입니다.

## 요구 사항 1: 배포

| 항목 | 요구 |
|---|---|
| 네임스페이스 | `cap-basic` |
| Deployment 이름 | `guestbook-front` |
| 이미지 | `nginx:1.30.6-alpine`, 컨테이너 포트 80에 이름 `http` |
| 레플리카 | 3 |
| 라벨 | 파드와 Deployment 모두 `app.kubernetes.io/name: guestbook`, `app.kubernetes.io/component: frontend`, `app.kubernetes.io/part-of: guestbook` |
| 업데이트 전략 | 롤링 업데이트 중 준비된 파드가 원하는 수보다 줄어들지 않을 것 |
| 변경 기록 | `rollout history`에 변경 이유가 남을 것 |
| Service | 이름 `guestbook-front`, ClusterIP, 포트 80 → 컨테이너 포트 이름 `http` |
| 확인용 파드 | `client` (`busybox:1.37.0`, `sleep 3600`) |

`client` 파드에서 `wget -qO- http://guestbook-front`가 nginx 페이지를 돌려주면 1단계 완료입니다.

## 요구 사항 2: 운영 변경

트래픽이 늘었고 보안 패치가 나왔습니다. **매니페스트 파일을 고쳐서** 한 번에 반영하세요.

- 레플리카를 4로 늘립니다.
- 이미지를 `nginx:1.31.7-alpine`으로 올립니다.
- 변경 이유를 기록합니다.

## 요구 사항 3: 장애 대응

동료가 급하게 아래 명령을 실행했습니다. 그대로 실행해 상황을 재현하세요.

```bash shell="실습 터미널"
kubectl set image deployment/guestbook-front nginx=nginx:1.31.70-alpine -n cap-basic
```

1. 서비스가 끊겼는지, 어떤 파드에 무슨 문제가 있는지 **근거(명령과 출력)**와 함께 적어 보세요.
2. 1.31.7, 레플리카 4개 상태로 복구하세요. 복구 후 다음에 누가 파일로 apply해도 같은 상태가 유지되어야 합니다.

## 성공 판정

```verify
id: bcap-state
title: 최종 상태: 1.31.7, 4/4 준비, 엔드포인트 4개, HTTP 200
explain: 이미지, 준비 레플리카, 준비된 엔드포인트 수, client 파드에서 받은 HTTP 상태 코드를 한 줄로 출력합니다.
command: NS=cap-basic; echo "image=$(kubectl get deploy guestbook-front -n $NS -o jsonpath='{.spec.template.spec.containers[0].image}') ready=$(kubectl get deploy guestbook-front -n $NS -o jsonpath='{.status.readyReplicas}/{.spec.replicas}') endpoints=$(kubectl get endpointslices -n $NS -l kubernetes.io/service-name=guestbook-front -o jsonpath='{range .items[*].endpoints[*]}{.conditions.ready}{"\n"}{end}' | grep -c true) http=$(kubectl exec client -n $NS -- wget -S -O /dev/null -T 5 http://guestbook-front 2>&1 | awk '/HTTP\//{print $2}' | tail -1)"
expect: ^image=nginx:1\.31\.7-alpine ready=4/4 endpoints=4 http=200$
criteria: image=nginx:1.31.7-alpine ready=4/4 endpoints=4 http=200
```

```verify
id: bcap-spec
title: 라벨과 무중단 전략
explain: part-of 라벨 값과 maxUnavailable 값을 출력합니다.
command: kubectl get deploy guestbook-front -n cap-basic -o jsonpath='{.metadata.labels.app\.kubernetes\.io/part-of} {.spec.strategy.rollingUpdate.maxUnavailable}{"\n"}'
expect: ^guestbook 0$
criteria: guestbook 0
```

검증 환경에서 해설 매니페스트로 진행한 실제 출력은 `image=nginx:1.31.7-alpine ready=4/4 endpoints=4 http=200`, `guestbook 0`이었습니다.

## 스스로 점검

- [ ] 매니페스트를 보지 않고 Deployment의 셀렉터와 템플릿 라벨이 왜 같아야 하는지 설명할 수 있다
- [ ] 장애 대응에서 서비스가 끊기지 않은 이유를 설정 이름으로 말할 수 있다
- [ ] `rollout undo`와 「파일 수정 후 apply」의 차이를 말할 수 있다
- [ ] 정리 명령이 이 과제의 자원만 지운다는 것을 확인했다

## 해설

:::answer 요구 사항 1·2 해설: 매니페스트
요구 사항 2까지 반영한 최종 파일입니다. 처음에는 `replicas: 3`, `nginx:1.30.6-alpine`, change-cause `"1.30.6 최초 배포, 3개"`로 시작해 세 군데를 고쳐 apply하면 됩니다.

```yaml file=guestbook.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: guestbook-front
  namespace: cap-basic
  labels:
    app.kubernetes.io/name: guestbook
    app.kubernetes.io/component: frontend
    app.kubernetes.io/part-of: guestbook
  annotations:
    kubernetes.io/change-cause: "1.31.7 업데이트, 4개로 확장"
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: guestbook
      app.kubernetes.io/component: frontend
  template:
    metadata:
      labels:
        app.kubernetes.io/name: guestbook
        app.kubernetes.io/component: frontend
        app.kubernetes.io/part-of: guestbook
    spec:
      containers:
        - name: nginx
          image: nginx:1.31.7-alpine
          ports:
            - name: http
              containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: guestbook-front
  namespace: cap-basic
  labels:
    app.kubernetes.io/name: guestbook
    app.kubernetes.io/part-of: guestbook
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: guestbook
    app.kubernetes.io/component: frontend
  ports:
    - name: http
      port: 80
      targetPort: http
```

```bash shell="실습 터미널"
kubectl create namespace cap-basic
kubectl apply -f guestbook.yaml
kubectl rollout status deployment/guestbook-front -n cap-basic
kubectl run client -n cap-basic --image=busybox:1.37.0 --restart=Never -- sleep 3600
kubectl wait pod/client -n cap-basic --for=condition=Ready --timeout=60s
kubectl exec client -n cap-basic -- wget -qO- -T 5 http://guestbook-front
```

셀렉터에 `part-of`를 넣지 않은 이유: 셀렉터는 만든 뒤 바꿀 수 없으므로, 앱을 식별하는 데 꼭 필요한 최소한의 라벨만 씁니다.
:::

:::answer 요구 사항 3 해설: 장애 대응
**진단.** `kubectl get pods -n cap-basic`을 보면 옛 1.31.7 파드 4개는 `Running`이고 새 파드 하나만 `ErrImagePull`입니다. `kubectl describe pod <그 파드>`의 Events에 `Failed to pull image "nginx:1.31.70-alpine"`이 보입니다. `maxUnavailable: 0`이므로 준비된 파드는 4개로 유지되어 **서비스는 끊기지 않았습니다**.

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME                               READY   STATUS         RESTARTS   AGE
client                             1/1     Running        0          33s
guestbook-front-78d4f86d75-59n7h   1/1     Running        0          30s
guestbook-front-78d4f86d75-7rq2p   1/1     Running        0          32s
guestbook-front-78d4f86d75-bqdnx   1/1     Running        0          32s
guestbook-front-78d4f86d75-jk98q   1/1     Running        0          31s
guestbook-front-fb8dfd5ff-n76rr    0/1     ErrImagePull   0          30s
```

**복구.** 파일에는 이미 올바른 1.31.7이 적혀 있으므로 파일을 다시 apply하는 것이 가장 확실합니다. 클러스터와 파일이 다시 일치하게 됩니다.

```bash shell="실습 터미널"
kubectl apply -f guestbook.yaml
kubectl rollout status deployment/guestbook-front -n cap-basic
```

`kubectl rollout undo`로도 복구되지만, 그 경우 파일과 클러스터가 어긋날 수 있다는 경고를 받습니다(기본 과정 2번째 실습 5단계 참고). 파일을 기준으로 삼으면 다음 사람이 apply해도 상태가 유지됩니다.
:::

## 정리와 재실행

```bash shell="실습 터미널"
kubectl delete namespace cap-basic
kubectl get namespace cap-basic
```

`NotFound`면 정리 완료입니다. 다시 도전할 때는 매니페스트를 처음부터 직접 써 보는 것을 권합니다.
