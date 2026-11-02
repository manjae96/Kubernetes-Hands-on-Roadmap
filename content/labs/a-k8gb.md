## 학습 목표

- k8gb가 **DNS로** 여러 클러스터에 트래픽을 나누는 방식(존 위임, 클러스터마다 권한 DNS, 건강 상태에 따른 답)을 설명할 수 있습니다.
- 엣지 DNS(BIND)·클러스터 두 개·MetalLB로 로컬에서 위임과 `failover` 전략을 직접 구성할 수 있습니다.
- 앱 장애·클러스터 전체 장애·복구 때 DNS 답이 바뀌는 데 걸리는 시간을 재고, 그 시간을 정하는 값(TTL·재조정 주기)을 말할 수 있습니다.
- 위임 키(TSIG)가 틀렸을 때의 증상을 엣지 DNS와 k8gb 양쪽 로그로 구분할 수 있습니다.

## 선수 지식

- DNS 위임·NS·glue·TTL: 도메인 항해도 [CoreDNS로 lab.test 존 운영하기](/domain/#/item/b-lab02)와 심화 노트 [도메인 등록과 위임](/deep/#/note/domain-registration)
- LoadBalancer 주소를 주는 MetalLB: [MetalLB 선택 실습](#/item/a-metallb) — 여기서는 설치만 하고 설명은 반복하지 않습니다.
- Helm 기본 사용, `kind`(Kubernetes in Docker) 설치
- 이 과정은 **선택 심화**입니다. 필수 과정·캡스톤 진행에 필요하지 않습니다.

:::note 검증 범위
**macOS(Apple 실리콘) · OrbStack(Docker Engine 29.8.2, 메모리 16GB) · kind v0.32.0(`kindest/node:v1.35.0`) 클러스터 2개 · MetalLB v0.16.0 · k8gb v1.0.1(Helm 차트) · BIND 9.21(`internetsystemsconsortium/bind9:9.21`, arm64 Mac에서는 amd64 에뮬레이션)** 에서 아래 명령을 처음부터 끝까지 실행했고, 출력 블록은 그 결과입니다(2026-11-02). 출력의 이름 `hangdo-verify-…`는 검증용 이름입니다(여러분은 `gslb-eu`·`gslb-us`·`k8gb-edge`·`k8gb-net`).

**유료 도메인·외부 DNS 계정은 쓰지 않습니다.** `example.com`(문서용 예약 도메인)의 권한 서버를 로컬 BIND 컨테이너로 흉내 냅니다. 그래서 실제 인터넷의 리졸버가 이 위임을 따라가지 않고, 질의는 같은 Docker 네트워크의 컨테이너에서 각 DNS 서버에 직접 합니다. **실행하지 않은 것:** 공용 DNS(Route 53·Cloudflare 등) 연동, 클라이언트 쪽 리졸버 캐시를 거친 체감 전환 시간, `roundRobin`·`geoip` 전략, 클러스터 3개 이상, Ingress·Gateway API 연동.
:::

## 개념: DNS로 클러스터를 고르는 방법

**무엇인가.** [[k8gb|k8gb]](CNCF Sandbox)는 클러스터마다 하나씩 두는 컨트롤러 + 전용 CoreDNS입니다. 부모 존(`example.com`)이 GSLB 존(`cloud.example.com`)을 **모든 클러스터의 CoreDNS에 위임**하고, 각 CoreDNS는 「지금 건강한 클러스터의 주소」로 답합니다. 클러스터끼리는 별도 통신 없이 **서로의 DNS에 물어** 상대의 건강 상태(그 클러스터가 내놓은 주소 목록)를 압니다.

**왜 필요한가.** 클러스터 하나 안의 장애는 Service·Deployment가 해결하지만, 데이터센터·리전 전체가 멈추면 클러스터 밖에서 「다른 곳으로 보내기」를 해야 합니다. 전역 로드밸런서 장비나 클라우드 서비스 대신, 어느 환경에나 있는 DNS로 그 일을 하는 것이 k8gb의 방식입니다.

<!-- visual:k8gb-delegation start — 생성: tools/visuals.py, 원본 content/visuals/src/k8gb-delegation.json -->
<figure class="visual" id="visual-k8gb-delegation">
<div class="visual-scroll"><a href="content/visuals/svg/k8gb-delegation.svg" target="_blank" rel="noopener"><img src="content/visuals/svg/k8gb-delegation.svg" alt="k8gb: 존 위임과 failover — 엣지 DNS(example.com 권한)가 cloud.example.com을 eu·us 두 클러스터의 CoreDNS에 위임하고, 각 클러스터의 external-dns가 그 NS·glue를 TSIG로 서명한 RFC 2136 업데이트로 씁니다. 두 CoreDNS는 서로의 상태를 DNS로 묻고, failover(primary eu)에서는 eu가 건강하면 둘 다 eu 앱 주소로, eu가 아프면 둘 다 us 앱 주소로 답합니다." width="499" loading="lazy" decoding="async"></a></div>
<figcaption><b>k8gb: 존 위임과 failover</b> — 엣지 DNS(example.com 권한)가 cloud.example.com을 eu·us 두 클러스터의 CoreDNS에 위임하고, 각 클러스터의 external-dns가 그 NS·glue를 TSIG로 서명한 RFC 2136 업데이트로 씁니다. 두 CoreDNS는 서로의 상태를 DNS로 묻고, failover(primary eu)에서는 eu가 건강하면 둘 다 eu 앱 주소로, eu가 아프면 둘 다 us 앱 주소로 답합니다. <span class="visual-links"><a href="content/visuals/svg/k8gb-delegation.svg" target="_blank" rel="noopener">크게 보기</a> · <a href="content/visuals/svg/k8gb-delegation.svg" download="k8gb-delegation.svg">SVG 받기</a></span></figcaption>
</figure>
<!-- visual:k8gb-delegation end -->

<details class="visual-text"><summary>그림 내용을 글로 보기</summary>

```text
엣지 DNS (example.com 권한) ── cloud.example.com NS → gslb-ns-eu · gslb-ns-us (glue: 각 CoreDNS 주소)
   ▲ RFC 2136 동적 업데이트 (TSIG 서명) — 각 클러스터의 external-dns가 자기 NS·glue를 씀
클러스터 eu: k8gb 컨트롤러 + CoreDNS(LB .200) ── web 앱 LB .201
클러스터 us: k8gb 컨트롤러 + CoreDNS(LB .210) ── web 앱 LB .211
   서로의 CoreDNS에 localtargets-web.cloud.example.com 을 물어 상대가 건강한지 앎
failover(primary=eu): eu가 건강하면 두 CoreDNS 모두 .201, eu가 아프면 둘 다 .211
```

</details>

| 구성 요소 | 하는 일 |
|---|---|
| `Gslb` 자원 (`k8gb.io/v1beta1`) | 어떤 이름(`web.cloud.example.com`)을 어떤 Service/Ingress에 묶고, 어떤 전략(`failover`·`roundRobin`·`geoip`)으로 답할지 |
| k8gb 컨트롤러 | 앱 엔드포인트의 건강 상태를 보고 DNS 레코드(`DNSEndpoint`)를 만듦, 상대 클러스터 상태를 DNS로 확인 |
| k8gb CoreDNS | `cloud.example.com`의 권한 서버. 위 레코드로 답함 |
| external-dns | 엣지 DNS에 「이 클러스터도 위임 대상」(NS·glue)을 씀. 여기서는 RFC 2136 + TSIG |

**한계도 DNS의 한계입니다.** 클라이언트·리졸버는 TTL 동안 옛 답을 기억하고, 죽은 클러스터의 NS가 위임에 남아 있으면 리졸버가 그쪽을 먼저 물었다가 시간 초과 후 다른 NS로 넘어갑니다. 연결 단위의 즉시 전환이 필요하면 L4/L7 전역 로드밸런서를 함께 씁니다.

## 실습 환경 점검

```bash shell="실습 터미널"
kind version; helm version --short; kubectl version --client | head -1
docker info --format 'Docker 메모리 {{.MemTotal}} bytes · CPU {{.NCPU}}'
docker network ls --format '{{.Name}}' | grep -x k8gb-net || echo "k8gb-net 없음 (새로 만듦)"
docker network inspect $(docker network ls -q) --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}' | tr ' ' '\n' | grep -x 172.31.250.0/24 || echo "172.31.250.0/24 비어 있음"
```

- 클러스터 두 개 + 엣지 DNS로 메모리 약 **3GB**, 디스크 약 **3GB**(노드 이미지·k8gb·MetalLB 이미지)를 씁니다. `kindest/node` 이미지는 kind 버전마다 기본값이 다르므로 이 문서와 같은 `v1.35.0`을 지정합니다.
- 대역 `172.31.250.0/24`가 이미 쓰이고 있으면 아래의 모든 `172.31.250.` 주소를 비어 있는 대역으로 바꿉니다.
- kubeconfig는 이 실습 폴더의 파일만 씁니다(평소 `~/.kube/config`를 건드리지 않음).

## 1단계: 엣지 DNS (example.com 권한 서버)

```text file=edge/named.conf
// 실습용 엣지 DNS: example.com의 권한 서버. k8gb(external-dns)가 TSIG 키로 cloud.example.com 위임(NS·glue)을 동적으로 씀
include "/etc/bind/ddns.key";
options {
  directory "/var/cache/bind";
  listen-on port 53 { any; };
  allow-query { any; };
  recursion no;                       // 권한 서버만 (재귀 질의는 받지 않음)
};
zone "example.com" {
  type primary;
  file "/var/lib/bind/example.com.zone";
  allow-transfer { key "externaldns-key"; };
  update-policy { grant externaldns-key zonesub ANY; };   // 이 키만 example.com 아래를 고칠 수 있음
};
```

```text file=edge/example.com.zone
$TTL 30
@   IN SOA ns.example.com. root.example.com. ( 1 30 30 30 30 )
    IN NS  ns.example.com.
ns  IN A   127.0.0.1
```

TSIG 키는 **직접 만들어** 이 폴더에만 둡니다(인터넷 예제의 고정 키를 복사하지 않음).

```bash shell="실습 터미널"
mkdir -p ~/k8gb-lab/edge && cd ~/k8gb-lab && umask 077
docker run --rm --platform linux/amd64 --entrypoint tsig-keygen internetsystemsconsortium/bind9:9.21 -a hmac-sha256 externaldns-key > edge/ddns.key 2>/dev/null
sed -E 's/secret "[^"]+"/secret "****"/' edge/ddns.key
mkdir -p edge-data && cp edge/example.com.zone edge-data/ && chmod 777 edge-data && chmod 644 edge-data/example.com.zone edge/named.conf edge/ddns.key
docker network create --subnet 172.31.250.0/24 --gateway 172.31.250.1 k8gb-net >/dev/null
docker run -d --name k8gb-edge --platform linux/amd64 --network k8gb-net --ip 172.31.250.53 \
  -v "$PWD/edge/named.conf:/etc/bind/named.conf:ro" -v "$PWD/edge/ddns.key:/etc/bind/ddns.key:ro" -v "$PWD/edge-data:/var/lib/bind" \
  internetsystemsconsortium/bind9:9.21 -g -c /etc/bind/named.conf >/dev/null
sleep 5; docker logs k8gb-edge 2>&1 | grep -E "zone example.com/IN: loaded|running$"
```

```output kind=verified env="검증 환경 (BIND 9.21)" date="2026-11-02"
key "externaldns-key" {
	algorithm hmac-sha256;
	secret "****";
};
2026-11-02T15:09:57.203+00:00 zone example.com/IN: loaded serial 1
2026-11-02T15:09:57.211+00:00 running
```

질의는 같은 네트워크의 일회용 컨테이너에서 합니다. 짧게 쓰려고 도우미를 둡니다.

```text file=dig.sh
#!/bin/sh
# 사용: ./dig.sh @<DNS 서버> <이름> [유형] [dig 옵션 …] — k8gb-net 안에서 dig 실행
exec docker run --rm --platform linux/amd64 --network k8gb-net --entrypoint dig internetsystemsconsortium/bind9:9.21 "$@" 2>/dev/null
```

`ddns.key`의 키는 example.com 아래를 **누구든 고칠 수 있는 권한**입니다. 화면·저장소에 올리지 않고, 실습이 끝나면 폴더째 지웁니다. 키를 볼 수 있는 BIND 컨테이너 권한 때문에 파일 권한을 644로 열었는데, 이 PC 안의 실습 폴더(700 umask로 만든 상위 폴더)라서 허용합니다.

## 2단계: 클러스터 두 개와 MetalLB

```bash shell="실습 터미널"
cd ~/k8gb-lab && chmod +x dig.sh && export KUBECONFIG=$PWD/kubeconfig KIND_EXPERIMENTAL_DOCKER_NETWORK=k8gb-net
for c in eu us; do kind create cluster --name gslb-$c --image kindest/node:v1.35.0 --wait 120s 2>&1 | grep -E "Ready after|ERROR"; done
for c in eu us; do kubectl --context kind-gslb-$c get nodes -o wide --no-headers | awk '{print $1, $2, $6}'; done
```

```output kind=verified env="검증 환경 (kind v0.32.0)" date="2026-11-02"
 • Ready after 18s 💚
 • Ready after 16s 💚
hangdo-verify-eu-control-plane Ready 172.31.250.2
hangdo-verify-us-control-plane Ready 172.31.250.3
```

MetalLB는 [MetalLB 선택 실습](#/item/a-metallb)과 같은 태그·체크섬으로 설치하고, 클러스터마다 **겹치지 않는 주소 풀**을 줍니다(eu `.200~.209`, us `.210~.219`). 단일 노드라 control-plane 제외 레이블을 뗍니다(이유는 MetalLB 실습 참고).

```bash shell="실습 터미널"
cd ~/k8gb-lab && export KUBECONFIG=$PWD/kubeconfig
curl -fsSLo metallb-native.yaml https://raw.githubusercontent.com/metallb/metallb/v0.16.0/config/manifests/metallb-native.yaml
shasum -a 256 metallb-native.yaml
for c in eu us; do
  [ $c = eu ] && R=172.31.250.200-172.31.250.209 || R=172.31.250.210-172.31.250.219
  k="kubectl --context kind-gslb-$c"
  $k apply -f metallb-native.yaml >/dev/null
  $k -n metallb-system wait --for=condition=Available deploy/controller --timeout=180s >/dev/null
  $k -n metallb-system rollout status ds/speaker --timeout=180s >/dev/null
  $k label node gslb-$c-control-plane node.kubernetes.io/exclude-from-external-load-balancers- >/dev/null
  printf 'apiVersion: metallb.io/v1beta1\nkind: IPAddressPool\nmetadata: { name: pool, namespace: metallb-system }\nspec: { addresses: ["%s"] }\n---\napiVersion: metallb.io/v1beta1\nkind: L2Advertisement\nmetadata: { name: l2, namespace: metallb-system }\nspec: { ipAddressPools: ["pool"] }\n' "$R" | $k apply -f - >/dev/null
  echo "$c: MetalLB 풀 $R"
done
```

```output kind=verified env="검증 환경 (MetalLB v0.16.0)" date="2026-11-02"
b0b9be2802f10aa32d45308b4457d06cde0c70544712c8d0cf5511657ffd2b69  metallb-native.yaml
eu: MetalLB 풀 172.31.250.200-172.31.250.209
us: MetalLB 풀 172.31.250.210-172.31.250.219
```

## 3단계: k8gb 설치

두 클러스터에 같은 차트를 넣고 `clusterGeoTag`만 다르게 줍니다. 차트 저장소를 PC에 등록하지 않도록 `--repo`로 바로 받습니다.

```yaml file=values.tmpl.yaml
# k8gb v1.0.1 실습 값 — 클러스터마다 GEO만 바꿈 (eu·us)
k8gb:
  clusterGeoTag: "GEO"
  extGslbClustersGeoTags: "eu,us"          # 함께 묶을 클러스터 전부 (자기 자신 포함)
  edgeDNSServers: ["172.31.250.53"]        # 엣지 DNS (위임을 적는 권한 서버)
  dnsZones:
    - parentZone: "example.com"
      loadBalancedZone: "cloud.example.com"  # k8gb가 답하는 영역
      dnsZoneNegTTL: 10
  reconcileRequeueSeconds: 10              # 실습: 상태를 10초마다 다시 봄 (기본 30)
  zoneDelegationReconcileRequeueSeconds: 10
  zoneDelegationRecoverySeconds: 10
coredns:
  serviceType: LoadBalancer                # 이 클러스터의 DNS 주소 = CoreDNS LoadBalancer 주소(MetalLB)
extdns:
  enabled: true
  fullnameOverride: k8gb-external-dns
  provider: { name: rfc2136 }              # 엣지 DNS에 RFC 2136 동적 업데이트(TSIG 서명)로 위임을 씀
  domainFilters: ["example.com"]
  txtPrefix: "k8gb-GEO-"
  txtOwnerId: "k8gb-GEO"
  env:
    - name: EXTERNAL_DNS_RFC2136_TSIG_SECRET
      valueFrom: { secretKeyRef: { name: rfc2136, key: secret } }
  extraArgs:
    rfc2136-host: "172.31.250.53"
    rfc2136-port: 53
    rfc2136-zone: example.com
    rfc2136-tsig-keyname: externaldns-key
    rfc2136-tsig-secret-alg: hmac-sha256
    rfc2136-tsig-axfr:
istio: { enabled: false }
gatewayapi: { enabled: false }
```

```bash shell="실습 터미널"
cd ~/k8gb-lab && export KUBECONFIG=$PWD/kubeconfig
SECRET=$(sed -nE 's/.*secret "([^"]+)".*/\1/p' edge/ddns.key)        # 화면에 내지 않고 Secret으로만
for c in eu us; do
  k="kubectl --context kind-gslb-$c"
  sed "s/GEO/$c/g" values.tmpl.yaml > values-$c.yaml
  $k create namespace k8gb --dry-run=client -o yaml | $k apply -f - >/dev/null
  $k -n k8gb create secret generic rfc2136 --from-literal=secret="$SECRET" --dry-run=client -o yaml | $k apply -f - >/dev/null
  helm --kube-context kind-gslb-$c -n k8gb upgrade -i k8gb k8gb --repo https://www.k8gb.io --version v1.0.1 -f values-$c.yaml --wait --timeout 10m 2>&1 | grep -E "^STATUS|Error"
  echo "$c: CoreDNS LB $($k -n k8gb get svc k8gb-coredns -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
done
unset SECRET
sleep 30
./dig.sh @172.31.250.53 cloud.example.com NS +noall +authority
./dig.sh @172.31.250.53 gslb-ns-eu-cloud.example.com +short
./dig.sh @172.31.250.53 gslb-ns-us-cloud.example.com +short
```

```output kind=verified env="검증 환경 (k8gb v1.0.1 · 차트 v1.0.1)" date="2026-11-02"
STATUS: deployed
eu: CoreDNS LB 172.31.250.200
STATUS: deployed
us: CoreDNS LB 172.31.250.210
cloud.example.com.	30	IN	NS	gslb-ns-us-cloud.example.com.
cloud.example.com.	30	IN	NS	gslb-ns-eu-cloud.example.com.
172.31.250.200
172.31.250.210
```

엣지 DNS에 **위임이 두 개** 생겼습니다 — `cloud.example.com`의 권한 서버는 eu·us 두 CoreDNS이고, glue(A)는 각 CoreDNS의 LoadBalancer 주소입니다. 위임 NS는 질의의 ANSWER가 아니라 AUTHORITY 절에 오므로(「여기는 내 담당이 아니니 저기에 물어라」) `+short`로는 보이지 않습니다. external-dns 로그에는 `--rfc2136-tsig-axfr is deprecated` 경고가 한 줄 나옵니다(이 차트 버전의 기본 예제 값을 그대로 쓴 결과, 동작에는 영향 없음).

## 4단계: 앱과 failover 전략

```yaml file=app.yaml
apiVersion: v1
kind: Namespace
metadata: { name: shop }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: web, namespace: shop }
spec:
  replicas: 2
  selector: { matchLabels: { app: web } }
  template:
    metadata: { labels: { app: web } }
    spec:
      containers:
      - name: whoami
        image: traefik/whoami:v1.11.0
        ports: [{ containerPort: 80 }]
        readinessProbe: { httpGet: { path: /, port: 80 }, periodSeconds: 3 }
---
apiVersion: v1
kind: Service
metadata: { name: web, namespace: shop, labels: { app: web } }
spec:
  type: LoadBalancer
  selector: { app: web }
  ports: [{ name: http, port: 80, targetPort: 80 }]
---
apiVersion: k8gb.io/v1beta1
kind: Gslb
metadata:
  name: web
  namespace: shop
  annotations:
    k8gb.io/hostname: "web.cloud.example.com"     # LoadBalancer Service는 이름이 없어서 주석으로 지정
spec:
  resourceRef:
    apiVersion: v1
    kind: Service
    matchLabels: { app: web }
  strategy:
    type: failover
    primaryGeoTag: "eu"                           # 평소에는 eu만, eu가 건강하지 않으면 us
    dnsTtlSeconds: 10
```

```bash shell="실습 터미널"
cd ~/k8gb-lab && export KUBECONFIG=$PWD/kubeconfig
for c in eu us; do k="kubectl --context kind-gslb-$c"; $k apply -f app.yaml >/dev/null; $k -n shop rollout status deploy/web --timeout=180s >/dev/null; echo "$c: web LB $($k -n shop get svc web -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"; done
sleep 30
for c in eu us; do kubectl --context kind-gslb-$c -n shop get gslbs.k8gb.io web -o jsonpath="$c: health={.status.serviceHealth} records={.status.healthyRecords}{'\n'}"; done
for ns in 172.31.250.200 172.31.250.210; do echo "@$ns → $(./dig.sh @$ns web.cloud.example.com A +short | tr '\n' ' ')"; done
```

```output kind=verified env="검증 환경 (k8gb v1.0.1)" date="2026-11-02"
eu: web LB 172.31.250.201
us: web LB 172.31.250.211
eu: health={"web.cloud.example.com":"Healthy"} records={"web.cloud.example.com":["172.31.250.201"]}
us: health={"web.cloud.example.com":"Healthy"} records={"web.cloud.example.com":["172.31.250.201"]}
@172.31.250.200 → 172.31.250.201 
@172.31.250.210 → 172.31.250.201 
```

- 두 CoreDNS **모두** eu의 주소(`.201`)로 답합니다. 리졸버가 위임된 NS 중 어느 쪽에 물어도 같은 답을 받아야 하기 때문입니다.
- `kubectl get gslb`는 옛 API 그룹(`k8gb.absa.oss`)으로 해석되어 `NotFound`가 날 수 있습니다(검증 중 실제로 그랬음). 새 그룹은 `gslbs.k8gb.io`로 적습니다.

## 5단계: 앱 장애 → 전환 → 복귀

eu의 앱을 0개로 줄여 「eu 클러스터는 살아 있지만 앱이 없음」을 만들고, 두 DNS의 답이 바뀌는 시간을 잽니다.

```text file=watch.sh
#!/bin/sh
# 사용: ./watch.sh <eu 레플리카 수> <기다릴 답(IP)> — eu 앱 수를 바꾸고 두 CoreDNS의 답이 그 IP가 될 때까지 잼
ans() { echo "eu-dns=$(./dig.sh @172.31.250.200 web.cloud.example.com A +short +time=2 +tries=1 | tr '\n' ' ')us-dns=$(./dig.sh @172.31.250.210 web.cloud.example.com A +short | tr '\n' ' ')"; }
kubectl --context kind-gslb-eu -n shop scale deploy/web --replicas="$1" >/dev/null; t0=$(date +%s)
echo "0초  $(ans)"
for i in $(seq 1 30); do sleep 5; a=$(ans); [ "$a" = "eu-dns=$2 us-dns=$2 " ] && { echo "$(( $(date +%s) - t0 ))초  $a"; break; }; done
kubectl --context kind-gslb-eu -n shop get gslbs.k8gb.io web -o jsonpath='eu Gslb: {.status.serviceHealth}{"\n"}'
```

```bash shell="실습 터미널"
cd ~/k8gb-lab && export KUBECONFIG=$PWD/kubeconfig && chmod +x watch.sh
./watch.sh 0 172.31.250.211
./watch.sh 2 172.31.250.201
```

```output kind=verified env="검증 환경 (k8gb v1.0.1 · reconcileRequeueSeconds 10 · dnsTtlSeconds 10)" date="2026-11-02"
0초  eu-dns=172.31.250.211 us-dns=172.31.250.201 
12초  eu-dns=172.31.250.211 us-dns=172.31.250.211 
eu Gslb: {"web.cloud.example.com":"Unhealthy"}
0초  eu-dns=172.31.250.211 us-dns=172.31.250.211 
12초  eu-dns=172.31.250.201 us-dns=172.31.250.201 
eu Gslb: {"web.cloud.example.com":"Healthy"}
```

- eu의 CoreDNS는 자기 앱 상태를 바로 알아서 먼저 바뀌고, us는 eu에 물어 확인하는 다음 재조정(여기서는 10초 주기)에 바뀝니다. 그 사이 몇 초는 **두 DNS의 답이 다릅니다**.
- 사용자가 체감하는 전환 시간 = 이 시간 + **리졸버·클라이언트 캐시의 TTL**(`dnsTtlSeconds`, 여기서는 10초). TTL을 너무 낮추면 DNS 질의가 늘어납니다.

## 6단계: 클러스터 전체 장애

eu 노드 컨테이너를 멈춰 eu 클러스터 전체(그 CoreDNS 포함)를 없앱니다.

```bash shell="실습 터미널"
cd ~/k8gb-lab && export KUBECONFIG=$PWD/kubeconfig
docker stop gslb-eu-control-plane >/dev/null; t0=$(date +%s)
echo "eu-dns: $(./dig.sh @172.31.250.200 web.cloud.example.com A +short +time=2 +tries=1 | head -1)"
for i in $(seq 1 40); do sleep 5; a=$(./dig.sh @172.31.250.210 web.cloud.example.com A +short | tr '\n' ' '); [ "$a" = "172.31.250.211 " ] && break; done; echo "$(( $(date +%s) - t0 ))초  us-dns: $a"
./dig.sh @172.31.250.53 cloud.example.com NS +noall +authority | sort
docker start gslb-eu-control-plane >/dev/null; t0=$(date +%s)
for i in $(seq 1 60); do sleep 5; a="eu-dns=$(./dig.sh @172.31.250.200 web.cloud.example.com A +short +time=2 +tries=1 | tr '\n' ' ')us-dns=$(./dig.sh @172.31.250.210 web.cloud.example.com A +short | tr '\n' ' ')"; [ "$a" = "eu-dns=172.31.250.201 us-dns=172.31.250.201 " ] && break; done; echo "복구 $(( $(date +%s) - t0 ))초  $a"
```

```output kind=verified env="검증 환경 (k8gb v1.0.1)" date="2026-11-02"
eu-dns: ;; communications error to 172.31.250.200#53: timed out
8초  us-dns: 172.31.250.211 
cloud.example.com.	30	IN	NS	gslb-ns-eu-cloud.example.com.
cloud.example.com.	30	IN	NS	gslb-ns-us-cloud.example.com.
복구 51초  eu-dns=172.31.250.201 us-dns=172.31.250.201 
```

- eu의 DNS는 아예 답하지 않고(시간 초과), us는 eu의 DNS에 물어도 답이 없으므로 eu를 빼고 자기 주소로 답합니다.
- **엣지의 위임에는 eu NS가 그대로 남아 있습니다.** 실제 리졸버는 eu NS를 먼저 고르면 시간 초과를 겪은 뒤 us NS로 넘어가므로, 첫 질의가 몇 초 늦을 수 있습니다(이 실습에는 리졸버가 없어 그 지연은 재지 않음).
- 복구는 앱 장애보다 오래 걸립니다 — 노드·kube-apiserver·k8gb·CoreDNS가 차례로 다시 떠야 하기 때문입니다.

## 7단계: 위임 키(TSIG)가 틀리면

us 클러스터의 Secret을 무작위 값으로 바꿔 external-dns를 다시 띄웁니다. 확인한 뒤 원래 키로 되돌립니다.

```bash shell="실습 터미널"
cd ~/k8gb-lab && export KUBECONFIG=$PWD/kubeconfig
k="kubectl --context kind-gslb-us -n k8gb"
$k create secret generic rfc2136 --from-literal=secret="$(openssl rand -base64 32)" --dry-run=client -o yaml | $k apply -f - >/dev/null
$k rollout restart deploy/k8gb-external-dns >/dev/null && $k rollout status deploy/k8gb-external-dns --timeout=120s >/dev/null
sleep 40
$k logs deploy/k8gb-external-dns --since=60s 2>&1 | grep -oE 'level=error msg="[^"]+"' | sort -u
docker logs k8gb-edge --since 60s 2>&1 | grep -oE "request has invalid signature: TSIG externaldns-key: tsig verify failure \(BADSIG\)" | sort -u
SECRET=$(sed -nE 's/.*secret "([^"]+)".*/\1/p' edge/ddns.key)
$k create secret generic rfc2136 --from-literal=secret="$SECRET" --dry-run=client -o yaml | $k apply -f - >/dev/null; unset SECRET
$k rollout restart deploy/k8gb-external-dns >/dev/null && $k rollout status deploy/k8gb-external-dns --timeout=120s >/dev/null; sleep 30
echo "복구 뒤 오류 줄 수: $($k logs deploy/k8gb-external-dns --since=25s 2>&1 | grep -c 'level=error')"
```

```output kind=verified env="검증 환경 (k8gb v1.0.1 · BIND 9.21)" date="2026-11-02"
level=error msg="AXFR error: dns: bad authentication"
level=error msg="Failed to do run once: soft error\nfailed to read AXFR response for zone \"
request has invalid signature: TSIG externaldns-key: tsig verify failure (BADSIG)
복구 뒤 오류 줄 수: 0
```

키가 틀리면 엣지 DNS는 서명을 거부하고(`BADSIG`), 그 클러스터는 **위임을 새로 쓰거나 고치지 못합니다.** 이미 있던 위임은 남아 있어 당장은 티가 나지 않다가, 주소가 바뀌거나 클러스터를 새로 더할 때 문제가 드러납니다. 그래서 external-dns 로그의 `error`를 경보로 받습니다.

## 흔한 오류

| 증상 | 원인 | 확인·해결 |
|---|---|---|
| 엣지에 `cloud.example.com` NS가 없음 | external-dns가 엣지에 못 씀 (주소·포트·TSIG 키·`update-policy`) | `kubectl -n k8gb logs deploy/k8gb-external-dns`, `docker logs k8gb-edge` |
| `AXFR error: dns: bad authentication` / `BADSIG` | TSIG 비밀값 불일치 | Secret `rfc2136`과 `ddns.key` 비교(값을 화면에 내지 않고) |
| CoreDNS LB 주소가 `<pending>` | MetalLB 없음·풀 없음·제외 레이블 | [MetalLB 실습](#/item/a-metallb)의 흔한 오류 표 |
| 두 클러스터의 답이 계속 다름 | `extGslbClustersGeoTags` 누락, 상대 NS를 엣지에서 못 찾음 | 두 values의 geo 태그, `./dig.sh @엣지 gslb-ns-us-cloud.example.com` |
| `gslbs.k8gb.absa.oss "web" not found` | 옛 API 그룹으로 조회 | `kubectl get gslbs.k8gb.io` |
| 전환이 느림 | `reconcileRequeueSeconds`(기본 30초), TTL, 리졸버 캐시 | 값을 줄이면 질의·부하가 늘어남 — 목표 전환 시간에서 거꾸로 정함 |
| 앱이 없는데 failover가 안 됨 | 엔드포인트가 「건강」의 기준 — 레디니스 없는 파드는 떠 있기만 하면 건강 | readinessProbe를 둠 |

## 성공 판정

```verify
id: k8gb-delegation
title: 엣지 DNS에 두 클러스터로의 위임이 있음
explain: 3단계 뒤 실행합니다. cloud.example.com NS 레코드 수를 셉니다.
command: cd ~/k8gb-lab && ./dig.sh @172.31.250.53 cloud.example.com NS +noall +authority | grep -c "IN	NS	gslb-ns-"
expect: ^2$
criteria: 2
```

```verify
id: k8gb-failover
title: eu 앱이 없으면 두 DNS 모두 us 주소로 답함
explain: 5단계와 같은 측정을 한 번 더 합니다. 마지막 두 줄에 「eu-dns=…211 us-dns=…211」과 「Unhealthy」가 보여야 합니다. 끝나면 ./watch.sh 2 172.31.250.201 로 되돌립니다.
command: cd ~/k8gb-lab && KUBECONFIG=$PWD/kubeconfig ./watch.sh 0 172.31.250.211 | tail -2 | tr '\n' ' '
expect: eu-dns=172\.31\.250\.211 us-dns=172\.31\.250\.211 .*Unhealthy
criteria: 두 DNS 모두 .211, eu Gslb Unhealthy
```

## 정리

```bash shell="실습 터미널" run=skip
cd ~/k8gb-lab && export KUBECONFIG=$PWD/kubeconfig
kind delete cluster --name gslb-eu; kind delete cluster --name gslb-us
docker rm -f -v k8gb-edge; docker network rm k8gb-net   # -v: BIND 이미지가 만든 익명 볼륨까지 (검증 중 빼먹어 남은 것을 확인)
cd ~ && rm -rf ~/k8gb-lab                  # TSIG 키·kubeconfig·값 파일
```

## 체크리스트

- [ ] 부모 존이 GSLB 존을 모든 클러스터의 CoreDNS에 위임하는 구조를 그릴 수 있다
- [ ] 위임 NS가 AUTHORITY 절에 오는 이유를 안다
- [ ] failover에서 두 CoreDNS가 같은 답을 하는 것과, 전환 중 잠깐 답이 다른 것을 확인했다
- [ ] 체감 전환 시간 = 재조정 주기 + TTL + 리졸버 동작이라는 것을 설명할 수 있다
- [ ] 클러스터 전체 장애 때 위임에 죽은 NS가 남는 영향을 말할 수 있다
- [ ] TSIG 키를 직접 만들고, 틀렸을 때의 증상(BADSIG)을 양쪽 로그로 봤다
- [ ] 공용 DNS 연동·리졸버 캐시 지연은 이 실습에서 실행하지 않았다는 것을 안다
