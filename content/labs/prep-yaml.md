## 학습 목표

- YAML의 스칼라·목록·맵을 읽고, 들여쓰기 오류를 찾을 수 있습니다.
- 모든 [[manifest|매니페스트]]의 공통 구조(`apiVersion`·`kind`·`metadata`·`spec`)를 압니다.
- `kubectl explain`으로 모르는 필드를 스스로 찾을 수 있습니다.
- KYAML 출력 형식을 읽을 수 있습니다.

## 선수 지식

- 없습니다. 「직접 확인」 명령은 [환경 준비](#/item/setup) 후 실행합니다. 모두 **읽기만** 하고 클러스터를 바꾸지 않습니다.

## 1. YAML의 세 가지 모양

```yaml
name: web                 # 스칼라: 키: 값
replicas: 3               # 숫자
enabled: true             # 불리언
version: "1.30"           # 따옴표: 문자열로 고정 (1.30 → 1.3 숫자로 바뀌는 것 방지)
ports:                    # 목록: 「- 」로 시작
  - 80
  - 443
labels:                   # 맵: 들여쓴 키: 값 묶음
  app: web
  tier: front
containers:               # 맵의 목록 (가장 흔한 모양)
  - name: nginx
    image: nginx:1.30.6-alpine
```

| 규칙 | 지키지 않으면 |
|---|---|
| 들여쓰기는 **공백**(탭 금지), 같은 단계는 같은 칸 | `mapping values are not allowed`, `found character that cannot start any token` |
| `키:` 뒤에는 공백 하나 | `key:value`는 문자열 하나로 읽힘 |
| `- ` 다음 줄의 키는 `-` 뒤 글자에 맞춤 | 목록 항목이 쪼개짐 |
| `yes`·`no`·`on`·`1.30`·`010` 같은 값은 따옴표 | 불리언·숫자·8진수로 바뀔 수 있음 |

한 파일에 여러 객체를 넣을 때는 `---`로 나눕니다.

## 2. 매니페스트의 공통 구조

```yaml
apiVersion: apps/v1       # API 그룹/버전 — 어느 API로 처리할지
kind: Deployment          # 객체 종류
metadata:                 # 이름표: name·namespace·labels·annotations
  name: web
  labels: { app: web }
spec:                     # 원하는 상태 (내가 씀)
  replicas: 2
  ...
status:                   # 현재 상태 (쿠버네티스가 씀 — 직접 쓰지 않음)
```

`{ app: web }`처럼 중괄호로 한 줄에 쓰는 것도 같은 맵입니다(JSON과 호환).

## 3. 들여쓰기 오류 찾기

```yaml file=prep-yaml/broken.yaml
apiVersion: v1
kind: Pod
metadata:
  name: yaml-demo
spec:
  containers:
  - name: web
    image: nginx:1.30.6-alpine
     ports:
    - containerPort: 80
```

```bash shell="실습 터미널"
cd ~/k8s-lab/prep-yaml 2>/dev/null || { mkdir -p ~/k8s-lab/prep-yaml && cd ~/k8s-lab/prep-yaml; }
kubectl apply --dry-run=client -f broken.yaml 2>&1 | sed 's#^.*broken.yaml#broken.yaml#' | head -2
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
broken.yaml: error converting YAML to JSON: yaml: line 9: mapping values are not allowed in this context
```

오류가 가리킨 **9번째 줄(`ports:`) 바로 앞**을 봅니다. `ports:`가 `image:`보다 한 칸 더 들여써져 `image` 값의 일부처럼 읽혔습니다. `ports:`를 `image:`와 같은 칸으로 맞추면 됩니다.

## 4. kubectl explain으로 필드 찾기

```bash shell="실습 터미널"
kubectl explain deployment.spec.replicas | sed -n '1,8p'
kubectl explain pod.spec.containers.imagePullPolicy | grep -m1 -A2 'DESCRIPTION'
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
GROUP:      apps
KIND:       Deployment
VERSION:    v1

FIELD: replicas <integer>


DESCRIPTION:
DESCRIPTION:
    Image pull policy. One of Always, Never, IfNotPresent. Defaults to Always if
    :latest tag is specified, or IfNotPresent otherwise. Cannot be updated. More
```

- `<integer>`, `<string>`, `<[]Object>`(목록), `<map[string]string>` 같은 **타입**을 보면 YAML 모양이 정해집니다.
- `kubectl explain pod.spec --recursive | less`로 전체 필드 트리를 볼 수 있습니다.

## 5. 출력 형식: YAML·JSON·KYAML

`kubectl get ... -o yaml`은 클러스터가 기억하는 객체 전체를 보여 줍니다. 최신 kubectl에는 **KYAML**(Kubernetes용 YAML 방언) 출력도 있습니다. 문자열을 항상 따옴표로 감싸고 목록·맵을 `[]`·`{}`로 써서, 위 1절의 「따옴표 빠뜨림·들여쓰기」 실수가 생기지 않게 만든 형식입니다.

```bash shell="실습 터미널"
kubectl get namespace default -o kyaml 2>&1 | head -8 || true
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
---
{
  apiVersion: "v1",
  kind: "Namespace",
  metadata: {
    creationTimestamp: "2026-10-25T14:27:35Z",
    labels: {
      kubernetes.io/metadata.name: "default",
```

KYAML도 YAML이므로 그대로 `kubectl apply`에 쓸 수 있습니다. 이 과정의 예제는 익숙한 일반 YAML로 씁니다.

## 확인 질문

:::answer 1. `version: 1.30`을 `kubectl apply`했더니 1.3이 들어갔다. 왜?
따옴표가 없어 숫자 1.30(=1.3)으로 읽혔습니다. `"1.30"`처럼 문자열로 씁니다.
:::

:::answer 2. 매니페스트에 status를 써서 apply하면?
`status`는 쿠버네티스가 관리하는 현재 상태라 무시됩니다(대부분 하위 리소스로 따로 갱신). 원하는 상태는 `spec`에 씁니다.
:::

## 정리

```bash shell="실습 터미널"
rm -rf ~/k8s-lab/prep-yaml && echo "정리 완료"
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
정리 완료
```
