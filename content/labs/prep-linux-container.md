## 학습 목표

- 프로세스·PID 1·SIGTERM이 Pod 종료(`terminationGracePeriodSeconds`)와 어떻게 연결되는지 설명할 수 있습니다.
- 앱이 `0.0.0.0`에서 들어야 Service로 접속된다는 것을 압니다.
- 환경 변수·설정 파일이 ConfigMap·Secret으로 이어진다는 것을 압니다.
- 이미지·태그·다이제스트·레지스트리를 읽고, `docker run` 옵션을 Pod 필드로 옮겨 쓸 수 있습니다.

## 선수 지식

- 리눅스·Docker가 처음이면 시리즈의 **리눅스 항해도**(`/linux/`)와 **도커 항해도**(`/docker/`) 기본 과정을 먼저 보세요. 이 강의는 쿠버네티스에 필요한 만큼만 다시 짚습니다.
- 마지막 「직접 확인」은 [환경 준비](#/item/setup)를 마친 뒤 해 봅니다.
- 쿠버네티스가 **왜** 필요해졌는지(모놀리스부터 클라우드 네이티브까지), 모놀리스가 더 나은 경우, Docker와 쿠버네티스가 푸는 문제의 차이는 심화 노트 [[cloud-native|클라우드 네이티브 등장 배경]]([전체 화면](/deep/#/note/cloud-native))에 있습니다.

## 1. 프로세스·PID 1·SIGTERM → Pod 종료

[[pod|Pod]] 안의 컨테이너도 결국 **리눅스 프로세스**입니다. 쿠버네티스가 Pod를 지울 때(롤링 업데이트, 스케일 다운, 노드 비우기) 순서는 이렇습니다.

```text
Pod 삭제 요청
 ├─ ① Service 엔드포인트에서 빠짐 (새 요청이 안 오게)
 ├─ ② preStop 훅이 있으면 실행
 ├─ ③ 컨테이너의 PID 1에 SIGTERM  ── 앱: 연결 마무리·저장 후 종료
 └─ ④ terminationGracePeriodSeconds(기본 30초) 지나도 살아 있으면 SIGKILL
```

| 증상 | 원인 | 해결 |
|---|---|---|
| Pod가 지워지는 데 항상 30초 | PID 1이 SIGTERM을 처리하지 않음 | 앱이 SIGTERM 처리, 또는 셸 래퍼 대신 `exec`로 실행 |
| 배포 중 일부 요청 실패 | 종료 신호와 엔드포인트 제거 사이의 짧은 틈 | preStop에 짧은 `sleep`, 앱의 우아한 종료 |

## 2. 포트와 바인딩 주소

| 앱이 듣는 주소 | Pod 밖(Service·다른 Pod)에서 접속 |
|---|---|
| `127.0.0.1:8080` | **안 됨** — 같은 Pod 안의 컨테이너끼리만 |
| `0.0.0.0:8080` | 됨 |

Pod는 자기 IP를 하나 가지고, 그 안의 컨테이너들은 네트워크를 함께 씁니다. `containerPort`는 **문서용 표시**일 뿐 포트를 열거나 막지 않습니다. 실제로 접속되는지는 앱이 듣는 주소와 [[service|Service]]의 `targetPort`가 결정합니다.

## 3. 환경 변수와 설정 파일 → ConfigMap·Secret

| 리눅스·Docker에서 | 쿠버네티스에서 |
|---|---|
| `export DB_HOST=…`, `docker run -e DB_HOST=…` | Pod `env`, 또는 [[configmap|ConfigMap]]에서 `envFrom` |
| `/etc/app/app.conf` 파일 | ConfigMap을 **볼륨으로 마운트** |
| 비밀번호 파일 (권한 600) | [[secret|Secret]] (기본은 base64 인코딩일 뿐 — 접근 권한이 중요) |

중급 1 「ConfigMap·Secret과 Probe」에서 직접 다룹니다.

## 4. 이미지·태그·다이제스트·레지스트리

```text
registry.example.com/shop/web:1.4.2@sha256:9a7d…
└── 레지스트리 ──┘ └ 저장소 ┘ └ 태그 ┘ └ 다이제스트 (내용의 해시, 바뀌지 않음) ┘
```

- **태그는 다시 붙일 수 있습니다.** 같은 `:1.4.2`가 나중에 다른 이미지를 가리킬 수 있습니다. 운영 매니페스트에서는 다이제스트로 고정하기도 합니다.
- `imagePullPolicy`: 태그가 `latest`이거나 없으면 기본 `Always`(매번 확인), 그 밖에는 `IfNotPresent`. 이미지를 고쳤는데 같은 태그라 반영이 안 되는 흔한 원인입니다.
- 이미지를 받지 못하면 Pod가 [[imagepullbackoff|ImagePullBackOff]] 상태가 됩니다(기본 2).

## 5. docker run 옵션 ↔ Pod 필드

| `docker run` | Pod·Deployment 필드 | 비고 |
|---|---|---|
| `nginx:1.30.6-alpine` | `spec.containers[].image` | |
| `--name web` | `metadata.name` | Deployment면 Pod 이름은 자동 |
| `-p 8080:80` | `containerPort: 80` + **Service** | 외부 노출은 Service가 함 |
| `-e KEY=V` | `env: [{name: KEY, value: V}]` | |
| `-v vol:/data` | `volumes` + `volumeMounts` | 오래 남기려면 PVC |
| `--memory 256m --cpus 0.5` | `resources.limits` (+ `requests`) | 중급 2 |
| `--restart always` | Pod `restartPolicy: Always` + Deployment | 다시 만드는 주체는 컨트롤러 |
| `--user 1000` | `securityContext.runAsUser` | 고급 |
| 마지막 인수 (명령) | `command` (ENTRYPOINT) · `args` (CMD) | 이름이 헷갈리기 쉬움 |

## 직접 확인 (선택)

```bash shell="실습 터미널"
kubectl run prep-demo --image=nginx:1.30.6-alpine --env=GREETING=hello --restart=Never --dry-run=client -o yaml | grep -E '^\s+(- env|  - name|    value|image|name|restartPolicy)' | head -8
```

```output kind=verified env="검증 환경 (minikube · Kubernetes v1.37.0)" date="2026-10-26"
  name: prep-demo
  - env:
    - name: GREETING
      value: hello
    image: nginx:1.30.6-alpine
    name: prep-demo
  restartPolicy: Never
```

`--dry-run=client -o yaml`은 클러스터에 아무것도 만들지 않고, `docker run`과 비슷한 한 줄 명령이 **어떤 매니페스트가 되는지** 보여 줍니다. 처음 매니페스트를 쓸 때 뼈대를 얻는 좋은 방법입니다.

## 확인 질문

:::answer 1. Pod가 Terminating에서 정확히 30초 머문다. 왜?
PID 1이 SIGTERM을 처리하지 않아 `terminationGracePeriodSeconds`(기본 30초) 뒤 SIGKILL로 끝났습니다.
:::

:::answer 2. containerPort를 지웠는데도 Service로 접속이 된다. 이상한가?
아닙니다. `containerPort`는 표시용입니다. 앱이 `0.0.0.0`에서 듣고 Service의 `targetPort`가 맞으면 접속됩니다.
:::
