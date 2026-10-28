## 과제 소개

여러분은 플랫폼 팀입니다. 새로 합류하는 「블루 팀」에 네임스페이스 `team-blue`를 내주려 합니다. 회사 보안 기준은 다음 세 가지입니다. 기준을 적용하고, 그 기준을 통과하는 앱을 배포하세요.

1. **파드 보안**: 모든 파드가 [[pss]]의 `restricted` 기준을 지켜야 하며, 어기는 파드는 생성 자체를 거부합니다.
2. **권한**: 팀의 배포 도구용 ServiceAccount는 그 네임스페이스 안에서 일반 워크로드만 다룰 수 있고, 권한 객체(RBAC)는 바꿀 수 없어야 합니다.
3. **네트워크**: 기본은 들어오고 나가는 통신을 모두 막고, DNS와 「프런트 클라이언트 → 웹」만 엽니다.

단계별 안내는 없습니다. [RBAC 실습](#/item/a-lab01)과 [NetworkPolicy 실습](#/item/a-lab02)을 참고하고, 막히면 해설을 펼칩니다.

## 실습 환경

NetworkPolicy가 집행되어야 하므로 **`k8s-lab-calico` 프로필**을 씁니다. 아직 없다면 [NetworkPolicy 실습의 환경 절](#/item/a-lab02)대로 만듭니다.

```bash shell="실습 터미널"
kubectl config use-context k8s-lab-calico
kubectl config current-context
kubectl get pods -n kube-system -l k8s-app=calico-node
kubectl get namespace team-blue
```

`k8s-lab-calico`, calico-node `Running`, `NotFound`를 확인합니다.

## 요구 사항

| 영역 | 요구 |
|---|---|
| 네임스페이스 | `team-blue`. [[psa]] 라벨로 `restricted`를 **enforce**하고, 같은 기준으로 **warn**도 켭니다. 버전은 클러스터 버전을 따르도록 `latest`. |
| ServiceAccount | `deployer`. 토큰 자동 마운트 끔. |
| 권한 | 기본 ClusterRole `edit`을 `team-blue`에서만 부여. |
| NetworkPolicy | ① 모든 파드의 ingress·egress 기본 차단 ② 모든 파드의 DNS(kube-system의 `k8s-app=kube-dns`, 53/UDP·TCP) egress 허용 ③ `role: frontend-client` 파드 → `web` 파드 TCP 8080만 허용(양방향 정책 모두 필요) |
| 앱 `web` | Deployment 2개, `busybox:1.37.0`의 `httpd`로 8080에서 응답. UID 10001로 실행, 루트 파일 시스템 읽기 전용, 모든 capability 제거, 권한 상승 금지, seccomp `RuntimeDefault`. Service `web` 80 → 8080. |
| 확인용 파드 | `tester`(`role: frontend-client` 라벨), `intruder`(라벨 없음). 둘 다 restricted 기준을 지켜야 생성됩니다. |

## 확인할 행동

1. 보안 설정 없이 `kubectl run bad -n team-blue --image=busybox:1.37.0 -- sleep 3600`을 실행하면 **거부**되어야 합니다.
2. `tester`에서 `http://web`은 성공, `intruder`에서는 실패해야 합니다.
3. `deployer`는 Deployment는 만들 수 있지만 RoleBinding은 만들 수 없어야 합니다.

## 성공 판정

```verify
id: acap-psa
title: 기준 미달 파드 거부
explain: 보안 설정 없는 파드를 만들어 보고 거부 메시지의 핵심 부분만 뽑습니다.
command: kubectl run bad -n team-blue --image=busybox:1.37.0 -- sleep 3600 2>&1 | grep -o 'violates PodSecurity "restricted:latest"'
expect: ^violates PodSecurity "restricted:latest"$
criteria: violates PodSecurity "restricted:latest"
```

```verify
id: acap-final
title: 앱 준비, 허용·차단, 권한 경계
explain: web 준비 상태, tester와 intruder의 접속 결과, deployer의 RoleBinding 생성 권한을 한 줄로 출력합니다. Calico 프로필에서 실행합니다.
command: NS=team-blue; echo "web=$(kubectl get deploy web -n $NS -o jsonpath='{.status.readyReplicas}/{.spec.replicas}') tester=$(kubectl exec tester -n $NS -- wget -qO- -T 3 http://web >/dev/null 2>&1 && echo ok || echo blocked) intruder=$(kubectl exec intruder -n $NS -- wget -qO- -T 3 http://web >/dev/null 2>&1 && echo ok || echo blocked) rbac=$(kubectl auth can-i create rolebindings -n $NS --as=system:serviceaccount:$NS:deployer)"
expect: ^web=2/2 tester=ok intruder=blocked rbac=no$
criteria: web=2/2 tester=ok intruder=blocked rbac=no
```

:::warn 검증 범위
첫 번째 판정은 검증 환경에서 실제로 실행해 같은 출력을 확인했습니다. 두 번째 판정은 검증 환경에 Calico가 없어 `web=2/2 tester=ok intruder=ok rbac=no`가 나왔습니다. 즉 Pod Security·RBAC·앱 동작은 검증했고, **intruder 차단(NetworkPolicy 집행)은 검증하지 못했습니다.**
:::

## 스스로 점검

- [ ] restricted 기준이 요구하는 securityContext 항목 다섯 가지를 말할 수 있다
- [ ] `edit` ClusterRole로 할 수 있는 것과 없는 것을 하나씩 예로 들 수 있다
- [ ] egress 기본 차단을 넣을 때 DNS를 왜 함께 열어야 하는지 설명할 수 있다
- [ ] 정리 명령이 `k8s-lab-calico` 컨텍스트의 `team-blue`만 지운다는 것을 확인했다

## 해설

:::answer 1. 네임스페이스와 Pod Security
```yaml file=ns.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-blue
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/warn-version: latest
```

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl apply -f ns.yaml
kubectl run bad -n team-blue --image=busybox:1.37.0 -- sleep 3600
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
Error from server (Forbidden): pods "bad" is forbidden: violates PodSecurity "restricted:latest": allowPrivilegeEscalation != false (container "bad" must set securityContext.allowPrivilegeEscalation=false), unrestricted capabilities (container "bad" must set securityContext.capabilities.drop=["ALL"]), runAsNonRoot != true (pod or container "bad" must set securityContext.runAsNonRoot=true), seccompProfile (pod or container "bad" must set securityContext.seccompProfile.type to "RuntimeDefault" or "Localhost")
```

거부 메시지가 지켜야 할 항목을 모두 알려 줍니다. Pod Security Admission은 **파드 생성 시점**에 검사합니다. Deployment 자체는 만들어지지만 ReplicaSet이 파드를 만들지 못하므로, Deployment가 0/N에 머물면 `kubectl describe replicaset`의 이벤트를 확인합니다. `warn` 라벨은 Deployment를 apply하는 순간에도 경고를 보여 주어 이 문제를 일찍 알아차리게 합니다.
:::

:::answer 2. ServiceAccount와 권한
```yaml file=rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: deployer
  namespace: team-blue
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: deployer-edit
  namespace: team-blue
subjects:
  - kind: ServiceAccount
    name: deployer
    namespace: team-blue
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: edit
```

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl apply -f rbac.yaml
D=system:serviceaccount:team-blue:deployer
kubectl auth can-i create deployments -n team-blue --as=$D
kubectl auth can-i create rolebindings -n team-blue --as=$D
kubectl auth can-i get secrets -n team-blue --as=$D
kubectl auth can-i create deployments -n default --as=$D
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
yes
no
yes
no
```

`edit`은 워크로드·Service·ConfigMap·Secret을 만들고 고칠 수 있지만 Role·RoleBinding은 다룰 수 없어, 스스로 권한을 늘릴 수 없습니다. 반면 **Secret을 읽을 수 있다**는 점은 꼭 알아 두세요. 배포 도구에는 보통 필요하지만, 더 좁히려면 `edit` 대신 직접 만든 Role을 씁니다.
:::

:::answer 3. NetworkPolicy
```yaml file=netpol.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: team-blue
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: team-blue
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-web-from-clients
  namespace: team-blue
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: web
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend-client
      ports:
        - protocol: TCP
          port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-clients-to-web
  namespace: team-blue
spec:
  podSelector:
    matchLabels:
      role: frontend-client
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: web
      ports:
        - protocol: TCP
          port: 8080
```

양방향 모두 기본 차단이므로, tester → web 통신은 **tester의 egress**와 **web의 ingress**를 둘 다 열어야 합니다. 한쪽만 열면 여전히 막힙니다. 포트는 Service 포트(80)가 아니라 파드 포트(8080)를 적습니다.

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl apply -f netpol.yaml
kubectl get networkpolicy -n team-blue
```
:::

:::answer 4. 기준을 통과하는 앱과 확인용 파드
```yaml file=web.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: team-blue
  labels:
    app.kubernetes.io/name: web
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: web
  template:
    metadata:
      labels:
        app.kubernetes.io/name: web
    spec:
      automountServiceAccountToken: false
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        runAsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: httpd
          image: busybox:1.37.0
          command: ["sh", "-c", "mkdir -p /tmp/www && echo '<h1>team-blue</h1>' > /tmp/www/index.html && exec httpd -f -v -p 8080 -h /tmp/www"]
          ports:
            - name: http
              containerPort: 8080
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          resources:
            requests:
              cpu: 10m
              memory: 16Mi
            limits:
              memory: 32Mi
          readinessProbe:
            tcpSocket:
              port: http
            periodSeconds: 5
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: team-blue
spec:
  selector:
    app.kubernetes.io/name: web
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: v1
kind: Pod
metadata:
  name: tester
  namespace: team-blue
  labels:
    role: frontend-client
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10002
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: client
      image: busybox:1.37.0
      command: ["sleep", "3600"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
---
apiVersion: v1
kind: Pod
metadata:
  name: intruder
  namespace: team-blue
spec:
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10003
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: client
      image: busybox:1.37.0
      command: ["sleep", "3600"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
```

| 설정 | restricted 기준과의 관계 |
|---|---|
| `runAsNonRoot: true`, `runAsUser: 10001` | 루트로 실행 금지. 이미지에 사용자가 없어도 UID 숫자로 지정할 수 있습니다. |
| `seccompProfile.type: RuntimeDefault` | 런타임 기본 시스템 콜 필터 사용(필수). |
| `allowPrivilegeEscalation: false` | setuid 등으로 권한을 높이지 못하게 함(필수). |
| `capabilities.drop: ["ALL"]` | 모든 리눅스 capability 제거(필수). 1024 미만 포트를 열 수 없으므로 8080을 씁니다. |
| `readOnlyRootFilesystem: true` + `/tmp` emptyDir | 기준 필수 항목은 아니지만 권장. 쓸 곳은 emptyDir로 따로 줍니다. |
| `automountServiceAccountToken: false` | API를 부르지 않는 앱에 토큰을 넣지 않습니다. |

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl apply -f web.yaml
kubectl rollout status deployment/web -n team-blue
kubectl wait pod tester intruder -n team-blue --for=condition=Ready --timeout=60s
kubectl exec tester -n team-blue -- wget -qO- -T 3 http://web
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드, 대체 busybox 이미지)" date="2026-10-15"
deployment "web" successfully rolled out
pod/tester condition met
pod/intruder condition met
<h1>team-blue</h1>
```
:::

## 정리와 재실행

```bash shell="실습 터미널"
kubectl config current-context
kubectl delete namespace team-blue
```

컨텍스트가 `k8s-lab-calico`인지 확인한 뒤 실행합니다. Calico 프로필이 더 필요 없으면 `minikube delete -p k8s-lab-calico`, 그다음 `kubectl config use-context k8s-lab`으로 기본 클러스터로 돌아갑니다. 다시 도전하려면 요구 사항부터 매니페스트를 직접 작성해 보세요.
