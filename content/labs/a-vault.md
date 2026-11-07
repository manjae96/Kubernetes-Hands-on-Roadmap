## 학습 목표

- Vault를 **dev 모드가 아닌** 구성(Raft 저장소)으로 띄우고 init·unseal·봉인의 의미를 설명할 수 있습니다.
- Pod가 **ServiceAccount 토큰(audience 지정)** 으로 Vault에 로그인해, 최소 권한 policy가 붙은 **짧은 토큰**으로 비밀 하나만 읽게 만들 수 있습니다.
- 잘못된 role·ServiceAccount·audience, 토큰 만료, 봉인 상태를 **오류 코드와 메시지로 구분**할 수 있습니다.
- audit 로그에 비밀값이 평문으로 남지 않는 것을 직접 확인하고, root 토큰을 폐기할 수 있습니다.

## 선수 지식

- 개념은 심화 노트 [[vault]]에 있습니다(봉인·auth method·role·policy·TTL·audit, 운영 구성). 여기서는 반복하지 않고 실습만 합니다.
- Secret·RBAC·ServiceAccount — [RBAC와 ServiceAccount로 최소 권한 부여](#/item/a-lab01), Secret이 base64일 뿐인 이유는 [[encryption]]
- 이 과정은 **선택 심화**입니다. 필수 과정·캡스톤 진행에 필요하지 않습니다.

:::note 검증 범위
**minikube v1.38.1(docker 드라이버·containerd) · Kubernetes v1.37.0 · Vault 2.2.1(`hashicorp/vault:2.2.1`, Raft 저장소 1노드, TLS 끔)** 에서 아래 명령을 처음부터 끝까지 실행했고, 출력 블록은 그 결과입니다(2026-11-02). 토큰·비밀값은 출력에서 가렸고(`****`), 실습 중 만든 키·토큰은 확인 뒤 클러스터와 함께 지웠습니다. **TLS·Raft 3노드·자동 봉인 해제·Vault Agent Injector·CSI 드라이버는 실행하지 않았습니다**(개념은 [[vault]]). 이 구성은 실습용이며 운영 구성이 아닙니다.
:::

:::warn 비밀을 다루는 규칙
- unseal 키와 root 토큰은 `~/vault-lab/init.json`(권한 600)에만 둡니다. 화면 캡처·메모·채팅·저장소에 붙이지 않고, 실습이 끝나면 파일째 지웁니다.
- 토큰을 명령줄 인자(`VAULT_TOKEN=hvs.… vault …`)로 넘기지 않습니다 — 다른 사용자가 `ps`로 볼 수 있습니다. 아래 명령은 표준 입력으로 넘깁니다.
- 실습용 비밀값은 `openssl rand`로 만든 무작위 값입니다. 진짜 비밀번호를 넣지 마세요.
:::

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context        # k8s-lab 이어야 함
kubectl get storageclass              # 기본(default) StorageClass가 있어야 Raft 볼륨이 생김
which jq openssl                      # 둘 다 경로가 나와야 함 (macOS 기본 포함)
mkdir -p ~/vault-lab && cd ~/vault-lab && umask 077
```

Vault 서버 이미지(약 190MB)를 받습니다. 메모리는 200MB 안팎이면 충분합니다.

## 1단계: Vault 서버 (Raft, dev 모드 아님)

```yaml file=vault.yaml
apiVersion: v1
kind: Namespace
metadata: { name: lab-vault }
---
apiVersion: v1
kind: ServiceAccount
metadata: { name: vault, namespace: lab-vault }
---
# Vault가 Pod의 토큰을 TokenReview API로 확인하려면 이 권한이 필요
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata: { name: lab-vault-auth-delegator }
roleRef: { apiGroup: rbac.authorization.k8s.io, kind: ClusterRole, name: system:auth-delegator }
subjects: [{ kind: ServiceAccount, name: vault, namespace: lab-vault }]
---
apiVersion: v1
kind: ConfigMap
metadata: { name: vault-config, namespace: lab-vault }
data:
  vault.hcl: |
    # 실습용 단일 노드 구성. 운영은 TLS 필수, Raft 노드 3·5개, 자동 봉인 해제(auto-unseal) 검토
    ui            = false
    disable_mlock = true
    api_addr      = "http://vault.lab-vault.svc:8200"
    cluster_addr  = "http://vault-0.vault-internal.lab-vault.svc:8201"
    storage "raft" {
      path    = "/vault/data"
      node_id = "vault-0"
    }
    listener "tcp" {
      address     = "0.0.0.0:8200"
      tls_disable = 1          # 실습만. 운영에서 끄면 토큰·비밀이 평문으로 오감
    }
---
apiVersion: v1
kind: Service
metadata: { name: vault, namespace: lab-vault }
spec: { selector: { app: vault }, ports: [{ name: http, port: 8200 }] }
---
apiVersion: v1
kind: Service
metadata: { name: vault-internal, namespace: lab-vault }
spec: { clusterIP: None, selector: { app: vault }, ports: [{ name: cluster, port: 8201 }] }
---
apiVersion: apps/v1
kind: StatefulSet
metadata: { name: vault, namespace: lab-vault }
spec:
  serviceName: vault-internal
  replicas: 1
  selector: { matchLabels: { app: vault } }
  template:
    metadata: { labels: { app: vault } }
    spec:
      serviceAccountName: vault
      containers:
      - name: vault
        image: hashicorp/vault:2.2.1
        args: ["server"]   # 이미지 entrypoint가 -config=/vault/config 를 붙임
        env: [{ name: VAULT_ADDR, value: "http://127.0.0.1:8200" }]
        ports: [{ containerPort: 8200 }, { containerPort: 8201 }]
        readinessProbe: { httpGet: { path: "/v1/sys/health?standbyok=true&sealedcode=204&uninitcode=204", port: 8200 }, periodSeconds: 5 }
        volumeMounts: [{ name: config, mountPath: /vault/config }, { name: data, mountPath: /vault/data }]
      volumes: [{ name: config, configMap: { name: vault-config } }]
  volumeClaimTemplates:
  - metadata: { name: data }
    spec: { accessModes: [ReadWriteOnce], resources: { requests: { storage: 1Gi } } }
```

`args`에 `-config=/vault/config/vault.hcl`을 또 적으면 같은 설정을 두 번 읽어 `listen tcp4 0.0.0.0:8200: bind: address already in use`로 재시작을 반복합니다(검증 중 실제로 겪음). readiness는 봉인·미초기화 상태도 준비로 봅니다(`sealedcode=204`) — 그래야 Service로 init·unseal 상태를 볼 수 있습니다.

```bash shell="실습 터미널"
kubectl apply -f vault.yaml
kubectl -n lab-vault rollout status sts/vault --timeout=180s
kubectl -n lab-vault exec vault-0 -- vault status | grep -E "Version|Storage Type|Initialized|Sealed"
```

```output kind=verified env="검증 환경 (minikube v1.38.1 · Kubernetes v1.37.0 · Vault 2.2.1)" date="2026-11-02"
partitioned roll out complete: 1 new pods have been updated...
command terminated with exit code 2
Initialized             false
Sealed                  true
Version                 2.2.1
Storage Type            raft
```

`exit code 2`는 오류가 아니라 「봉인됨」을 뜻하는 `vault status`의 종료 코드입니다(0 = 열림, 1 = 오류, 2 = 봉인).

## 2단계: init과 unseal, root 토큰은 파일에만

init은 처음 한 번만 하는 초기화로, unseal 키 조각과 root 토큰(모든 권한을 가진 첫 관리 토큰)을 돌려줍니다. unseal(봉인 해제)은 그 키 조각을 정해진 개수(임계값)만큼 넣어, 저장된 데이터를 풀 열쇠를 메모리에 다시 만드는 일입니다(자세한 원리는 [[vault]]). 실습이라 키를 1조각·임계값 1로 만듭니다. 운영 기본은 5조각·임계값 3(서로 다른 사람이 나눠 보관)이거나 KMS·HSM 자동 봉인 해제입니다.

```bash shell="실습 터미널"
kubectl -n lab-vault exec vault-0 -- vault operator init -key-shares=1 -key-threshold=1 -format=json > init.json
ls -l init.json | cut -c1-10                     # -rw------- 이어야 함
jq '{unseal_keys: (.unseal_keys_b64 | length), threshold: .unseal_threshold}' init.json   # 키 자체는 출력하지 않음
jq -r '.unseal_keys_b64[0]' init.json | kubectl -n lab-vault exec -i vault-0 -- sh -c 'vault operator unseal "$(cat)"' | grep -E "^(Sealed|HA Enabled)"
jq -r '.root_token' init.json | kubectl -n lab-vault exec -i vault-0 -- vault login -no-print -
kubectl -n lab-vault exec vault-0 -- vault token lookup -format=json | jq '.data | {display_name, policies, ttl}'
```

```output kind=verified env="검증 환경 (Vault 2.2.1)" date="2026-11-02"
-rw-------
{
  "unseal_keys": 1,
  "threshold": 1
}
Sealed                  false
HA Enabled              true
{
  "display_name": "root",
  "policies": [
    "root"
  ],
  "ttl": 0
}
```

`vault login -`는 표준 입력으로 토큰을 받아 **Vault 컨테이너 안**의 `~/.vault-token`에만 저장합니다. root 토큰은 `ttl 0`(만료 없음) · 모든 권한이므로 설정을 마치면 7단계에서 폐기합니다.

## 3단계: audit, 비밀, 최소 권한 policy

```text file=app-read.hcl
# 이 경로의 읽기만 허락 (나머지는 기본 거부)
path "secret/data/app/db" {
  capabilities = ["read"]
}
```

```bash shell="실습 터미널"
kubectl -n lab-vault exec vault-0 -- vault audit enable file file_path=/vault/data/audit.log
kubectl -n lab-vault exec vault-0 -- vault secrets enable -path=secret kv-v2
openssl rand -hex 12 > db-password.txt           # 실습용 무작위 비밀값 (화면에 출력하지 않음)
kubectl -n lab-vault exec -i vault-0 -- sh -c 'vault kv put -mount=secret app/db username=app password="$(cat)" >/dev/null && echo stored' < db-password.txt
kubectl -n lab-vault exec -i vault-0 -- vault policy write app-read - < app-read.hcl
```

```output kind=verified env="검증 환경 (Vault 2.2.1)" date="2026-11-02"
Success! Enabled the file audit device at: file/
Success! Enabled the kv-v2 secrets engine at: secret/
stored
Success! Uploaded policy: app-read
```

kv **v2**는 API 경로에 `data/`가 붙습니다. CLI의 `-mount=secret app/db`는 `secret/data/app/db`로 바뀌므로 policy도 그 경로로 씁니다(`secret/app/db`로 쓰면 읽기가 403).

## 4단계: Kubernetes 인증과 role

```bash shell="실습 터미널"
kubectl -n lab-vault exec vault-0 -- vault auth enable kubernetes
kubectl -n lab-vault exec vault-0 -- vault write auth/kubernetes/config kubernetes_host=https://kubernetes.default.svc:443
kubectl -n lab-vault exec vault-0 -- vault write auth/kubernetes/role/app \
  bound_service_account_names=app bound_service_account_namespaces=lab-app \
  audience=vault token_policies=app-read token_ttl=60s token_max_ttl=120s
kubectl -n lab-vault exec vault-0 -- vault read -format=json auth/kubernetes/role/app | jq -c '.data | {bound_service_account_names, bound_service_account_namespaces, audience, token_policies, token_ttl, token_max_ttl}'
```

```output kind=verified env="검증 환경 (Vault 2.2.1)" date="2026-11-02"
Success! Enabled kubernetes auth method at: kubernetes/
Success! Data written to: auth/kubernetes/config
Success! Data written to: auth/kubernetes/role/app
{"bound_service_account_names":["app"],"bound_service_account_namespaces":["lab-app"],"audience":"vault","token_policies":["app-read"],"token_ttl":60,"token_max_ttl":120}
```

`kubernetes_host`만 적으면 Vault는 **자기 Pod의 ServiceAccount 토큰과 CA**로 TokenReview를 부릅니다(Vault가 클러스터 안에 있을 때). TTL 60초는 만료를 눈으로 보려고 일부러 짧게 잡았습니다.

## 5단계: Pod에서 로그인하고 비밀 읽기

ServiceAccount `app`(허용)과 `other`(허용 안 함) Pod를 띄웁니다. 둘 다 **audience가 `vault`인 프로젝션 토큰**을 따로 마운트합니다. 기본으로 마운트되는 토큰은 API 서버용 audience라 Vault role과 맞지 않습니다.

```yaml file=app.yaml
apiVersion: v1
kind: Namespace
metadata: { name: lab-app }
---
apiVersion: v1
kind: ServiceAccount
metadata: { name: app, namespace: lab-app }
---
apiVersion: v1
kind: ServiceAccount
metadata: { name: other, namespace: lab-app }
---
apiVersion: v1
kind: Pod
metadata: { name: app, namespace: lab-app }
spec:
  serviceAccountName: app
  containers:
  - name: client
    image: hashicorp/vault:2.2.1        # vault CLI만 클라이언트로 씀 (서버로 띄우지 않음)
    command: ["sleep", "3600"]
    env: [{ name: VAULT_ADDR, value: "http://vault.lab-vault.svc:8200" }]
    volumeMounts: [{ name: vault-token, mountPath: /var/run/secrets/vault, readOnly: true }]
  volumes:
  - name: vault-token
    projected:
      sources:
      - serviceAccountToken: { path: token, audience: vault, expirationSeconds: 600 }
---
apiVersion: v1
kind: Pod
metadata: { name: other, namespace: lab-app }
spec:
  serviceAccountName: other
  containers:
  - name: client
    image: hashicorp/vault:2.2.1
    command: ["sleep", "3600"]
    env: [{ name: VAULT_ADDR, value: "http://vault.lab-vault.svc:8200" }]
    volumeMounts: [{ name: vault-token, mountPath: /var/run/secrets/vault, readOnly: true }]
  volumes:
  - name: vault-token
    projected:
      sources:
      - serviceAccountToken: { path: token, audience: vault, expirationSeconds: 600 }
```

```bash shell="실습 터미널"
kubectl apply -f app.yaml
kubectl -n lab-app wait --for=condition=Ready pod/app pod/other --timeout=120s
kubectl -n lab-app exec app -- sh -c '
  vault write -field=token auth/kubernetes/login role=app jwt=@/var/run/secrets/vault/token > /tmp/t
  export VAULT_TOKEN=$(cat /tmp/t)
  vault token lookup -format=json | grep -E "\"(display_name|path|ttl)\""
  vault kv get -mount=secret -field=username app/db; echo
  vault kv get -mount=secret -field=password app/db | wc -c'
```

```output kind=verified env="검증 환경 (Vault 2.2.1)" date="2026-11-02"
namespace/lab-app created
serviceaccount/app created
serviceaccount/other created
pod/app created
pod/other created
pod/app condition met
pod/other condition met
    "display_name": "kubernetes-lab-app-app",
    "path": "auth/kubernetes/login",
    "ttl": 59,
app
24
```

비밀번호는 화면에 내지 않고 길이(24자)만 봅니다. 토큰은 Pod 안의 `/tmp/t`에만 있고 Pod가 지워지면 함께 없어집니다.

**policy 밖은 모두 거부** — 같은 토큰으로 쓰기와 다른 경로 읽기:

```bash shell="실습 터미널"
kubectl -n lab-app exec app -- sh -c 'export VAULT_TOKEN=$(cat /tmp/t)
  vault kv put -mount=secret app/db password=changed 2>&1 | grep -E "Code|denied"
  vault kv get -mount=secret app/other 2>&1 | grep -E "Code|denied"'
```

```output kind=verified env="검증 환경 (Vault 2.2.1)" date="2026-11-02"
Code: 403. Errors:
	* permission denied
Code: 403. Errors:
	* permission denied
```

## 6단계: 장애와 만료

**① 토큰 만료** — TTL 60초가 지난 뒤 같은 토큰:

```bash shell="실습 터미널"
sleep 65
kubectl -n lab-app exec app -- sh -c 'VAULT_TOKEN=$(cat /tmp/t) vault kv get -mount=secret app/db 2>&1 | grep -E "Code|denied|invalid"'
```

```output kind=verified env="검증 환경 (Vault 2.2.1)" date="2026-11-02"
Code: 403. Errors:
	* permission denied
	* invalid token
```

앱은 만료 전에 갱신(`vault token renew`, `token_max_ttl`까지)하거나 다시 로그인합니다. Vault Agent가 이 일을 대신해 줍니다.

**② 잘못된 role · ③ 잘못된 ServiceAccount · ④ 잘못된 audience**

```bash shell="실습 터미널"
kubectl -n lab-app exec app -- vault write auth/kubernetes/login role=ap jwt=@/var/run/secrets/vault/token 2>&1 | grep -E "Code|\* "
kubectl -n lab-app exec other -- vault write auth/kubernetes/login role=app jwt=@/var/run/secrets/vault/token 2>&1 | grep -E "Code|\* "
kubectl -n lab-app exec app -- vault write auth/kubernetes/login role=app jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token 2>&1 | grep -E "Code|\* "
```

```output kind=verified env="검증 환경 (Vault 2.2.1)" date="2026-11-02"
Code: 400. Errors:
* invalid role name "ap"
Code: 403. Errors:
* service account name not authorized
Code: 403. Errors:
* invalid audience (aud) claim: audience claim does not match any expected audience
```

| 오류 | 어디를 고치나 |
|---|---|
| `400 invalid role name` | 로그인 요청의 `role=` (앱 설정) |
| `403 service account name not authorized` | Pod의 `serviceAccountName` 또는 role의 `bound_service_account_names` |
| `403 invalid audience (aud) claim` | 프로젝션 토큰의 `audience` 또는 role의 `audience` — 기본 SA 토큰을 쓰고 있지 않은지 |
| `403 permission denied` + `invalid token` | 토큰 만료·폐기 → 다시 로그인 |
| `403 permission denied`만 | policy에 경로·동작 없음 (kv v2의 `data/`·`metadata/` 경로 확인) |

**⑤ 재시작하면 봉인** — Vault는 종료할 때 봉인되고, 다시 뜨면 unseal 전까지 요청을 받지 않습니다.

```bash shell="실습 터미널"
kubectl -n lab-vault delete pod vault-0
sleep 5
kubectl -n lab-vault wait --for=condition=Ready pod/vault-0 --timeout=120s
until kubectl -n lab-app exec app -- vault status >/dev/null 2>&1 || [ $? -eq 2 ]; do sleep 2; done   # 2 = 응답은 왔고 봉인 상태
kubectl -n lab-vault exec vault-0 -- vault status | grep -E "^Sealed"
kubectl -n lab-app exec app -- vault write auth/kubernetes/login role=app jwt=@/var/run/secrets/vault/token 2>&1 | grep -E "Code|\* "
jq -r '.unseal_keys_b64[0]' init.json | kubectl -n lab-vault exec -i vault-0 -- sh -c 'vault operator unseal "$(cat)"' | grep -E "^Sealed"
kubectl -n lab-app exec app -- sh -c 'VAULT_TOKEN=$(vault write -field=token auth/kubernetes/login role=app jwt=@/var/run/secrets/vault/token) vault kv get -mount=secret -field=username app/db'
```

```output kind=verified env="검증 환경 (Vault 2.2.1)" date="2026-11-02"
pod "vault-0" deleted from lab-vault namespace
pod/vault-0 condition met
command terminated with exit code 2
Sealed                  true
Code: 503. Errors:
* Vault is sealed
Sealed                  false
app
```

**결론** — 다시 뜬 Vault는 데이터를 그대로 갖고 있지만, unseal 전까지는 모든 요청을 503 「Vault is sealed」로 거절합니다.

- **본 것**: 새 Pod는 Ready인데 `Sealed true`이고, 앱의 로그인은 `Code: 503 … Vault is sealed`였습니다. unseal 뒤에는 같은 로그인으로 `app`을 읽었습니다.
- **왜**: 데이터를 풀 열쇠는 메모리에만 있어 프로세스가 끝나면 사라집니다. 데이터는 Raft 저장소(Vault가 자체로 쓰는 저장 방식, 여기서는 PVC)에 암호화된 채 남아 있으므로, unseal로 열쇠를 다시 만들면 그대로 읽힙니다.
- **확인**: `vault status`의 `Sealed` 줄(종료 코드 2 = 봉인).
- **주의**: `until` 줄은 새 Pod가 Service 뒤에 붙을 때까지 기다립니다. 검증에서 이 줄 없이 바로 로그인하면 엔드포인트가 아직 비어 `connect: connection refused`가 났습니다(503 「봉인됨」과 다른 증상). 운영에서는 사람이 매번 unseal하지 않도록 자동 봉인 해제(auto-unseal)를 씁니다.

## 7단계: audit 로그와 root 토큰 폐기

```bash shell="실습 터미널"
kubectl -n lab-vault exec vault-0 -- cat /vault/data/audit.log > audit.log
wc -l < audit.log
grep -c -F -f db-password.txt audit.log          # 진짜 비밀값이 몇 번 나오나
jq -c 'select(.type=="response" and .request.path=="secret/data/app/db" and .request.operation=="read" and .response.data != null)
  | {data: (.response.data.data | map_values(.[0:24] + "…")), client_token: (.auth.client_token[0:24] + "…")}' audit.log | head -1
```

```output kind=verified env="검증 환경 (Vault 2.2.1) — 5·6단계 직후, 재시작 시나리오 전" date="2026-11-02"
      46
0
{"data":{"password":"hmac-sha256:aeb1e8696e14…","username":"hmac-sha256:6aba7162714f…"},"client_token":"hmac-sha256:6fecaccecaf1…"}
```

**결론** — audit 로그는 누가 무엇을 읽었는지는 남기지만, 비밀값은 **HMAC 값**으로만 남깁니다. 로그 파일만으로는 비밀값을 알 수 없습니다.

- **본 것**: 실습 비밀번호가 그대로 나온 줄은 0개이고, 읽기 응답의 `password`·`username`·`client_token`은 모두 `hmac-sha256:…`입니다.
- **왜**: HMAC은 Vault가 가진 열쇠를 넣어 만든 해시입니다. 같은 값이면 같은 HMAC이 나오지만, HMAC에서 원래 값을 되돌릴 수는 없습니다.
- **확인**: 「이 토큰이 이 값을 읽었나」를 조사할 때는 의심 값을 Vault에 넣어 같은 방식의 HMAC을 받은 뒤 로그와 대조합니다 — `vault write sys/audit-hash/file input=…`.
- 줄 수는 실습을 어디까지 했는지에 따라 다릅니다.

이제 설정이 끝났으니 root 토큰을 폐기합니다. 다시 관리 권한이 필요하면 unseal 키 보유자들이 `vault operator generate-root`로 새로 만듭니다.

```bash shell="실습 터미널"
kubectl -n lab-vault exec vault-0 -- vault token revoke -self
kubectl -n lab-vault exec vault-0 -- vault token lookup 2>&1 | grep -E "Code|\* "
```

```output kind=verified env="검증 환경 (Vault 2.2.1)" date="2026-11-02"
Success! Revoked token (if it existed)
Code: 403. Errors:
* 2 errors occurred:
	* permission denied
	* invalid token
```

## 흔한 오류

| 증상 | 원인 | 확인·해결 |
|---|---|---|
| Pod가 `CrashLoopBackOff`, 로그에 `address already in use` | 설정 파일을 두 번 읽음(`-config` 중복) | `args: ["server"]`만 |
| `Vault is sealed` (503) | 재시작 후 unseal 안 함 | `vault operator unseal`, 운영은 auto-unseal |
| `connect: connection refused` (Service 주소) | 새 Pod가 아직 엔드포인트에 없음 · readiness 실패 | `kubectl -n lab-vault get endpointslice` |
| 로그인 시 `permission denied … tokenreviews` | Vault SA에 `system:auth-delegator` 없음 | ClusterRoleBinding 확인 |
| `invalid audience (aud) claim` | 기본 SA 토큰 사용, 프로젝션 토큰 audience 불일치 | `audience: vault` 프로젝션 볼륨 |
| `permission denied`(policy 맞게 썼는데) | kv v2 경로에 `data/` 빠짐 | 읽기는 `secret/data/<경로>`, 목록·메타데이터는 `secret/metadata/<경로>` |
| PVC `Pending` | 기본 StorageClass 없음 | `kubectl get storageclass` |
| 모든 요청이 갑자기 실패 | audit 장치 쓰기 실패(디스크 가득) — Vault는 기록 못 하면 거부 | audit 장치 2개, 디스크 감시 |

## 성공 판정

```verify
id: vault-k8s-read
title: Pod가 ServiceAccount로 로그인해 허락된 비밀만 읽음
explain: 5단계 뒤(봉인이 풀린 상태에서) 실행합니다. 새로 로그인해 username 필드만 읽습니다.
command: kubectl -n lab-app exec app -- sh -c 'VAULT_TOKEN=$(vault write -field=token auth/kubernetes/login role=app jwt=@/var/run/secrets/vault/token) vault kv get -mount=secret -field=username app/db'
expect: ^app$
criteria: app
```

```verify
id: vault-audit-hmac
title: audit 로그에 기록은 있고 비밀값 평문은 없음
explain: 「HMAC 값이 나온 줄 수」와 「실습 비밀값이 나온 줄 수」를 출력합니다. 앞은 1 이상, 뒤는 0이어야 합니다.
command: L=$(kubectl -n lab-vault exec vault-0 -- cat /vault/data/audit.log); echo "$(printf '%s\n' "$L" | grep -c hmac-sha256) $(printf '%s\n' "$L" | grep -c -F -f ~/vault-lab/db-password.txt)"
expect: ^[1-9][0-9]* 0$
criteria: 「67 0」처럼 앞은 1 이상, 뒤는 0
```

## 정리

```bash shell="실습 터미널" run=skip
kubectl delete namespace lab-app lab-vault          # PVC(Raft 데이터)도 함께 지워짐
kubectl delete clusterrolebinding lab-vault-auth-delegator
rm -rf ~/vault-lab                                  # unseal 키·root 토큰·비밀값·audit 사본
kubectl get pv | grep lab-vault || echo "PV 없음"
```

검증에서 위 순서로 지운 뒤 두 네임스페이스·ClusterRoleBinding·PV가 남지 않은 것을 확인했습니다.

## 체크리스트

- [ ] dev 모드가 운영 구성이 아닌 이유(메모리 저장·자동 unseal·root 토큰 노출·TLS 꺼짐)를 말할 수 있다
- [ ] unseal 키·root 토큰을 파일(600)에만 두고 명령줄 인자로 넘기지 않았다
- [ ] role의 SA 이름·네임스페이스·audience 세 가지를 장애 메시지로 구분할 수 있다
- [ ] policy에 적지 않은 동작·경로가 403이 되는 것을 확인했다
- [ ] 토큰 TTL이 지나면 `invalid token`이 되는 것을 확인했다
- [ ] audit 로그에서 비밀값이 HMAC으로만 남는 것을 확인했다
- [ ] root 토큰을 폐기하고 실습 파일을 지웠다
