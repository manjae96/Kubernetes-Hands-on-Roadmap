## 학습 목표

- Kubespray가 kubeadm 위에서 **무엇을 자동화하는지**(OS 준비·런타임·kubeadm·CNI·애드온)와 어떤 플레이북이 어떤 작업인지 설명할 수 있습니다.
- 릴리스 **태그로 고정**한 Kubespray와 그 버전의 **공식 컨테이너 이미지**로, 실제 노드 없이 인벤토리·변수·플레이북을 검사할 수 있습니다.
- 인벤토리 그룹(`kube_control_plane`·`etcd`·`kube_node`)과 `group_vars`로 HA 구성과 버전·CNI를 정하는 방법을 읽을 수 있습니다.
- 노드에 닿지 못할 때의 증상(`UNREACHABLE`)을 보고 원인을 좁힐 수 있습니다.

## 선수 지식

- 개념(kubeadm init·join, HA, 업그레이드 순서, Kubespray와 kubeadm의 관계)은 심화 노트 [[kubeadm|클러스터 구축]]에 있습니다. kubeadm 자체는 [kubeadm 업그레이드 실습](#/item/a-kubeadm)에서 손으로 해 봅니다.
- Docker로 컨테이너를 실행할 수 있어야 합니다.
- 이 과정은 **선택 심화**입니다. 필수 과정·캡스톤 진행에 필요하지 않습니다.

:::note 검증 범위
**Kubespray v2.32.0(태그, 커밋 `9751ea6f`) · 공식 이미지 `quay.io/kubespray/kubespray:v2.32.0`(ansible-core 2.19.13)** 으로 아래 명령을 실행했고, 출력 블록은 그 결과입니다(2026-11-02). **실제 노드에 클러스터를 설치(`cluster.yml` 실행)하지 않았습니다** — VM 5대가 필요하고, 이 항해도의 원칙상 이미 쓰고 있는 VM은 쓰지 않습니다. 그래서 이 과정의 판정은 「인벤토리·변수·플레이북이 올바른가」까지이며, 설치·HA 동작·업그레이드는 **정적 설명**입니다.
:::

## 실습 환경 점검

```bash shell="실습 터미널"
docker version --format '{{.Server.Version}} {{.Server.Arch}}'
docker pull -q quay.io/kubespray/kubespray:v2.32.0 >/dev/null && docker image inspect --format '{{.Os}}/{{.Architecture}}' quay.io/kubespray/kubespray:v2.32.0
```

공식 이미지는 **amd64만** 있습니다. 애플 실리콘(arm64) Mac에서는 Docker Desktop이 에뮬레이션으로 실행하므로(경고가 한 줄 나옴) 느리지만 이 실습의 검사에는 충분합니다. 이미지는 약 730MB입니다.

로컬 Python으로 설치해도 되지만, Kubespray v2.32.0의 `requirements.txt`는 `ansible==12.3.0`이라 **Python 3.11 이상**이 필요합니다(macOS 기본 `python3`는 3.9라 설치되지 않음). 버전 충돌을 피하려고 이 실습은 이미지로 합니다.

## 1단계: 태그 고정으로 받기

```bash shell="실습 터미널"
mkdir -p ~/kubespray-lab && cd ~/kubespray-lab
git -c advice.detachedHead=false clone -q --depth 1 --branch v2.32.0 https://github.com/kubernetes-sigs/kubespray.git
git -C kubespray describe --tags; git -C kubespray rev-parse --short=8 HEAD
cat kubespray/requirements.txt | grep -vE "^#"
ls kubespray/*.yml | xargs -n1 basename | tr "\n" " "; echo
```

```output kind=verified env="검증 환경 (Kubespray v2.32.0)" date="2026-11-02"
v2.32.0
9751ea6f
ansible==12.3.0
bcrypt<6
cryptography==50.0.1
jmespath==1.1.0
netaddr==1.3.0
passlib==1.7.4
_config.yml cluster.yml galaxy.yml recover-control-plane.yml remove_node.yml remove-node.yml reset.yml scale.yml upgrade_cluster.yml upgrade-cluster.yml 
```

| 플레이북 | 하는 일 |
|---|---|
| `cluster.yml` | 처음 구축 (OS 준비 → 런타임 → etcd → kubeadm init·join → CNI → 애드온) |
| `scale.yml` | 워커 노드 추가 (컨트롤 플레인은 건드리지 않음) |
| `upgrade-cluster.yml` | 노드를 하나씩 drain → 업그레이드 → uncordon |
| `remove-node.yml` | 노드 제거 |
| `reset.yml` | 모든 노드 초기화 (**되돌릴 수 없음**) |
| `recover-control-plane.yml` | 컨트롤 플레인·etcd 일부를 잃었을 때 복구 |

`upgrade_cluster.yml`·`remove_node.yml`(밑줄)은 같은 작업의 다른 이름이고, `_config.yml`(문서 사이트)·`galaxy.yml`(Ansible 컬렉션 정보)은 플레이북이 아닙니다. README의 Docker 예시는 이 태그에서도 `kubespray:v2.31.0`으로 적혀 있습니다 — **이미지 태그는 받은 Kubespray 태그(v2.32.0)와 맞춥니다**.

## 2단계: 인벤토리 — 컨트롤 플레인 3 + 워커 2

샘플 인벤토리를 복사해 고칩니다. 주소는 **문서용 예약 대역(192.0.2.0/24, RFC 5737)** 이라 어디에도 실제로 닿지 않습니다.

```bash shell="실습 터미널"
cd ~/kubespray-lab && rm -rf inventory && cp -R kubespray/inventory/sample inventory
cat > inventory/inventory.ini <<'INV'
# 컨트롤 플레인 3대에 etcd를 함께 (stacked etcd) + 워커 2대
[kube_control_plane]
cp1 ansible_host=192.0.2.11 etcd_member_name=etcd1
cp2 ansible_host=192.0.2.12 etcd_member_name=etcd2
cp3 ansible_host=192.0.2.13 etcd_member_name=etcd3

[etcd:children]
kube_control_plane

[kube_node]
w1 ansible_host=192.0.2.21
w2 ansible_host=192.0.2.22
INV
grep -nE "^(kube_network_plugin|kube_proxy_mode|container_manager|cluster_name):" inventory/group_vars/k8s_cluster/k8s-cluster.yml
```

```output kind=verified env="검증 환경 (Kubespray v2.32.0 샘플 group_vars)" date="2026-11-02"
83:kube_network_plugin: calico
136:kube_proxy_mode: ipvs
167:cluster_name: cluster.local
236:container_manager: containerd
```

샘플 기본값은 CNI **Calico**, kube-proxy **ipvs**, 런타임 **containerd**, 클러스터 DNS 도메인 `cluster.local`입니다. 바꾸려면 이 파일을 고칩니다(예: `kube_network_plugin: cilium`). 이 파일에 없는 변수는 role 기본값(`kubespray/roles/kubespray_defaults/`)을 씁니다. Kubernetes 버전(`kube_version`)도 기본값이 role에 있습니다 — v2.32.0은 체크섬 표의 첫 항목(**1.36.4**)이며, 체크섬 표에 없는 버전은 설치되지 않습니다.

## 3단계: 공식 이미지로 검사

인벤토리를 **읽기 전용**으로 마운트하고, SSH 키는 마운트하지 않습니다(접속할 일이 없음).

```bash shell="실습 터미널"
cd ~/kubespray-lab
docker run --rm -v "$PWD/inventory:/inventory:ro" quay.io/kubespray/kubespray:v2.32.0 bash -c '
ansible --version | head -1
ansible-inventory -i /inventory/inventory.ini --graph
for p in cluster.yml scale.yml upgrade-cluster.yml reset.yml; do ansible-playbook -i /inventory/inventory.ini --syntax-check $p 2>&1 | tail -1; done
echo "cluster.yml 태스크 수: $(ansible-playbook -i /inventory/inventory.ini cluster.yml --list-tasks 2>/dev/null | grep -c TAGS)"' 2>&1 | grep -v "platform (linux/amd64) does not match"
```

```output kind=verified env="검증 환경 (kubespray:v2.32.0 · arm64 Mac에서 에뮬레이션)" date="2026-11-02"
ansible [core 2.19.13]
@all:
  |--@ungrouped:
  |--@etcd:
  |  |--@kube_control_plane:
  |  |  |--cp1
  |  |  |--cp2
  |  |  |--cp3
  |--@kube_node:
  |  |--w1
  |  |--w2
playbook: cluster.yml
playbook: scale.yml
playbook: upgrade-cluster.yml
playbook: reset.yml
cluster.yml 태스크 수: 722
```

- `--graph`: `etcd` 그룹이 `kube_control_plane`을 품어(`[etcd:children]`) 컨트롤 플레인 3대가 곧 etcd 3대입니다(쿼럼 2). etcd를 따로 두려면 `[etcd]`에 다른 호스트를 적습니다.
- `--syntax-check`는 플레이북·role·변수 파일의 **문법과 구조**만 봅니다. 노드에 접속하지 않으므로 OS·네트워크·버전 문제는 여기서 드러나지 않습니다.
- `cluster.yml` 하나가 720여 개 태스크입니다 — 손으로 하던 OS 준비·런타임·인증서·kubeadm·CNI·애드온이 모두 여기에 들어 있습니다.

## 4단계: 노드에 닿지 못하면

실제 구축 첫 단계는 모든 노드에 SSH로 접속해 사실(facts)을 모으는 것입니다. 닿지 않는 주소로 그 단계만 해 봅니다.

```bash shell="실습 터미널"
cd ~/kubespray-lab
docker run --rm -e ANSIBLE_SSH_ARGS='-o ConnectTimeout=5' -v "$PWD/inventory:/inventory:ro" quay.io/kubespray/kubespray:v2.32.0 \
  ansible -i /inventory/inventory.ini cp1 -m ping 2>&1 | grep -v "platform (linux/amd64) does not match"
```

```output kind=verified env="검증 환경 (kubespray:v2.32.0)" date="2026-11-02"
[ERROR]: Task failed: Failed to connect to the host via ssh: ssh: connect to host 192.0.2.11 port 22: Connection timed out

Task failed.
Origin: <adhoc 'ping' task>

{'action': 'ping', 'args': {}, 'timeout': 0, 'async_val': 0, 'poll': 15}

<<< caused by >>>

Failed to connect to the host via ssh: ssh: connect to host 192.0.2.11 port 22: Connection timed out

cp1 | UNREACHABLE! => {
    "changed": false,
    "msg": "Task failed: Failed to connect to the host via ssh: ssh: connect to host 192.0.2.11 port 22: Connection timed out",
    "unreachable": true
}
```

`ANSIBLE_SSH_ARGS`로 Kubespray `ansible.cfg`의 SSH 옵션(`ControlMaster`·`ControlPersist`·`ConnectionAttempts=100`)을 바꿔 5초 만에 끝나게 했습니다. 바꾸지 않으면 설정상 최대 100번까지 다시 시도하고, 검증한 arm64 Mac(에뮬레이션)에서는 `[ERROR]: A worker was found in a dead state`로 바로 죽었습니다 — **애플 실리콘 Mac에서 이 이미지로 실제 노드에 배포하는 것은 확인하지 못했다**는 뜻이기도 합니다(리눅스 amd64 관리 PC를 권장).

`UNREACHABLE`는 Ansible이 **노드에 들어가지도 못했다**는 뜻입니다(태스크 실패 `FAILED`와 다름). 주소·방화벽(22번)·SSH 사용자·키(`--private-key`, `ansible_user`)·`become`(sudo) 순서로 봅니다.

## 5단계: 실제로 구축한다면 (실행하지 않음)

아래는 Kubespray v2.32.0 문서 기준의 순서이며, **이 실습에서 실행하지 않았고 출력도 싣지 않습니다.**

```bash shell="참고 (실행하지 않음)" run=skip
# 노드 5대에 SSH 키 배포, 스왑 끄기는 Kubespray가 처리
docker run --rm -it -v "$PWD/inventory:/inventory" -v "$HOME/.ssh/id_ed25519:/root/.ssh/id_ed25519:ro" \
  quay.io/kubespray/kubespray:v2.32.0 bash
ansible-playbook -i /inventory/inventory.ini --private-key /root/.ssh/id_ed25519 -u <사용자> --become cluster.yml
# 워커 추가: 인벤토리에 w3 추가 후
ansible-playbook -i /inventory/inventory.ini ... --become scale.yml --limit=w3
# 업그레이드: kube_version을 올리고 (한 번에 마이너 하나씩)
ansible-playbook -i /inventory/inventory.ini ... --become upgrade-cluster.yml -e kube_version=<새 버전>
```

| 다룬 범위 | 이 실습 | 근거 |
|---|---|---|
| 태그 고정 받기, 인벤토리 그룹, group_vars 기본값, 플레이북 문법, 태스크 수 | 실행 | 1~3단계 |
| SSH 접속 실패 증상 | 실행 | 4단계 |
| `cluster.yml`·`scale.yml`·`upgrade-cluster.yml` 실제 실행, HA 동작 | **정적** | [[kubeadm|클러스터 구축]] · Kubespray 문서 |

## 흔한 오류

| 증상 | 원인 | 확인·해결 |
|---|---|---|
| `pip install -r requirements.txt`가 ansible 버전을 못 찾음 | Python이 낮음 (ansible 12는 3.11+) | 공식 이미지 사용 또는 Python 3.11+ 가상환경 |
| `UNREACHABLE! … Connection timed out` | 주소·방화벽·라우팅 | `ssh <사용자>@<주소>`로 먼저 확인 |
| `UNREACHABLE! … Permission denied (publickey)` | 키·사용자 | `--private-key`, `-u`, `ansible_user` |
| `Missing sudo password` | `become`에 비밀번호 필요 | 노드에 NOPASSWD sudo 또는 `--ask-become-pass` |
| `kube_version … not in kubelet_checksums` 류의 assert 실패 | 이 Kubespray 태그가 모르는 Kubernetes 버전 | 그 버전을 지원하는 Kubespray 태그로 올림 |
| 이미지 태그와 저장소 태그가 다름 | README 예시를 그대로 복사 | `kubespray:<받은 태그>` |
| arm64 Mac에서 느림·경고 | amd64 이미지 에뮬레이션 | 검사에는 충분 |
| `A worker was found in a dead state` | arm64 Mac 에뮬레이션에서 SSH ControlMaster | `-e ANSIBLE_SSH_ARGS=…`로 바꾸거나 amd64 리눅스에서 실행 |
| 설치 중 etcd 단계 실패 | etcd 호스트 수가 짝수·네트워크 지연 | etcd는 홀수(1·3·5) |

## 성공 판정

```verify
id: kubespray-syntax
title: 태그 고정 Kubespray와 내 인벤토리로 cluster.yml 문법 검사 통과
explain: 3단계 뒤 실행합니다. 이미지 안에서 문법 검사 결과의 마지막 줄만 봅니다.
command: cd ~/kubespray-lab && docker run --rm -v "$PWD/inventory:/inventory:ro" quay.io/kubespray/kubespray:v2.32.0 ansible-playbook -i /inventory/inventory.ini --syntax-check cluster.yml 2>/dev/null | tail -1
expect: ^playbook: cluster\.yml$
criteria: playbook: cluster.yml
```

```verify
id: kubespray-inventory
title: 컨트롤 플레인 3 · etcd 3 · 워커 2 인벤토리
explain: 그룹별 호스트 수를 셉니다.
command: cd ~/kubespray-lab && docker run --rm -v "$PWD/inventory:/inventory:ro" quay.io/kubespray/kubespray:v2.32.0 ansible-inventory -i /inventory/inventory.ini --list 2>/dev/null | jq -r '[(.kube_control_plane.hosts|length), (.etcd.children|length), (.kube_node.hosts|length)] | join(" ")'
expect: ^3 1 2$
criteria: 3 1 2 (컨트롤 플레인 3, etcd는 하위 그룹 1개 = 컨트롤 플레인, 워커 2)
```

## 정리

```bash shell="실습 터미널" run=skip
rm -rf ~/kubespray-lab
docker image rm quay.io/kubespray/kubespray:v2.32.0     # 약 730MB
```

## 체크리스트

- [ ] Kubespray가 kubeadm 위에서 자동화하는 범위를 말할 수 있다
- [ ] 저장소 태그와 이미지 태그를 같은 버전으로 고정했다
- [ ] `[etcd:children]`이 stacked etcd를 뜻한다는 것을 그래프로 확인했다
- [ ] `--syntax-check`가 확인하는 것과 확인하지 못하는 것을 구분할 수 있다
- [ ] `UNREACHABLE`과 `FAILED`의 차이를 안다
- [ ] 실제 구축·HA·업그레이드는 이 실습에서 실행하지 않았다는 것을 안다
