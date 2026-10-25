## 학습 목표

- Service 유형 네 가지(ClusterIP·NodePort·LoadBalancer·ExternalName)가 각각 **어디서 접속할 수 있게** 하는지 구분할 수 있습니다.
- minikube에서 `minikube service --url`과 `minikube tunnel`로 클러스터 밖에서 접속할 수 있습니다.
- LoadBalancer의 `EXTERNAL-IP`가 `<pending>`인 이유를 설명할 수 있습니다.
- `.spec.externalIPs` 대신 무엇을 쓰는지, Gateway API가 무엇인지 압니다.

## 선수 지식

- [기본 1 「첫 Deployment·Service」](#/item/b-lab01)의 ClusterIP Service

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context
kubectl create namespace lab-svc >/dev/null && kubectl create deployment web -n lab-svc --image=nginx:1.30.6-alpine --replicas=2 >/dev/null
kubectl rollout status deployment/web -n lab-svc --timeout=120s
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
k8s-lab
Waiting for deployment "web" rollout to finish: 0 of 2 updated replicas are available...
Waiting for deployment "web" rollout to finish: 1 of 2 updated replicas are available...
deployment "web" successfully rolled out
```

## 개념: 네 가지 유형은 「한 겹씩 더하기」

```text
ExternalName  ─ 클러스터 안의 이름 → 바깥 DNS 이름 (프록시 없음, CNAME)

LoadBalancer  ─ 클라우드 LB의 외부 IP ─┐
NodePort      ─ 모든 노드의 IP:30000~32767 ─┤  (LoadBalancer는 NodePort를 포함)
ClusterIP     ─ 클러스터 안의 가상 IP:포트 ──┘  (NodePort는 ClusterIP를 포함)
                         │
                         ▼  kube-proxy가 전달
                       Pod들 (selector로 고름)
```

| 유형 | 접속할 수 있는 곳 | 쓰는 곳 |
|---|---|---|
| **ClusterIP** (기본) | 클러스터 안 | Pod끼리 (DB·내부 API) |
| **NodePort** | 노드 IP에 접속할 수 있는 곳 | 개발·온프레미스, LB가 없을 때 |
| **LoadBalancer** | 인터넷(클라우드 LB가 외부 IP를 줌) | 클라우드에서 앱을 직접 공개 |
| ExternalName | 클러스터 안 (이름만 바꿔 줌) | 외부 DB를 내부 이름으로 부를 때 |

웹 서비스 여러 개를 도메인·경로로 나눠 공개할 때는 Service를 하나씩 LoadBalancer로 만드는 대신 **Ingress**(시리즈 Ingress 항해도) 또는 **Gateway API**를 앞에 둡니다.

## 1단계: NodePort

```bash shell="실습 터미널"
kubectl expose deployment web -n lab-svc --name web-np --type=NodePort --port=80 >/dev/null
kubectl get svc web-np -n lab-svc -o custom-columns='TYPE:.spec.type,CLUSTER-IP:.spec.clusterIP,PORT:.spec.ports[0].port,NODEPORT:.spec.ports[0].nodePort' | sed -E 's/10\.[0-9.]+/<ClusterIP>/; s/3[0-9]{4}/<30000~32767 중 하나>/'
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
TYPE       CLUSTER-IP      PORT   NODEPORT
NodePort   <ClusterIP>   80     <30000~32767 중 하나>
```

NodePort를 지정하지 않으면 30000~32767 중 하나가 자동으로 정해집니다. 노드 IP와 이 포트로 접속합니다. docker 드라이버의 minikube는 노드가 컨테이너 안에 있어서, 내 PC에서는 `minikube service`가 다리를 놓아 줍니다.

```bash shell="실습 터미널" run=skip
minikube service web-np -n lab-svc -p k8s-lab --url      # 이 창을 열어 둔 채 출력된 주소로 접속
```

자동 검증에서는 같은 일을 클러스터 안의 노드 주소로 확인합니다.

```bash shell="실습 터미널"
NP=$(kubectl get svc web-np -n lab-svc -o jsonpath='{.spec.ports[0].nodePort}')
NODE=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
kubectl run curl-np -n lab-svc --rm -i --restart=Never --image=curlimages/curl:8.17.0 -- curl -s -o /dev/null -w 'NodePort로 접속: %{http_code}\n' "http://$NODE:$NP/" 2>/dev/null | grep NodePort
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
NodePort로 접속: 200
```

## 2단계: LoadBalancer와 `<pending>`

```bash shell="실습 터미널"
kubectl expose deployment web -n lab-svc --name web-lb --type=LoadBalancer --port=80 >/dev/null
sleep 3
kubectl get svc web-lb -n lab-svc -o custom-columns='TYPE:.spec.type,EXTERNAL-IP:.status.loadBalancer.ingress[0].ip' | sed 's/<none>/<pending>/'
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
TYPE           EXTERNAL-IP
LoadBalancer   <pending>
```

**왜 pending인가.** 외부 IP는 쿠버네티스가 아니라 **클라우드의 로드밸런서 컨트롤러**가 만들어 채워 줍니다. 클라우드가 아닌 곳(minikube, 사내 서버)에는 그 역할을 하는 것이 없어 영원히 `<pending>`입니다.

| 환경 | 외부 IP를 채워 주는 것 |
|---|---|
| AWS·GCP·Azure·국내 클라우드 | 클라우드 컨트롤러 매니저 (자동, **비용 발생**) |
| minikube | `minikube tunnel` (내 PC 주소를 빌려 줌) |
| 사내·베어메탈 | MetalLB, kube-vip, Cilium LB-IPAM 등 |

```bash shell="실습 터미널" run=skip
minikube tunnel -p k8s-lab      # 관리자 비밀번호를 물을 수 있음, 열어 둔 채 다른 창에서:
kubectl get svc web-lb -n lab-svc   # EXTERNAL-IP에 127.0.0.1 등이 채워짐 → http://<그 IP>/ 접속
```

## 3단계: ExternalName

```bash shell="실습 터미널"
kubectl create service externalname docs -n lab-svc --external-name kubernetes.io >/dev/null
kubectl run dns-test -n lab-svc --rm -i --restart=Never --image=busybox:1.37.0 -- nslookup docs.lab-svc.svc.cluster.local 2>/dev/null | grep -m1 'canonical name' | sed 's/\t/ /g'
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
docs.lab-svc.svc.cluster.local canonical name = kubernetes.io
```

ExternalName은 IP도 포트도 없이 **DNS 별칭(CNAME)** 만 만듭니다. 나중에 외부 DB를 클러스터 안으로 옮겨도, 앱은 같은 이름(`docs`)을 계속 쓰고 Service만 바꾸면 됩니다.

## 참고: externalIPs 폐기와 Gateway API

- Service의 `.spec.externalIPs`는 아무 IP나 적으면 그 주소로 오는 트래픽을 가로챌 수 있는 보안 문제(CVE-2020-8554) 때문에 **v1.36부터 폐기(deprecated)** 됐습니다. 새로 쓰지 말고 LoadBalancer(+ MetalLB 등)나 Ingress·Gateway를 씁니다.
- **Gateway API**는 Ingress의 다음 세대 표준입니다(GatewayClass·Gateway·HTTPRoute). 역할(인프라 관리자·앱 개발자)별로 객체를 나누고 헤더·가중치 라우팅 같은 기능을 표준으로 담았습니다. 시리즈의 Ingress 항해도 고급 과정에서 다룹니다.

## 성공 판정

```verify
id: bsvc-types
title: 세 유형의 Service가 만들어짐
explain: lab-svc의 Service 이름과 유형을 봅니다.
command: kubectl get svc -n lab-svc -o jsonpath='{range .items[*]}{.metadata.name}={.spec.type} {end}{"\n"}'
expect: docs=ExternalName web-lb=LoadBalancer web-np=NodePort
criteria: docs=ExternalName web-lb=LoadBalancer web-np=NodePort
```

## 정리

```bash shell="실습 터미널"
kubectl delete namespace lab-svc >/dev/null && echo "lab-svc 정리 완료"
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
lab-svc 정리 완료
```
