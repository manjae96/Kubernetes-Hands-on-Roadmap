## 학습 목표

- [[configmap]]으로 설정 값과 설정 파일을, [[secret]]으로 민감한 값을 컨테이너에 주입할 수 있습니다.
- 설정을 바꿨을 때 파일로 주입한 값과 환경 변수로 주입한 값이 각각 언제 반영되는지 설명할 수 있습니다.
- [[startup]], [[readiness]], [[liveness]] 프로브의 차이를 이해하고, 준비되지 않은 파드가 트래픽에서 빠지는 것을 확인할 수 있습니다.

## 선수 지식

- [롤링 업데이트·로그·이벤트](#/item/b-lab02)까지의 기본 과정 내용
- nginx 설정 파일을 몰라도 됩니다. 필요한 부분은 표로 설명합니다.

## 실습 환경 점검

```bash shell="실습 터미널"
kubectl config current-context
kubectl get nodes
kubectl get namespace lab-i01
```

`k8s-lab`, `Ready`, 그리고 `NotFound`가 나와야 합니다.

## 개념: 이미지는 그대로, 설정은 밖에서

**무엇인가.** 같은 이미지를 개발·운영 환경에서 다르게 동작시키려면 설정을 이미지 밖에 둬야 합니다. [[configmap]]은 일반 설정을, [[secret]]은 비밀번호·토큰을 담습니다. 둘 다 파드에 **환경 변수** 또는 **볼륨(파일)**로 주입합니다.

**왜 필요한가.** 설정이 바뀔 때마다 이미지를 다시 빌드하면 느리고, 비밀번호가 이미지에 남는 사고가 생깁니다. Secret을 따로 두면 RBAC로 읽을 수 있는 사람을 제한할 수 있습니다.

:::danger Secret은 기본적으로 암호화가 아닙니다
Secret 값은 base64로 **인코딩**되어 저장될 뿐입니다. 누구나 디코딩할 수 있습니다. 실제 운영에서는 Secret 읽기 권한을 RBAC로 제한하고, etcd 저장 시 암호화(encryption at rest)를 설정하고, Secret을 매니페스트 저장소에 평문으로 커밋하지 않아야 합니다.
:::

**프로브는 어떻게 동작하나.** [[kubelet]]이 정해진 주기로 컨테이너를 검사합니다([[probe]]).

| 프로브 | 실패하면 | 언제 쓰나 |
|---|---|---|
| startupProbe | 성공 전까지 다른 프로브를 멈춤. 끝내 실패하면 재시작 | 기동이 오래 걸리는 앱 |
| readinessProbe | **Service 엔드포인트에서 제외**. 재시작하지 않음 | 일시적으로 요청을 받으면 안 될 때 (기동 중, 의존 서비스 장애) |
| livenessProbe | **컨테이너 재시작** | 교착 상태처럼 스스로 회복 못 하는 고장 |

<figure class="diagram">
<svg viewBox="0 0 760 250" role="img" aria-label="ConfigMap과 Secret이 파드에 파일과 환경 변수로 주입되고, kubelet이 프로브 결과로 엔드포인트와 재시작을 결정하는 구성도">
<defs><marker id="i1a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="arrowhead"/></marker></defs>
<rect class="box accent" x="10" y="20" width="170" height="44" rx="6"/><text x="22" y="47">ConfigMap web-html</text>
<rect class="box accent" x="10" y="74" width="170" height="44" rx="6"/><text x="22" y="101">ConfigMap web-nginx-conf</text>
<rect class="box accent" x="10" y="128" width="170" height="44" rx="6"/><text x="22" y="155">ConfigMap web-settings</text>
<rect class="box warn" x="10" y="182" width="170" height="44" rx="6"/><text x="22" y="209">Secret db-cred</text>
<rect class="zone" x="250" y="14" width="270" height="222" rx="8"/><text class="small" x="262" y="32">파드 web-…</text>
<rect class="box" x="270" y="44" width="230" height="174" rx="6"/><text x="282" y="66">컨테이너 nginx</text>
<text class="mono" x="282" y="92">/usr/share/nginx/html/</text>
<text class="mono" x="282" y="116">/etc/nginx/conf.d/</text>
<text class="mono" x="282" y="140">env APP_MODE</text>
<text class="mono" x="282" y="164">env DB_USER, DB_PASSWORD</text>
<text class="mono" x="282" y="196">/usr/share/nginx/state/ready</text>
<path class="line" d="M182 42L268 88M182 96L268 112M182 150L268 136M182 204L268 160" marker-end="url(#i1a)"/>
<text class="small" x="196" y="64">파일</text><text class="small" x="196" y="185">환경 변수</text>
<rect class="box dim" x="580" y="40" width="160" height="54" rx="6"/><text x="592" y="63">kubelet</text><text class="small" x="592" y="81">GET /ready, /healthz</text>
<path class="line" d="M578 70H502" marker-end="url(#i1a)"/>
<rect class="box" x="580" y="128" width="160" height="40" rx="6"/><text x="592" y="153">/ready 503 → 엔드포인트 제외</text>
<rect class="box" x="580" y="180" width="160" height="40" rx="6"/><text x="592" y="205">/healthz 실패 3회 → 재시작</text>
<path class="line dim" d="M660 96V126" marker-end="url(#i1a)"/>
</svg>
<figcaption>설정 주입 경로(왼쪽)와 프로브 판정 결과(오른쪽)</figcaption>
</figure>

## 1단계: 네임스페이스와 Secret 만들기

Secret은 매니페스트 파일에 남기지 않도록 명령으로 만듭니다.

```bash shell="실습 터미널"
kubectl create namespace lab-i01
kubectl create secret generic db-cred -n lab-i01 --from-literal=username=shop --from-literal=password='S3cr3t-Pa55'
kubectl get secret db-cred -n lab-i01 -o yaml
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
data:
  password: UzNjcjN0LVBhNTU=
  username: c2hvcA==
```

base64는 암호화가 아니라는 것을 직접 확인합니다.

```bash shell="실습 터미널"
kubectl get secret db-cred -n lab-i01 -o jsonpath='{.data.password}' | base64 -d; echo
```

`S3cr3t-Pa55`가 그대로 나옵니다. macOS의 오래된 base64는 `-d` 대신 `-D`를 씁니다.

## 2단계: ConfigMap 만들기

`web-config.yaml`로 저장합니다. ConfigMap 세 개가 들어 있습니다.

```yaml file=web-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-settings
  namespace: lab-i01
data:
  APP_MODE: "production"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-nginx-conf
  namespace: lab-i01
data:
  default.conf: |
    server {
        listen 80;
        location / {
            root   /usr/share/nginx/html;
            index  index.html;
        }
        location = /healthz {
            access_log off;
            default_type text/plain;
            return 200 "ok\n";
        }
        location = /ready {
            access_log off;
            default_type text/plain;
            root /usr/share/nginx/state;
            try_files /ready =503;
        }
    }
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-html
  namespace: lab-i01
data:
  index.html: |
    <meta charset="utf-8">
    <h1>주문 페이지 - 버전 1</h1>
```

| 부분 | 의미 |
|---|---|
| `data.APP_MODE` | 환경 변수로 주입할 단순 값. 값은 항상 문자열이므로 따옴표로 감쌉니다. |
| `default.conf: \|` | `\|`는 여러 줄 문자열입니다. 키 이름이 볼륨으로 마운트될 때 **파일 이름**이 됩니다. |
| `location = /healthz` | 항상 200을 돌려주는 생존 확인 경로. liveness·startup 프로브가 씁니다. |
| `location = /ready` + `try_files /ready =503` | `/usr/share/nginx/state/ready` 파일이 있으면 200, 없으면 503. 준비 상태를 파일 하나로 바꿀 수 있게 만든 실습용 장치입니다. |

```bash shell="실습 터미널"
kubectl apply -f web-config.yaml
kubectl get configmaps -n lab-i01
```

## 3단계: 설정을 주입한 Deployment 배포

`web.yaml`로 저장합니다.

```yaml file=web.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: lab-i01
  labels:
    app.kubernetes.io/name: web
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: web
  template:
    metadata:
      labels:
        app.kubernetes.io/name: web
    spec:
      initContainers:
        - name: mark-ready
          image: busybox:1.37.0
          command: ["sh", "-c", "echo ok > /state/ready"]
          volumeMounts:
            - name: state
              mountPath: /state
      containers:
        - name: nginx
          image: nginx:1.30.6-alpine
          ports:
            - name: http
              containerPort: 80
          env:
            - name: APP_MODE
              valueFrom:
                configMapKeyRef:
                  name: web-settings
                  key: APP_MODE
            - name: DB_USER
              valueFrom:
                secretKeyRef:
                  name: db-cred
                  key: username
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-cred
                  key: password
          volumeMounts:
            - name: nginx-conf
              mountPath: /etc/nginx/conf.d
              readOnly: true
            - name: html
              mountPath: /usr/share/nginx/html
              readOnly: true
            - name: state
              mountPath: /usr/share/nginx/state
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 2
            failureThreshold: 30
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            periodSeconds: 3
            failureThreshold: 1
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            periodSeconds: 10
            failureThreshold: 3
      volumes:
        - name: nginx-conf
          configMap:
            name: web-nginx-conf
        - name: html
          configMap:
            name: web-html
        - name: state
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: lab-i01
spec:
  selector:
    app.kubernetes.io/name: web
  ports:
    - name: http
      port: 80
      targetPort: http
```

| 필드 | 의미 |
|---|---|
| `initContainers` | 본 컨테이너보다 먼저 실행되고 끝나야 하는 컨테이너. 여기서는 준비 표시 파일을 만듭니다. |
| `env[].valueFrom.configMapKeyRef` / `secretKeyRef` | ConfigMap·Secret의 특정 키를 환경 변수로 넣습니다. 키가 없으면 파드가 `CreateContainerConfigError`로 시작하지 못합니다. |
| `volumes[].configMap` + `volumeMounts` | ConfigMap의 각 키를 파일로 만들어 디렉터리에 마운트합니다. 그 디렉터리의 원래 파일은 가려집니다. |
| `emptyDir: {}` | 파드가 사는 동안 유지되는 빈 디렉터리. 컨테이너끼리 파일을 나눌 때 씁니다. |
| `startupProbe` (2초 × 30회) | 최대 60초 동안 기동을 기다립니다. 성공 전에는 readiness·liveness를 검사하지 않습니다. |
| `readinessProbe` (`failureThreshold: 1`) | 한 번만 실패해도 엔드포인트에서 뺍니다. 실습에서 변화를 빨리 보려고 낮게 잡았습니다. |
| `livenessProbe` (10초 × 3회) | 30초 동안 연속 실패하면 재시작합니다. readiness보다 느슨하게 잡는 것이 원칙입니다. |
| `port: http` | 컨테이너 포트 이름으로 지정하면 포트 번호가 바뀌어도 프로브를 고칠 필요가 없습니다. |

```bash shell="실습 터미널"
kubectl apply -f web.yaml
kubectl rollout status deployment/web -n lab-i01 --timeout=120s
kubectl run client -n lab-i01 --image=busybox:1.37.0 --restart=Never -- sleep 3600
kubectl wait pod/client -n lab-i01 --for=condition=Ready --timeout=60s
kubectl exec client -n lab-i01 -- wget -qO- -T 5 http://web
kubectl exec deploy/web -c nginx -n lab-i01 -- printenv APP_MODE DB_USER
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드, 대체 이미지)" date="2026-10-15"
deployment "web" successfully rolled out
pod/client created
pod/client condition met
<h1>주문 페이지 - 버전 1</h1>
production
shop
```

검증 당시 `index.html`에 `<meta charset>` 줄이 없었으며, 지금의 매니페스트는 브라우저에서 한글이 깨지지 않도록 그 줄을 더했습니다. 출력 첫 줄에 `<meta charset="utf-8">`가 함께 보이는 것이 정상입니다.

## 4단계: Readiness 실패를 일부러 만들기

파드 하나의 준비 표시 파일을 지웁니다. **예상해 보세요.** 파드는 재시작될까요? 요청은 실패할까요?

```bash shell="실습 터미널"
kubectl get pods -n lab-i01 -l app.kubernetes.io/name=web
kubectl exec <파드 이름> -c nginx -n lab-i01 -- rm /usr/share/nginx/state/ready
```

몇 초 뒤 확인합니다.

```bash shell="실습 터미널"
kubectl get pods -n lab-i01 -l app.kubernetes.io/name=web
kubectl events -n lab-i01 --for pod/<파드 이름> --types=Warning
for i in 1 2 3 4; do kubectl exec client -n lab-i01 -- wget -qO- -T 5 http://web; done
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME                   READY   STATUS    RESTARTS   AGE
web-7d994d76bd-jlbjd   0/1     Running   0          19s
web-7d994d76bd-rc5jl   1/1     Running   0          19s
LAST SEEN         TYPE      REASON      OBJECT                     MESSAGE
1s (x4 over 7s)   Warning   Unhealthy   Pod/web-7d994d76bd-jlbjd   Readiness probe failed: HTTP probe failed with statuscode: 503
<h1>주문 페이지 - 버전 1</h1>
<h1>주문 페이지 - 버전 1</h1>
<h1>주문 페이지 - 버전 1</h1>
<h1>주문 페이지 - 버전 1</h1>
```

READY가 `0/1`이지만 RESTARTS는 0입니다. 요청 4번이 모두 성공한 것은 Service가 준비된 파드로만 보냈기 때문입니다. 지금 상태를 판정합니다.

```verify
id: i1-ready
title: 준비되지 않은 파드가 엔드포인트에서 제외됨
explain: Service 엔드포인트 중 ready=true와 ready=false인 개수를 셉니다. 4단계에서 파일을 지운 직후에 실행하세요.
command: echo "ready=$(kubectl get endpointslices -n lab-i01 -l kubernetes.io/service-name=web -o jsonpath='{range .items[*].endpoints[*]}{.conditions.ready}{"\n"}{end}' | grep -c true) notready=$(kubectl get endpointslices -n lab-i01 -l kubernetes.io/service-name=web -o jsonpath='{range .items[*].endpoints[*]}{.conditions.ready}{"\n"}{end}' | grep -c false)"
expect: ^ready=1 notready=1$
criteria: ready=1 notready=1
```

:::note 엔드포인트 목록에는 여전히 IP가 보입니다
`kubectl get endpointslices -n lab-i01 -o wide`의 ENDPOINTS 열에는 준비되지 않은 파드 IP도 표시됩니다. 실제로 트래픽을 받는지는 각 엔드포인트의 `conditions.ready` 값으로 판단합니다. 위 판정 명령이 이 값을 읽습니다.
:::

파일을 되살리면 다시 엔드포인트에 들어갑니다.

```bash shell="실습 터미널"
kubectl exec <파드 이름> -c nginx -n lab-i01 -- sh -c 'echo ok > /usr/share/nginx/state/ready'
kubectl get pods -n lab-i01 -l app.kubernetes.io/name=web
```

## 5단계: Liveness 실패와 재시작

공식 문서의 예제를 이미지 버전만 고정해 사용합니다. 컨테이너는 30초 뒤 스스로 건강 표시 파일을 지웁니다. `liveness-demo.yaml`로 저장합니다.

```yaml file=liveness-demo.yaml
apiVersion: v1
kind: Pod
metadata:
  name: liveness-demo
  namespace: lab-i01
spec:
  containers:
    - name: app
      image: busybox:1.37.0
      args:
        - /bin/sh
        - -c
        - touch /tmp/healthy; sleep 30; rm -f /tmp/healthy; sleep 600
      livenessProbe:
        exec:
          command:
            - cat
            - /tmp/healthy
        initialDelaySeconds: 5
        periodSeconds: 5
```

```bash shell="실습 터미널"
kubectl apply -f liveness-demo.yaml
```

약 1분 30초 뒤에 확인합니다.

```bash shell="실습 터미널"
kubectl get pod liveness-demo -n lab-i01
kubectl events -n lab-i01 --for pod/liveness-demo
```

```output kind=verified env="검증 환경 (v1.37.1 소스 빌드)" date="2026-10-15"
NAME            READY   STATUS    RESTARTS      AGE
liveness-demo   1/1     Running   1 (22s ago)   97s
18s (x3 over 28s)   Warning   Unhealthy   Pod/liveness-demo   Liveness probe failed: cat: can't open '/tmp/healthy': No such file or directory
18s                 Normal    Killing     Pod/liveness-demo   Container app failed liveness probe, will be restarted
```

30초 뒤 파일이 지워지고, 5초 간격으로 3번(기본 `failureThreshold`) 실패하면 kubelet이 컨테이너를 종료합니다. `sh`가 종료 신호를 바로 처리하지 않아 기본 유예 시간(30초)을 채운 뒤 재시작되므로, RESTARTS가 1이 되기까지 1분 넘게 걸릴 수 있습니다.

```verify
id: i1-liveness
title: Liveness 실패로 재시작됨
explain: liveness-demo 컨테이너의 재시작 횟수를 출력합니다.
command: kubectl get pod liveness-demo -n lab-i01 -o jsonpath='{.status.containerStatuses[0].restartCount}{"\n"}'
expect: ^[1-9][0-9]*$
criteria: 1 이상의 숫자
```

## 6단계: 설정 바꾸기와 반영 시점

`web-config.yaml`에서 `버전 1`을 `버전 2`로, `"production"`을 `"maintenance"`로 고치고 apply합니다.

```bash shell="실습 터미널"
kubectl apply -f web-config.yaml
```

**예상해 보세요.** 웹 페이지(파일로 주입)와 `APP_MODE`(환경 변수로 주입) 중 어느 쪽이 먼저 바뀔까요? 5초 간격으로 확인합니다.

```bash shell="실습 터미널"
kubectl exec client -n lab-i01 -- wget -qO- -T 5 http://web
kubectl exec deploy/web -c nginx -n lab-i01 -- printenv APP_MODE
```

검증 환경에서는 apply 후 약 60초 뒤에 페이지가 「버전 2」로 바뀌었지만, `APP_MODE`는 계속 `production`이었습니다.

- **볼륨으로 마운트한 ConfigMap**은 kubelet이 주기적으로 동기화하므로 **수십 초~1분 남짓 뒤** 파일이 바뀝니다. 단, 앱이 파일을 다시 읽어야 의미가 있습니다. nginx 설정 파일(`default.conf`)을 바꿨다면 nginx를 다시 불러와야(reload) 적용됩니다. `subPath`로 마운트한 파일은 갱신되지 않습니다.
- **환경 변수**는 컨테이너가 시작될 때 한 번만 읽습니다. 바꾸려면 파드를 새로 만들어야 합니다.

```bash shell="실습 터미널"
kubectl rollout restart deployment/web -n lab-i01
kubectl rollout status deployment/web -n lab-i01
kubectl exec deploy/web -c nginx -n lab-i01 -- printenv APP_MODE
```

`maintenance`가 나옵니다. `rollout restart`는 템플릿에 재시작 시각 어노테이션을 넣어 롤링 업데이트를 일으키는 명령입니다.

## 성공 판정

4단계와 5단계의 판정에 더해 최종 상태를 확인합니다.

```verify
id: i1-config
title: 설정 변경이 페이지와 환경 변수에 모두 반영됨
explain: 페이지 본문과 환경 변수 값을 한 줄로 출력합니다. 롤아웃 직후 몇 초 동안은 종료 중인 파드로 요청이 가서 시간 초과가 날 수 있으니, 그때는 10초 뒤 다시 실행하세요.
command: echo "$(kubectl exec client -n lab-i01 -- wget -qO- -T 5 http://web | grep -o '버전 [0-9]') $(kubectl exec deploy/web -c nginx -n lab-i01 -- printenv APP_MODE)"
expect: ^버전 2 maintenance$
criteria: 버전 2 maintenance
```

## 흔한 오류, 진단 순서, 해결 방법

진단 순서: **파드 STATUS → describe의 Events → 컨테이너 로그 → 엔드포인트**.

| 증상 | 확인 명령 | 원인과 해결 |
|---|---|---|
| `CreateContainerConfigError` | `kubectl describe pod`의 Events: `secret "db-cred" not found` 또는 `couldn't find key` | Secret·ConfigMap 이름이나 키가 틀렸거나, 파드보다 늦게 만들었습니다. 만든 뒤 잠시 기다리면 kubelet이 다시 시도합니다. |
| 파드가 `Init:0/1`에서 멈춤 | `kubectl logs <파드> -c mark-ready` | init 컨테이너가 끝나지 않았거나 실패했습니다. |
| READY `0/1`이 계속 | `kubectl events --for pod/<파드>`의 `Readiness probe failed` | 프로브 경로·포트가 틀렸거나 앱이 아직 준비되지 않았습니다. 프로브 경로를 클라이언트 파드에서 직접 `wget`해 봅니다. |
| RESTARTS가 계속 증가 | `kubectl describe pod`의 Last State, Events의 `Liveness probe failed` | liveness 기준이 너무 엄격하거나(`initialDelaySeconds`·`failureThreshold`), 기동이 느린데 startupProbe가 없습니다. |
| ConfigMap을 바꿨는데 반영 안 됨 | `kubectl exec ... cat <파일>` | 환경 변수라면 재시작이 필요합니다. 파일이라면 1분 정도 기다리고, 앱이 다시 읽는지 확인합니다. `subPath` 마운트는 갱신되지 않습니다. |
| nginx 파드가 `CrashLoopBackOff` | `kubectl logs <파드> --previous` | `default.conf` 문법 오류입니다. 로그의 `[emerg]` 줄에 줄 번호가 나옵니다. |

## 응용 과제

**과제 1.** `web-nginx-conf`의 `default.conf`에 `location = /mode { return 200 "$host\n"; }`를 추가하고 apply했습니다. 1분을 기다려도 `/mode`가 404라면 왜일까요? 재시작 없이 반영하는 방법은?

:::answer 힌트와 해설
힌트: 파일은 바뀌었는지 `kubectl exec deploy/web -c nginx -n lab-i01 -- cat /etc/nginx/conf.d/default.conf`로 확인하세요.

해설: 파일은 갱신되었지만 nginx는 시작할 때 읽은 설정을 그대로 씁니다. `kubectl exec <파드> -c nginx -n lab-i01 -- nginx -s reload`로 파드마다 다시 불러오거나, `kubectl rollout restart`로 파드를 교체합니다. 운영에서는 ConfigMap 내용의 해시를 파드 템플릿 어노테이션에 넣어 설정이 바뀌면 자동으로 롤링 업데이트되게 하는 방법을 많이 씁니다.
:::

**과제 2.** Secret을 YAML로 관리해야 한다면 `data` 대신 어떤 필드를 쓰면 base64 변환 없이 쓸 수 있나요? 그 파일을 Git에 올려도 될까요?

:::answer 해설
`stringData` 필드에 평문을 쓰면 API 서버가 저장할 때 base64로 바꿉니다. 하지만 평문 비밀번호가 담긴 파일이므로 그대로 Git에 올리면 안 됩니다. 외부 비밀 관리 도구(외부 생태계: Sealed Secrets, External Secrets Operator 등)를 쓰거나 배포 파이프라인에서 주입합니다.
:::

**과제 3.** readinessProbe만 지우고 4단계를 반복하면 어떻게 되나요?

:::answer 해설
readiness 프로브가 없으면 컨테이너가 실행 중인 한 항상 준비된 것으로 봅니다. 준비 파일을 지워도 엔드포인트에 남아 있어, 요청 일부가 `/`는 성공하더라도 실제로 준비되지 않은 파드로 갈 수 있습니다. 「준비되지 않았음」을 앱이 알릴 방법이 없어집니다.
:::

## 정리와 재실행

```bash shell="실습 터미널"
kubectl delete namespace lab-i01
kubectl get namespace lab-i01
```

Secret·ConfigMap·Deployment·파드가 모두 네임스페이스와 함께 지워집니다. 다시 하려면 `web-config.yaml`을 원래 값(`버전 1`, `"production"`)으로 되돌리고 1단계부터 반복합니다.
