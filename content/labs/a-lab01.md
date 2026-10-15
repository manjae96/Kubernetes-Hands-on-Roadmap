## 학습 목표

- [[serviceaccount]]와 [[role]], [[rolebinding]]으로 「한 네임스페이스의 파드와 로그만 읽는」 최소 권한을 만들 수 있습니다.
- `kubectl auth can-i`로 권한을 미리 검사하고, 실제 토큰으로 허용·거부를 확인할 수 있습니다.
- 기본 제공 ClusterRole을 RoleBinding으로 한 네임스페이스에만 재사용할 수 있습니다.

## 선수 지식

- 기본 과정의 kubectl 사용과 네임스페이스 개념
- 인증(Authentication: 누구인가)과 인가(Authorization: 무엇을 할 수 있나)의 차이

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context
kubectl auth can-i '*' '*' --all-namespaces
kubectl get namespace lab-a01
```

`k8s-lab`, `yes`(현재 사용자가 클러스터 관리자), `NotFound`가 나와야 합니다. 이 실습은 `lab-a01` 네임스페이스 안에만 권한 객체를 만들고, 현재 폴더에 `reader.kubeconfig` 파일 하나를 만듭니다.

## 개념: 주체, 동작, 대상을 묶는 세 객체

**무엇인가.** [[rbac]]는 「**누가**(subject) **어떤 자원**(resource)에 **무엇을**(verb) 할 수 있는가」를 정합니다. Role은 허용 목록(자원 + 동작)이고, RoleBinding은 그 목록을 주체에게 연결합니다. 주체는 사람(User·Group) 또는 파드 안의 프로그램이 쓰는 ServiceAccount입니다.

**왜 필요한가.** 로그 수집기, CI 배포 도구, 모니터링 에이전트처럼 API를 호출하는 프로그램이 많습니다. 이들에게 관리자 권한을 주면 하나가 탈취되었을 때 클러스터 전체가 위험해집니다. RBAC는 **허용만 있고 거부 규칙이 없는** 방식이라, 명시적으로 준 것 외에는 모두 거부됩니다.

**어떻게 동작하나.** 요청이 오면 [[kube-apiserver]]가 인증으로 주체를 확인하고, 인가 단계에서 그 주체에 연결된 모든 Binding의 규칙을 합쳐 요청이 허용 목록에 있는지 봅니다. Role·RoleBinding은 네임스페이스에 속하고, ClusterRole·ClusterRoleBinding은 클러스터 전체에 속합니다. **ClusterRole을 RoleBinding으로 연결하면 권한이 그 네임스페이스로 제한**됩니다.

<figure class="diagram">
<svg viewBox="0 0 760 230" role="img" aria-label="ServiceAccount log-reader가 RoleBinding을 통해 Role pod-log-reader의 권한을 lab-a01 네임스페이스 안에서만 얻는 구조">
<defs><marker id="a1a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="arrowhead"/></marker></defs>
<rect class="zone" x="10" y="12" width="740" height="150" rx="8"/><text class="small" x="22" y="30">네임스페이스 lab-a01</text>
<rect class="box accent" x="30" y="60" width="170" height="60" rx="6"/><text x="42" y="84">ServiceAccount</text><text class="mono" x="42" y="104">log-reader</text>
<rect class="box" x="290" y="60" width="180" height="60" rx="6"/><text x="302" y="84">RoleBinding</text><text class="mono" x="302" y="104">log-reader-binding</text>
<rect class="box accent" x="560" y="40" width="175" height="100" rx="6"/><text x="572" y="62">Role pod-log-reader</text>
<text class="mono" x="572" y="86">pods: get list watch</text><text class="mono" x="572" y="106">pods/log: get</text><text class="small" x="572" y="128">그 밖은 모두 거부</text>
<path class="line" d="M288 90H202" marker-end="url(#a1a)"/><text class="small" x="210" y="82">subjects</text>
<path class="line" d="M472 90H558" marker-end="url(#a1a)"/><text class="small" x="482" y="82">roleRef</text>
<rect class="box dim" x="30" y="180" width="300" height="40" rx="6"/><text x="42" y="205">default 네임스페이스의 파드 → 거부</text>
<rect class="box dim" x="350" y="180" width="300" height="40" rx="6"/><text x="362" y="205">lab-a01의 Secret, 파드 삭제 → 거부</text>
</svg>
<figcaption>RoleBinding이 「누구」와 「무엇」을 이어 주며, 효력은 RoleBinding이 있는 네임스페이스로 한정됩니다.</figcaption>
</figure>

## 1단계: 대상 자원 준비

권한을 시험할 파드 하나를 띄웁니다. 5초마다 로그를 남깁니다.

```bash shell="실습 터미널"
kubectl create namespace lab-a01
kubectl run demo -n lab-a01 --image=busybox:1.37.0 -- sh -c 'while true; do echo "주문 처리 $(date +%T)"; sleep 5; done'
```

## 2단계: ServiceAccount, Role, RoleBinding 만들기

`rbac.yaml`로 저장합니다.

```yaml file=rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: log-reader
  namespace: lab-a01
automountServiceAccountToken: false
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-log-reader
  namespace: lab-a01
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: log-reader-binding
  namespace: lab-a01
subjects:
  - kind: ServiceAccount
    name: log-reader
    namespace: lab-a01
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: pod-log-reader
```

| 필드 | 의미 |
|---|---|
| `automountServiceAccountToken: false` | 이 SA를 쓰는 파드에 토큰을 자동으로 넣지 않습니다. 이 실습은 토큰을 직접 발급해 쓰므로 자동 주입이 필요 없습니다. |
| `apiGroups: [""]` | 빈 문자열은 core 그룹(Pod, Service, Secret 등). Deployment라면 `"apps"`입니다. |
| `resources: ["pods/log"]` | 로그는 파드의 **하위 자원**이라 따로 허용해야 합니다. `pods`만 허용하면 `kubectl logs`가 거부됩니다. |
| `verbs` | `get`(하나 조회), `list`(목록), `watch`(변경 구독). 쓰기는 `create`·`update`·`patch`·`delete`입니다. |
| `roleRef` | 연결할 Role. **만든 뒤에는 바꿀 수 없어** 바꾸려면 RoleBinding을 지우고 다시 만듭니다. |

```bash shell="실습 터미널"
kubectl apply -f rbac.yaml
```

## 3단계: kubectl auth can-i로 미리 검사

관리자는 `--as`로 다른 주체를 흉내 내어(impersonation) 권한을 검사할 수 있습니다. ServiceAccount의 사용자 이름은 `system:serviceaccount:<네임스페이스>:<이름>` 형식입니다.

**각 결과를 먼저 예상해 보세요.**

```bash shell="실습 터미널"
SA=system:serviceaccount:lab-a01:log-reader
kubectl auth can-i list pods -n lab-a01 --as=$SA
kubectl auth can-i get pods --subresource=log -n lab-a01 --as=$SA
kubectl auth can-i delete pods -n lab-a01 --as=$SA
kubectl auth can-i list secrets -n lab-a01 --as=$SA
kubectl auth can-i list pods -n default --as=$SA
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
yes
yes
no
no
no
```

허용 목록 전체는 `kubectl auth can-i --list -n lab-a01 --as=$SA`로 봅니다. 출력에 `pods [get list watch]`, `pods/log [get]` 외에 `selfsubjectreviews` 같은 항목도 보이는데, 이는 모든 인증된 사용자에게 기본으로 주어지는 「내 권한 조회」용 권한입니다.

## 4단계: 실제 토큰으로 접속해 보기

`--as`는 관리자가 흉내 낸 결과입니다. 이제 ServiceAccount의 **진짜 토큰**으로 접속합니다. `kubectl create token`은 TokenRequest API로 수명이 짧은 토큰을 발급합니다.

```bash shell="실습 터미널 (bash·zsh)"
TOKEN=$(kubectl create token log-reader -n lab-a01 --duration=10m)
SERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl config view --minify --flatten -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > lab-ca.crt
kubectl config set-cluster k8s-lab --server=$SERVER --certificate-authority=lab-ca.crt --embed-certs --kubeconfig=reader.kubeconfig
kubectl config set-credentials log-reader --token=$TOKEN --kubeconfig=reader.kubeconfig
kubectl config set-context reader --cluster=k8s-lab --user=log-reader --namespace=lab-a01 --kubeconfig=reader.kubeconfig
kubectl config use-context reader --kubeconfig=reader.kubeconfig
rm lab-ca.crt
```

| 명령 | 의미 |
|---|---|
| `--duration=10m` | 10분 뒤 만료되는 토큰. 실습이 길어지면 다시 발급합니다. |
| `--minify --flatten` | 현재 컨텍스트 정보만, 인증서 파일 경로를 데이터로 펼쳐서 보여 줍니다. minikube kubeconfig는 CA를 파일 경로로 저장하기 때문에 필요합니다. |
| `--kubeconfig=reader.kubeconfig` | 원래 `~/.kube/config`를 건드리지 않고 별도 파일에 저장합니다. |

이제 이 파일로 요청합니다.

```bash shell="실습 터미널"
kubectl --kubeconfig=reader.kubeconfig auth whoami
kubectl --kubeconfig=reader.kubeconfig get pods
kubectl --kubeconfig=reader.kubeconfig logs demo --tail=2
kubectl --kubeconfig=reader.kubeconfig delete pod demo
kubectl --kubeconfig=reader.kubeconfig get secrets
kubectl --kubeconfig=reader.kubeconfig get pods -n default
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
ATTRIBUTE                                           VALUE
Username                                            system:serviceaccount:lab-a01:log-reader
UID                                                 5fe0c8e0-bfac-4f40-a2d1-f1fa799c2ff1
Groups                                              [system:serviceaccounts system:serviceaccounts:lab-a01 system:authenticated]
Extra: authentication.kubernetes.io/credential-id   [JTI=552833ef-ef27-4d21-8c04-43ca5f04075e]
NAME   READY   STATUS    RESTARTS   AGE
demo   1/1     Running   0          2s
주문 처리 01:27:50
주문 처리 01:27:55
Error from server (Forbidden): pods "demo" is forbidden: User "system:serviceaccount:lab-a01:log-reader" cannot delete resource "pods" in API group "" in the namespace "lab-a01"
Error from server (Forbidden): secrets is forbidden: User "system:serviceaccount:lab-a01:log-reader" cannot list resource "secrets" in API group "" in the namespace "lab-a01"
Error from server (Forbidden): pods is forbidden: User "system:serviceaccount:lab-a01:log-reader" cannot list resource "pods" in API group "" in the namespace "default"
```

Forbidden 메시지는 **누가, 어떤 동작을, 어떤 자원에, 어느 네임스페이스에서** 거부당했는지 정확히 알려 줍니다. 권한 문제를 진단할 때 이 네 가지를 Role 규칙과 하나씩 대조하면 됩니다. 로그의 시각은 컨테이너의 시간대(UTC) 기준입니다.

:::danger 토큰이 든 파일
`reader.kubeconfig`에는 유효한 토큰이 평문으로 들어 있습니다. 실습 후 반드시 지우고, 실무에서는 토큰을 파일·셸 기록에 남기지 않도록 주의합니다. 토큰은 만료 시각이 지나면 쓸 수 없습니다.
:::

## 5단계: 기본 ClusterRole을 한 네임스페이스에만 재사용

Kubernetes는 `view`, `edit`, `admin`, `cluster-admin` 같은 기본 ClusterRole을 제공합니다. 이를 **RoleBinding**으로 연결하면 그 네임스페이스에서만 효력이 생깁니다.

```bash shell="실습 터미널"
kubectl create serviceaccount auditor -n lab-a01
kubectl create rolebinding auditor-view --clusterrole=view --serviceaccount=lab-a01:auditor -n lab-a01
kubectl auth can-i list deployments -n lab-a01 --as=system:serviceaccount:lab-a01:auditor
kubectl auth can-i list deployments -n default --as=system:serviceaccount:lab-a01:auditor
kubectl auth can-i get secrets -n lab-a01 --as=system:serviceaccount:lab-a01:auditor
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
yes
no
no
```

`view`는 대부분의 자원을 읽을 수 있지만, 권한 상승에 쓰일 수 있는 **Secret 읽기는 의도적으로 빠져** 있습니다.

## 성공 판정

```verify
id: a1-cani
title: 허용 2개, 거부 2개
explain: 파드 목록, 파드 로그, 파드 삭제, Secret 목록에 대한 판정을 한 줄로 출력합니다.
command: for v in "list pods" "get pods --subresource=log" "delete pods" "list secrets"; do kubectl auth can-i $v -n lab-a01 --as=system:serviceaccount:lab-a01:log-reader; done | paste -sd' ' -
expect: ^yes yes no no$
criteria: yes yes no no
```

```verify
id: a1-token
title: 발급 토큰의 신원
explain: reader.kubeconfig로 접속했을 때 API 서버가 인식한 사용자 이름을 출력합니다. 토큰이 만료되었다면 4단계 첫 줄부터 다시 실행하세요.
command: kubectl --kubeconfig=reader.kubeconfig auth whoami -o jsonpath='{.status.userInfo.username}{"\n"}'
expect: ^system:serviceaccount:lab-a01:log-reader$
criteria: system:serviceaccount:lab-a01:log-reader
```

## 흔한 오류, 진단 순서, 해결 방법

진단 순서: **Forbidden 메시지에서 주체·동작·자원·네임스페이스 읽기 → `kubectl auth can-i ... --as`로 재현 → `kubectl get rolebinding -n <ns> -o wide`로 연결 확인 → `kubectl describe role`로 규칙 확인**.

| 증상 | 확인 명령 | 원인과 해결 |
|---|---|---|
| `kubectl logs`만 Forbidden | `kubectl auth can-i get pods --subresource=log --as=...` | `pods/log` 하위 자원 규칙이 없습니다. |
| Deployment 조회가 Forbidden | `kubectl describe role ...` | `apiGroups`가 `""`입니다. Deployment는 `"apps"` 그룹입니다. |
| Role이 있는데도 전부 거부 | `kubectl get rolebinding -n lab-a01 -o wide` | 바인딩의 subject 이름·네임스페이스 오타, 또는 RoleBinding이 다른 네임스페이스에 있습니다. |
| `error: You must be logged in to the server (Unauthorized)` | 토큰 만료 시각 | 인증 실패(401)입니다. 인가(403)와 다릅니다. 토큰을 다시 발급합니다. |
| RoleBinding의 roleRef 변경이 거부됨 | `kubectl apply` 오류 메시지 | roleRef는 변경할 수 없는 필드입니다. 지우고 다시 만듭니다. |
| `--as` 사용 시 Forbidden (impersonate) | `kubectl auth can-i impersonate serviceaccounts` | 현재 사용자에게 흉내 내기 권한이 없습니다. minikube 기본 사용자는 관리자라 해당 없습니다. |

## 응용 과제

**과제 1.** log-reader가 같은 네임스페이스의 Deployment 목록도 볼 수 있게 Role을 고치세요. 바꾼 뒤 `can-i`로 확인합니다.

:::answer 해설
규칙을 하나 추가합니다.

```yaml
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
```

apply 후 `kubectl auth can-i list deployments -n lab-a01 --as=system:serviceaccount:lab-a01:log-reader`가 `yes`입니다. Role 변경은 즉시 반영되며 토큰을 다시 받을 필요가 없습니다.
:::

**과제 2.** 「모든 네임스페이스의 파드 로그를 읽는」 권한이 필요하다면 어떤 객체 조합을 써야 하나요? 그 권한이 왜 위험할 수 있나요?

:::answer 해설
같은 규칙을 가진 ClusterRole과 ClusterRoleBinding이 필요합니다. 로그에는 요청 내용, 토큰, 개인정보가 섞여 들어갈 수 있으므로 클러스터 전체 로그 읽기는 사실상 민감 정보 접근 권한입니다. 꼭 필요한 네임스페이스마다 RoleBinding을 만드는 편이 안전합니다.
:::

**과제 3.** log-reader를 쓰는 파드를 만들고(`serviceAccountName: log-reader`), 컨테이너 안에 토큰이 마운트되는지 확인하세요. `automountServiceAccountToken`을 어디에 설정하면 파드별로 바꿀 수 있나요?

:::answer 해설
SA에 `false`를 줬으므로 `/var/run/secrets/kubernetes.io/serviceaccount/`가 생기지 않습니다. 파드 스펙의 `spec.automountServiceAccountToken: true`가 SA 설정보다 우선하므로 파드별로 켤 수 있습니다. API를 호출하지 않는 앱은 끄는 것이 좋습니다.
:::

## 정리와 재실행

이 실습은 네임스페이스 안의 객체와 로컬 파일 하나를 만들었습니다.

```bash shell="실습 터미널"
kubectl delete namespace lab-a01
rm -f reader.kubeconfig
kubectl get namespace lab-a01
```

네임스페이스를 지우면 그 안의 ServiceAccount·Role·RoleBinding도 함께 지워지고, 발급한 토큰은 ServiceAccount가 사라지는 즉시 쓸 수 없게 됩니다. 다시 하려면 1단계부터 반복합니다.
