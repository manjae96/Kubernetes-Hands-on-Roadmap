## 학습 목표

- kubeadm이 만든 클러스터에서 **인증서·kubeconfig·스태틱 파드 매니페스트·kubeadm-config**가 어디에 있는지 찾아 설명할 수 있습니다.
- 부트스트랩 토큰과 `--discovery-token-ca-cert-hash`가 `join`에서 각각 무엇을 보증하는지 설명하고, 토큰을 만들고 지울 수 있습니다.
- `kubeadm upgrade plan` → 새 kubeadm 받기(체크섬 확인) → `upgrade apply` → drain → kubelet → uncordon 순서로 **패치 업그레이드를 직접 수행**할 수 있습니다.
- 인증서 만료를 확인하고, 업그레이드가 인증서를 갱신한다는 것을 출력으로 확인할 수 있습니다.

## 선수 지식

- 개념(init·join 단계, HA 토폴로지, 업그레이드 순서, 인증서 수명, Kubespray와의 관계)은 심화 노트 [[kubeadm|클러스터 구축]]에 있습니다. 여기서는 반복하지 않고 손으로 해 봅니다.
- 컨트롤 플레인 구성 요소: [[kube-apiserver]] · [[etcd]] · [[kubelet]]
- 이 과정은 **선택 심화**입니다. 필수 과정·캡스톤 진행에 필요하지 않습니다.

:::warn 평소 실습 클러스터를 쓰지 않습니다
업그레이드는 되돌리기 어렵습니다. 평소 쓰는 `k8s-lab`이 아니라 **이 실습만을 위한 minikube 프로필 `kubeadm-lab`** 을 새로 만들고, 끝나면 통째로 지웁니다. 회사·학교 클러스터나 이미 쓰고 있는 VM에서 따라 하지 마세요.
:::

:::note 검증 범위
**minikube v1.38.1(docker 드라이버·containerd · 노드 이미지 Debian 12, arm64) · Kubernetes v1.37.0 → v1.37.2** 의 임시 프로필에서 이 문서의 명령을 처음부터 순서대로 실행했고, 출력 블록은 그 결과입니다(2026-11-02). 출력의 노드 이름 `hangdo-verify-kubeadm`은 검증용 프로필 이름입니다(여러분은 `kubeadm-lab`). minikube도 내부에서 kubeadm으로 클러스터를 만들지만 **인증서 경로(`/var/lib/minikube/certs`)·바이너리 위치·API 포트(8443)가 표준 kubeadm 설치와 다릅니다** — 차이는 단계마다 적었습니다.

**실행하지 않은 것:** 빈 노드에서의 `kubeadm init`·`kubeadm join`, 컨트롤 플레인 3대 HA 구성, 마이너 업그레이드(1.36 → 1.37), 여러 노드의 순차 업그레이드. 이 부분(7단계)은 공식 문서 기준의 **정적 설명**이며 출력 예시를 싣지 않았습니다.
:::

## 실습 환경 점검

```bash shell="실습 터미널"
minikube start -p kubeadm-lab --driver=docker --container-runtime=containerd --kubernetes-version=v1.37.0 --cpus=2 --memory=4g
kubectl config current-context        # kubeadm-lab
kubectl get nodes
minikube -p kubeadm-lab ssh -- uname -m   # aarch64(애플 실리콘) 또는 x86_64 — 아래 다운로드 주소의 arm64·amd64를 맞춤
```

메모리 4GB·디스크 약 3GB(이미지)를 씁니다. 이후 `minikube -p kubeadm-lab ssh -- '…'`는 노드 컨테이너 안에서 실행됩니다. minikube는 kubeadm을 `PATH`에 두지 않고 `/var/lib/minikube/binaries/v1.37.0/`에 둡니다.

## 1단계: kubeadm이 만든 것 찾기

```bash shell="실습 터미널"
minikube -p kubeadm-lab ssh -- 'sudo ls /etc/kubernetes/manifests; sudo ls /var/lib/minikube/certs | tr "\n" " "; echo'
kubectl -n kube-system get cm kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' | grep -E "kubernetesVersion|controlPlaneEndpoint|certificatesDir|podSubnet|serviceSubnet"
minikube -p kubeadm-lab ssh -- 'sudo grep -E "^\s+- (--|kube-apiserver)" /etc/kubernetes/manifests/kube-apiserver.yaml | head -8'
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · 4단계 업그레이드 뒤 다시 실행)" date="2026-11-02"
etcd.yaml	     kube-controller-manager.yaml
kube-apiserver.yaml  kube-scheduler.yaml
apiserver-etcd-client.crt apiserver-etcd-client.key apiserver-kubelet-client.crt apiserver-kubelet-client.key apiserver.crt apiserver.key ca.crt ca.key etcd front-proxy-ca.crt front-proxy-ca.key front-proxy-client.crt front-proxy-client.key proxy-client-ca.crt proxy-client-ca.key proxy-client.crt proxy-client.key sa.key sa.pub 
certificatesDir: /var/lib/minikube/certs
controlPlaneEndpoint: control-plane.minikube.internal:8443
kubernetesVersion: v1.37.2
  podSubnet: 10.244.0.0/16
  serviceSubnet: 10.96.0.0/12
    - kube-apiserver
    - --advertise-address=192.168.58.2
    - --allow-privileged=true
    - --authorization-mode=Node,RBAC
    - --client-ca-file=/var/lib/minikube/certs/ca.crt
    - --enable-bootstrap-token-auth=true
    - --etcd-cafile=/var/lib/minikube/certs/etcd/ca.crt
    - --etcd-certfile=/var/lib/minikube/certs/apiserver-etcd-client.crt
```

검증에서는 출력 모양을 고친 뒤 이 명령을 업그레이드 뒤에 다시 실행해 `kubernetesVersion: v1.37.2`입니다. 업그레이드 전 첫 실행에서는 `v1.37.0`이었고, 여러분도 지금은 `v1.37.0`이 나옵니다.

- `/etc/kubernetes/manifests/` 4개 파일 = **스태틱 파드**. kubelet이 이 디렉터리를 보고 직접 띄우므로, 파일을 고치면 API 서버를 거치지 않고 파드가 바뀝니다(그래서 업그레이드가 이 파일을 바꿔 끼웁니다).
- 표준 kubeadm은 인증서를 `/etc/kubernetes/pki`에 둡니다. minikube는 `certificatesDir`를 바꿔 둡니다 — 그래서 아래 명령에 `--cert-dir`를 붙입니다.
- `kubeadm-config` ConfigMap은 `init` 때 쓴 설정이며 `upgrade`가 읽습니다. `controlPlaneEndpoint`는 HA에서 로드밸런서 주소가 들어가는 자리입니다.
- `--enable-bootstrap-token-auth=true`가 있어야 2단계의 부트스트랩 토큰으로 `join`할 수 있습니다.

## 2단계: 인증서 만료 확인

```bash shell="실습 터미널"
minikube -p kubeadm-lab ssh -- 'sudo /var/lib/minikube/binaries/v1.37.0/kubeadm certs check-expiration --cert-dir /var/lib/minikube/certs --kubeconfig /etc/kubernetes/admin.conf'
```

```output kind=verified env="검증 환경 (kubeadm v1.37.0, 클러스터 생성 직후)" date="2026-11-02"
[check-expiration] Reading configuration from the "kubeadm-config" ConfigMap in namespace "kube-system"...
[check-expiration] Use 'kubeadm init phase upload-config kubeadm --config your-config-file' to re-upload it.

CERTIFICATE                EXPIRES                  RESIDUAL TIME   CERTIFICATE AUTHORITY   EXTERNALLY MANAGED
admin.conf                 Nov 02, 2027 13:55 UTC   364d            ca                      no      
apiserver                  Nov 01, 2029 13:55 UTC   2y364d          ca                      no      
apiserver-etcd-client      Nov 02, 2027 13:55 UTC   364d            etcd-ca                 no      
apiserver-kubelet-client   Nov 02, 2027 13:55 UTC   364d            ca                      no      
controller-manager.conf    Nov 02, 2027 13:55 UTC   364d            ca                      no      
etcd-healthcheck-client    Nov 02, 2027 13:55 UTC   364d            etcd-ca                 no      
etcd-peer                  Nov 02, 2027 13:55 UTC   364d            etcd-ca                 no      
etcd-server                Nov 02, 2027 13:55 UTC   364d            etcd-ca                 no      
front-proxy-client         Nov 02, 2027 13:55 UTC   364d            front-proxy-ca          no      
scheduler.conf             Nov 02, 2027 13:55 UTC   364d            ca                      no      
super-admin.conf           Nov 02, 2027 13:55 UTC   364d            ca                      no      

CERTIFICATE AUTHORITY   EXPIRES                  RESIDUAL TIME   EXTERNALLY MANAGED
ca                      Oct 30, 2036 13:16 UTC   9y              no      
etcd-ca                 Oct 30, 2036 13:55 UTC   9y              no      
front-proxy-ca          Oct 30, 2036 13:55 UTC   9y              no      
```

컴포넌트 인증서는 1년, CA는 10년입니다. `apiserver`만 2년 364일인 것은 minikube가 이 인증서를 직접 만들기 때문입니다(minikube `--cert-expiration` 기본 3년, 표준 kubeadm이면 다른 것과 같이 1년). `ca`의 시각이 다른 것과 다른 것도 minikube가 CA를 프로필 사이에 재사용하기 때문입니다. 날짜는 여러분이 클러스터를 만든 시각이 됩니다. 4단계 뒤 다시 보면 달라집니다.

## 3단계: 부트스트랩 토큰과 join 명령

```bash shell="실습 터미널"
minikube -p kubeadm-lab ssh -- '
K="sudo /var/lib/minikube/binaries/v1.37.0/kubeadm"; KC="--kubeconfig /etc/kubernetes/admin.conf"
T=$($K token create --ttl 10m $KC); echo created ${T%%.*}.****
$K token list $KC | sed -E "s/\.[a-z0-9]{16}/.****************/"
$K token delete ${T%%.*} $KC
$K token create --ttl 5m --print-join-command $KC | sed -E "s/--token [^ ]+/--token <****>/; s/sha256:[0-9a-f]+/sha256:<****>/"'
```

```output kind=verified env="검증 환경 (kubeadm v1.37.0)" date="2026-11-02"
created 0few4t.****
TOKEN                     TTL         EXPIRES                USAGES                   DESCRIPTION                                                EXTRA GROUPS
0few4t.****************   9m          2026-11-02T14:05:41Z   authentication,signing   <none>                                                     system:bootstrappers:kubeadm:default-node-token
vckvrb.****************   23h         2026-11-03T13:55:38Z   authentication,signing   <none>                                                     system:bootstrappers:kubeadm:default-node-token
bootstrap token "0few4t" deleted
kubeadm join control-plane.minikube.internal:8443 --token <****> --discovery-token-ca-cert-hash sha256:<****> 
```

- 토큰은 `<id>.<secret>` 모양이고, 비밀 부분은 **노드를 붙일 수 있는 자격 증명**이라 가렸습니다. `vckvrb`(TTL 23h)는 클러스터를 만들 때 생긴 기본 24시간 토큰입니다.
- `--discovery-token-ca-cert-hash`는 **CA 공개키의 sha256** 입니다. 새 노드는 이 값으로 「내가 붙는 API 서버가 진짜 이 클러스터」인지 확인합니다. 토큰만으로 붙으면(`--discovery-token-unsafe-skip-ca-verification`) 가짜 API 서버에 붙을 수 있습니다.
- 실습이 끝나면 만든 토큰을 지웁니다: `kubeadm token list`에서 TTL이 분 단위인 것을 `token delete`.

## 4단계: 컨트롤 플레인 업그레이드 (v1.37.0 → v1.37.2)

먼저 **지금 kubeadm**으로 계획을 봅니다.

```bash shell="실습 터미널"
minikube -p kubeadm-lab ssh -- 'sudo /var/lib/minikube/binaries/v1.37.0/kubeadm upgrade plan --kubeconfig /etc/kubernetes/admin.conf 2>&1 | sed -n "/Cluster version/,/update kubeadm/p"'
```

```output kind=verified env="검증 환경 (kubeadm v1.37.0)" date="2026-11-02"
[upgrade/versions] Cluster version: 1.37.0
[upgrade/versions] kubeadm version: v1.37.0
[upgrade/versions] Target version: v1.37.2
[upgrade/versions] Latest version in the v1.37 series: v1.37.2

Components that must be upgraded manually after you have upgraded the control plane with 'kubeadm upgrade apply':
COMPONENT   NODE                    CURRENT   TARGET
kubelet     hangdo-verify-kubeadm   v1.37.0   v1.37.2

Upgrade to the latest version in the v1.37 series:

COMPONENT                 NODE                    CURRENT   TARGET
kube-apiserver            hangdo-verify-kubeadm   v1.37.0   v1.37.2
kube-controller-manager   hangdo-verify-kubeadm   v1.37.0   v1.37.2
kube-scheduler            hangdo-verify-kubeadm   v1.37.0   v1.37.2
kube-proxy                                        1.37.0    v1.37.2
CoreDNS                                           v1.14.6   v1.14.6
etcd                      hangdo-verify-kubeadm   3.7.0-0   3.7.0-0

You can now apply the upgrade by executing the following command:

	kubeadm upgrade apply v1.37.2

Note: Before you can perform this upgrade, you have to update kubeadm to v1.37.2.
```

계획이 말하는 순서 그대로: **kubeadm 먼저** 올리고, 컨트롤 플레인, 그다음 kubelet(수동). 목표 버전은 계획을 실행한 날의 최신 패치라 여러분은 다를 수 있습니다 — 아래 명령의 `v1.37.2`를 계획에 나온 값으로 바꿉니다.

새 kubeadm은 공식 주소(`dl.k8s.io`)에서 받고 **같은 곳의 sha256과 대조**합니다. 노드의 `/tmp`는 `noexec`라 실행 파일을 `/opt/up`에 둡니다.

```bash shell="실습 터미널"
minikube -p kubeadm-lab ssh -- 'set -e; ARCH=$(dpkg --print-architecture); sudo mkdir -p /opt/up && cd /opt/up
sudo curl -fsSLO https://dl.k8s.io/release/v1.37.2/bin/linux/$ARCH/kubeadm
sudo curl -fsSLO https://dl.k8s.io/release/v1.37.2/bin/linux/$ARCH/kubeadm.sha256
echo "$(cat kubeadm.sha256)  kubeadm" | sha256sum --check
sudo chmod +x kubeadm && ./kubeadm version -o short'
```

```output kind=verified env="검증 환경 (arm64 노드)" date="2026-11-02"
kubeadm: OK
v1.37.2
```

`kubeadm: OK`가 아니면 멈춥니다. 이제 적용합니다. minikube는 kubelet도 `PATH`에 두지 않아 preflight가 `couldn't get kubelet version: … executable file not found in $PATH`로 실패하므로(검증 중 실제로 겪음) 경로를 붙여 줍니다 — 표준 설치에서는 필요 없는 부분입니다.

```bash shell="실습 터미널"
minikube -p kubeadm-lab ssh -- 'cd /opt/up && sudo env PATH=/var/lib/minikube/binaries/v1.37.0:$PATH ./kubeadm upgrade apply v1.37.2 --yes --kubeconfig /etc/kubernetes/admin.conf' 2>&1 | grep -vE "^\s*$" | grep -E "preflight\]|versions\]|Renewing|upgraded successfully|backing up|SUCCESS|proceed"
```

```output kind=verified env="검증 환경 (kubeadm v1.37.2 · 약 2분)" date="2026-11-02"
[upgrade/preflight] Running preflight checks
[upgrade/preflight] You have chosen to upgrade the cluster version to "v1.37.2"
[upgrade/versions] Cluster version: v1.37.0
[upgrade/versions] kubeadm version: v1.37.2
[upgrade/preflight] Pulling images required for setting up a Kubernetes cluster
[upgrade/preflight] This might take a minute or two, depending on the speed of your internet connection
[upgrade/preflight] You can also perform this action beforehand using 'kubeadm config images pull'
[upgrade/staticpods] Renewing etcd-server certificate
[upgrade/staticpods] Renewing etcd-peer certificate
[upgrade/staticpods] Renewing etcd-healthcheck-client certificate
[upgrade/staticpods] Restarting the etcd static pod and backing up its manifest to "/etc/kubernetes/tmp/kubeadm-backup-manifests-2026-11-02-13-56-45/etcd.yaml"
[upgrade/staticpods] Component "etcd" upgraded successfully!
[upgrade/staticpods] Renewing apiserver certificate
[upgrade/staticpods] Renewing apiserver-kubelet-client certificate
[upgrade/staticpods] Renewing front-proxy-client certificate
[upgrade/staticpods] Renewing apiserver-etcd-client certificate
[upgrade/staticpods] Moving new manifest to "/etc/kubernetes/manifests/kube-apiserver.yaml" and backing up old manifest to "/etc/kubernetes/tmp/kubeadm-backup-manifests-2026-11-02-13-56-45/kube-apiserver.yaml"
[upgrade/staticpods] Component "kube-apiserver" upgraded successfully!
[upgrade/staticpods] Renewing controller-manager.conf certificate
[upgrade/staticpods] Moving new manifest to "/etc/kubernetes/manifests/kube-controller-manager.yaml" and backing up old manifest to "/etc/kubernetes/tmp/kubeadm-backup-manifests-2026-11-02-13-56-45/kube-controller-manager.yaml"
[upgrade/staticpods] Component "kube-controller-manager" upgraded successfully!
[upgrade/staticpods] Renewing scheduler.conf certificate
[upgrade/staticpods] Moving new manifest to "/etc/kubernetes/manifests/kube-scheduler.yaml" and backing up old manifest to "/etc/kubernetes/tmp/kubeadm-backup-manifests-2026-11-02-13-56-45/kube-scheduler.yaml"
[upgrade/staticpods] Component "kube-scheduler" upgraded successfully!
[upgrade] SUCCESS! A control plane node of your cluster was upgraded to "v1.37.2".
[upgrade] Now please proceed with upgrading the rest of the nodes by following the right order.
```

출력은 전체 로그에서 단계 줄만 고른 것입니다(전체는 50여 줄: kubeconfig 갱신, kubelet 설정, 부트스트랩 토큰 RBAC, CoreDNS·kube-proxy 애드온 포함). 컴포넌트마다 **옛 매니페스트를 `/etc/kubernetes/tmp/kubeadm-backup-manifests-…`에 백업**하고 새 매니페스트로 바꿔 kubelet이 다시 띄우기를 기다립니다. 같은 때 **인증서도 갱신**합니다.

```bash shell="실습 터미널"
kubectl version | tail -1
kubectl get nodes
kubectl -n kube-system get pods -o 'custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image' | grep -E "apiserver|scheduler|controller|proxy|etcd|coredns"
```

```output kind=verified env="검증 환경 (upgrade apply 직후)" date="2026-11-02"
Server Version: v1.37.2
NAME                    STATUS   ROLES           AGE     VERSION
hangdo-verify-kubeadm   Ready    control-plane   2m46s   v1.37.0
coredns-559f6c778d-ghclk                        registry.k8s.io/coredns/coredns:v1.14.6
etcd-hangdo-verify-kubeadm                      registry.k8s.io/etcd:3.7.0-0
kube-apiserver-hangdo-verify-kubeadm            registry.k8s.io/kube-apiserver:v1.37.2
kube-controller-manager-hangdo-verify-kubeadm   registry.k8s.io/kube-controller-manager:v1.37.2
kube-proxy-fr7bd                                registry.k8s.io/kube-proxy:v1.37.2
kube-scheduler-hangdo-verify-kubeadm            registry.k8s.io/kube-scheduler:v1.37.2
```

**API 서버는 v1.37.2인데 노드 VERSION은 아직 v1.37.0** 입니다. `kubectl get nodes`의 VERSION은 **kubelet** 버전이고, kubelet은 `upgrade apply`가 바꾸지 않습니다.

## 5단계: drain → kubelet → uncordon

```bash shell="실습 터미널"
kubectl drain kubeadm-lab --ignore-daemonsets --delete-emptydir-data --timeout=120s 2>&1 | tail -4
```

```output kind=verified env="검증 환경 (minikube 단일 노드)" date="2026-11-02"
error: unable to drain node "hangdo-verify-kubeadm" due to error: cannot delete Pods that declare no controller (use --force to override): kube-system/storage-provisioner, continuing command...
There are pending nodes to be drained:
 hangdo-verify-kubeadm
cannot delete Pods that declare no controller (use --force to override): kube-system/storage-provisioner
```

drain은 **컨트롤러가 없는 파드**(다시 만들어 줄 주인이 없는 파드)를 지우지 않고 멈춥니다. minikube의 `storage-provisioner`가 그런 파드입니다. 노드는 이미 cordon(새 파드 배치 금지)된 상태입니다. 운영이라면 그 파드가 무엇인지 확인하고 `--force`(그 파드는 사라짐) 여부를 결정합니다. 이 실습은 단일 노드라 옮겨 갈 곳도 없으므로 cordon만 된 상태로 진행합니다.

```bash shell="실습 터미널"
minikube -p kubeadm-lab ssh -- 'set -e; ARCH=$(dpkg --print-architecture); cd /opt/up
sudo curl -fsSLO https://dl.k8s.io/release/v1.37.2/bin/linux/$ARCH/kubelet
sudo curl -fsSLO https://dl.k8s.io/release/v1.37.2/bin/linux/$ARCH/kubelet.sha256
echo "$(cat kubelet.sha256)  kubelet" | sha256sum --check
systemctl cat kubelet | grep -m1 "^ExecStart=/"
sudo systemctl stop kubelet
sudo install -m 0755 kubelet /var/lib/minikube/binaries/v1.37.0/kubelet
sudo systemctl daemon-reload && sudo systemctl start kubelet
sleep 3; systemctl is-active kubelet; /var/lib/minikube/binaries/v1.37.0/kubelet --version'
sleep 20; kubectl uncordon kubeadm-lab; kubectl get nodes
```

```output kind=verified env="검증 환경 (kubelet v1.37.2)" date="2026-11-02"
kubelet: OK
ExecStart=/var/lib/minikube/binaries/v1.37.0/kubelet
active
Kubernetes v1.37.2
node/hangdo-verify-kubeadm uncordoned
NAME                    STATUS   ROLES           AGE     VERSION
hangdo-verify-kubeadm   Ready    control-plane   3m22s   v1.37.2
```

minikube는 kubelet을 `/var/lib/minikube/binaries/<처음 버전>/kubelet`에서 실행하므로 그 파일을 바꿔 끼웠습니다(폴더 이름은 v1.37.0 그대로). **표준 설치에서는** 배포판 패키지로 올립니다: `apt-mark unhold kubelet kubectl && apt-get install -y kubelet='1.37.2-*' kubectl='1.37.2-*' && apt-mark hold kubelet kubectl && systemctl daemon-reload && systemctl restart kubelet`(이 줄은 실행하지 않았습니다).

## 6단계: 업그레이드가 갱신한 인증서

```bash shell="실습 터미널"
minikube -p kubeadm-lab ssh -- 'sudo /var/lib/minikube/binaries/v1.37.0/kubeadm certs check-expiration --cert-dir /var/lib/minikube/certs --kubeconfig /etc/kubernetes/admin.conf 2>&1 | grep -E "^(CERTIFICATE|admin.conf|apiserver |etcd-server|ca )"; sudo ls /etc/kubernetes/tmp'
```

```output kind=verified env="검증 환경 (업그레이드 뒤)" date="2026-11-02"
CERTIFICATE                EXPIRES                  RESIDUAL TIME   CERTIFICATE AUTHORITY   EXTERNALLY MANAGED
admin.conf                 Nov 02, 2027 13:56 UTC   364d            ca                      no      
apiserver                  Nov 02, 2027 13:56 UTC   364d            ca                      no      
etcd-server                Nov 02, 2027 13:56 UTC   364d            etcd-ca                 no      
CERTIFICATE AUTHORITY   EXPIRES                  RESIDUAL TIME   EXTERNALLY MANAGED
ca                      Oct 30, 2036 13:16 UTC   9y              no      
kubeadm-backup-etcd-2026-11-02-13-56-45
kubeadm-backup-manifests-2026-11-02-13-56-45
kubeadm-kubelet-config-2026-11-02-13-58-18
```

만료 시각이 업그레이드 시각(13:56)으로 바뀌었습니다 — 2단계의 `apiserver` 2년 364일도 kubeadm 기준 1년으로 다시 발급됐습니다. CA는 그대로입니다. **1년 안에 한 번은 업그레이드하면 인증서가 자동으로 갱신**되고, 그렇지 않으면 `kubeadm certs renew all`을 직접 해야 합니다. `/etc/kubernetes/tmp`에는 업그레이드 전 etcd 데이터·매니페스트·kubelet 설정 백업이 남습니다(되돌릴 때 씀).

## 7단계: 실행하지 않은 부분 — init·join·HA·마이너 업그레이드

아래는 공식 문서 기준의 순서이며, **이 실습에서 실행하지 않았고 출력도 싣지 않습니다.** 직접 해 보려면 VM 3~5대(또는 클라우드 인스턴스)가 필요합니다.

```bash shell="참고 (실행하지 않음)" run=skip
# 첫 컨트롤 플레인 (HA면 앞에 로드밸런서 주소를 먼저 준비)
sudo kubeadm init --control-plane-endpoint "<LB 주소>:6443" --upload-certs --pod-network-cidr 10.244.0.0/16
# 추가 컨트롤 플레인 (init 출력의 --certificate-key 포함 명령)
sudo kubeadm join <LB 주소>:6443 --token … --discovery-token-ca-cert-hash sha256:… --control-plane --certificate-key …
# 워커
sudo kubeadm join <LB 주소>:6443 --token … --discovery-token-ca-cert-hash sha256:…
# 마이너 업그레이드: 첫 컨트롤 플레인은 upgrade apply, 나머지 컨트롤 플레인·워커는 노드마다
sudo kubeadm upgrade node
```

| 다룬 범위 | 이 실습 | 확인 방법 |
|---|---|---|
| 인증서·매니페스트·kubeadm-config 위치, 토큰, `upgrade plan` | 실행 | 1~3단계 |
| 패치 업그레이드(컨트롤 플레인 → kubelet), drain이 막히는 경우, 인증서 갱신 | 실행 (단일 노드) | 4~6단계 |
| 빈 노드 init, 워커·컨트롤 플레인 join, HA(로드밸런서·stacked etcd) | **정적** | [[kubeadm|클러스터 구축]] · 공식 문서 |
| 마이너 업그레이드, 여러 노드 순차 업그레이드 | **정적** | 공식 문서 「Upgrading kubeadm clusters」 |

## 흔한 오류

| 증상 | 원인 | 확인·해결 |
|---|---|---|
| `./kubeadm: Permission denied` | `/tmp`가 `noexec`로 마운트됨 (minikube 노드) | 실행 파일은 `/opt/…`처럼 실행 가능한 곳에 |
| `couldn't get kubelet version: … not found in $PATH` | kubelet이 `PATH`에 없음 (minikube) | `sudo env PATH=/var/lib/minikube/binaries/<버전>:$PATH …` |
| `sha256sum: WARNING: 1 computed checksum did NOT match` | 받은 파일이 다름(중간 손상·다른 아키텍처) | 지우고 다시 받기, `dpkg --print-architecture` 확인 |
| `Specified version to upgrade to "v…" is higher than the kubeadm version` | 새 kubeadm을 안 받고 옛 kubeadm으로 apply | 4단계의 `/opt/up/kubeadm`으로 실행 |
| 마이너 두 단계 건너뛰기 실패 | kubeadm은 한 번에 마이너 하나씩 | 1.35 → 1.36 → 1.37 |
| `cannot delete Pods that declare no controller` | 주인 없는 파드 | 파드를 확인하고 `--force` 여부 결정 |
| `cannot evict pod as it would violate the pod's disruption budget` | PodDisruptionBudget | 레플리카를 늘리거나 기다림 — PDB를 끄지 않음 |
| 노드 VERSION이 안 바뀜 | kubelet을 안 올림 (`upgrade apply`는 kubelet을 바꾸지 않음) | 5단계 |
| 1년 뒤 `x509: certificate has expired or is not yet valid` | 업그레이드·갱신 없이 1년 | `kubeadm certs renew all` 후 컨트롤 플레인 재시작 |

## 성공 판정

```verify
id: kubeadm-upgraded
title: 컨트롤 플레인과 kubelet이 모두 목표 패치 버전
explain: 5단계 뒤 실행합니다. API 서버 버전과 노드(kubelet) 버전을 나란히 출력합니다.
command: echo "$(kubectl version -o json | jq -r .serverVersion.gitVersion) $(kubectl get node kubeadm-lab -o jsonpath='{.status.nodeInfo.kubeletVersion}')"
expect: ^v1\.37\.([1-9][0-9]*) v1\.37\.\1$
criteria: 「v1.37.2 v1.37.2」처럼 두 값이 같고 v1.37.0이 아님
```

```verify
id: kubeadm-node-schedulable
title: uncordon까지 마쳐 노드에 다시 파드를 놓을 수 있음
explain: cordon이 남아 있으면 true가 나옵니다.
command: kubectl get node kubeadm-lab -o jsonpath='{.spec.unschedulable}{"|"}{.status.conditions[?(@.type=="Ready")].status}'
expect: ^\|True$
criteria: |True (unschedulable 값이 비어 있고 Ready가 True)
```

## 정리

```bash shell="실습 터미널" run=skip
minikube delete -p kubeadm-lab           # 이 실습용 프로필만 지움 (k8s-lab은 그대로)
kubectl config use-context k8s-lab
minikube profile list
```

검증에서는 임시 프로필을 통째로 지우고, 평소 kubectl 컨텍스트가 원래대로인 것을 확인했습니다.

## 체크리스트

- [ ] 스태틱 파드 매니페스트·인증서·kubeadm-config의 위치와 역할을 말할 수 있다
- [ ] 부트스트랩 토큰과 CA 해시가 join에서 각각 무엇을 보증하는지 말할 수 있다
- [ ] kubeadm을 먼저 올리고(체크섬 확인) `upgrade plan` → `apply`를 했다
- [ ] `upgrade apply` 뒤에도 노드 VERSION이 그대로인 이유(kubelet)를 설명할 수 있다
- [ ] drain이 멈추는 경우(주인 없는 파드·PDB)를 하나 이상 겪거나 설명할 수 있다
- [ ] 업그레이드가 인증서를 갱신한다는 것을 만료 시각으로 확인했다
- [ ] init·join·HA·마이너 업그레이드는 이 실습에서 실행하지 않았다는 것을 안다
