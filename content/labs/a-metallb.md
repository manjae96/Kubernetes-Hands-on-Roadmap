## 학습 목표

- 클라우드가 아닌 클러스터(베어메탈·VM·minikube)에서 `type: LoadBalancer` Service가 왜 `<pending>`으로 멈추는지 설명할 수 있습니다.
- [[metallb|MetalLB]]의 두 구성 요소(controller: 주소 할당, speaker: 주소 알리기)와 **L2 모드**의 동작(ARP·NDP 응답)을 확인할 수 있습니다.
- `IPAddressPool`·`L2Advertisement`로 주소를 나눠 주고, **주소 할당**과 **주소 알리기**가 따로라는 것을 장애로 구분할 수 있습니다.
- `externalTrafficPolicy`(Cluster·Local)가 클라이언트 IP 보존에 주는 차이를 측정하고, kube-proxy·CNI·Ingress와 역할을 나눠 설명할 수 있습니다.

## 선수 지식

- [Service 유형 심화: NodePort와 LoadBalancer](#/item/b-service-types): ClusterIP ⊂ NodePort ⊂ LoadBalancer 포함 관계
- 리눅스 네트워크 기초(같은 서브넷·ARP·기본 경로) — [리눅스 고급 1 「네트워크 진단」](/linux/#/item/a-lab01)
- 이 과정은 **선택 심화**입니다. Ingress 컨트롤러 자체는 [인그레스 항해도](/ingress/)에서, Service·EndpointSlice의 동작 원리는 심화 노트 [[service]]에서 다룹니다(여기서는 반복하지 않음).

:::note 검증 범위
**minikube v1.38.1(docker 드라이버·containerd) · Kubernetes v1.37.0 · MetalLB v0.16.0 L2 모드**로 설치 → 주소 할당 → ARP 응답 → 트래픽 → `externalTrafficPolicy` → 장애 5가지(주소 풀 바닥·control-plane 제외 레이블·L2Advertisement 없음·speaker 중단·다른 대역 풀) → 제거까지 실제로 실행했고, 출력 블록은 그 결과입니다(2026-11-02). **BGP 모드는 실습 라우터가 없어 실행하지 않았습니다**(개념만, 정적 검증). `L2Advertisement.spec.interfaces`로 인터페이스를 고르는 설정도 실행하지 않았습니다. 주소(192.168.58.x)는 minikube가 만든 Docker 네트워크에 따라 PC마다 다릅니다.
:::

## 개념: LoadBalancer 주소는 누가 주나

**무엇인가.** `type: LoadBalancer` Service는 「바깥에서 들어올 주소를 하나 달라」는 요청일 뿐이고, 그 주소를 주고 실제로 트래픽을 끌어오는 일은 **클라우드 제공자의 컨트롤러**(cloud-controller-manager)가 합니다. 클라우드가 없는 클러스터에서는 아무도 응답하지 않아 `EXTERNAL-IP`가 영원히 `<pending>`입니다. MetalLB는 그 빈자리를 채우는 **베어메탈용 로드밸런서 구현**입니다.

**왜 필요한가.** NodePort(30000~32767)는 포트가 높고 노드마다 열려, 사람이 쓰는 주소로는 불편합니다. 사내 데이터센터·폐쇄망·홈랩에서도 「80·443을 가진 고정 주소 하나」를 Ingress 컨트롤러 앞에 두려면 LoadBalancer 구현이 필요합니다.

**어떻게 동작하나.**

| 구성 요소 | 종류 | 하는 일 |
|---|---|---|
| controller | Deployment 1개 | `IPAddressPool`에서 주소를 골라 Service `status.loadBalancer.ingress`에 **할당** (이벤트 `IPAllocated`) |
| speaker | DaemonSet (노드마다) | 할당된 주소를 네트워크에 **알림** — L2 모드는 ARP(IPv4)·NDP(IPv6)에 「그 주소는 내 MAC」이라고 답함, BGP 모드는 라우터에 경로를 광고 |

| 모드 | 어떻게 알리나 | 장애 때 | 이 실습 |
|---|---|---|---|
| L2 | 서비스마다 **노드 하나**가 대표로 ARP·NDP에 응답 (그 노드가 모든 트래픽을 받음) | 대표 노드가 죽으면 다른 노드가 이어받고 무상 ARP(gratuitous ARP)로 알림 — 클라이언트 ARP 캐시에 따라 수 초 끊김 | 실행 검증 |
| BGP | 노드마다 라우터와 BGP 세션 → 라우터가 ECMP로 여러 노드에 나눔 | 세션이 끊긴 노드는 경로에서 빠짐 | **정적** (라우터 없음) |

**역할 나누기.** 「주소를 바깥에 알리는 일」은 MetalLB, 「그 주소로 들어온 패킷을 파드로 보내는 일」은 kube-proxy(또는 CNI의 kube-proxy 대체), 「HTTP 호스트·경로로 나누는 일」은 Ingress 컨트롤러입니다. MetalLB는 패킷을 직접 프록시하지 않습니다.

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context        # k8s-lab 이어야 함
kubectl get nodes
docker network inspect k8s-lab --format '{{range .IPAM.Config}}{{.Subnet}} gw {{.Gateway}}{{end}}'
```

마지막 줄의 대역(예: `192.168.58.0/24`)에서 **노드·게이트웨이와 겹치지 않는 윗부분**(예: `.200`~`.210`)을 주소 풀로 씁니다. 같은 대역의 다른 장비가 이미 쓰는 주소를 풀에 넣으면 두 장비가 같은 IP로 ARP에 답해 통신이 끊깁니다(주소 충돌).

## 1단계: 주소가 없는 LoadBalancer

```bash shell="실습 터미널"
kubectl create namespace lab-mlb
kubectl -n lab-mlb create deployment web --image=traefik/whoami:v1.11.0 --replicas=2
kubectl -n lab-mlb expose deployment web --type=LoadBalancer --port=80
kubectl -n lab-mlb rollout status deploy/web --timeout=120s
kubectl -n lab-mlb get svc web
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd · MetalLB 설치 전)" date="2026-11-02"
NAME   TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
web    LoadBalancer   10.111.104.213   <pending>     80:32355/TCP   9s
```

`<pending>`: 주소를 줄 컨트롤러가 없습니다. NodePort(32355)는 이미 열려 있습니다 — LoadBalancer는 NodePort를 포함하기 때문입니다.

## 2단계: MetalLB 설치 (태그 고정)

설치 파일은 **릴리스 태그로 고정**한 주소에서 받습니다. 공식 체크섬 파일은 없으므로, 받은 파일의 sha256을 아래 값과 비교해 검토한 그 파일만 씁니다(값이 다르면 태그 안 내용이 바뀐 것 — 적용하지 말고 원인 확인).

```bash shell="실습 터미널"
mkdir -p ~/mlb-lab && cd ~/mlb-lab
curl -fsSLo metallb-native.yaml https://raw.githubusercontent.com/metallb/metallb/v0.16.0/config/manifests/metallb-native.yaml
shasum -a 256 metallb-native.yaml        # 리눅스는 sha256sum
grep -o "image: quay.io/metallb/[a-z]*:v[0-9.]*" metallb-native.yaml | sort -u
kubectl apply -f metallb-native.yaml
kubectl -n metallb-system wait --for=condition=Available deploy/controller --timeout=180s
kubectl -n metallb-system rollout status ds/speaker --timeout=180s
```

```output kind=verified env="검증 환경 (MetalLB v0.16.0)" date="2026-11-02"
b0b9be2802f10aa32d45308b4457d06cde0c70544712c8d0cf5511657ffd2b69  metallb-native.yaml
image: quay.io/metallb/controller:v0.16.0
image: quay.io/metallb/speaker:v0.16.0
deployment.apps/controller condition met
daemon set "speaker" successfully rolled out
```

## 3단계: 주소 풀과 L2 알리기

```yaml file=pool.yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata: { name: lab-pool, namespace: metallb-system }
spec:
  addresses: ["192.168.58.200-192.168.58.210"]   # 점검 단계에서 확인한 내 대역으로 바꿈
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata: { name: lab-l2, namespace: metallb-system }
spec:
  ipAddressPools: ["lab-pool"]                   # 이 풀의 주소만 L2로 알림
```

```bash shell="실습 터미널"
kubectl apply -f pool.yaml
kubectl -n lab-mlb get svc web
kubectl -n lab-mlb get events --field-selector involvedObject.name=web -o custom-columns=REASON:.reason,FROM:.source.component,MSG:.message
```

```output kind=verified env="검증 환경 (MetalLB v0.16.0 L2)" date="2026-11-02"
NAME   TYPE           CLUSTER-IP       EXTERNAL-IP      PORT(S)        AGE
web    LoadBalancer   10.111.104.213   192.168.58.200   80:32355/TCP   83s
REASON              FROM                    MSG
IPAllocated         metallb-controller      Assigned IP ["192.168.58.200"]
```

주소는 할당됐는데(`IPAllocated`), **알리는 이벤트(`nodeAssigned`)가 없습니다.** 같은 네트워크의 컨테이너에서 확인합니다 — macOS·Windows의 docker 드라이버에서는 호스트가 이 대역에 직접 닿지 않으므로(아래 「흔한 오류」), 같은 Docker 네트워크에 붙인 일회용 컨테이너를 클라이언트로 씁니다.

```bash shell="실습 터미널"
docker run --rm --network k8s-lab busybox:1.36 sh -c 'wget -qO- -T 5 http://192.168.58.200/ | grep -E "^(Hostname|RemoteAddr)"; arping -c 2 -I eth0 192.168.58.200 | tail -1'
```

```output kind=verified env="검증 환경 (minikube 단일 노드 · MetalLB v0.16.0)" date="2026-11-02"
wget: can't connect to remote host (192.168.58.200): No route to host
Received 0 response(s) (0 request(s), 0 broadcast(s))
```

ARP에 아무도 답하지 않습니다. 원인은 노드 레이블입니다.

```bash shell="실습 터미널"
kubectl get node --show-labels | tr ',' '\n' | grep -E "exclude|control-plane"
```

```output kind=verified env="검증 환경 (minikube 단일 노드)" date="2026-11-02"
node-role.kubernetes.io/control-plane=
node.kubernetes.io/exclude-from-external-load-balancers=
```

kubeadm은 control-plane 노드에 `node.kubernetes.io/exclude-from-external-load-balancers` 레이블을 붙이고, **MetalLB L2 speaker는 이 레이블이 있는 노드에서 알리지 않습니다.** 운영 클러스터에서는 워커 노드가 알리므로 문제가 없지만, 노드가 하나뿐인 실습 클러스터에서는 알릴 노드가 없습니다. **실습 클러스터에서만** 레이블을 뗍니다(정리 단계에서 되돌림).

```bash shell="실습 터미널"
kubectl label node k8s-lab node.kubernetes.io/exclude-from-external-load-balancers-
kubectl get servicel2statuses -A -o custom-columns='SERVICE:.status.serviceName,NODE:.status.node'
docker run --rm --network k8s-lab busybox:1.36 sh -c 'wget -qO- -T 5 http://192.168.58.200/ | grep -E "^(Hostname|RemoteAddr)"; arping -c 1 -I eth0 192.168.58.200 | sed -n 2p; ip neigh | grep 192.168.58.200'
docker inspect k8s-lab --format '{{range .NetworkSettings.Networks}}노드 {{.IPAddress}} {{.MacAddress}}{{end}}'
```

```output kind=verified env="검증 환경 (minikube 단일 노드 · MetalLB v0.16.0 L2)" date="2026-11-02"
SERVICE   NODE
web       hangdo-verify-mlb
Hostname: web-76f7b8779b-wp9f7
RemoteAddr: 10.244.0.1:5685
Unicast reply from 192.168.58.200 [d2:0f:3a:98:9b:bd] 0.004ms
192.168.58.200 dev eth0 lladdr d2:0f:3a:98:9b:bd ref 1 used 0/0/0 probes 4 REACHABLE
노드 192.168.58.2 d2:0f:3a:98:9b:bd
```

(검증 클러스터 이름은 `hangdo-verify-mlb`, 실습에서는 `k8s-lab`으로 보입니다.) **192.168.58.200의 MAC = 노드 192.168.58.2의 MAC**입니다. L2 모드는 주소를 노드 인터페이스에 붙이지 않고, speaker가 ARP 질문에 노드 MAC으로 대신 답할 뿐입니다. 노드에 도착한 패킷은 kube-proxy 규칙이 파드로 보냅니다. `ServiceL2Status`로 어느 노드가 알리는지 볼 수 있습니다(서비스마다 노드 하나 — 그 노드가 모든 트래픽의 입구).

## 4단계: externalTrafficPolicy — 클라이언트 IP를 볼 수 있나

```bash shell="실습 터미널"
for p in Cluster Local; do
  kubectl -n lab-mlb patch svc web -p "{\"spec\":{\"externalTrafficPolicy\":\"$p\"}}" >/dev/null; sleep 4
  echo "== $p"
  docker run --rm --network k8s-lab busybox:1.36 sh -c 'ip -4 -o addr show eth0 | awk "{print \"클라이언트 \"\$4}"; wget -qO- -T 5 http://192.168.58.200/ | grep RemoteAddr'
done
kubectl -n lab-mlb patch svc web -p '{"spec":{"externalTrafficPolicy":"Cluster"}}'
```

```output kind=verified env="검증 환경 (minikube 단일 노드 · MetalLB v0.16.0 L2)" date="2026-11-02"
== Cluster
클라이언트 192.168.58.3/24
RemoteAddr: 10.244.0.1:6638
== Local
클라이언트 192.168.58.3/24
RemoteAddr: 192.168.58.3:36096
```

| 정책 | 패킷이 가는 곳 | 앱이 보는 출발지 | 대가 |
|---|---|---|---|
| `Cluster` (기본) | 어느 노드든 받고, 다른 노드의 파드로도 보냄 | 노드 쪽 주소로 바뀜(SNAT) — 위 `10.244.0.1` | 클라이언트 IP를 잃음 |
| `Local` | 파드가 있는 노드에서만 처리 | **진짜 클라이언트 IP** | 파드가 없는 노드가 알리면 트래픽이 버려짐 — MetalLB L2는 파드가 있는 노드만 고르고, `healthCheckNodePort`로 노드 상태를 알림 |

접근 제어·감사 로그에 클라이언트 IP가 필요하면 `Local`, 고르게 나누는 것이 중요하면 `Cluster`입니다.

## 5단계: 장애 네 가지

**① 주소 풀 바닥** — 풀을 1개로 줄이고 LoadBalancer Service를 하나 더 만듭니다.

```bash shell="실습 터미널"
kubectl -n metallb-system patch ipaddresspool lab-pool --type=merge -p '{"spec":{"addresses":["192.168.58.200/32"]}}'
kubectl -n lab-mlb expose deployment web --name=web2 --type=LoadBalancer --port=80
kubectl -n lab-mlb get svc web2
kubectl -n lab-mlb get events --field-selector involvedObject.name=web2 -o custom-columns=REASON:.reason,MSG:.message
```

```output kind=verified env="검증 환경 (MetalLB v0.16.0)" date="2026-11-02"
NAME   TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)        AGE
web2   LoadBalancer   10.106.194.177   <pending>     80:32614/TCP   5s
REASON             MSG
AllocationFailed   Failed to allocate IP for "lab-mlb/web2": no available IPs
```

복구: `kubectl -n lab-mlb delete svc web2`, 풀을 원래 범위로 되돌립니다(`kubectl apply -f pool.yaml`).

**② L2Advertisement 없음** — 주소는 그대로 있는데 아무도 알리지 않습니다.

```bash shell="실습 터미널"
kubectl -n metallb-system delete l2advertisement lab-l2
kubectl -n lab-mlb get svc web -o jsonpath='EXTERNAL-IP {.status.loadBalancer.ingress[0].ip}{"\n"}'
docker run --rm --network k8s-lab busybox:1.36 sh -c 'wget -qO- -T 4 http://192.168.58.200/ 2>&1 | head -1; arping -c 1 -w 2 -I eth0 192.168.58.200 | tail -1'
kubectl apply -f pool.yaml        # 복구
```

```output kind=verified env="검증 환경 (MetalLB v0.16.0)" date="2026-11-02"
EXTERNAL-IP 192.168.58.200
wget: can't connect to remote host (192.168.58.200): No route to host
Received 0 response(s) (0 request(s), 0 broadcast(s))
```

**`EXTERNAL-IP`가 보인다고 접속되는 것이 아닙니다.** 할당(controller)과 알리기(speaker + L2Advertisement)는 따로입니다 — 「주소는 있는데 ARP 응답이 없다」면 알리기 쪽(L2Advertisement·노드 레이블·speaker)을 봅니다.

**③ speaker 중단** — speaker를 노드에서 뺍니다(어떤 노드에도 맞지 않는 nodeSelector).

```bash shell="실습 터미널"
kubectl -n metallb-system patch ds speaker -p '{"spec":{"template":{"spec":{"nodeSelector":{"hangdo-lab/no-speaker":"true"}}}}}'
kubectl -n metallb-system get pods -l component=speaker
docker run --rm --network k8s-lab busybox:1.36 sh -c 'wget -qO- -T 4 http://192.168.58.200/ 2>&1 | head -1'
kubectl -n metallb-system patch ds speaker --type=json -p '[{"op":"remove","path":"/spec/template/spec/nodeSelector/hangdo-lab~1no-speaker"}]'   # 복구
kubectl -n metallb-system rollout status ds/speaker
```

```output kind=verified env="검증 환경 (MetalLB v0.16.0)" date="2026-11-02"
No resources found in metallb-system namespace.
wget: can't connect to remote host (192.168.58.200): No route to host
```

새 클라이언트(ARP 캐시가 빈 컨테이너)는 바로 실패합니다. 이미 연결해 둔 클라이언트는 ARP 캐시가 남은 동안(리눅스 기본 수십 초) 계속 되다가 끊길 수 있어, **증상이 사람마다 다르게** 보입니다. 노드가 여러 대면 다른 노드의 speaker가 이어받고 무상 ARP를 보냅니다.

**④ 노드와 다른 대역의 풀** — 노드 서브넷 밖의 주소(예: `10.99.0.10`)를 풀에 넣으면, 할당은 되지만 같은 L2에 있는 클라이언트가 그 주소로 가는 길이 없습니다(클라이언트는 기본 경로 = 게이트웨이로 보냄). 검증에서는 할당 `10.99.0.10`, 알리는 노드 없음(이 풀은 L2Advertisement에 없음), 클라이언트에서 `Connection refused`(게이트웨이가 거절)였습니다. L2 모드의 풀은 **노드가 붙은 서브넷 안**이어야 합니다.

## 흔한 오류

| 증상 | 원인 | 확인·해결 |
|---|---|---|
| `EXTERNAL-IP <pending>` | MetalLB 미설치 · 풀 없음 · 풀 바닥(`AllocationFailed`) · 서비스가 고른 풀 이름 오타 | `kubectl get events`의 `AllocationFailed`, `kubectl get ipaddresspool -A` |
| 주소는 있는데 접속·ARP 실패 | L2Advertisement 없음 · control-plane만 있고 exclude 레이블 · speaker 없음 · 풀이 다른 대역 | `kubectl get servicel2statuses -A`가 비면 알리는 노드 없음 → `kubectl -n metallb-system logs ds/speaker` |
| macOS·Windows에서 브라우저로 안 열림 | docker 드라이버의 노드 네트워크는 호스트에서 직접 닿지 않음 (리눅스 호스트는 닿음) | 같은 Docker 네트워크 컨테이너로 시험, 또는 `minikube tunnel -p k8s-lab` |
| 가끔 다른 장비로 가거나 끊김 | 풀 주소를 다른 장비(공유기 DHCP 등)도 씀 — 같은 IP에 두 MAC | 풀을 DHCP 범위 밖으로, `arping`에 응답 MAC이 둘이면 충돌 |
| 클라이언트 IP가 노드 주소로 보임 | `externalTrafficPolicy: Cluster`의 SNAT | `Local`로 바꾸고 파드가 있는 노드만 알리는지 확인 |
| 웹훅 오류 `failed calling webhook "ipaddresspoolvalidationwebhook"` | controller가 아직 준비 안 됨 | `kubectl -n metallb-system wait --for=condition=Available deploy/controller` 뒤 다시 |
| 인터페이스가 여러 개인 노드에서 엉뚱한 망으로 알림 | L2 speaker는 기본으로 모든 인터페이스에서 응답 | `L2Advertisement.spec.interfaces`·`nodeSelectors`로 제한 (이 실습에서는 실행 안 함) |

## 성공 판정

```verify
id: metallb-l2-ip
title: LoadBalancer Service가 MetalLB 풀의 주소를 받고 노드가 알림
explain: 3단계 뒤 실행합니다. 할당된 주소와 그 주소를 알리는 노드 수를 출력합니다.
command: echo "$(kubectl -n lab-mlb get svc web -o jsonpath='{.status.loadBalancer.ingress[0].ip}') $(kubectl get servicel2statuses -A --no-headers | wc -l | tr -d ' ')"
expect: ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+ [1-9]
criteria: 「192.168.x.200 1」처럼 주소와 1 이상의 숫자
```

```verify
id: metallb-l2-traffic
title: 같은 L2 네트워크의 클라이언트에서 그 주소로 응답이 옴
explain: 일회용 컨테이너로 접속합니다. 주소는 위 판정에서 나온 값으로 바꿉니다.
command: docker run --rm --network k8s-lab busybox:1.36 wget -qO- -T 5 http://192.168.58.200/ | grep -c Hostname
expect: ^1$
criteria: 1
```

## 정리

```bash shell="실습 터미널" run=skip
kubectl delete namespace lab-mlb
kubectl delete -f ~/mlb-lab/pool.yaml --ignore-not-found
kubectl delete -f ~/mlb-lab/metallb-native.yaml --ignore-not-found
kubectl label node k8s-lab node.kubernetes.io/exclude-from-external-load-balancers= --overwrite   # 떼었던 레이블을 되돌림
kubectl api-resources --api-group=metallb.io --no-headers | wc -l     # 0이면 CRD까지 제거됨
rm -rf ~/mlb-lab
```

검증에서 위 순서로 지운 뒤 `metallb-system` 네임스페이스와 `metallb.io` API가 모두 없어진 것을 확인했습니다.

## 체크리스트

- [ ] `<pending>`의 이유를 「주소를 줄 컨트롤러가 없음」으로 설명할 수 있다
- [ ] controller(할당)와 speaker(알리기)를 장애 증상으로 구분할 수 있다
- [ ] L2 모드에서 ARP 응답 MAC이 노드 MAC인 이유를 설명할 수 있다
- [ ] control-plane 노드의 exclude 레이블이 단일 노드 실습에서 어떤 문제를 만드는지 안다
- [ ] `externalTrafficPolicy` Cluster·Local의 클라이언트 IP 차이를 측정했다
- [ ] BGP 모드가 L2와 어떻게 다른지(라우터·ECMP) 말할 수 있다 — 이 과정에서는 실행하지 않았다
