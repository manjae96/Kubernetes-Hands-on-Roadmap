## 학습 목표

- 컨테이너·파드의 저장 공간은 파드와 함께 사라진다는 것을 확인하고, [[pvc]]로 파드가 바뀌어도 남는 저장 공간을 요청할 수 있습니다.
- [[storageclass]]가 [[pv]]를 자동으로 만들어 PVC에 묶는(동적 프로비저닝) 과정을 상태 변화로 설명할 수 있습니다.
- [[statefulset]]의 고정 이름, 순서, 파드마다 따로 붙는 볼륨(volumeClaimTemplates)을 Deployment와 비교해 설명할 수 있습니다.
- PVC를 지우면 데이터가 어떻게 되는지([[storageclass]]의 회수 정책) 알고, 지우기 전에 확인할 수 있습니다.

## 선수 지식

- [ConfigMap·Secret과 Probe](#/item/i-lab01)까지의 내용 (볼륨 마운트 문법)
- [기본 과정](#/level/basic)의 Deployment·Service

## 실습 환경 점검

```bash shell="실습 터미널" expect=fail
kubectl config current-context
kubectl get nodes
kubectl get namespace lab-i03
```

`k8s-lab`, `Ready`, 그리고 `NotFound`가 나와야 합니다.

```bash shell="실습 터미널"
kubectl create namespace lab-i03
kubectl get storageclass
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd)" date="2026-10-24"
namespace/lab-i03 created
NAME                 PROVISIONER                RECLAIMPOLICY   VOLUMEBINDINGMODE   ALLOWVOLUMEEXPANSION   AGE
standard (default)   k8s.io/minikube-hostpath   Delete          Immediate           false                  46s
```

minikube에는 `standard`라는 **기본 StorageClass**가 있습니다. 노드(컨테이너) 디스크의 폴더를 볼륨으로 내주는 단순한 프로비저너입니다.

## 개념: 볼륨을 「요청」과 「실물」로 나누기

**무엇인가.** 쿠버네티스는 저장 공간을 세 객체로 나눕니다.

| 객체 | 누가 만드나 | 뜻 | 비유 |
|---|---|---|---|
| [[pvc]] PersistentVolumeClaim | 앱 개발자 (네임스페이스 안) | 「1Gi, 한 노드에서 읽기·쓰기」 같은 **요청서** | 주차권 신청서 |
| [[pv]] PersistentVolume | 관리자 또는 StorageClass (클러스터 전체) | 실제 디스크 한 덩어리 | 실제 주차 칸 |
| [[storageclass]] StorageClass | 관리자 | PVC가 오면 PV를 **자동으로 만드는 규칙**(어떤 디스크, 지우면 어떻게) | 「신청서가 오면 칸을 새로 그려 준다」 |

**왜 필요한가.** 파드는 언제든 지워지고 다른 이름으로 다시 만들어집니다. 데이터베이스·업로드 파일처럼 파드보다 오래 살아야 하는 데이터는 파드 밖(PV)에 두고, 파드는 PVC 이름으로 그 볼륨을 「빌려 쓰기」만 합니다. 앱은 디스크가 어디 있는지(클라우드 디스크, NFS, 노드 폴더) 몰라도 됩니다.

**상태 흐름**

```text
PVC 생성 ─▶ Pending ─(StorageClass가 PV를 만들어 묶음)─▶ Bound ─▶ 파드가 마운트해 사용
                                                       │
                       PVC 삭제 ─▶ 회수 정책 Delete: PV와 데이터 삭제 / Retain: PV 남음(Released)
```

## 1단계: 파드 안에 쓴 데이터는 파드와 함께 사라진다

[[deployment]]가 파드 안의 `emptyDir` 볼륨에 파일을 씁니다. `emptyDir`은 파드가 살아 있는 동안만 있는 임시 볼륨입니다.

```yaml file=notes-emptydir.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notes
  namespace: lab-i03
spec:
  replicas: 1
  selector:
    matchLabels: { app: notes }
  template:
    metadata:
      labels: { app: notes }
    spec:
      containers:
        - name: app
          image: busybox:1.37.0
          command: ["sh", "-c", "sleep 3600"]
          volumeMounts:
            - { name: data, mountPath: /data }
      volumes:
        - name: data
          emptyDir: {}
```

```bash shell="실습 터미널"
kubectl apply -f notes-emptydir.yaml
kubectl rollout status deployment/notes -n lab-i03 --timeout=120s
kubectl exec -n lab-i03 deploy/notes -- sh -c 'echo "메모 1: 회의는 3시" > /data/memo.txt; cat /data/memo.txt'
kubectl delete pod -n lab-i03 -l app=notes --wait=true
kubectl rollout status deployment/notes -n lab-i03 --timeout=120s
kubectl exec -n lab-i03 deploy/notes -- sh -c 'cat /data/memo.txt 2>&1 || true'
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd)" date="2026-10-24"
deployment.apps/notes created
Waiting for deployment "notes" rollout to finish: 0 of 1 updated replicas are available...
deployment "notes" successfully rolled out
메모 1: 회의는 3시
pod "notes-57fb8f9644-b5l7g" deleted from lab-i03 namespace
deployment "notes" successfully rolled out
cat: can't open '/data/memo.txt': No such file or directory
```

Deployment가 새 파드를 만들었지만, 새 파드의 `emptyDir`은 빈 폴더입니다. 메모가 사라졌습니다.

## 2단계: PVC로 파드보다 오래 사는 볼륨 요청

1Gi짜리 PVC를 요청합니다. `storageClassName`을 비워 두면 기본 StorageClass(`standard`)가 쓰입니다.

```yaml file=notes-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: notes-data
  namespace: lab-i03
spec:
  accessModes: ["ReadWriteOnce"]   # 한 노드에서 읽기·쓰기
  resources:
    requests:
      storage: 1Gi
```

```bash shell="실습 터미널"
kubectl apply -f notes-pvc.yaml
sleep 3
kubectl get pvc notes-data -n lab-i03
kubectl get pv -o custom-columns='NAME:.metadata.name,CAPACITY:.spec.capacity.storage,RECLAIM:.spec.persistentVolumeReclaimPolicy,STATUS:.status.phase,CLAIM:.spec.claimRef.name' | sed 's/pvc-[0-9a-f-]*/pvc-<자동 생성 이름>/'
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd)" date="2026-10-24"
persistentvolumeclaim/notes-data created
NAME         STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
notes-data   Bound    pvc-8afe11d7-4f23-453a-a1c5-bb4442070f3b   1Gi        RWO            standard       <unset>                 3s
NAME                                       CAPACITY   RECLAIM   STATUS   CLAIM
pvc-<자동 생성 이름>   1Gi        Delete    Bound    notes-data
```

PV는 직접 만들지 않았는데 StorageClass가 만들어 PVC에 **묶었습니다(Bound)**. 이제 Deployment가 `emptyDir` 대신 이 PVC를 쓰게 합니다.

```yaml title="모범 답안 · notes-pvc-deploy.yaml"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notes
  namespace: lab-i03
spec:
  replicas: 1
  strategy:
    type: Recreate            # RWO 볼륨: 옛 파드가 내려간 뒤 새 파드를 올림
  selector:
    matchLabels: { app: notes }
  template:
    metadata:
      labels: { app: notes }
    spec:
      containers:
        - name: app
          image: busybox:1.37.0
          command: ["sh", "-c", "sleep 3600"]
          volumeMounts:
            - { name: data, mountPath: /data }
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: notes-data     # emptyDir 대신 PVC
```

```bash shell="실습 터미널"
kubectl apply -f notes-pvc-deploy.yaml
kubectl rollout status deployment/notes -n lab-i03 --timeout=120s
kubectl exec -n lab-i03 deploy/notes -- sh -c 'echo "메모 2: 보고서 금요일까지" > /data/memo.txt'
kubectl delete pod -n lab-i03 -l app=notes --wait=true
kubectl rollout status deployment/notes -n lab-i03 --timeout=120s
kubectl exec -n lab-i03 deploy/notes -- cat /data/memo.txt
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd)" date="2026-10-24"
deployment.apps/notes configured
Waiting for deployment "notes" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "notes" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "notes" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "notes" rollout to finish: 0 of 1 updated replicas are available...
deployment "notes" successfully rolled out
pod "notes-66dc445fdb-89smc" deleted from lab-i03 namespace
deployment "notes" successfully rolled out
메모 2: 보고서 금요일까지
```

새 파드가 같은 PVC를 다시 붙여 메모가 남았습니다.

:::note accessModes
| 모드 | 뜻 | 예 |
|---|---|---|
| `ReadWriteOnce` (RWO) | **한 노드**에서 읽기·쓰기 | 대부분의 블록 디스크 (클라우드 디스크, minikube hostPath) |
| `ReadOnlyMany` (ROX) | 여러 노드에서 읽기만 | |
| `ReadWriteMany` (RWX) | 여러 노드에서 읽기·쓰기 | NFS·파일 스토리지 |
| `ReadWriteOncePod` | **한 파드**만 | 동시 쓰기를 확실히 막을 때 |

RWO 볼륨을 쓰는 Deployment는 업데이트 때 새 파드와 옛 파드가 동시에 볼륨을 잡으려다 멈출 수 있어 `strategy: Recreate`를 씁니다(다중 노드에서 특히).
:::

## 3단계: StatefulSet — 파드마다 자기 이름과 자기 볼륨

데이터베이스 복제본처럼 **파드마다 다른 데이터**를 가져야 하면 Deployment(모든 파드가 같은 PVC 하나를 공유하거나, 아무 것도 없거나)로는 부족합니다. [[statefulset]]은 파드에 `web-0`, `web-1`처럼 **고정된 이름과 순서**를 주고, `volumeClaimTemplates`로 **파드마다 PVC를 하나씩** 만들어 줍니다. 파드를 이름으로 찾을 수 있도록 Headless Service(`clusterIP: None`)를 함께 만듭니다.

```yaml file=web-sts.yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: lab-i03
spec:
  clusterIP: None              # Headless: 파드마다 DNS 이름 (web-0.web.lab-i03.svc.cluster.local)
  selector: { app: web }
  ports: [{ port: 80, name: http }]
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
  namespace: lab-i03
spec:
  serviceName: web
  replicas: 2
  selector:
    matchLabels: { app: web }
  template:
    metadata:
      labels: { app: web }
    spec:
      containers:
        - name: app
          image: busybox:1.37.0
          # 처음 뜰 때만 자기 이름을 기록, 이후에는 기존 기록을 유지
          command: ["sh", "-c", "[ -f /data/id ] || echo \"$(hostname) 가 처음 만든 데이터\" > /data/id; sleep 3600"]
          volumeMounts:
            - { name: data, mountPath: /data }
  volumeClaimTemplates:          # 파드마다 PVC 하나씩: data-web-0, data-web-1
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 1Gi
```

```bash shell="실습 터미널"
kubectl apply -f web-sts.yaml
kubectl rollout status statefulset/web -n lab-i03 --timeout=180s
kubectl get pods -n lab-i03 -l app=web -o custom-columns='NAME:.metadata.name,STATUS:.status.phase'
kubectl get pvc -n lab-i03 -o custom-columns='NAME:.metadata.name,STATUS:.status.phase,CAPACITY:.status.capacity.storage'
for p in web-0 web-1; do kubectl exec -n lab-i03 $p -- cat /data/id; done
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd)" date="2026-10-24"
service/web created
statefulset.apps/web created
Waiting for 2 pods to be ready...
Waiting for 1 pods to be ready...
Waiting for 1 pods to be ready...
partitioned roll out complete: 2 new pods have been updated...
NAME    STATUS
web-0   Running
web-1   Running
NAME         STATUS   CAPACITY
data-web-0   Bound    1Gi
data-web-1   Bound    1Gi
notes-data   Bound    1Gi
web-0 가 처음 만든 데이터
web-1 가 처음 만든 데이터
```

- 파드 이름은 무작위 해시가 아니라 `web-0`, `web-1`입니다. 순서대로(0 → 1) 만들어집니다.
- PVC는 `<템플릿 이름>-<파드 이름>` = `data-web-0`, `data-web-1`로 파드마다 따로 생겼습니다.

이제 `web-0`을 지워 봅니다. Deployment라면 새 이름의 파드가 생기지만, StatefulSet은 **같은 이름**으로 다시 만들고 **같은 PVC**를 붙입니다. 다른 파드에서 이름으로 찾아갈 수 있는지도 봅니다.

```bash shell="실습 터미널"
kubectl delete pod web-0 -n lab-i03 --wait=true
kubectl wait --for=condition=Ready pod/web-0 -n lab-i03 --timeout=120s
kubectl exec -n lab-i03 web-0 -- cat /data/id
kubectl exec -n lab-i03 web-1 -- nslookup web-0.web.lab-i03.svc.cluster.local 2>/dev/null | grep -A1 '^Name:' | head -2 | sed 's/[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}\.[0-9]\{1,3\}/<파드 IP>/'
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd)" date="2026-10-24"
pod "web-0" deleted from lab-i03 namespace
pod/web-0 condition met
web-0 가 처음 만든 데이터
Name:	web-0.web.lab-i03.svc.cluster.local
Address: <파드 IP>
```

파드는 새로 만들어졌지만(IP는 바뀔 수 있음) 이름·DNS·데이터는 그대로입니다. 이것이 「상태 저장(stateful)」의 뜻입니다.

| | Deployment | StatefulSet |
|---|---|---|
| 파드 이름 | `notes-5d7f…` 무작위 | `web-0`, `web-1` 고정 |
| 만들고 지우는 순서 | 동시에 | 0 → 1 → … (지울 때는 역순) |
| 볼륨 | 모든 파드가 같은 PVC (또는 없음) | `volumeClaimTemplates`로 파드마다 자기 PVC |
| 네트워크 이름 | Service 하나 | Headless Service로 파드마다 DNS 이름 |
| 어울리는 앱 | 웹·API (파드끼리 같음) | DB·메시지 큐·검색 엔진 (파드마다 역할·데이터가 다름) |

## 4단계: 줄여도 볼륨은 남는다, PVC를 지우면 데이터도 지워진다

```bash shell="실습 터미널"
kubectl scale statefulset web -n lab-i03 --replicas=1
kubectl wait --for=delete pod/web-1 -n lab-i03 --timeout=120s
kubectl get pvc data-web-1 -n lab-i03 -o custom-columns='NAME:.metadata.name,STATUS:.status.phase'
kubectl scale statefulset web -n lab-i03 --replicas=2
kubectl wait --for=condition=Ready pod/web-1 -n lab-i03 --timeout=120s
kubectl exec -n lab-i03 web-1 -- cat /data/id
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd)" date="2026-10-24"
statefulset.apps/web scaled
pod/web-1 condition met
NAME         STATUS
data-web-1   Bound
statefulset.apps/web scaled
pod/web-1 condition met
web-1 가 처음 만든 데이터
```

파드 수를 줄여도 `data-web-1`은 지워지지 않고 남아 있다가, 다시 늘리면 `web-1`에 그대로 붙습니다. StatefulSet은 기본으로 PVC를 **지우지 않습니다**(데이터 보호). 반대로 PVC를 사람이 지우면 어떻게 될까요?

```bash shell="실습 터미널"
PV=$(kubectl get pvc notes-data -n lab-i03 -o jsonpath='{.spec.volumeName}')
kubectl delete deployment notes -n lab-i03
kubectl delete pvc notes-data -n lab-i03
sleep 5
kubectl get pv $PV 2>&1 | sed 's/pvc-[0-9a-f-]*/pvc-<notes-data의 PV>/'
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd)" date="2026-10-24"
deployment.apps "notes" deleted from lab-i03 namespace
persistentvolumeclaim "notes-data" deleted from lab-i03 namespace
Error from server (NotFound): persistentvolumes "pvc-<notes-data의 PV>" not found
```

`standard` StorageClass의 회수 정책은 **Delete**라서, PVC를 지우는 순간 PV와 그 안의 데이터가 함께 지워졌습니다. 운영 데이터라면 회수 정책을 `Retain`으로 둔 StorageClass를 쓰거나, 지우기 전에 백업(스냅숏)을 남깁니다.

:::danger 지우기 전에 확인할 것
`kubectl delete namespace`도 그 안의 PVC를 모두 지웁니다. 운영 클러스터에서는 `kubectl get pv -o custom-columns=NAME:.metadata.name,RECLAIM:.spec.persistentVolumeReclaimPolicy,CLAIM:.spec.claimRef.name`으로 회수 정책부터 봅니다.
:::

## 성공 판정

```verify
id: i3-sts-identity
title: StatefulSet 파드를 지워도 같은 이름·같은 데이터로 돌아옴
explain: web-0을 지운 뒤 다시 뜬 web-0이 처음 만든 데이터를 그대로 갖고 있는지 확인합니다.
command: kubectl delete pod web-0 -n lab-i03 --wait=true >/dev/null && kubectl wait --for=condition=Ready pod/web-0 -n lab-i03 --timeout=120s >/dev/null && kubectl exec -n lab-i03 web-0 -- cat /data/id
expect: ^web-0 가 처음 만든 데이터\s*$
criteria: web-0 가 처음 만든 데이터
```

```verify
id: i3-pvc-per-pod
title: 파드마다 PVC가 하나씩 Bound
explain: StatefulSet이 만든 PVC 두 개의 상태를 확인합니다.
command: kubectl get pvc data-web-0 data-web-1 -n lab-i03 -o jsonpath='{range .items[*]}{.metadata.name}={.status.phase} {end}{"\n"}'
expect: ^data-web-0=Bound data-web-1=Bound\s*$
criteria: data-web-0=Bound data-web-1=Bound
```

## 흔한 오류, 진단 순서, 해결 방법

| 증상 | 확인 | 원인과 해결 |
|---|---|---|
| PVC가 계속 `Pending` | `kubectl describe pvc <이름>` 이벤트 | 기본 StorageClass 없음(`storageClassName` 지정), 요청 크기·accessModes를 지원하지 않음, `WaitForFirstConsumer` 클래스라면 파드가 생길 때까지 기다리는 것이 정상 |
| 파드가 `ContainerCreating`에서 멈춤 | `kubectl describe pod` 의 `FailedMount`·`Multi-Attach` | RWO 볼륨을 다른 노드의 파드가 잡고 있음 → `strategy: Recreate`, 옛 파드 종료 확인 |
| PVC를 지웠는데 `Terminating`에서 안 지워짐 | `kubectl get pvc -o yaml`의 `finalizers` | 아직 그 PVC를 쓰는 파드가 있음(사용 중 삭제 방지) → 파드부터 지움 |
| StatefulSet 파드가 하나씩만 뜸 | `kubectl get pods -w` | 정상 — 앞 파드가 Ready여야 다음 파드를 만듦 (`podManagementPolicy: Parallel`로 바꿀 수 있음) |

## 더 깊이: PV·PVC 실습 항해도

이 실습은 쿠버네티스 기본기 한 바퀴 중 「스토리지」 칸입니다. 운영에서 마주치는 나머지는 시리즈의 **PV·PVC 실습 항해도**(허브 [`/pv/`](/pv/))에서 이어집니다.

| 더 알고 싶다면 | PV·PVC 항해도 |
|---|---|
| PV를 직접 만들고 묶는 규칙, `Retain`과 `Released` 복구 | 기본 2 |
| StorageClass 설계 (회수 정책·바인딩 모드·기본 클래스) | 중급 1 |
| StatefulSet PVC 보존 정책 (`persistentVolumeClaimRetentionPolicy`) | 중급 2 |
| CSI 드라이버, 볼륨 확장, `ReadWriteOncePod` | 중급 3 |
| VolumeSnapshot으로 되돌리기, PVC 복제 | 중급 4 |
| NFS로 여러 파드가 공유(RWX), Velero 백업·복구, 스토리지 장애 진단 | 고급 |

이 실습을 마쳤다면 PV·PVC 항해도의 기본 1(첫 PVC)은 복습으로 빠르게 넘어가도 됩니다.

## 정리와 재실행

```bash shell="실습 터미널"
kubectl delete namespace lab-i03
kubectl get pv -o custom-columns='CLAIM:.spec.claimRef.namespace' --no-headers 2>/dev/null | grep -c lab-i03 || true
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · containerd)" date="2026-10-24"
namespace "lab-i03" deleted
0
```

네임스페이스를 지우면 그 안의 PVC(`data-web-0`, `data-web-1`)도 지워지고, 회수 정책 Delete에 따라 PV도 함께 지워집니다.
