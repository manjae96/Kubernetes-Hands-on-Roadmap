## 학습 목표

- [[networkpolicy]]가 Kubernetes API 객체이고, 실제 집행은 [[cni]] 플러그인이 맡는다는 점을 설명할 수 있습니다.
- 「기본 차단 + 필요한 것만 허용」 방식으로 ingress 정책을 작성하고 결과를 확인할 수 있습니다.
- `namespaceSelector`와 `podSelector`를 같은 항목에 쓸 때(AND)와 따로 쓸 때(OR)의 차이를 구분할 수 있습니다.
- egress를 막을 때 DNS를 함께 허용해야 하는 이유를 설명할 수 있습니다.

## 선수 지식

- [첫 Deployment·Service](#/item/b-lab01): Service, 라벨 셀렉터, 클라이언트 파드에서 `wget`으로 확인하는 방법
- TCP·UDP 포트, DNS가 53번 포트를 쓴다는 것

## 이 실습만의 환경: Calico 프로필

:::why 왜 별도 환경이 필요한가
minikube 기본 CNI(kindnet)는 NetworkPolicy를 **집행하지 않습니다**. 정책 객체는 오류 없이 만들어지지만 아무 효과가 없어, 실습 결과가 「다 통과」로만 나옵니다. 그래서 정책을 집행하는 [[calico]]를 설치한 **별도 프로필 `k8s-lab-calico`**를 만듭니다. 기존 `k8s-lab`에 CNI를 바꿔 끼우는 것보다 새로 만드는 편이 훨씬 간단하고 안전합니다. 고급 종합 과제도 이 프로필을 씁니다.
:::

| 구성 요소 | 구분 | 버전 |
|---|---|---|
| NetworkPolicy (`networking.k8s.io/v1`) | Kubernetes 기능 | 1.35 · 1.36 · 1.37 동일 |
| Calico | 외부 생태계 도구 (CNI) | v3.32.2 (minikube v1.39.0 내장 매니페스트) |

**설치** — 노드 이미지는 이미 받아 두었으므로 첫 프로필보다 빠르지만, Calico 이미지를 내려받느라 수 분이 걸립니다.

```bash shell="실습 터미널"
minikube start -p k8s-lab-calico --driver=docker --kubernetes-version=v1.37.0 --cni=calico --cpus=2 --memory=4096
```

1.36·1.35로 학습한다면 `--kubernetes-version`을 `v1.36.4`·`v1.35.8`로 바꿉니다. 메모리가 부족하면 먼저 `minikube stop -p k8s-lab`으로 기본 프로필을 멈춥니다.

**검증** — minikube가 kubectl 컨텍스트를 새 프로필로 바꿉니다. **이 실습의 모든 명령은 이 컨텍스트에서 실행합니다.**

```bash shell="실습 터미널"
kubectl config current-context
kubectl get pods -n kube-system -l k8s-app=calico-node
kubectl get pods -n kube-system -l k8s-app=calico-kube-controllers
```

```output kind=example note="minikube v1.39.0 --cni=calico 기준 · 접미사와 AGE는 환경마다 다름"
k8s-lab-calico
NAME                READY   STATUS    RESTARTS   AGE
calico-node-xxxxx   1/1     Running   0          3m
NAME                                       READY   STATUS    RESTARTS   AGE
calico-kube-controllers-xxxxxxxxxx-xxxxx   1/1     Running   0          3m
```

두 파드가 모두 `1/1 Running`이 될 때까지 기다립니다. **삭제 방법**은 맨 아래 「정리」에 있습니다.

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context
kubectl get namespace lab-a02 lab-a02-partner
```

`k8s-lab-calico`와 두 개의 `NotFound`가 나와야 합니다. 컨텍스트가 `k8s-lab`이면 `kubectl config use-context k8s-lab-calico`로 바꿉니다.

## 개념: 선택된 파드는 허용 목록 밖을 차단

**무엇인가.** NetworkPolicy는 파드 단위 방화벽 규칙입니다. `podSelector`로 정책을 적용할 파드를 고르고, `ingress`(들어오는)·`egress`(나가는) 방향별로 허용할 상대와 포트를 적습니다.

**왜 필요한가.** 기본적으로 클러스터 안의 모든 파드는 서로 통신할 수 있습니다. 웹 파드 하나가 뚫리면 DB까지 바로 접근할 수 있다는 뜻입니다. 정책으로 「DB에는 API 파드만」처럼 경로를 좁히면 피해 범위가 줄어듭니다.

**어떻게 동작하나.** 세 가지 규칙만 기억하면 됩니다.

1. 어떤 정책에도 선택되지 않은 파드는 **모두 허용**입니다.
2. 한 방향(예: Ingress)으로 **하나라도** 정책에 선택된 파드는, 그 방향에서 정책들이 허용한 것 **외에는 모두 차단**됩니다.
3. 정책끼리는 **합집합**입니다. 거부 규칙은 없고, 여러 정책의 허용이 더해질 뿐입니다.

정책은 [[kube-apiserver]]에 저장될 뿐이고, 각 노드의 CNI 에이전트(여기서는 calico-node)가 이를 읽어 실제 패킷 필터를 설정합니다.

<figure class="diagram">
<svg viewBox="0 0 760 260" role="img" aria-label="default-deny 정책 위에서 api 파드와 파트너 네임스페이스의 api 파드만 db에 접근할 수 있고 stranger는 차단되는 구성">
<defs><marker id="a2a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="arrowhead"/></marker></defs>
<rect class="zone" x="10" y="12" width="470" height="236" rx="8"/><text class="small" x="22" y="30">네임스페이스 lab-a02 · default-deny-ingress 적용</text>
<rect class="box accent" x="330" y="100" width="130" height="60" rx="6"/><text x="342" y="124">db (nginx)</text><text class="small" x="342" y="142">TCP 80</text>
<rect class="box" x="30" y="60" width="140" height="44" rx="6"/><text x="42" y="80">api</text><text class="small" x="42" y="96">role=api</text>
<rect class="box" x="30" y="170" width="140" height="44" rx="6"/><text x="42" y="190">stranger</text><text class="small" x="42" y="206">라벨 없음</text>
<path class="line" d="M172 82L328 120" marker-end="url(#a2a)"/><text class="small" x="210" y="88">allow-api-to-db</text>
<path class="line bad" d="M172 192L320 150"/><text x="236" y="182" style="fill:var(--bad);font-weight:700">✕</text>
<rect class="zone" x="510" y="80" width="240" height="110" rx="8"/><text class="small" x="522" y="98">네임스페이스 lab-a02-partner</text>
<rect class="box" x="560" y="114" width="140" height="44" rx="6"/><text x="572" y="134">api</text><text class="small" x="572" y="150">role=api</text>
<path class="line" d="M558 136H462" marker-end="url(#a2a)"/><text class="small" x="476" y="72">allow-partner-api</text>
<text class="small" x="476" y="232">namespaceSelector AND podSelector</text>
</svg>
<figcaption>Calico 프로필에서 기대하는 최종 상태. 화살표는 허용된 경로입니다.</figcaption>
</figure>

## 1단계: 앱과 클라이언트 배포

DB 역할의 nginx, 허용할 `api` 파드, 막을 `stranger` 파드를 만듭니다. `app.yaml`로 저장합니다.

```yaml file=app.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db
  namespace: lab-a02
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: db
  template:
    metadata:
      labels:
        app.kubernetes.io/name: db
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.6-alpine
          ports:
            - name: http
              containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: db
  namespace: lab-a02
spec:
  selector:
    app.kubernetes.io/name: db
  ports:
    - name: http
      port: 80
      targetPort: http
---
apiVersion: v1
kind: Pod
metadata:
  name: api
  namespace: lab-a02
  labels:
    role: api
spec:
  containers:
    - name: client
      image: busybox:1.37.0
      command: ["sleep", "3600"]
---
apiVersion: v1
kind: Pod
metadata:
  name: stranger
  namespace: lab-a02
spec:
  containers:
    - name: client
      image: busybox:1.37.0
      command: ["sleep", "3600"]
```

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl create namespace lab-a02
kubectl apply -f app.yaml
kubectl wait pod --all -n lab-a02 --for=condition=Ready --timeout=120s
```

정책 전 상태를 확인하는 짧은 셸 함수를 정의합니다. 같은 터미널에서 이후 단계마다 다시 씁니다.

```bash shell="실습 터미널 (bash·zsh)"
check() { for p in api stranger; do kubectl exec $p -n lab-a02 -- wget -qO- -T 3 http://db >/dev/null 2>&1 && echo "$p=ok" || echo "$p=blocked"; done | paste -sd' ' -; }
check
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드, 정책 미집행 CNI)" date="2026-10-15"
api=ok stranger=ok
```

**예상해 보세요.** 정책이 하나도 없으니 둘 다 `ok`여야 합니다.

## 2단계: 기본 차단

```yaml file=np-default-deny.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: lab-a02
spec:
  podSelector: {}
  policyTypes:
    - Ingress
```

| 필드 | 의미 |
|---|---|
| `podSelector: {}` | 빈 셀렉터는 **네임스페이스의 모든 파드**를 선택합니다. |
| `policyTypes: [Ingress]` + `ingress` 없음 | 들어오는 트래픽을 하나도 허용하지 않습니다. 나가는 트래픽은 영향받지 않습니다. |

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl apply -f np-default-deny.yaml
check
```

```output kind=example note="Calico 프로필에서 기대하는 결과 · 검증 환경에서는 정책이 집행되지 않아 확인하지 못함"
api=blocked stranger=blocked
```

`blocked`는 `wget`이 3초 안에 응답을 받지 못했다는 뜻입니다. Calico는 차단된 패킷을 조용히 버리므로 거부 응답 대신 시간 초과가 납니다.

## 3단계: api만 허용

```yaml file=np-allow-api.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-to-db
  namespace: lab-a02
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: db
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: api
      ports:
        - protocol: TCP
          port: 80
```

| 필드 | 의미 |
|---|---|
| `spec.podSelector` | 이 정책이 보호하는 파드: DB. |
| `ingress[].from[].podSelector` | **같은 네임스페이스**에서 `role=api` 라벨을 가진 파드만 허용합니다. |
| `ports` | 그 파드에서 오는 TCP 80만 허용합니다. Service 포트가 아니라 **파드의 포트**를 적습니다. |

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl apply -f np-allow-api.yaml
check
```

```output kind=example note="Calico 프로필에서 기대하는 결과"
api=ok stranger=blocked
```

default-deny와 allow-api-to-db는 둘 다 DB 파드를 선택합니다. 거부 규칙은 없으므로 결과는 두 정책 허용의 합집합, 즉 「api만 허용」입니다.

## 4단계: 다른 네임스페이스에서 오는 트래픽

파트너 팀 네임스페이스의 `api` 파드도 허용해야 한다고 합시다.

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl create namespace lab-a02-partner
kubectl run api -n lab-a02-partner --image=busybox:1.37.0 --labels=role=api -- sleep 3600
kubectl wait pod/api -n lab-a02-partner --for=condition=Ready --timeout=60s
kubectl exec api -n lab-a02-partner -- wget -qO- -T 3 http://db.lab-a02 >/dev/null && echo ok || echo blocked
```

라벨이 `role=api`여도 `blocked`입니다. 3단계의 `podSelector`만 쓴 규칙은 **같은 네임스페이스**의 파드만 뜻하기 때문입니다. 네임스페이스까지 지정하는 정책을 더합니다.

```yaml file=np-allow-partner.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-partner-api
  namespace: lab-a02
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: db
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: lab-a02-partner
          podSelector:
            matchLabels:
              role: api
      ports:
        - protocol: TCP
          port: 80
```

:::warn 한 줄 차이: AND와 OR
위 정책의 `from` 항목은 **하나**이고, 그 안에 `namespaceSelector`와 `podSelector`가 함께 있습니다. 이는 「lab-a02-partner 네임스페이스에 있으면서 **동시에** role=api인 파드」(AND)입니다. `podSelector` 앞에 `-`를 붙여 항목을 둘로 나누면 「lab-a02-partner의 **모든** 파드 **또는** lab-a02의 role=api 파드」(OR)가 되어 의도보다 훨씬 넓게 열립니다. `kubectl describe networkpolicy`로 항상 해석 결과를 확인하세요.
:::

`kubernetes.io/metadata.name`은 Kubernetes가 모든 네임스페이스에 자동으로 붙이는 라벨(값은 네임스페이스 이름)이라 따로 라벨을 붙이지 않아도 됩니다.

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl apply -f np-allow-partner.yaml
kubectl describe networkpolicy allow-partner-api -n lab-a02
kubectl exec api -n lab-a02-partner -- wget -qO- -T 3 http://db.lab-a02 >/dev/null && echo ok || echo blocked
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드) · describe 출력은 CNI와 무관" date="2026-10-15"
Spec:
  PodSelector:     app.kubernetes.io/name=db
  Allowing ingress traffic:
    To Port: 80/TCP
    From:
      NamespaceSelector: kubernetes.io/metadata.name=lab-a02-partner
      PodSelector: role=api
  Not affecting egress traffic
  Policy Types: Ingress
```

`From:` 아래에 두 셀렉터가 한 묶음으로 나오면 AND입니다. Calico 프로필에서는 마지막 명령이 `ok`를 출력해야 합니다.

## 5단계: 나가는 트래픽 제한과 DNS

api 파드가 DB 외에는 아무 데도 나가지 못하게 하려면 egress 정책을 씁니다. 이때 **DNS를 허용하지 않으면** `http://db`라는 이름부터 풀 수 없어 DB 접속도 실패합니다.

```yaml file=np-egress.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-egress
  namespace: lab-a02
spec:
  podSelector:
    matchLabels:
      role: api
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
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: db
      ports:
        - protocol: TCP
          port: 80
```

| 규칙 | 의미 |
|---|---|
| 첫 번째 `to` | kube-system 네임스페이스의 `k8s-app=kube-dns` 파드(CoreDNS)로 가는 UDP·TCP 53 허용 |
| 두 번째 `to` | 같은 네임스페이스의 DB 파드로 가는 TCP 80 허용 |

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl apply -f np-egress.yaml
check
kubectl exec api -n lab-a02 -- wget -qO- -T 3 http://example.com >/dev/null 2>&1 && echo api-to-internet=ok || echo api-to-internet=blocked
```

```output kind=example note="Calico 프로필에서 기대하는 결과"
api=ok stranger=blocked
api-to-internet=blocked
```

egress 정책 적용 전에 마지막 명령을 실행하면(인터넷이 연결된 PC라면) `ok`가 나옵니다. 정책은 DB와 DNS 외의 모든 목적지를 막습니다. 첫 번째 egress 규칙을 지우고 다시 apply하면 `api=blocked`로 바뀌는 것을 직접 확인해 보세요(응용 과제 1).

## 성공 판정

```verify
id: a2-policy
title: api만 DB에 접근
explain: 같은 네임스페이스의 api와 stranger 파드에서 DB로 요청한 결과를 한 줄로 출력합니다. Calico 프로필에서 실행해야 합니다.
command: for p in api stranger; do kubectl exec $p -n lab-a02 -- wget -qO- -T 3 http://db >/dev/null 2>&1 && echo "$p=ok" || echo "$p=blocked"; done | paste -sd' ' -
expect: ^api=ok stranger=blocked$
criteria: api=ok stranger=blocked
```

```verify
id: a2-partner
title: 파트너 네임스페이스의 api 허용
explain: lab-a02-partner의 api 파드에서 DB로 요청합니다.
command: kubectl exec api -n lab-a02-partner -- wget -qO- -T 3 http://db.lab-a02 >/dev/null 2>&1 && echo partner=ok || echo partner=blocked
expect: ^partner=ok$
criteria: partner=ok
```

:::warn 검증 범위와 집행되지 않는 CNI의 증거
이 사이트의 검증 환경에는 Calico를 설치할 수 없어 **차단 결과는 검증하지 못했습니다.** 다만 정책 네 개를 모두 적용한 상태에서도 검증 환경에서는 `api=ok stranger=ok`가 나왔습니다. 이것이 「정책을 집행하지 않는 CNI에서는 NetworkPolicy가 오류 없이 무시된다」는 실제 증거입니다. 내 환경에서 같은 결과가 나오면 컨텍스트가 `k8s-lab-calico`인지, calico-node가 Ready인지부터 확인하세요.
:::

## 흔한 오류, 진단 순서, 해결 방법

진단 순서: **현재 컨텍스트와 CNI 확인 → `kubectl get networkpolicy -n <ns>`로 어떤 정책이 그 파드를 선택하는지 → `kubectl describe networkpolicy`로 해석 확인 → 파드 라벨(`--show-labels`)과 네임스페이스 라벨 대조 → DNS와 IP 직접 접속을 나눠 시험**.

| 증상 | 확인 명령 | 원인과 해결 |
|---|---|---|
| 정책을 넣어도 모두 `ok` | `kubectl config current-context`, `kubectl get pods -n kube-system -l k8s-app=calico-node` | 정책을 집행하지 않는 CNI(기본 kindnet)이거나 calico-node가 준비되지 않았습니다. |
| 허용했는데 `blocked` | `kubectl get pod api -n lab-a02 --show-labels` | 라벨 오타, 또는 `ports`에 Service 포트(예: 8080)를 적었는데 파드 포트가 다릅니다. |
| 다른 네임스페이스 허용이 안 됨 | `kubectl get ns --show-labels` | `namespaceSelector` 없이 `podSelector`만 썼거나, 네임스페이스 라벨 값이 다릅니다. |
| 너무 넓게 열림 | `kubectl describe networkpolicy` | `from` 항목을 둘로 나눠 OR가 되었습니다. |
| egress 적용 후 이름 해석 실패(`bad address`) | `kubectl exec ... -- nslookup db` | DNS(53) 허용이 빠졌습니다. CoreDNS 파드 라벨(`k8s-app=kube-dns`)을 확인합니다. |
| IP로는 되는데 이름으로는 안 됨 | 위와 같음 | DNS 문제입니다. 정책이 아니라 DNS 경로를 먼저 봅니다. |

## 응용 과제

**과제 1.** `np-egress.yaml`에서 DNS 규칙(첫 번째 `to`)을 지우고 apply하세요. api에서 `wget http://db`와 `wget http://<db 파드 IP>`의 결과를 비교하세요.

:::answer 해설
이름으로는 `bad address 'db'`(이름 해석 실패)가 나고, 파드 IP로는 성공합니다. egress를 막으면 DNS 질의도 나가는 트래픽이므로 함께 막힙니다. 실습 후 원래 파일로 되돌려 apply합니다.
:::

**과제 2.** 4단계 정책을 OR 형태로 바꾸면 lab-a02의 stranger가 DB에 접근할 수 있게 될까요? 실제로 바꿔 보고 `describe` 출력과 `check` 결과로 확인하세요.

:::answer 해설
OR 형태(`- namespaceSelector: ...`와 `- podSelector: ...`를 별도 항목으로)에서 podSelector 항목은 「lab-a02의 role=api」이므로 stranger는 여전히 막힙니다. 하지만 lab-a02-partner 네임스페이스의 **모든 파드**가 DB에 접근할 수 있게 됩니다. `describe`에서 `From:` 아래 항목이 두 묶음으로 나뉘어 보입니다.
:::

**과제 3.** 네임스페이스의 모든 파드에 대해 egress까지 기본 차단하는 정책을 만들고, 그 상태에서 필요한 통신만 여는 순서를 설계해 보세요.

:::answer 해설
`podSelector: {}`, `policyTypes: [Ingress, Egress]`, 규칙 없음으로 전체 차단 정책을 만들고, 곧바로 모든 파드에 DNS egress 허용 정책을 더한 뒤, 앱별 ingress·egress를 하나씩 엽니다. 고급 종합 과제에서 이 순서를 사용합니다.
:::

## 정리와 재실행

이 실습에서 만든 네임스페이스 두 개를 지웁니다. **`k8s-lab-calico` 컨텍스트에서 실행하는지 다시 확인하세요.**

```bash shell="실습 터미널 (컨텍스트 k8s-lab-calico)"
kubectl config current-context
kubectl delete namespace lab-a02 lab-a02-partner
```

고급 종합 과제를 이어서 할 예정이면 프로필을 그대로 둡니다. 쉬는 동안에는 `minikube stop -p k8s-lab-calico`로 멈춥니다. 프로필 자체를 삭제하고 기본 클러스터로 돌아가려면 다음을 실행합니다.

```bash shell="실습 터미널"
minikube delete -p k8s-lab-calico
kubectl config use-context k8s-lab
```

다시 하려면 「이 실습만의 환경」의 설치부터 반복합니다. 프로필을 유지했다면 1단계부터 시작합니다.
