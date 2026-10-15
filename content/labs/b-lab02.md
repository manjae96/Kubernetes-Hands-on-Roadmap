## 학습 목표

- [[label]]과 [[selector]]로 원하는 자원만 골라 조회하고, 라벨을 붙이거나 바꿀 수 있습니다.
- [[rolling-update]]로 이미지 버전을 무중단으로 올리고, [[rollout]] 기록을 확인할 수 있습니다.
- 잘못된 배포를 [[event]]와 [[logs]]로 진단하고 이전 버전으로 되돌릴 수 있습니다.

## 선수 지식

- [클러스터 둘러보기와 첫 Deployment·Service](#/item/b-lab01)에서 Deployment·ReplicaSet·Service의 관계를 익혔어야 합니다.

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context
kubectl get nodes
kubectl get namespace lab-b02
```

`k8s-lab`, 노드 `Ready`를 확인합니다. 마지막 명령은 `NotFound`가 정상입니다. 이미 있다면 이전 실습 잔여물이니 맨 아래 「정리」를 먼저 실행합니다.

## 개념: 라벨로 고르고, ReplicaSet을 바꿔 끼우며 업데이트한다

**라벨과 셀렉터.** 라벨은 객체에 붙이는 이름표이고, 셀렉터는 이름표로 객체를 고르는 조건입니다. Kubernetes에서 「무엇이 무엇을 관리하는가」는 대부분 라벨로 이어집니다. Deployment는 라벨로 자기 파드를 알아보고, Service는 라벨로 트래픽 보낼 파드를 고릅니다. 이 실습은 공식 문서가 권장하는 `app.kubernetes.io/*` 라벨을 씁니다.

**왜 롤링 업데이트인가.** 모든 파드를 한 번에 바꾸면 그 사이 서비스가 끊깁니다. Deployment는 파드 템플릿이 바뀌면 **새 ReplicaSet**을 만들고, 새 쪽을 하나 늘리고 옛 쪽을 하나 줄이는 일을 반복합니다. `maxSurge`(원하는 개수보다 최대 몇 개 더 만들지)와 `maxUnavailable`(최대 몇 개까지 준비 안 된 상태를 허용할지)로 속도와 안전성을 조절합니다.

**왜 되돌릴 수 있나.** 옛 ReplicaSet은 지우지 않고 레플리카 0으로 남겨 둡니다. 그래서 `kubectl rollout undo`는 옛 ReplicaSet을 다시 키우기만 하면 됩니다. 몇 개를 남길지는 `revisionHistoryLimit`이 정합니다.

<figure class="diagram">
<svg viewBox="0 0 760 230" role="img" aria-label="maxSurge 1, maxUnavailable 0일 때 새 ReplicaSet이 하나씩 늘고 옛 ReplicaSet이 하나씩 줄어드는 과정">
<defs><marker id="b2a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="arrowhead"/></marker></defs>
<text class="small" x="10" y="20">replicas: 3 · maxSurge: 1 · maxUnavailable: 0</text>
<g>
<text x="10" y="62">옛 RS (1.30.6)</text><text x="10" y="132">새 RS (1.31.7)</text>
<g transform="translate(130,0)"><text class="small" x="0" y="40">시작</text>
<rect class="box" x="0" y="48" width="22" height="22" rx="4"/><rect class="box" x="28" y="48" width="22" height="22" rx="4"/><rect class="box" x="56" y="48" width="22" height="22" rx="4"/></g>
<g transform="translate(260,0)"><text class="small" x="0" y="40">1단계: 새 1 추가</text>
<rect class="box" x="0" y="48" width="22" height="22" rx="4"/><rect class="box" x="28" y="48" width="22" height="22" rx="4"/><rect class="box" x="56" y="48" width="22" height="22" rx="4"/>
<rect class="box accent" x="0" y="118" width="22" height="22" rx="4"/></g>
<g transform="translate(400,0)"><text class="small" x="0" y="40">2단계: 옛 1 제거, 새 1 추가</text>
<rect class="box" x="0" y="48" width="22" height="22" rx="4"/><rect class="box" x="28" y="48" width="22" height="22" rx="4"/>
<rect class="box accent" x="0" y="118" width="22" height="22" rx="4"/><rect class="box accent" x="28" y="118" width="22" height="22" rx="4"/></g>
<g transform="translate(600,0)"><text class="small" x="0" y="40">끝: 옛 RS 0개로 보관</text>
<rect class="box dim" x="0" y="48" width="78" height="22" rx="4"/><text class="small" x="10" y="63">레플리카 0</text>
<rect class="box accent" x="0" y="118" width="22" height="22" rx="4"/><rect class="box accent" x="28" y="118" width="22" height="22" rx="4"/><rect class="box accent" x="56" y="118" width="22" height="22" rx="4"/></g>
<path class="line" d="M215 95H250M355 95H390M530 95H590" marker-end="url(#b2a)"/>
</g>
<text class="small" x="10" y="190">준비된 파드는 어느 순간에도 3개 아래로 내려가지 않습니다(maxUnavailable: 0). 새 파드가 준비되지 않으면 옛 파드도 줄지 않습니다.</text>
<text class="small" x="10" y="210">rollout undo는 레플리카 0으로 보관된 옛 RS를 다시 키우는 동작입니다.</text>
</svg>
<figcaption>롤링 업데이트 중 두 ReplicaSet의 파드 수 변화</figcaption>
</figure>

## 1단계: 라벨이 다른 두 Deployment 배포

`shop.yaml`로 저장합니다. 한 파일에 `---`로 구분한 객체 세 개가 들어 있습니다.

```yaml file=shop.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: lab-b02
  labels:
    app.kubernetes.io/name: shop
    app.kubernetes.io/component: frontend
  annotations:
    kubernetes.io/change-cause: "nginx 1.30.6 최초 배포"
spec:
  replicas: 3
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app.kubernetes.io/name: shop
      app.kubernetes.io/component: frontend
  template:
    metadata:
      labels:
        app.kubernetes.io/name: shop
        app.kubernetes.io/component: frontend
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.6-alpine
          ports:
            - name: http
              containerPort: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: lab-b02
  labels:
    app.kubernetes.io/name: shop
    app.kubernetes.io/component: api
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: shop
      app.kubernetes.io/component: api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: shop
        app.kubernetes.io/component: api
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.6-alpine
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: lab-b02
spec:
  selector:
    app.kubernetes.io/name: shop
    app.kubernetes.io/component: frontend
  ports:
    - name: http
      port: 80
      targetPort: http
```

| 필드 | 의미 |
|---|---|
| `metadata.annotations."kubernetes.io/change-cause"` | [[annotation]]. 이 값이 `rollout history`의 CHANGE-CAUSE 열에 기록됩니다. 고르는 기준이 아니라 기록용입니다. |
| `revisionHistoryLimit: 5` | 롤백용으로 보관할 옛 ReplicaSet 수(기본 10). |
| `strategy.rollingUpdate.maxSurge: 1` | 업데이트 중 원하는 수(3)보다 최대 1개 더 만들 수 있습니다. |
| `strategy.rollingUpdate.maxUnavailable: 0` | 준비된 파드 수가 3 아래로 내려가지 않게 합니다. 새 파드가 준비되지 않으면 업데이트가 멈춥니다. |
| 두 라벨을 쓴 `selector` | `name=shop`이면서 `component=frontend`인 파드만 고릅니다. api 파드는 Service 대상이 아닙니다. |

```bash shell="실습 터미널"
kubectl create namespace lab-b02
kubectl apply -f shop.yaml
kubectl rollout status deployment/frontend -n lab-b02
kubectl get pods -n lab-b02 --show-labels
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드, 대체 이미지)" date="2026-10-15"
NAME                        READY   STATUS    RESTARTS   AGE   LABELS
api-994d7b98c-npbg7         1/1     Running   0          1s    app.kubernetes.io/component=api,app.kubernetes.io/name=shop,pod-template-hash=994d7b98c
frontend-79f7755d8b-8mbjk   1/1     Running   0          1s    app.kubernetes.io/component=frontend,app.kubernetes.io/name=shop,pod-template-hash=79f7755d8b
frontend-79f7755d8b-g5wx7   1/1     Running   0          1s    app.kubernetes.io/component=frontend,app.kubernetes.io/name=shop,pod-template-hash=79f7755d8b
frontend-79f7755d8b-n4jcc   1/1     Running   0          1s    app.kubernetes.io/component=frontend,app.kubernetes.io/name=shop,pod-template-hash=79f7755d8b
```

`pod-template-hash`는 Deployment가 ReplicaSet별로 자동으로 붙이는 라벨입니다. 같은 Deployment의 옛·새 파드를 구분하는 데 쓰입니다.

## 2단계: 셀렉터로 골라 보기

```bash shell="실습 터미널"
# 같음 조건
kubectl get pods -n lab-b02 -l app.kubernetes.io/component=frontend
# 집합 조건, 라벨 값을 열로 표시
kubectl get pods -n lab-b02 -l 'app.kubernetes.io/component in (frontend,api)' -L app.kubernetes.io/component
# 부정 조건
kubectl get pods -n lab-b02 -l 'app.kubernetes.io/component!=frontend'
# 라벨 추가 후 열로 확인
kubectl label deployment api -n lab-b02 team=payments
kubectl get deployments -n lab-b02 -L team
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME                        READY   STATUS    RESTARTS   AGE   COMPONENT
api-994d7b98c-npbg7         1/1     Running   0          1s    api
frontend-79f7755d8b-8mbjk   1/1     Running   0          1s    frontend
frontend-79f7755d8b-g5wx7   1/1     Running   0          1s    frontend
frontend-79f7755d8b-n4jcc   1/1     Running   0          1s    frontend
```

집합 조건은 셸이 괄호와 쉼표를 해석하지 않도록 작은따옴표로 감쌉니다.

## 3단계: 롤링 업데이트

파일에서 frontend의 이미지를 `nginx:1.31.7-alpine`으로, change-cause를 `"nginx 1.31.7로 업데이트"`로 고칩니다. 편집기를 쓰거나 아래 명령을 씁니다. (macOS 기본 `sed`는 `-i ''`가 필요하므로 편집기로 고치는 편이 간단합니다.)

```bash shell="Linux · WSL2 (GNU sed)"
sed -i 's/nginx:1.30.6-alpine/nginx:1.31.7-alpine/; s/nginx 1.30.6 최초 배포/nginx 1.31.7로 업데이트/' shop.yaml
```

이 `sed` 명령은 줄마다 처음 일치하는 곳을 바꾸므로, 서로 다른 줄에 있는 frontend와 api의 이미지가 **둘 다** 1.31.7로 바뀝니다. 그래서 apply하면 api도 함께 업데이트됩니다. frontend만 바꾸고 싶다면 편집기로 해당 줄만 고칩니다. 어느 쪽이든 아래 `grep`으로 결과를 확인하는 습관을 들이세요.

```bash shell="실습 터미널"
grep -n "image:" shop.yaml
kubectl apply -f shop.yaml
kubectl rollout status deployment/frontend -n lab-b02
kubectl get replicasets -n lab-b02 -l app.kubernetes.io/component=frontend
kubectl rollout history deployment/frontend -n lab-b02
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
deployment "frontend" successfully rolled out
NAME                  DESIRED   CURRENT   READY   AGE
frontend-5568dd6cf8   3         3         3       2s
frontend-79f7755d8b   0         0         0       4s
deployment.apps/frontend 
REVISION  CHANGE-CAUSE
1         nginx 1.30.6 최초 배포
2         nginx 1.31.7로 업데이트
```

옛 ReplicaSet(`79f7755d8b`)이 레플리카 0으로 남아 있는 것이 롤백의 근거입니다. 업데이트 과정을 눈으로 보고 싶다면 다른 터미널에서 `kubectl get pods -n lab-b02 -l app.kubernetes.io/component=frontend -w`를 켜 두고 apply합니다.

## 4단계: 잘못된 배포 재현과 진단

태그에 오타가 있는 이미지로 바꿉니다. 실무에서 가장 흔한 배포 실패입니다.

```bash shell="실습 터미널"
kubectl set image deployment/frontend nginx=nginx:1.31.77-alpine -n lab-b02
kubectl annotate deployment/frontend -n lab-b02 kubernetes.io/change-cause="태그 오타 배포" --overwrite
kubectl rollout status deployment/frontend -n lab-b02 --timeout=60s
```

**예상해 보세요.** 롤아웃이 끝나지 않고 시간 초과가 납니다. 그렇다면 서비스는 끊겼을까요?

```bash shell="실습 터미널"
kubectl get pods -n lab-b02 -l app.kubernetes.io/component=frontend
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME                        READY   STATUS         RESTARTS   AGE
frontend-5568dd6cf8-cdsmj   1/1     Running        0          61s
frontend-5568dd6cf8-prnpx   1/1     Running        0          62s
frontend-5568dd6cf8-wj9t5   1/1     Running        0          62s
frontend-7cd75f58ff-sc7z9   0/1     ErrImagePull   0          60s
```

`maxUnavailable: 0` 덕분에 옛 파드 3개는 그대로 일하고, 새 파드 1개만 막혀 있습니다. 서비스는 끊기지 않았습니다. 이제 원인을 찾습니다. **진단 순서: 파드 상태 → describe의 Events → 이벤트 목록.**

```bash shell="실습 터미널"
kubectl describe pod <ErrImagePull 파드 이름> -n lab-b02
kubectl events -n lab-b02 --for pod/<ErrImagePull 파드 이름> --types=Warning
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드) · 레지스트리 접근이 막힌 환경이라 실패 사유 문구가 minikube와 다름" date="2026-10-15"
Events:
  Type     Reason     Age                From               Message
  ----     ------     ----               ----               -------
  Normal   Scheduled  67s                default-scheduler  Successfully assigned lab-b02/frontend-7cd75f58ff-sc7z9 to k8s-lab
  Normal   Pulling    29s (x3 over 68s)  kubelet            spec.containers{nginx}: Pulling image "nginx:1.31.77-alpine"
  Warning  Failed     28s (x3 over 68s)  kubelet            spec.containers{nginx}: Failed to pull image "nginx:1.31.77-alpine": failed to pull and unpack image "docker.io/library/nginx:1.31.77-alpine ...
  Warning  Failed     28s (x3 over 68s)  kubelet            spec.containers{nginx}: Error: ErrImagePull
  Normal   BackOff    13s (x3 over 67s)  kubelet            spec.containers{nginx}: Back-off pulling image "nginx:1.31.77-alpine"
  Warning  Failed     13s (x3 over 67s)  kubelet            spec.containers{nginx}: Error: ImagePullBackOff
```

인터넷에 연결된 minikube에서는 Failed 메시지 끝에 `not found`가 붙어 「그런 태그가 없다」는 것이 드러납니다. `ErrImagePull`은 방금 실패한 상태, [[imagepullbackoff]]는 재시도 간격을 늘리며 기다리는 상태입니다.

## 5단계: 롤백

```bash shell="실습 터미널"
kubectl rollout undo deployment/frontend -n lab-b02
kubectl rollout status deployment/frontend -n lab-b02
kubectl rollout history deployment/frontend -n lab-b02
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
Warning: resource deployments/frontend was previously managed with 'kubectl apply'. Rolling back will not update the kubectl.kubernetes.io/last-applied-configuration annotation, which may cause unexpected behavior on future 'kubectl apply' operations. Consider using 'kubectl apply' with your previous configuration file instead.
deployment.apps/frontend rolled back
deployment "frontend" successfully rolled out
deployment.apps/frontend 
REVISION  CHANGE-CAUSE
1         nginx 1.30.6 최초 배포
3         태그 오타 배포
4         nginx 1.31.7로 업데이트
```

롤백은 「리비전 2로 돌아가기」가 아니라 **리비전 2의 템플릿으로 새 리비전 4를 만드는 것**입니다. 그래서 2가 사라지고 4가 생겼습니다. 특정 리비전으로 가려면 `--to-revision=<번호>`를 씁니다.

:::warn 경고 문구의 의미
kubectl은 「apply로 관리하던 객체를 undo로 바꿨으니, 다음 apply 때 예상과 다르게 동작할 수 있다」고 알려 줍니다. 클러스터는 1.31.7로 돌아갔지만 `kubectl set image`를 쓰지 않은 파일(`shop.yaml`)에도 1.31.7이 적혀 있으므로 이 실습에서는 문제없습니다. 실무에서는 **파일을 되돌리고 apply하는 것**을 기본으로 삼고, undo는 긴급 조치로 씁니다.
:::

## 6단계: 로그와 이벤트 읽기

```bash shell="실습 터미널"
# Deployment의 파드 하나를 골라 마지막 3줄
kubectl logs deployment/frontend -n lab-b02 --tail=3
# 라벨로 고른 모든 파드의 로그, 파드 이름을 앞에 붙여서
kubectl logs -n lab-b02 -l app.kubernetes.io/component=frontend --tail=2 --prefix
```

다음은 시작하자마자 오류를 내고 종료되는 파드입니다. [[crashloopbackoff]]를 재현합니다.

```bash shell="실습 터미널"
kubectl run crasher -n lab-b02 --image=busybox:1.37.0 -- sh -c 'echo "설정 확인 중..."; echo "오류: DB_HOST 환경 변수가 설정되지 않음" >&2; exit 1'
```

30초쯤 기다린 뒤 확인합니다.

```bash shell="실습 터미널"
kubectl get pod crasher -n lab-b02
kubectl logs crasher -n lab-b02
kubectl describe pod crasher -n lab-b02 | grep -A6 "Last State"
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME      READY   STATUS   RESTARTS      AGE
crasher   0/1     Error    2 (39s ago)   40s
설정 확인 중...
오류: DB_HOST 환경 변수가 설정되지 않음
    Last State:     Terminated
      Reason:       Error
      Exit Code:    1
```

STATUS는 확인 시점에 따라 `Error`나 `CrashLoopBackOff`로 보입니다. 표준 출력과 표준 오류는 모두 컨테이너 로그로 수집됩니다. 컨테이너가 **재시작되어 다시 실행 중**일 때 직전 실행의 로그를 보려면 `kubectl logs <파드> --previous`를 씁니다. 지금처럼 컨테이너가 종료된 채 다음 재시작을 기다리는 동안에는 `--previous` 없이도 마지막 실행의 로그가 보입니다.

## 성공 판정

```verify
id: b2-rollback
title: 롤백 후 1.31.7로 3개 모두 준비, 리비전 4
explain: 현재 이미지, 준비된 레플리카 수, Deployment 리비전 번호를 출력합니다.
command: kubectl get deploy frontend -n lab-b02 -o jsonpath='{.spec.template.spec.containers[0].image} {.status.readyReplicas}/{.spec.replicas} {.metadata.annotations.deployment\.kubernetes\.io/revision}{"\n"}'
expect: ^nginx:1\.31\.7-alpine 3/3 \d+$
criteria: 「nginx:1.31.7-alpine 3/3 4」 (리비전 번호는 연습을 더 했다면 다를 수 있음)
```

```verify
id: b2-logs
title: 크래시 원인 로그 확인
explain: 종료된 컨테이너의 로그에서 오류 원인을 읽습니다.
command: kubectl logs crasher -n lab-b02
expect: DB_HOST
criteria: 출력에 「DB_HOST」가 포함됨
```

검증 환경에서의 실제 출력은 각각 `nginx:1.31.7-alpine 3/3 4`와 위 6단계의 로그 두 줄이었습니다.

## 흔한 오류, 진단 순서, 해결 방법

| 증상 | 확인 명령 | 원인과 해결 |
|---|---|---|
| `rollout status`가 끝나지 않음 | `kubectl get pods -l ...`, `kubectl describe pod` | 새 파드가 준비되지 않았습니다. Events에서 이미지·자원·프로브 문제를 찾고, 고칠 수 없으면 `rollout undo`. |
| `ErrImagePull` 뒤에 `not found` | `kubectl describe pod` | 태그 오타입니다. 레지스트리에서 태그를 확인합니다. |
| `ErrImagePull` 뒤에 `unauthorized`·`denied` | 같음 | 비공개 이미지입니다. `imagePullSecrets`가 필요합니다. |
| `ErrImagePull` 뒤에 `i/o timeout`·`no such host` | `minikube ssh -p k8s-lab -- curl -sI https://registry-1.docker.io` | 노드에서 레지스트리로 연결이 안 됩니다. 프록시·DNS 설정을 확인합니다. |
| 셀렉터 조회 결과가 비어 있음 | `kubectl get pods --show-labels` | 라벨 키 철자나 값이 다릅니다. 따옴표 누락으로 셸이 괄호를 해석했는지도 봅니다. |
| `logs`에 아무것도 없음 | `kubectl logs ... --previous`, `describe`의 Last State | 앱이 파일에만 로그를 쓰거나, 재시작 전 로그입니다. 앱은 표준 출력으로 로그를 남기도록 설정하는 것이 원칙입니다. |
| 이벤트가 보이지 않음 | `kubectl get events -n lab-b02` | 이벤트는 기본 1시간 뒤 삭제됩니다. 오래된 문제는 로그·모니터링으로 추적합니다. |

## 응용 과제

**과제 1.** `maxSurge: 0`, `maxUnavailable: 1`로 바꾸고 이미지를 `nginx:1.30.6-alpine`으로 되돌려 apply하세요. 업데이트 중 준비된 파드 수가 어떻게 달라지나요? 이 설정에서 태그 오타를 배포하면 어떤 일이 생길까요?

:::answer 힌트와 해설
힌트: `kubectl get pods -w`와 `kubectl get deploy frontend -w`를 다른 터미널에 띄워 두세요.

해설: 새 파드를 먼저 만들지 않고 옛 파드를 하나 지운 뒤 새 파드를 만듭니다. 업데이트 중 준비된 파드가 2개로 줄어듭니다. 이 상태에서 오타를 배포하면 옛 파드 하나가 이미 지워진 뒤 새 파드가 막히므로 **용량이 줄어든 채로 멈춥니다**. 여유 자원이 없는 클러스터에서 쓰는 설정이지만, 실패 시 영향이 더 큽니다.
:::

**과제 2.** `--to-revision`으로 1.30.6(리비전 1)으로 되돌려 보고, `kubectl rollout history deployment/frontend -n lab-b02 --revision=<번호>`로 각 리비전의 템플릿을 비교하세요.

:::answer 해설
`kubectl rollout undo deployment/frontend -n lab-b02 --to-revision=1`. 리비전 1이 새 번호(예: 5)로 다시 나타나고 원래 1은 목록에서 사라집니다. `--revision`을 붙인 history는 해당 리비전의 파드 템플릿(이미지, 라벨)을 보여 줍니다.
:::

**과제 3.** crasher 파드의 명령을 고쳐 정상 동작하게 하려면 무엇을 바꿔야 하나요? 파드의 `command`는 만든 뒤 바꿀 수 있을까요?

:::answer 해설
파드의 컨테이너 명령은 생성 후 바꿀 수 없습니다(이미지 등 일부 필드만 변경 가능). 파드를 지우고 다시 만들어야 합니다. 이것이 파드를 직접 만들지 않고 Deployment를 쓰는 또 하나의 이유입니다. Deployment는 템플릿을 바꾸면 새 파드로 교체해 줍니다.
:::

## 정리와 재실행

```bash shell="실습 터미널"
kubectl delete namespace lab-b02
kubectl get namespace lab-b02
```

`NotFound`가 나오면 정리 완료입니다. 다시 하려면 `shop.yaml`의 이미지를 `nginx:1.30.6-alpine`, change-cause를 `"nginx 1.30.6 최초 배포"`로 되돌린 뒤 1단계부터 반복합니다. 「YAML 받기」로 원본을 다시 받아도 됩니다.
