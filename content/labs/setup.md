## 학습 목표

- 내 PC에 Docker, [[minikube]], [[kubectl]]을 설치합니다.
- 모든 실습에서 쓸 전용 클러스터 `k8s-lab`을 만들고 정상 동작을 확인합니다.
- 클러스터를 멈추고, 다시 켜고, 버전을 바꾸고, 지우는 방법을 익힙니다.

## 선수 지식과 준비물

- 터미널에서 명령을 붙여 넣고 실행할 수 있으면 됩니다.
- **하드웨어**: CPU 2개 이상, 여유 메모리 4GB 이상 권장(minikube 최소 요구는 2GB), 디스크 여유 20GB 이상
- **인터넷 연결**: 처음 클러스터를 만들 때 이미지 수백 MB를 내려받습니다.

:::note 명령어 블록 읽는 법
모든 코드 블록 위에는 **어느 셸에서 실행하는지** 적혀 있습니다. 예를 들어 「bash · WSL2 Ubuntu 셸」이면 Windows PowerShell이 아니라 WSL 안의 Ubuntu 터미널에서 실행합니다. 「예시 출력」으로 표시된 블록은 실제 실행 결과가 아니라 모양을 보여 주는 예시이며, 이름 접미사·IP·시간 값은 환경마다 다릅니다.
:::

## 왜 minikube이고, 왜 전용 프로필인가

[[minikube]]는 내 PC 안에 단일 노드 Kubernetes 클러스터를 만들어 주는 **외부 생태계 도구**입니다. Kubernetes 자체가 아니라 Kubernetes를 손쉽게 띄우는 도구라는 점을 구분해 두세요. 이 사이트는 모든 실습을 minikube v1.39.0(2026-09-01 출시)의 docker 드라이버로 통일합니다. 같은 도구와 같은 버전을 쓰면 예상 결과를 정확하게 안내할 수 있기 때문입니다.

`-p k8s-lab`처럼 **프로필 이름을 붙여 실습 전용 클러스터**를 만듭니다. 이미 다른 클러스터(회사 개발 클러스터, 다른 minikube)를 쓰고 있어도 섞이지 않고, 실습이 끝나면 이 프로필만 지우면 됩니다.

:::warn 실습은 반드시 전용 환경에서
실습에는 네임스페이스 삭제 같은 명령이 나옵니다. 각 삭제 명령은 해당 실습에서 만든 자원으로 범위를 한정했지만, kubectl이 **다른 클러스터를 가리키고 있으면** 엉뚱한 곳에 실행될 수 있습니다. 실습을 시작할 때마다 `kubectl config current-context`가 `k8s-lab`인지 확인하세요.
:::

## 운영체제별 설치

자신의 운영체제 절만 따라 하면 됩니다. 버전은 이 사이트가 검증 기준으로 삼는 값으로 고정했습니다.

| 도구 | 고정 버전 | 구분 |
|---|---|---|
| minikube | v1.39.0 | 외부 생태계 도구 |
| kubectl | v1.37.1 | Kubernetes 공식 CLI (클러스터와 마이너 1 이내) |
| Kubernetes (클러스터) | v1.37.0 / v1.36.4 / v1.35.8 | minikube v1.39.0이 지원하는 각 마이너의 최신 패치 |
| Docker | Docker Engine 또는 Docker Desktop 최신 안정판 | minikube 드라이버 |

### Windows: WSL2

Windows에서는 **WSL2 안의 Ubuntu**에서 모든 실습을 진행합니다. Windows용 minikube·kubectl을 따로 설치하지 않습니다.

**1. WSL2와 Ubuntu 설치** — 관리자 권한 PowerShell에서 실행합니다.

```powershell shell="Windows PowerShell (관리자)"
wsl --install -d Ubuntu-24.04
wsl -l -v
```

`wsl -l -v` 출력의 VERSION 열이 `2`인지 확인합니다. 1이면 `wsl --set-version Ubuntu-24.04 2`로 바꿉니다. 설치 후 시작 메뉴에서 「Ubuntu 24.04」를 열면 이후 명령을 실행할 WSL2 Ubuntu 셸이 열립니다.

**2. Docker 준비** — 둘 중 하나를 고릅니다.

- **Docker Desktop for Windows**를 설치하고 Settings → Resources → WSL integration에서 Ubuntu-24.04를 켭니다.
- 또는 WSL Ubuntu 안에 Docker Engine을 직접 설치합니다(아래 Linux 절의 Docker 설치와 같음).

```bash shell="WSL2 Ubuntu 셸"
docker version
docker run --rm hello-world
```

**3. cgroup v2 확인** — Kubernetes 1.35부터 kubelet은 cgroup v1 노드에서 기본적으로 시작하지 않습니다.

```bash shell="WSL2 Ubuntu 셸"
stat -fc %T /sys/fs/cgroup/
```

`cgroup2fs`가 나오면 그대로 진행합니다. `tmpfs`가 나오면 cgroup v1 또는 혼합 모드입니다. 아래 「흔한 오류」의 cgroup 항목을 먼저 해결하세요.

**4. minikube와 kubectl 설치** — WSL2 Ubuntu 셸에서 아래 「Linux」 절의 4·5단계를 그대로 실행합니다(x86-64 기준).

:::note WSL2에서 서비스에 접속할 때
docker 드라이버를 쓰면 minikube 노드가 컨테이너 안에서 실행되므로 `minikube ip`로 나온 주소에 Windows 브라우저로 바로 접속할 수 없습니다. NodePort 서비스는 `minikube service <이름> --url -p k8s-lab`, 그 밖에는 `kubectl port-forward`를 씁니다. 실습에서는 클러스터 안의 테스트 파드로 확인하므로 이 차이가 문제 되지 않습니다.
:::

### macOS

**1. Docker Desktop 설치** — docker.com에서 Apple Silicon 또는 Intel용 Docker Desktop을 설치하고 실행합니다. Settings → Resources에서 메모리를 4GB 이상으로 둡니다.

```bash shell="macOS 터미널 (zsh)"
docker version
docker run --rm hello-world
```

**2. minikube 설치** — Apple Silicon 기준입니다. Intel Mac은 `darwin-arm64`를 `darwin-amd64`로 바꿉니다.

```bash shell="macOS 터미널 (zsh)"
curl -LO https://github.com/kubernetes/minikube/releases/download/v1.39.0/minikube-darwin-arm64
sudo install minikube-darwin-arm64 /usr/local/bin/minikube && rm minikube-darwin-arm64
minikube version
```

Homebrew(`brew install minikube`)도 됩니다. 다만 그 시점의 최신 버전이 설치되므로 이 사이트의 예상 출력과 조금 다를 수 있습니다.

**3. kubectl 설치** — 공식 문서의 방법으로 v1.37.1을 설치하고 체크섬을 검증합니다.

```bash shell="macOS 터미널 (zsh)"
curl -LO "https://dl.k8s.io/release/v1.37.1/bin/darwin/arm64/kubectl"
curl -LO "https://dl.k8s.io/release/v1.37.1/bin/darwin/arm64/kubectl.sha256"
echo "$(cat kubectl.sha256)  kubectl" | shasum -a 256 --check
chmod +x ./kubectl
sudo mv ./kubectl /usr/local/bin/kubectl
sudo chown root: /usr/local/bin/kubectl
rm kubectl.sha256
kubectl version --client
```

체크섬 검증이 `kubectl: OK`로 끝나야 합니다. Docker Desktop의 Linux VM은 cgroup v2를 쓰므로 macOS에서는 cgroup 확인이 필요 없습니다.

### Linux (Ubuntu·Debian 계열 x86-64)

**1. Docker Engine 설치** — docs.docker.com의 「Install Docker Engine」 안내를 따른 뒤, sudo 없이 docker를 쓰도록 그룹에 추가합니다.

```bash shell="Linux 터미널 (bash)"
sudo usermod -aG docker $USER
newgrp docker
docker version
docker run --rm hello-world
```

**2. cgroup v2 확인**

```bash shell="Linux 터미널 (bash)"
stat -fc %T /sys/fs/cgroup/
```

`cgroup2fs`면 됩니다. Ubuntu 22.04 이후, Debian 12 이후, Fedora 31 이후는 기본이 cgroup v2입니다.

**3. 자원 확인**

```bash shell="Linux 터미널 (bash)"
nproc
free -h
df -h ~
```

**4. minikube 설치** — ARM64 장비는 `linux-amd64`를 `linux-arm64`로 바꿉니다.

```bash shell="Linux 터미널 (bash)"
curl -LO https://github.com/kubernetes/minikube/releases/download/v1.39.0/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube && rm minikube-linux-amd64
minikube version
```

**5. kubectl 설치**

```bash shell="Linux 터미널 (bash)"
curl -LO "https://dl.k8s.io/release/v1.37.1/bin/linux/amd64/kubectl"
curl -LO "https://dl.k8s.io/release/v1.37.1/bin/linux/amd64/kubectl.sha256"
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm kubectl kubectl.sha256
kubectl version --client
```

```output kind=example
kubectl: OK
Client Version: v1.37.1
Kustomize Version: v5.8.1
```

:::note 설치한 바이너리가 맞는지
`kubectl`·`minikube`가 여러 곳에 깔려 있으면 예전 것이 먼저 실행될 수 있습니다. `type -a kubectl`로 후보를, `uname -m`과 `file -L "$(command -v kubectl)"`로 아키텍처(amd64·arm64)가 맞는지 확인합니다. 체크섬·서명의 의미와 전체 점검표는 [리눅스 「환경 변수·PATH·셸 설정 파일」 개념 6](/linux/#/item/b-env)에 있습니다.
:::

## 실습 클러스터 만들기

여기서부터는 운영체제와 관계없이 같습니다. Windows 사용자는 WSL2 Ubuntu 셸에서 실행합니다.

```bash shell="실습 터미널 (WSL2 Ubuntu 셸 · macOS 터미널 · Linux 터미널)"
minikube start -p k8s-lab --driver=docker --kubernetes-version=v1.37.0 --cpus=2 --memory=4096
```

| 옵션 | 의미 |
|---|---|
| `-p k8s-lab` | 프로필(클러스터) 이름. kubectl 컨텍스트 이름도 `k8s-lab`이 됩니다. |
| `--driver=docker` | 노드를 Docker 컨테이너로 실행합니다. |
| `--kubernetes-version=v1.37.0` | 클러스터 버전. 1.36은 `v1.36.4`, 1.35는 `v1.35.8`을 씁니다. |
| `--cpus=2 --memory=4096` | 노드 컨테이너에 줄 CPU 수와 메모리(MB). HPA 실습까지 고려한 값입니다. |

처음 실행하면 노드 이미지와 Kubernetes 구성 요소를 내려받느라 수 분이 걸립니다.

```output kind=example
😄  [k8s-lab] minikube v1.39.0 on Ubuntu 24.04
✨  Using the docker driver based on user configuration
👍  Starting "k8s-lab" primary control-plane node in "k8s-lab" cluster
🔥  Creating docker container (CPUs=2, Memory=4096MB) ...
🐳  Preparing Kubernetes v1.37.0 on containerd ...
🔎  Verifying Kubernetes components...
🌟  Enabled addons: storage-provisioner, default-storageclass
🏄  Done! kubectl is now configured to use "k8s-lab" cluster and "default" namespace by default
```

## 결과 확인

```bash shell="실습 터미널"
minikube status -p k8s-lab
kubectl config current-context
kubectl version
kubectl get nodes
```

```output kind=example
k8s-lab
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured

k8s-lab
Client Version: v1.37.1
Kustomize Version: v5.8.1
Server Version: v1.37.0
NAME      STATUS   ROLES           AGE   VERSION
k8s-lab   Ready    control-plane   2m    v1.37.0
```

확인 기준은 세 가지입니다. 현재 컨텍스트가 `k8s-lab`이고, Server Version이 선택한 버전이며, 노드 STATUS가 `Ready`여야 합니다.

```verify
id: setup-node
title: 실습 클러스터 준비 완료
explain: 노드 이름, Ready 상태, kubelet 버전을 한 줄로 출력합니다.
command: kubectl get nodes -o jsonpath='{.items[0].metadata.name} {.items[0].status.conditions[?(@.type=="Ready")].status} {.items[0].status.nodeInfo.kubeletVersion}{"\n"}'
expect: ^k8s-lab True v1\.3[5-7]\.\d+$
criteria: 「k8s-lab True v1.37.0」처럼 노드 이름 k8s-lab, 상태 True, 버전 v1.35~v1.37
```

## 날마다 쓰는 명령

```bash shell="실습 터미널"
# 실습을 마칠 때: 클러스터를 멈춰 CPU·메모리를 돌려받습니다 (데이터는 유지)
minikube stop -p k8s-lab

# 다시 시작할 때
minikube start -p k8s-lab

# kubectl이 다른 클러스터를 가리키고 있다면 되돌립니다
kubectl config use-context k8s-lab
```

### 다른 Kubernetes 버전으로 학습하기

상단의 「Kubernetes」 선택을 1.36이나 1.35로 바꾸면, 해당 버전에서 쓸 수 없는 실습에 이유가 표시됩니다. 클러스터 버전을 바꾸려면 프로필을 지우고 다시 만듭니다. **클러스터 안의 모든 실습 자원이 사라집니다.**

```bash shell="실습 터미널"
minikube delete -p k8s-lab
minikube start -p k8s-lab --driver=docker --kubernetes-version=v1.36.4 --cpus=2 --memory=4096
```

kubectl v1.37.1은 버전 차이 정책에 따라 1.36·1.38 클러스터와 함께 쓸 수 있습니다. 1.35 클러스터는 마이너 2 차이라 지원 범위 밖이므로, 1.35로 학습할 때는 kubectl v1.35.9 또는 v1.36.5를 설치하거나 minikube에 포함된 kubectl을 씁니다.

```bash shell="실습 터미널"
# 클러스터 버전과 같은 kubectl을 minikube가 내려받아 실행합니다
minikube -p k8s-lab kubectl -- version
```

## 흔한 오류, 진단 순서, 해결 방법

진단은 항상 **도구 → Docker → minikube → kubectl 연결** 순서로 좁혀 갑니다.

| 증상 | 확인 명령 | 원인과 해결 |
|---|---|---|
| `Cannot connect to the Docker daemon` | `docker ps` | Docker Desktop이 꺼져 있거나 WSL integration이 꺼져 있습니다. Docker를 실행하고 해당 배포판의 integration을 켭니다. Linux는 `sudo systemctl start docker`. |
| `permission denied ... docker.sock` | `groups` | 현재 사용자가 docker 그룹에 없습니다. `sudo usermod -aG docker $USER` 후 다시 로그인합니다. |
| `Exiting due to RSRC_INSUFFICIENT_SYS_MEMORY` 등 자원 부족 | `docker info \| grep -i memory` | Docker에 배정된 메모리가 부족합니다. Docker Desktop 설정에서 늘리거나 `--memory=3072`로 줄여 시작합니다. |
| 노드가 `NotReady`이고 kubelet이 계속 재시작 | `minikube logs -p k8s-lab \| grep -i cgroup` | 호스트가 cgroup v1입니다. 1.35부터 kubelet 기본값이 cgroup v1에서 실패하도록 바뀌었습니다. 호스트를 cgroup v2로 전환하세요. WSL2는 `%UserProfile%\.wslconfig`의 `[wsl2]` 절에 `kernelCommandLine = cgroup_no_v1=all`을 넣고 `wsl --shutdown` 후 다시 엽니다(WSL 버전에 따라 이미 기본이 v2일 수 있음). |
| `The connection to the server ... was refused` | `minikube status -p k8s-lab` | 클러스터가 멈춰 있습니다. `minikube start -p k8s-lab`. |
| 엉뚱한 클러스터 정보가 나옴 | `kubectl config get-contexts` | 컨텍스트가 바뀌었습니다. `kubectl config use-context k8s-lab`. |
| `kubectl version`에 skew 경고 | `kubectl version` | 클라이언트와 서버 차이가 마이너 1을 넘습니다. 위 「다른 Kubernetes 버전으로 학습하기」를 참고합니다. |

그래도 해결되지 않으면 `minikube start -p k8s-lab --alsologtostderr -v=3` 출력의 마지막 오류와 `minikube logs -p k8s-lab`를 함께 확인합니다.

## 정리와 재실행

모든 과정을 마쳤거나 처음부터 다시 하고 싶을 때만 실행합니다. 이 명령은 `k8s-lab` 프로필만 지우며 다른 minikube 프로필은 건드리지 않습니다.

```bash shell="실습 터미널"
minikube delete -p k8s-lab
minikube profile list
```

다시 만들 때는 「실습 클러스터 만들기」부터 반복합니다. 고급 과정의 NetworkPolicy 실습은 별도 프로필 `k8s-lab-calico`를 쓰며, 만드는 방법은 그 실습에서 안내합니다.
