## 학습 목표

- 쿠버네티스에서 VM을 돌리는 KubeVirt의 구성 요소(virt-operator·virt-controller·virt-handler·virt-launcher)와 VirtualMachine·VirtualMachineInstance의 관계를 설명할 수 있습니다.
- 노드에 하드웨어 가상화(`/dev/kvm`)가 있는지 확인하고, 없을 때 VM이 **왜·어떻게** 실패하는지 자원(`devices.kubevirt.io/kvm`)과 이벤트로 읽을 수 있습니다.
- 소프트웨어 에뮬레이션(`useEmulation`)의 의미와 한계(특히 arm64)를 말할 수 있습니다.
- VM 부팅·노출·라이브 마이그레이션에 필요한 조건을 정리할 수 있습니다(이 과정에서는 정적 설명).

## 선수 지식

- VM과 컨테이너의 차이, KubeVirt 동작 흐름은 심화 노트 [[kubevirt|VM과 컨테이너 · KubeVirt]]에 있습니다. 여기서는 반복하지 않습니다.
- 파드 스케줄링과 확장 자원(extended resource)을 읽는 법: [자원 요청·제한](#/item/i-lab02)
- `kind`(Kubernetes in Docker) 설치
- 이 과정은 **선택 심화**입니다. 필수 과정·캡스톤 진행에 필요하지 않습니다.

:::warn 부분 검증 — 이 PC 종류에서는 VM이 켜지지 않았습니다
검증 PC는 **Apple 실리콘(M5 Pro) · macOS 26.6.2 · OrbStack(Docker Engine 29.8.2)** 으로 컨테이너 안에 `/dev/kvm`이 없습니다. 그래서 **KubeVirt v1.9.1 설치, KVM이 없을 때의 실패, 에뮬레이션을 켰을 때 arm64에서 생기는 실패**까지만 실제로 실행했고 출력 블록은 그 결과입니다(2026-11-02, kind v0.32.0 · `kindest/node:v1.35.0` 임시 클러스터, 확인 후 삭제). amd64 노드 이미지를 에뮬레이션으로 띄워 보는 것도 시도했지만 컨트롤 플레인이 뜨지 않았습니다.

**VM 부팅·콘솔·Service 노출·라이브 마이그레이션은 실행하지 않았습니다**(6단계, 정적 설명·출력 없음). 직접 해 보려면 KVM이 있는 리눅스 PC나, 중첩 가상화를 켠 리눅스 VM이 필요합니다.
:::

## 실습 환경 점검

```bash shell="실습 터미널"
uname -sm
docker run --rm --privileged alpine:3.20 sh -c 'ls -l /dev/kvm 2>&1; uname -m'
docker info --format 'Docker 메모리 {{.MemTotal}} bytes · CPU {{.NCPU}} · {{.OperatingSystem}}'
```

```output kind=verified env="검증 PC (Apple 실리콘 · OrbStack)" date="2026-11-02"
Darwin arm64
ls: /dev/kvm: No such file or directory
aarch64
Docker 메모리 16818118656 bytes · CPU 15 · OrbStack
```

- 두 번째 줄에 `crw-rw---- … /dev/kvm`이 보이면 KVM이 있습니다 — 리눅스 x86_64·arm64 PC의 Docker가 보통 그렇습니다. 그 PC라면 4단계의 에뮬레이션을 건너뛰고 6단계를 실제로 해 볼 수 있습니다.
- `No such file or directory`면 이 과정은 검증 PC와 같은 **부분 실습**이 됩니다. macOS의 Docker(Desktop·OrbStack)는 VM 안에서 돌아, 그 안까지 KVM이 전달되지 않습니다.
- 메모리 약 **2GB**(KubeVirt 구성 요소), 디스크 약 **2GB**(이미지)를 씁니다.

## 1단계: 클러스터와 KubeVirt 설치 (태그 고정·체크섬)

```bash shell="실습 터미널"
mkdir -p ~/kubevirt-lab && cd ~/kubevirt-lab
export KUBECONFIG=$PWD/kubeconfig KIND_EXPERIMENTAL_DOCKER_NETWORK=kubevirt-net
kind create cluster --name kubevirt-lab --image kindest/node:v1.35.0 --wait 120s 2>&1 | grep -E "Ready after|ERROR"
curl -fsSLO https://github.com/kubevirt/kubevirt/releases/download/v1.9.1/kubevirt-operator.yaml
curl -fsSLO https://github.com/kubevirt/kubevirt/releases/download/v1.9.1/kubevirt-cr.yaml
shasum -a 256 kubevirt-operator.yaml kubevirt-cr.yaml
kubectl apply -f kubevirt-operator.yaml >/dev/null && kubectl apply -f kubevirt-cr.yaml >/dev/null
kubectl -n kubevirt wait kv kubevirt --for condition=Available --timeout=900s
kubectl -n kubevirt get pods --no-headers | awk '{print $1, $3}' | sed -E 's/-[a-z0-9]{8,10}(-[a-z0-9]{5})? / /' | sort -u
```

```output kind=verified env="검증 환경 (kind v0.32.0 · KubeVirt v1.9.1 · arm64)" date="2026-11-02"
 • Ready after 16s 💚
9ac45a436c49d32e6fc21d542bcb7600b970705297b9e6752f3ef9b0a1d292da  kubevirt-operator.yaml
43106136dbce3312bdbfdeae612aacafc6c12da518d233f90645b4685d84a2af  kubevirt-cr.yaml
Warning: spec.template.spec.affinity.nodeAffinity.requiredDuringSchedulingIgnoredDuringExecution.nodeSelectorTerms[1].matchExpressions[0].key: node-role.kubernetes.io/master is use "node-role.kubernetes.io/control-plane" instead
kubevirt.kubevirt.io/kubevirt condition met
virt-api Running
virt-controller Running
virt-exportproxy Running
virt-handler-jskdb Running
virt-operator Running
virt-template-apiserver Running
virt-template-controller Running
```

받은 두 파일의 sha256은 GitHub 릴리스 페이지가 각 파일에 표시하는 digest와 같아야 합니다(검증: operator `9ac45a43…92da`, cr `43106136…a2af`). 설치에는 검증 PC에서 약 5분 걸렸습니다.

| 구성 요소 | 종류 | 하는 일 |
|---|---|---|
| virt-operator | Deployment | KubeVirt 자체를 설치·업그레이드 |
| virt-api | Deployment | VM 관련 API·웹훅(검증) |
| virt-controller | Deployment | VM → VMI → virt-launcher 파드를 만듦 |
| virt-handler | DaemonSet | 노드마다 VM을 실제로 띄우고, 노드에 `devices.kubevirt.io/kvm` 같은 자원을 알림 |
| virt-launcher | VM마다 파드 하나 | 그 안의 libvirt·QEMU 프로세스가 VM |

## 2단계: 노드가 알린 가상화 자원

```bash shell="실습 터미널"
cd ~/kubevirt-lab && export KUBECONFIG=$PWD/kubeconfig
kubectl get node kubevirt-lab-control-plane -o jsonpath='{.status.allocatable}' | tr ',' '\n' | grep devices.kubevirt.io
```

```output kind=verified env="검증 환경 (KVM 없음)" date="2026-11-02"
"devices.kubevirt.io/kvm":"0"
"devices.kubevirt.io/sev":"0"
"devices.kubevirt.io/tun":"1k"
"devices.kubevirt.io/vhost-net":"1k"
```

`devices.kubevirt.io/kvm`이 **0**이면 이 노드에는 VM을 놓을 수 없습니다. virt-launcher 파드는 이 자원을 1 요청하기 때문입니다(`tun`·`vhost-net`은 네트워크용, `sev`는 AMD 메모리 암호화용).

## 3단계: KVM 없이 VM 만들기 → 스케줄 실패

```yaml file=vm.yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata: { name: cirros, namespace: lab-vm }
spec:
  runStrategy: Always                 # 만들면 바로 켬 (Halted면 꺼 둠)
  template:
    metadata: { labels: { app: cirros } }
    spec:
      domain:
        cpu: { cores: 1 }
        memory: { guest: 256Mi }
        devices:
          disks:
          - name: root
            disk: { bus: virtio }
          interfaces:
          - name: default
            masquerade: {}            # 파드 네트워크 뒤에 NAT로 붙음 (파드 IP = VM의 바깥 주소)
      networks:
      - name: default
        pod: {}
      volumes:
      - name: root
        containerDisk: { image: quay.io/kubevirt/cirros-container-disk-demo:v1.9.1 }   # 이미지 안의 디스크 (지우면 사라짐)
```

```bash shell="실습 터미널"
cd ~/kubevirt-lab && export KUBECONFIG=$PWD/kubeconfig
kubectl create namespace lab-vm >/dev/null && kubectl apply -f vm.yaml
sleep 40
kubectl -n lab-vm get vm cirros -o jsonpath='VM {.status.printableStatus}{"\n"}'
kubectl -n lab-vm get vmi cirros -o jsonpath='VMI {.status.phase}{"\n"}'
kubectl -n lab-vm get pods --no-headers | awk '{print $1, $3}' | sed -E 's/-[a-z0-9]{5} / /'
kubectl -n lab-vm get events -o jsonpath='{range .items[?(@.reason=="FailedScheduling")]}{.message}{"\n"}{end}' | sort -u | cut -c1-70
```

```output kind=verified env="검증 환경 (KVM 없음)" date="2026-11-02"
virtualmachine.kubevirt.io/cirros created
VM ErrorUnschedulable
VMI Scheduling
virt-launcher-cirros Pending
0/1 nodes are available: 1 Insufficient devices.kubevirt.io/kvm. no ne
```

VM은 그대로 있고(설정), 실행 단위인 VMI가 `Scheduling`에서 멈춥니다. 원인은 이벤트에 그대로 있습니다 — 일반 파드가 CPU·메모리가 모자라 `Pending`인 것과 같은 방식입니다.

## 4단계: 소프트웨어 에뮬레이션 켜기 (실습 전용)

`useEmulation`을 켜면 KubeVirt는 KVM 대신 QEMU가 CPU를 소프트웨어로 흉내 내게 합니다. 훨씬 느려 **운영에 쓰지 않고**, KVM이 없는 실습·CI에서만 씁니다.

```bash shell="실습 터미널"
cd ~/kubevirt-lab && export KUBECONFIG=$PWD/kubeconfig
kubectl -n kubevirt patch kubevirt kubevirt --type merge -p '{"spec":{"configuration":{"developerConfiguration":{"useEmulation":true}}}}'
sleep 20
kubectl -n lab-vm patch vm cirros --type merge -p '{"spec":{"runStrategy":"Halted"}}' >/dev/null
kubectl -n lab-vm wait vmi cirros --for=delete --timeout=180s >/dev/null 2>&1
kubectl -n lab-vm patch vm cirros --type merge -p '{"spec":{"runStrategy":"Always"}}' >/dev/null
sleep 120
kubectl -n lab-vm get vmi cirros -o jsonpath='VMI {.status.phase} · 노드 {.status.nodeName}{"\n"}'
kubectl -n lab-vm get events -o jsonpath='{range .items[?(@.reason=="SyncFailed")]}{.message}{"\n"}{end}' | sort -u | grep -o "Message='[^']*'[^)]*" | head -1
```

```output kind=verified env="검증 환경 (useEmulation · arm64)" date="2026-11-02"
kubevirt.kubevirt.io/kubevirt patched
VMI Scheduled · 노드 hangdo-verify-kv-control-plane
Message='unsupported configuration: CPU mode 'host-passthrough' for aarch64 qemu domain on aarch64 host is not supported by hypervisor'
```

이번에는 노드에 배치되고 virt-launcher 파드도 뜨지만, VM 정의를 넘기는 순간 libvirt가 거절합니다. KubeVirt는 arm64에서 CPU 모드를 `host-passthrough`로 정하는데, 에뮬레이션에서는 그 모드를 쓸 수 없기 때문입니다. CPU 모델을 바꿔 보면:

```bash shell="실습 터미널"
cd ~/kubevirt-lab && export KUBECONFIG=$PWD/kubeconfig
kubectl -n lab-vm patch vm cirros --type merge -p '{"spec":{"runStrategy":"Halted"}}' >/dev/null
kubectl -n lab-vm wait vmi cirros --for=delete --timeout=180s >/dev/null 2>&1
kubectl -n lab-vm patch vm cirros --type merge -p '{"spec":{"template":{"spec":{"domain":{"cpu":{"cores":1,"model":"cortex-a57"}}}},"runStrategy":"Always"}}' >/dev/null
sleep 20
kubectl -n lab-vm get events -o jsonpath='{range .items[?(@.reason=="FailedCreate")]}{.message}{"\n"}{end}' | sort -u | grep -o 'denied the request: .*'
```

```output kind=verified env="검증 환경 (useEmulation · arm64)" date="2026-11-02"
denied the request: currently, host-passthrough is the only model supported on Arm64
```

KubeVirt의 검증 웹훅이 막습니다. 정리하면 **arm64 노드에서는 KVM이 꼭 있어야 VM이 켜집니다.** x86_64 노드는 `useEmulation`으로 (느리게) 켜진다고 공식 문서가 설명하지만, 이 과정에서는 확인하지 못했습니다.

## 5단계: 무엇이 VM을 막았는지 정리

| 단계 | 상태 | 막은 곳 | 고치는 법 |
|---|---|---|---|
| KVM 없음 | VM `ErrorUnschedulable`, 파드 `Pending` | 스케줄러 (`devices.kubevirt.io/kvm` 0) | KVM 있는 노드, 또는 실습 한정 `useEmulation` |
| 에뮬레이션 + arm64 | VMI `Scheduled`, `SyncFailed` | libvirt (`host-passthrough` 불가) | KVM 있는 arm64 노드 |
| CPU 모델 변경 + arm64 | VMI 생성 거절 | KubeVirt 웹훅 | 같음 |

## 6단계: KVM이 있는 노드라면 (실행하지 않음)

아래는 KubeVirt 문서 기준의 다음 단계이며, **이 과정에서 실행하지 않았고 출력도 싣지 않습니다.**

```bash shell="참고 (실행하지 않음)" run=skip
# 부팅 확인: VMI가 Running이 되고 파드 IP를 받음
kubectl -n lab-vm wait vmi cirros --for=condition=Ready --timeout=300s
kubectl -n lab-vm get vmi cirros -o wide
# 콘솔: virtctl(KubeVirt CLI, 같은 버전) — 받을 때 릴리스의 체크섬 확인
virtctl console -n lab-vm cirros
# 노출: VM도 레이블이 있으므로 일반 Service로 노출 (masquerade 인터페이스)
virtctl expose vmi cirros -n lab-vm --name cirros-ssh --port 22 --type ClusterIP
# 라이브 마이그레이션: 노드 2대 이상 + 공유(RWX) 또는 마이그레이션 가능한 디스크
virtctl migrate cirros -n lab-vm
kubectl -n lab-vm get vmim
```

| 하고 싶은 것 | 필요한 조건 |
|---|---|
| VM 부팅 | 노드의 `/dev/kvm` (x86_64는 실습 한정 에뮬레이션도 가능) |
| 영구 디스크 | PVC 또는 CDI의 DataVolume (`containerDisk`는 지우면 사라짐) |
| 라이브 마이그레이션 | 노드 2대 이상, 공유(RWX) 스토리지 또는 마이그레이션 가능한 디스크, 같은 CPU 계열 |
| drain 때 끄지 않고 옮기기 | `evictionStrategy: LiveMigrate` + 위 조건 |

## 흔한 오류

| 증상 | 원인 | 확인·해결 |
|---|---|---|
| `kubectl wait kv … Available`이 오래 걸림 | 이미지 여러 개를 받음 | `kubectl -n kubevirt get pods` — 검증 PC 약 5분 |
| VM `ErrorUnschedulable` | `devices.kubevirt.io/kvm` 0 | 2단계 명령, `/dev/kvm` 확인 |
| `SyncFailed … host-passthrough … not supported by hypervisor` | arm64 + 에뮬레이션 | KVM 있는 arm64 노드 |
| `host-passthrough is the only model supported on Arm64` | arm64에서 CPU 모델 지정 | 모델 지정을 빼고 KVM 노드 사용 |
| VMI가 `Scheduling`에서 메모리 부족 | VM 메모리 + 오버헤드가 노드에 안 맞음 | `memory.guest`를 줄이거나 노드 자원 확인 |
| 경고 `node-role.kubernetes.io/master is use … control-plane instead` | 설치 매니페스트의 옛 레이블 | 설치 시 한 번 나오는 경고, 동작에 영향 없음 |

## 성공 판정

```verify
id: kubevirt-installed
title: KubeVirt가 설치되고 노드가 가상화 자원을 알림
explain: 1·2단계 뒤 실행합니다. KubeVirt 상태와 노드의 kvm 자원 값을 출력합니다. KVM이 없는 PC는 0, 있는 PC는 1 이상입니다.
command: cd ~/kubevirt-lab && KUBECONFIG=$PWD/kubeconfig sh -c 'echo "$(kubectl -n kubevirt get kv kubevirt -o jsonpath={.status.phase}) kvm=$(kubectl get node kubevirt-lab-control-plane -o jsonpath="{.status.allocatable.devices\.kubevirt\.io/kvm}")"'
expect: ^Deployed kvm=[0-9]+
criteria: 「Deployed kvm=0」(KVM 없음) 또는 「Deployed kvm=1000」처럼 1 이상
```

```verify
id: kubevirt-why
title: VM이 켜지지 않은 이유를 이벤트에서 찾음
explain: 3·4단계 뒤 실행합니다. VM 관련 실패 이벤트의 이유(reason) 종류를 모읍니다. KVM이 있는 PC에서는 아무것도 나오지 않을 수 있습니다(그 경우 VM이 켜진 것).
command: cd ~/kubevirt-lab && KUBECONFIG=$PWD/kubeconfig kubectl -n lab-vm get events -o jsonpath='{range .items[*]}{.reason}{"\n"}{end}' | grep -E 'FailedScheduling|SyncFailed|FailedCreate' | sort -u | tr '\n' ' '
expect: FailedScheduling
criteria: KVM 없는 PC: FailedScheduling(과 arm64면 SyncFailed·FailedCreate)
```

## 정리

```bash shell="실습 터미널" run=skip
cd ~/kubevirt-lab && export KUBECONFIG=$PWD/kubeconfig
kind delete cluster --name kubevirt-lab
docker network rm kubevirt-net
cd ~ && rm -rf ~/kubevirt-lab
```

## 체크리스트

- [ ] VirtualMachine·VirtualMachineInstance·virt-launcher 파드의 관계를 말할 수 있다
- [ ] 노드의 `devices.kubevirt.io/kvm` 값으로 VM을 놓을 수 있는 노드인지 판단했다
- [ ] KVM이 없을 때 VM이 스케줄러에서 막히는 것을 이벤트로 확인했다
- [ ] `useEmulation`이 실습 전용이고, arm64에서는 그것으로도 켜지지 않는다는 것을 확인했다
- [ ] VM 부팅·노출·라이브 마이그레이션에 필요한 조건을 표로 정리했다 — 이 과정에서는 실행하지 않았다
