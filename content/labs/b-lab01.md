## 학습 목표

- kubectl로 [[cluster]]의 [[node]]와 구성 요소를 살펴보고, 필드 설명을 직접 찾을 수 있습니다.
- [[deployment]]로 웹 서버 파드 여러 개를 띄우고, [[service]]로 하나의 주소에 묶을 수 있습니다.
- 레플리카 수를 바꾸고, 파드를 지워도 다시 채워지는 것(자가 치유)을 확인할 수 있습니다.

## 선수 지식

- [환경 준비](#/item/setup)를 마쳐 `k8s-lab` 클러스터가 `Ready`여야 합니다.
- 컨테이너 이미지와 포트 개념. YAML이 처음이면 들여쓰기만 정확히 따라 쓰면 됩니다.

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context
kubectl get nodes
```

`k8s-lab`이 나오고 노드가 `Ready`여야 합니다. 아니라면 [환경 준비의 흔한 오류](#/item/setup)를 먼저 해결합니다. 이 실습은 `lab-b01` 네임스페이스만 만들고 지웁니다.

## 개념: 원하는 상태를 적으면 컨트롤러가 맞춘다

**무엇인가.** [[pod]]는 컨테이너를 실행하는 가장 작은 단위입니다. 하지만 파드를 직접 만들면, 파드가 죽었을 때 아무도 다시 만들어 주지 않습니다. [[deployment]]는 「이 템플릿으로 파드를 N개 유지하라」는 **원하는 상태**를 적은 객체이고, 실제로 개수를 맞추는 일은 Deployment가 만든 [[replicaset]]이 합니다.

**왜 필요한가.** 파드는 노드 장애, 재배포, 자원 부족으로 언제든 사라지고 IP도 바뀝니다. 그래서 두 가지가 필요합니다. 개수를 지켜 주는 장치(Deployment·ReplicaSet), 그리고 바뀌는 파드들 앞에 고정된 주소를 붙여 주는 장치([[service]])입니다.

**어떻게 동작하나.** `kubectl apply`는 매니페스트를 [[kube-apiserver]]로 보내고, API 서버는 이를 [[etcd]]에 저장합니다. [[controller-manager]] 안의 Deployment 컨트롤러가 ReplicaSet을, ReplicaSet 컨트롤러가 파드를 만듭니다. [[scheduler]]가 파드를 노드에 배정하면 그 노드의 [[kubelet]]이 [[container-runtime]]으로 컨테이너를 실행합니다. Service는 [[selector]]에 맞는 [[label]]을 가진 파드를 찾아 [[endpointslice]]에 기록하고, 각 노드의 [[kube-proxy]]가 Service IP로 온 요청을 그 파드들에 나눠 보냅니다.

<figure class="diagram">
<svg viewBox="0 0 760 300" role="img" aria-label="Deployment가 ReplicaSet을, ReplicaSet이 파드를 관리하고 Service가 라벨로 파드를 고르는 구성도">
<defs><marker id="b1a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="arrowhead"/></marker></defs>
<rect class="zone" x="190" y="12" width="555" height="276" rx="8"/>
<text class="small" x="200" y="30">네임스페이스 lab-b01</text>
<rect class="box" x="10" y="40" width="150" height="54" rx="6"/><text x="22" y="63">kubectl apply</text><text class="small" x="22" y="81">web-deploy.yaml</text>
<rect class="box dim" x="10" y="130" width="150" height="54" rx="6"/><text x="22" y="153">kube-apiserver</text><text class="small" x="22" y="171">etcd에 원하는 상태 저장</text>
<path class="line" d="M85 94V128" marker-end="url(#b1a)"/>
<rect class="box accent" x="210" y="40" width="160" height="54" rx="6"/><text x="222" y="63">Deployment web</text><text class="small" x="222" y="81">replicas: 2 → 4</text>
<rect class="box" x="210" y="130" width="160" height="54" rx="6"/><text x="222" y="153">ReplicaSet</text><text class="small" x="222" y="171">web-6fb5555c85</text>
<path class="line dim" d="M160 157H208" marker-end="url(#b1a)"/>
<path class="line" d="M290 94V128" marker-end="url(#b1a)"/>
<rect class="box" x="400" y="110" width="150" height="40" rx="6"/><text class="mono" x="410" y="134">pod web-…-kwfmw</text>
<rect class="box" x="400" y="160" width="150" height="40" rx="6"/><text class="mono" x="410" y="184">pod web-…-pnsmn</text>
<path class="line" d="M370 150L398 132M370 162L398 178" marker-end="url(#b1a)"/>
<text class="small" x="400" y="222">라벨 app.kubernetes.io/name=web</text>
<rect class="box accent" x="590" y="130" width="140" height="54" rx="6"/><text x="602" y="153">Service web</text><text class="small" x="602" y="171">ClusterIP · 80</text>
<path class="line" d="M588 150L552 132M588 164L552 180" marker-end="url(#b1a)"/>
<rect class="box dim" x="590" y="230" width="140" height="44" rx="6"/><text x="602" y="257">client 파드</text>
<path class="line" d="M660 228V186" marker-end="url(#b1a)"/>
<text class="small" x="672" y="212">http://web</text>
</svg>
<figcaption>Deployment → ReplicaSet → Pod는 소유 관계, Service → Pod는 라벨 셀렉터로 고르는 관계입니다.</figcaption>
</figure>

## 1단계: 클러스터 둘러보기

[[control-plane]]과 노드가 무엇으로 이루어져 있는지 먼저 봅니다.

```bash shell="실습 터미널"
kubectl get nodes -o wide
kubectl get pods -n kube-system
```

```output kind=example note="minikube v1.39.0 · Kubernetes v1.37.0 기준 · 해시 접미사와 AGE는 환경마다 다름"
NAME      STATUS   ROLES           AGE   VERSION   INTERNAL-IP    ...   CONTAINER-RUNTIME
k8s-lab   Ready    control-plane   10m   v1.37.0   192.168.49.2   ...   containerd://(버전)
NAME                              READY   STATUS    RESTARTS   AGE
coredns-xxxxxxxxxx-xxxxx          1/1     Running   0          10m
etcd-k8s-lab                      1/1     Running   0          10m
kindnet-xxxxx                     1/1     Running   0          10m
kube-apiserver-k8s-lab            1/1     Running   0          10m
kube-controller-manager-k8s-lab   1/1     Running   0          10m
kube-proxy-xxxxx                  1/1     Running   0          10m
kube-scheduler-k8s-lab            1/1     Running   0          10m
storage-provisioner               1/1     Running   0          10m
```

`-o wide`는 노드 IP, OS, 커널, 컨테이너 런타임 열을 더 보여 줍니다(예시에서는 일부 열을 `...`로 줄였습니다). `etcd-`, `kube-apiserver-`, `kube-controller-manager-`, `kube-scheduler-`가 컨트롤 플레인입니다. minikube는 이들을 노드 안의 「스태틱 파드」로 실행하므로 목록에 보입니다. `coredns`는 [[cluster-dns]], `kindnet`은 파드 네트워크를 만드는 [[cni]], `kube-proxy`는 Service 트래픽 규칙을 담당합니다. 클러스터 구성 방식에 따라 이 목록은 달라질 수 있습니다.

모르는 필드는 공식 문서를 찾기 전에 `kubectl explain`으로 바로 확인할 수 있습니다.

```bash shell="실습 터미널"
kubectl explain deployment.spec.replicas
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
GROUP:      apps
KIND:       Deployment
VERSION:    v1

FIELD: replicas <integer>


DESCRIPTION:
    Number of desired pods. This is a pointer to distinguish between explicit
    zero and not specified. Defaults to 1.
```

## 2단계: 전용 네임스페이스 만들기

[[namespace]]는 자원 이름과 권한을 나누는 구역입니다. 실습마다 전용 네임스페이스를 만들면 마지막에 네임스페이스 하나만 지워서 깔끔하게 정리할 수 있습니다.

```bash shell="실습 터미널"
kubectl create namespace lab-b01
kubectl get namespaces
```

이후 모든 명령에는 `-n lab-b01`을 붙입니다. 기본 네임스페이스를 바꾸는 방법도 있지만, 명령마다 대상을 드러내 두는 편이 실수를 줄입니다.

## 3단계: Deployment 배포

아래 [[manifest]]를 `web-deploy.yaml`로 저장합니다. 코드 블록의 「YAML 받기」를 눌러도 됩니다.

```yaml file=web-deploy.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: lab-b01
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
      containers:
        - name: nginx
          image: nginx:1.30.6-alpine
          ports:
            - name: http
              containerPort: 80
```

| 필드 | 의미 |
|---|---|
| `apiVersion: apps/v1`, `kind: Deployment` | 어떤 API 그룹·버전의 어떤 종류 객체인지. Deployment는 1.16부터 `apps/v1`만 제공됩니다. |
| `metadata.namespace` | 만들 네임스페이스. 파일에 적어 두면 `-n`을 빠뜨려도 엉뚱한 곳에 만들어지지 않습니다. |
| `spec.replicas` | 유지할 파드 수(원하는 상태). |
| `spec.selector.matchLabels` | 이 Deployment가 자기 파드로 인식할 라벨 조건. 만든 뒤에는 바꿀 수 없습니다. |
| `spec.template.metadata.labels` | 새로 만들 파드에 붙일 라벨. **셀렉터와 반드시 일치**해야 하며, 다르면 API 서버가 거부합니다. |
| `containers[].image` | 실행할 이미지와 태그. `latest` 대신 구체적인 태그를 쓰면 언제 어디서나 같은 결과를 얻습니다. |
| `ports[].name: http` | 포트에 이름을 붙여 두면 Service에서 숫자 대신 이름으로 가리킬 수 있습니다. |

```bash shell="실습 터미널"
kubectl apply -f web-deploy.yaml
kubectl rollout status deployment/web -n lab-b01
kubectl get deployment,replicaset,pod -n lab-b01
```

**결과를 먼저 예상해 보세요.** Deployment 1개, ReplicaSet 1개, 파드 2개가 보여야 합니다. 파드 이름은 `<Deployment>-<템플릿 해시>-<무작위 5자>` 형식입니다.

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드, 대체 이미지)" date="2026-10-15"
deployment "web" successfully rolled out
NAME                  READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/web   2/2     2            2           0s

NAME                             DESIRED   CURRENT   READY   AGE
replicaset.apps/web-6fb5555c85   2         2         2       0s

NAME                       READY   STATUS    RESTARTS   AGE
pod/web-6fb5555c85-kwfmw   1/1     Running   0          0s
pod/web-6fb5555c85-pnsmn   1/1     Running   0          0s
```

처음 실행하면 이미지를 내려받느라 `ContainerCreating` 상태가 수십 초 이어질 수 있습니다. 해시(`6fb5555c85`)와 무작위 접미사는 환경마다 다릅니다.

## 4단계: Service로 묶고 접속하기

`web-svc.yaml`로 저장합니다.

```yaml file=web-svc.yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: lab-b01
spec:
  type: ClusterIP
  selector:
    app.kubernetes.io/name: web
  ports:
    - name: http
      port: 80
      targetPort: http
```

| 필드 | 의미 |
|---|---|
| `type: ClusterIP` | [[clusterip]]. 클러스터 안에서만 접근 가능한 가상 IP를 받습니다(기본값). |
| `selector` | 이 라벨을 가진 **모든** 파드로 트래픽을 보냅니다. Deployment와 무관하게 라벨만 봅니다. |
| `port: 80` | Service가 받는 포트. |
| `targetPort: http` | 파드 쪽 포트. 컨테이너 포트 이름 `http`(80)를 가리킵니다. |

```bash shell="실습 터미널"
kubectl apply -f web-svc.yaml
kubectl get service web -n lab-b01
kubectl get endpointslices -n lab-b01 -l kubernetes.io/service-name=web
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME   TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
web    ClusterIP   10.96.164.131   <none>        80/TCP    0s
NAME        ADDRESSTYPE   PORTS   ENDPOINTS                 AGE
web-j88g8   IPv4          80      10.244.0.51,10.244.0.50   0s
```

CLUSTER-IP와 파드 IP는 환경마다 다릅니다. ENDPOINTS에 파드 IP 두 개가 보이면 Service가 파드를 찾은 것입니다.

이제 클러스터 안에서 요청을 보내 봅니다. 테스트용 클라이언트 파드를 하나 띄워 두고 `kubectl exec`로 명령을 실행합니다.

```bash shell="실습 터미널"
kubectl run client -n lab-b01 --image=busybox:1.37.0 --restart=Never -- sleep 3600
kubectl wait pod/client -n lab-b01 --for=condition=Ready --timeout=60s
kubectl exec client -n lab-b01 -- wget -qO- -T 5 http://web
```

nginx 기본 페이지의 HTML(`<title>Welcome to nginx!</title>` 포함)이 출력되면 성공입니다. `http://web`이 동작하는 이유는 [[cluster-dns]]가 같은 네임스페이스의 Service 이름을 IP로 바꿔 주기 때문입니다. 다른 네임스페이스에서는 `http://web.lab-b01.svc.cluster.local`처럼 전체 이름을 씁니다.

:::note 내 PC 브라우저로 보고 싶다면
`kubectl port-forward -n lab-b01 svc/web 8080:80`을 실행해 두고 브라우저에서 `http://localhost:8080`을 엽니다. 이 명령은 실행 중인 동안만 연결을 유지하므로 확인 후 `Ctrl+C`로 끕니다. WSL2에서도 localhost로 접속됩니다.
:::

## 5단계: 확장과 자가 치유

```bash shell="실습 터미널"
kubectl scale deployment web -n lab-b01 --replicas=4
kubectl rollout status deployment/web -n lab-b01
kubectl get pods -n lab-b01 -l app.kubernetes.io/name=web -o wide
```

**예상해 보세요.** 파드가 4개로 늘고, Service 엔드포인트도 자동으로 4개가 됩니다. 이제 파드 하나를 일부러 지웁니다. `<파드 이름>`은 위 출력에서 아무것이나 고릅니다.

```bash shell="실습 터미널"
kubectl delete pod <파드 이름> -n lab-b01
kubectl get pods -n lab-b01 -l app.kubernetes.io/name=web
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
pod "web-6fb5555c85-4n4qm" deleted from lab-b01 namespace
NAME                   READY   STATUS    RESTARTS   AGE
web-6fb5555c85-kwfmw   1/1     Running   0          5s
web-6fb5555c85-nt6p9   1/1     Running   0          1s
web-6fb5555c85-pnsmn   1/1     Running   0          5s
web-6fb5555c85-ttgdk   1/1     Running   0          2s
```

AGE가 가장 짧은 파드가 방금 새로 만들어진 파드입니다. ReplicaSet이 「4개여야 하는데 3개다」라는 차이를 보고 즉시 하나를 채운 것입니다. 이것이 **제어 루프**입니다.

:::why 명령형 scale과 선언형 apply의 차이
`kubectl scale`은 클러스터의 현재 값만 바꿉니다. 파일의 `replicas: 2`는 그대로이므로 나중에 `kubectl apply -f web-deploy.yaml`을 다시 하면 2개로 돌아갑니다. 실제 운영에서는 파일을 고치고 apply하는 [[declarative]] 방식을 기본으로 삼고, scale은 긴급 대응에만 씁니다.
:::

## 성공 판정

```verify
id: b1-final
title: 레플리카 4개가 모두 준비되고 Service 엔드포인트도 4개
explain: Deployment의 준비된 레플리카 수와, Service 엔드포인트 중 준비된 수를 함께 출력합니다.
command: echo "ready=$(kubectl get deploy web -n lab-b01 -o jsonpath='{.status.readyReplicas}') endpoints=$(kubectl get endpointslices -n lab-b01 -l kubernetes.io/service-name=web -o jsonpath='{range .items[*].endpoints[*]}{.conditions.ready}{"\n"}{end}' | grep -c true)"
expect: ^ready=4 endpoints=4$
criteria: ready=4 endpoints=4
```

검증 환경에서 위 명령의 실제 출력은 `ready=4 endpoints=4`였습니다.

## 흔한 오류, 진단 순서, 해결 방법

진단 순서는 **Deployment → ReplicaSet → Pod → 이벤트 → Service 엔드포인트**입니다. 위에서부터 어디서 숫자가 어긋나는지 봅니다.

| 증상 | 확인 명령 | 원인과 해결 |
|---|---|---|
| `error: the server doesn't have a resource type` 또는 연결 거부 | `kubectl config current-context` | 다른 클러스터를 가리키거나 minikube가 꺼져 있습니다. `kubectl config use-context k8s-lab`, `minikube start -p k8s-lab`. |
| `apply` 시 `selector does not match template labels` | 매니페스트 확인 | `selector.matchLabels`와 `template.metadata.labels` 값이 다릅니다. 둘을 같게 맞춥니다. |
| 파드가 `ImagePullBackOff`·`ErrImagePull` | `kubectl describe pod <이름> -n lab-b01`의 Events | 이미지 이름·태그 오타 또는 인터넷 연결 문제입니다. 태그를 확인합니다. 다음 실습에서 자세히 다룹니다. |
| 파드가 `Pending` | `kubectl describe pod`의 Events | `Insufficient cpu/memory`면 노드 자원 부족입니다. 레플리카를 줄이거나 minikube 메모리를 늘립니다. |
| `wget: bad address 'web'` | `kubectl get svc -n lab-b01` | Service가 없거나, 클라이언트 파드가 다른 네임스페이스에 있습니다. 전체 이름 `web.lab-b01.svc.cluster.local`로 시도합니다. |
| `wget: can't connect to remote host ... Connection refused`, 엔드포인트가 `<unset>` | `kubectl get endpointslices -n lab-b01 -l kubernetes.io/service-name=web`, `kubectl get pods -n lab-b01 --show-labels` | Service 셀렉터와 파드 라벨이 다릅니다. 라벨 철자(`app.kubernetes.io/name`)를 비교합니다. |

## 응용 과제

**과제 1.** 파일의 `replicas`를 3으로 고치고 `kubectl apply`로 반영하세요. `kubectl scale`로 4개였던 상태가 어떻게 바뀌나요?

:::answer 힌트와 해설
힌트: apply는 파일에 적힌 값을 원하는 상태로 삼습니다.

해설: 3개로 줄어듭니다. ReplicaSet은 남는 파드 하나를 지웁니다. `kubectl get pods -n lab-b01 -w`로 지켜보면 하나가 `Terminating`이 되는 것을 볼 수 있습니다. 운영에서 scale과 apply를 섞어 쓰면 이렇게 서로의 변경을 덮어쓰므로, 한 가지 방식을 정해 둡니다.
:::

**과제 2.** Service의 셀렉터를 `app.kubernetes.io/name: webb`으로 일부러 틀리게 바꿔 apply한 뒤, 클라이언트 파드에서 `wget`이 어떻게 실패하는지, 엔드포인트가 어떻게 보이는지 확인하세요. 확인 후 원래대로 돌려놓습니다.

:::answer 힌트와 해설
힌트: `kubectl get endpointslices -n lab-b01 -l kubernetes.io/service-name=web`

해설: Service 자체는 정상적으로 만들어지고 ClusterIP도 그대로지만, 고를 파드가 없어 ENDPOINTS가 `<unset>`이 됩니다. 이름 해석은 되므로 `bad address`가 아니라 `can't connect to remote host ...: Connection refused`가 납니다. 엔드포인트가 없는 Service로 온 연결을 kube-proxy가 거부하기 때문입니다(검증 환경 iptables 모드에서 확인). 「Service는 있는데 연결이 안 된다」면 엔드포인트부터 확인하는 습관을 들이세요.
:::

**과제 3.** `kubectl explain`으로 `deployment.spec.revisionHistoryLimit`의 의미와 기본값을 찾아 보세요.

:::answer 해설
Deployment가 롤백용으로 보관할 이전 ReplicaSet 수이며 기본값은 10입니다. 다음 실습의 `rollout undo`가 이 기록을 사용합니다.
:::

## 정리와 재실행

이 실습에서 만든 자원은 모두 `lab-b01` 네임스페이스 안에 있으므로 네임스페이스만 지우면 됩니다. 다음 실습은 새 네임스페이스를 쓰므로 정리해도 괜찮습니다.

```bash shell="실습 터미널"
kubectl delete namespace lab-b01
kubectl get namespace lab-b01
```

마지막 명령이 `Error from server (NotFound): namespaces "lab-b01" not found`를 출력하면 정리가 끝난 것입니다. 삭제에는 수십 초가 걸릴 수 있습니다. **다시 하려면** 2단계부터 반복합니다. 저장해 둔 YAML 파일은 그대로 다시 쓸 수 있습니다.
