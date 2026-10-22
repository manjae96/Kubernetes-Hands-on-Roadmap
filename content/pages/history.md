## 한눈에 보기

Kubernetes는 **2015년 7월 1.0**부터 **2026년 8월 1.37**까지 **마이너 버전 38개**를 냈습니다. 마이너 버전(1.**37**)마다 새 기능·변경·제거가 들어가고, 패치 버전(1.37.**1**)은 버그·보안 수정만 담습니다. 이 페이지는 실습 없이 읽는 자료로, 각 버전에서 **무엇이 강조되었고(강조), 무엇이 사라졌고(사라짐·EOS), 무엇이 바뀌어(바뀜)** 지금의 실습 내용까지 왔는지 시대별로 정리합니다.

| 항목 | 내용 |
|---|---|
| 기간 | 1.0 (2015-07) → 1.37 (2026-08), 11년 |
| 출시 주기 | 초기 1년에 4번 → 1.22(2021)부터 **1년에 3번** (대략 4월·8월·12월) |
| 지원 기간 | 최근 3개 마이너 유지. 1.19부터 패치 지원 **약 1년**(이전 약 9개월), 지금은 출시 후 약 14개월 |
| 지금 지원 중 (2026-10-23) | **1.35 · 1.36 · 1.37**, 그리고 **1.34(2026-10-27 종료 예정)** — 나머지 34개는 지원 종료(EOS) |
| 가장 큰 전환점 | 1.16·1.22·1.25의 **베타 API 대량 제거**, 1.24 **dockershim 제거**, 1.25 **PodSecurityPolicy 제거**, 1.31 **클라우드 제공자 코드 분리 완료**, 1.35 **cgroup v1 기본 차단** |

:::note 읽는 법
- **강조**: 그 버전의 공식 발표 글(kubernetes.io 블로그)이 앞세운 내용
- **사라짐**: 제거(removed)·사용 중단(deprecated)·지원 종료. 사용 중단은 「지금은 되지만 앞으로 없어짐」, 제거는 「이제 안 됨」입니다.
- **바뀜**: 단계가 올라간 기능(Alpha → Beta → Stable), 기본값 변경
- 기능 단계는 [버전 비교](#/versions)의 「기능 성숙도 읽는 법」을, 용어는 [[deprecation|사용 중단 정책]]·[[stability|안정성 단계]]를 참고하세요.
:::

## 시대 1 · 탄생과 기본기 (1.0–1.5, 2015–2016)

구글 내부 시스템(Borg)의 경험으로 만든 오픈 소스가 1.0을 내고, **지금도 쓰는 기본 객체**가 거의 이 시기에 처음 나옵니다. 대부분 Beta로 시작해 이후 몇 년에 걸쳐 Stable이 됩니다.

| 버전 | 출시 | 강조 | 사라짐 · 바뀜 |
|---|---|---|---|
| **1.0** | 2015‑07 | 첫 정식 버전, OSCON에서 출시 행사 | 프로젝트는 이후 CNCF(클라우드 네이티브 컴퓨팅 재단)에 기증 |
| **1.1** | 2015‑11 | 성능 개선, **HPA**(수평 자동 확장)·**Job**·HTTP 로드 밸런서(**Ingress**의 시작) Beta | 롤링 업데이트 개선 |
| **1.2** | 2016‑03 | 클러스터 1,000노드·컨테이너 3만 개, **ConfigMap**, **Deployment**·**DaemonSet**·**Ingress** Beta, 새 대시보드 | 노드 드레인(정상 종료) |
| **1.3** | 2016‑07 | **PetSet**(→ 1.5에 StatefulSet), **Init 컨테이너**, **Minikube** 첫 소개, CNI·OCI 지원 | 다중 클러스터 연합(Federation) |
| **1.4** | 2016‑09 | **kubeadm** 첫 등장(두 명령으로 클러스터 만들기), 동적 PVC 프로비저닝 Beta, Init 컨테이너 Beta, ScheduledJob(→ CronJob) Alpha | 인증서 API·kubelet TLS 부트스트랩 시작 |
| **1.5** | 2016‑12 | **StatefulSet** Beta(PetSet 이름 변경), **PodDisruptionBudget** Beta, **CRI**(컨테이너 런타임 인터페이스) Alpha, Windows 컨테이너 Alpha | PetSet → StatefulSet |

이 시기의 「Beta」는 지금보다 가볍게 쓰였습니다. 이후 **Beta로 오래 머문 API들이 1.16·1.22에 대량으로 제거**되는 원인이 됩니다(시대 3·4).

## 시대 2 · 확장성과 보안의 기반 (1.6–1.12, 2017–2018)

「여러 팀·여러 회사가 같이 쓰는 플랫폼」이 되기 위해 **권한(RBAC)**, **확장 지점(CRD·CRI·CSI)**, **설치 도구(kubeadm)** 가 자리를 잡습니다. 1.8 무렵부터 거버넌스와 릴리스 절차도 정비됩니다.

| 버전 | 출시 | 강조 | 사라짐 · 바뀜 |
|---|---|---|---|
| **1.6** | 2017‑03 | **RBAC** Beta, 5,000노드·15만 파드 확장성(etcd v3 덕분), 고급 스케줄링(affinity·taint), 동적 스토리지 프로비저닝 | 기본 저장소 **etcd v3**, kubelet 기본 런타임 경로가 **Docker-CRI**(CRI Beta) |
| **1.7** | 2017‑06 | **NetworkPolicy** Stable, 노드 인가(Node authorizer), etcd 안 Secret 암호화 Alpha, StatefulSet 업데이트 Beta, API 집계(aggregation), 감사 로그 | 로컬 스토리지 Alpha |
| **1.8** | 2017‑09 | **RBAC Stable**, 아웃바운드(egress) NetworkPolicy Beta, 워크로드 API `apps/v1beta2`, CronJob Beta, CRD Beta 유지 | kubelet TLS 인증서 교체 Beta |
| **1.9** | 2017‑12 | **Workloads API `apps/v1` GA** (Deployment·DaemonSet·ReplicaSet·StatefulSet), Windows Beta | 이후 `extensions/v1beta1` 등 옛 그룹 정리의 출발점 |
| **1.10** | 2018‑03 | **CSI** Beta, 로컬 PV Beta, 외부 kubectl 인증 플러그인 Alpha, **CoreDNS** 설치 옵션 Beta | 사용 중인 PV·PVC 삭제 방지 Beta |
| **1.11** | 2018‑06 | **IPVS 기반 kube-proxy**·**CoreDNS** GA, CRD 다중 버전 Beta | `gitRepo` 볼륨 사용 중단 시작(→ 1.33·1.36 완전 차단) |
| **1.12** | 2018‑09 | **kubelet TLS 부트스트랩 GA**, Azure VMSS·클러스터 오토스케일러 Stable | **RuntimeClass**·볼륨 스냅샷 Alpha, 토폴로지 인식 프로비저닝 Beta |

## 시대 3 · 성숙과 첫 대청소 (1.13–1.19, 2018–2020)

설치(kubeadm)·스토리지(CSI)·DNS(CoreDNS)가 GA가 되며 「운영할 만한 플랫폼」이 됩니다. 그리고 **1.16에서 처음으로 오래된 베타 API를 실제로 끕니다** — 매니페스트를 고치지 않은 사용자들이 업그레이드 후 배포가 깨지는 일을 처음 겪은 시기입니다.

| 버전 | 출시 | 강조 | 사라짐 · 바뀜 |
|---|---|---|---|
| **1.13** | 2018‑12 | **kubeadm GA**, **CSI GA**, **CoreDNS 기본 DNS** | kube-dns → CoreDNS 기본 교체 (kube-dns는 1.37에 사용 중단) |
| **1.14** | 2019‑03 | **Windows 노드 정식 지원**, kubectl에 **kustomize**(`-k`), 로컬 PV GA, Pod 우선순위·선점 | 기본 RBAC에서 비인증 디스커버리 접근 축소 |
| **1.15** | 2019‑06 | CRD 확장(가지치기·기본값), **kubeadm HA 컨트롤 플레인 Beta** | `extensions/v1beta1`·`apps/v1beta1`·`apps/v1beta2` 「1.16에 중단」 예고 |
| **1.16** | 2019‑09 | **CRD GA**, **EndpointSlice** Alpha, 메트릭 정비, 볼륨 확장 | **처음으로 사용 중단 API 서비스 중지** — Deployment·DaemonSet·StatefulSet·ReplicaSet·NetworkPolicy·PodSecurityPolicy의 `extensions/v1beta1`·`apps/v1beta1·v1beta2` |
| **1.17** | 2019‑12 | 볼륨 스냅샷 Beta, **in-tree 스토리지 → CSI 이전** Beta, 클라우드 제공자 레이블 GA | 「Taint Node by Condition」 등 14개 Stable |
| **1.18** | 2020‑03 | 토폴로지 매니저 Beta, 서버 측 적용(SSA) Beta 2, **IngressClass** 도입, `kubectl debug` Alpha | Ingress 클래스 **주석(annotation) 방식 → `ingressClassName` 필드** |
| **1.19** | 2020‑08 | **지원 기간 1년으로 연장**, **Ingress GA**(`networking.k8s.io/v1`), 구조화 로그, 일반 임시 볼륨 | 이 버전부터 각 마이너가 약 1년 패치 지원 |

## 시대 4 · 런타임과 보안의 대전환 (1.20–1.25, 2020–2022)

컨테이너 실행을 **Docker에서 CRI 런타임(containerd·CRI-O)** 으로 완전히 넘기고, 파드 보안을 **PodSecurityPolicy에서 Pod Security Admission**으로 바꿉니다. 베타 API는 두 번 더 대량 제거되고, **새 베타 API는 기본으로 꺼 두는** 원칙이 생깁니다.

| 버전 | 출시 | 강조 | 사라짐 · 바뀜 |
|---|---|---|---|
| **1.20** | 2020‑12 | 볼륨 스냅샷 Stable, `kubectl debug` Beta, API 우선순위·공정성 Beta, PID 제한 GA, 정상 노드 종료 Alpha | **dockershim 사용 중단 발표** (Docker로 만든 이미지는 그대로 사용 가능), exec 프로브 타임아웃 처리 변경 |
| **1.21** | 2021‑04 | **CronJob Stable**, 변경 불가 Secret·ConfigMap, IPv4/IPv6 이중 스택 Beta, **EndpointSlice Stable** | **PodSecurityPolicy 사용 중단**, Service `topologyKeys` 사용 중단 |
| **1.22** | 2021‑08 | **서버 측 적용 GA**, 외부 인증 플러그인 Stable, etcd 3.5, 메모리 QoS·스왑 Alpha, seccomp 기본 프로필 Alpha | **베타 API 두 번째 대량 제거** — Ingress·IngressClass·CRD·RBAC·웹훅·CSR 등의 `v1beta1`, 사용 중단 API 경고 메커니즘 Stable |
| **1.23** | 2021‑12 | **이중 스택 GA**, **HPA `autoscaling/v2` GA**, PodSecurity Beta, **CRI v1 기본**, CRD CEL 검증 Alpha | **FlexVolume 사용 중단**, klog 전용 플래그 사용 중단 |
| **1.24** | 2022‑05 | 릴리스 산출물 서명, OpenAPI v3, gRPC 프로브 Beta, 스토리지 용량·볼륨 확장 GA | **dockershim 제거**, **새 베타 API 기본 비활성**, 동적 kubelet 설정 제거 |
| **1.25** | 2022‑08 | **Pod Security Admission Stable**, 임시 컨테이너 Stable, **cgroup v2 Stable**, 이미지 저장소 **registry.k8s.io**로 이전 | **PodSecurityPolicy 제거**, 베타 API 세 번째 제거(CronJob·EndpointSlice·Event·HPA·PDB·RuntimeClass의 v1beta1 등) |

:::why dockershim 제거는 「Docker 이미지를 못 쓴다」는 뜻이 아닙니다
1.20 발표 글: "Docker-produced images will continue to work in your cluster with all runtimes." 바뀐 것은 kubelet이 컨테이너를 실행하는 경로(Docker 엔진을 거치던 shim)이고, 이미지 형식(OCI)은 그대로입니다. 그래서 이 항해도의 실습 클러스터도 containerd로 Docker Hub 이미지를 그대로 받습니다.
:::

## 시대 5 · 레거시 정리와 운영 다듬기 (1.26–1.31, 2022–2024)

남아 있던 옛 구조를 하나씩 들어냅니다 — 옛 이미지 저장소, CRI v1alpha2, **쿠버네티스 코드 안에 있던 클라우드·스토리지 드라이버**. 동시에 사이드카, nftables, 구조화된 인증 설정 같은 운영 기능이 자라고, **DRA**(동적 자원 할당, GPU 같은 장치)가 등장합니다.

| 버전 | 출시 | 강조 | 사라짐 · 바뀜 |
|---|---|---|---|
| **1.26** | 2022‑12 | **DRA** Alpha, CEL 기반 어드미션 Alpha, 파드 스케줄링 준비(scheduling gates) Alpha, 릴리스 서명 Beta | **CRI v1alpha2 제거**, in-tree **GlusterFS·OpenStack Cinder** 드라이버 제거, HPA·흐름 제어 베타 API 제거 |
| **1.27** | 2023‑04 | **SeccompDefault Stable**, Job 스케줄링 지시 변경 GA, 노드 로그 API Alpha | **k8s.gcr.io 저장소 동결**, seccomp 주석 지원 제거, CSIStorageCapacity `v1beta1` 제거 |
| **1.28** | 2023‑08 | **버전 차이 허용 n-2 → n-3**(노드가 컨트롤 플레인보다 3단계까지 낮아도 됨), 비정상 노드 종료 복구 GA, **사이드카 컨테이너** Alpha, 스왑 Beta, ValidatingAdmissionPolicy Beta | GCE PD CSI 이전 기능 제거 |
| **1.29** | 2023‑12 | **KMS v2 저장 암호화 GA**, ReadWriteOncePod GA, **kube-proxy nftables** Alpha, 옛 Secret 기반 ServiceAccount 토큰 정리 Beta | in-tree 클라우드 제공자 통합 기본 비활성, 흐름 제어 `v1beta2` 제거 |
| **1.30** | 2024‑04 | 파드 스케줄링 준비 Stable, 구조화된 인증·인가 설정 Beta, LoadBalancer 동작 인식 Beta | **SecurityContextDeny 어드미션 플러그인 제거** (→ Pod Security Admission) |
| **1.31** | 2024‑08 | **AppArmor Stable**, nftables Beta, 다중 Service CIDR, 트래픽 분배, 이미지 볼륨 Alpha | **in-tree 클라우드 제공자 통합 전부 제거**(쿠버네티스 역사상 가장 큰 이전 완료), **CephFS·Ceph RBD** 드라이버 제거, **cgroup v1 유지 보수 모드** |

## 시대 6 · 대규모 워크로드와 하드웨어의 시대 (1.32–1.37, 2024–2026)

AI·GPU 워크로드가 늘면서 **DRA가 GA**가 되고 그룹 스케줄링(Gang scheduling)·워크로드 인식 스케줄링이 들어옵니다. 파드를 다시 만들지 않고 자원을 바꾸는 **In-place 리사이즈**, 사이드카가 정식이 되고, 마지막 레거시(cgroup v1, ipvs, Endpoints, kube-dns, gitRepo)의 퇴장이 진행 중입니다.

| 버전 | 출시 | 강조 | 사라짐 · 바뀜 |
|---|---|---|---|
| **1.32** | 2024‑12 | DRA 구조화 파라미터, StatefulSet이 만든 PVC 자동 삭제, **파드 수준 자원 지정** Alpha, CEL 변경(mutating) 어드미션 Alpha | 옛 DRA 구현 철회, 흐름 제어 `v1beta3` 제거 |
| **1.33** | 2025‑04 | **사이드카 컨테이너 Stable**, **In-place 리사이즈 Beta**, **nftables Stable**, 사용자 네임스페이스 Beta, `.kuberc` Alpha | **Endpoints API 사용 중단**(→ EndpointSlice), kube-proxy 버전 필드 제거, in-tree `gitRepo` 드라이버 코드 제거 |
| **1.34** | 2025‑08 | **DRA 핵심 GA**, **리눅스 노드 스왑 Stable**, KYAML Alpha, 파드 수준 자원 Beta | kubelet `cgroupDriver` 수동 설정 사용 중단, `PreferClose` 트래픽 분배 사용 중단 |
| **1.35** | 2025‑12 | **In-place 리사이즈 Stable**, 파드 인증서 Beta, Gang scheduling Alpha | **cgroup v1 노드에서 kubelet 기본 시작 실패**(`failCgroupV1: true`), **kube-proxy ipvs 모드 사용 중단**(→ nftables), **ingress-nginx 은퇴(2026-03)** 안내 |
| **1.36** | 2026‑04 | 세분화된 API 인가 Stable, 볼륨 그룹 스냅샷·사용자 네임스페이스·Mutating Admission Policy Stable, 워크로드 인식 스케줄링 Alpha | **`gitRepo` 볼륨 영구 비활성**, Service `spec.externalIPs` 사용 중단 |
| **1.37** | 2026‑08 | watch 캐시 초기화 Stable, **HPA 0까지 축소 Beta**, **KYAML·`metrics.k8s.io` Stable**, 파드 인증서 Stable, 파드 체크포인트·복원 Alpha | **kube-dns 사용 중단**(1.40 이후 새 패키지 없음 예정), cgroup v1 완전 제거 예고, `kubectl run -f` 사용 중단 예고 |

## 사라진 것 모아 보기

사용 중단 → 제거까지 보통 **여러 버전(1–2년 이상)** 의 유예가 있습니다. 업그레이드 전 이 표의 항목을 쓰고 있는지 확인합니다.

| 대상 | 사용 중단 | 제거·차단 | 대신 쓰는 것 |
|---|---|---|---|
| 워크로드 API `extensions/v1beta1`·`apps/v1beta1·v1beta2` | 1.9(`apps/v1` GA) 이후 | **1.16** | `apps/v1` |
| Ingress `extensions`·`networking.k8s.io/v1beta1` | 1.19(v1 GA) | **1.22** | `networking.k8s.io/v1` |
| Ingress 클래스 주석 `kubernetes.io/ingress.class` | 1.18 | (주석은 남아 있으나 표준 아님) | `spec.ingressClassName` |
| dockershim (Docker 엔진 직접 실행) | 1.20 | **1.24** | containerd·CRI-O |
| 동적 kubelet 설정 | 1.22 | **1.24** | 설정 파일 |
| PodSecurityPolicy | 1.21 | **1.25** | Pod Security Admission |
| `k8s.gcr.io` 이미지 저장소 | 1.25(이전) | **1.27 동결** | `registry.k8s.io` |
| CRI `v1alpha2` | 1.23(v1 기본) | **1.26** | CRI `v1` |
| SecurityContextDeny 어드미션 | 1.27 | **1.30** | Pod Security Admission |
| in-tree 클라우드 제공자 통합 | 오랜 기간 단계적 | **1.31** | 외부 cloud-controller-manager |
| in-tree GlusterFS·Cinder / CephFS·RBD | — | **1.26 / 1.31** | CSI 드라이버 |
| FlexVolume | 1.23 | (사용 중단) | CSI |
| `gitRepo` 볼륨 | 1.11 | 1.33 코드 제거 → **1.36 영구 비활성** | init 컨테이너·git-sync |
| cgroup v1 | 1.31 유지 보수 모드 | **1.35 기본 차단** → 완전 제거 예고 | cgroup v2 |
| Endpoints API | **1.33** | (예정) | EndpointSlice |
| kube-proxy ipvs 모드 | **1.35** | (예정) | nftables |
| Service `externalIPs` | **1.36** | (예정) | LoadBalancer·Gateway |
| kube-dns | **1.37** | 1.40 이후 새 패키지 없음 예정 | CoreDNS |
| ingress-nginx (커뮤니티 컨트롤러) | 2025-11 은퇴 발표 | **2026-03 유지 보수 종료** | 다른 Ingress 컨트롤러·Gateway API |

API 제거의 버전별 전체 목록은 공식 [Deprecated API Migration Guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)에 있습니다(1.16 · 1.22 · 1.25 · 1.26 · 1.27 · 1.29 · 1.32).

## 지원 기간(EOS) 한눈에

공식 웹사이트의 릴리스 데이터(`data/releases`) 기준입니다. **굵게** 표시한 버전은 지금(2026-10-23) 지원 중입니다.

| 마이너 | 출시 | 지원 종료(EOL) | 마지막 패치 |
|---|---|---|---|
| 1.0 · 1.1 | 2015-07 · 2015-11 | 공식 기록 없음 | — |
| 1.2 · 1.3 · 1.4 · 1.5 | 2016-03 · 2016-07 · 2016-09 · 2016-12 | 2016-10 · 2016-11 · 2017-04 · 2017-10 | 1.2.7 · 1.3.10 · 1.4.12 · 1.5.8 |
| 1.6 · 1.7 · 1.8 · 1.9 | 2017-03 · 2017-06 · 2017-09 · 2017-12 | 2017-11 · 2018-04 · 2018-07 · 2018-09 | 1.6.13 · 1.7.16 · 1.8.15 · 1.9.11 |
| 1.10 · 1.11 · 1.12 · 1.13 | 2018-03 · 2018-06 · 2018-09 · 2018-12 | 2019-02 · 2019-05 · 2019-07 · 2019-10 | 1.10.13 · 1.11.10 · 1.12.10 · 1.13.12 |
| 1.14 · 1.15 · 1.16 · 1.17 | 2019-03 · 2019-06 · 2019-09 · 2019-12 | 2019-12 · 2020-05 · 2020-09 · 2021-01 | 1.14.10 · 1.15.12 · 1.16.15 · 1.17.17 |
| 1.18 · 1.19 · 1.20 · 1.21 | 2020-03 · 2020-08 · 2020-12 · 2021-04 | 2021-06 · 2021-10 · 2022-02 · 2022-06 | 1.18.20 · 1.19.16 · 1.20.15 · 1.21.14 |
| 1.22 · 1.23 · 1.24 · 1.25 | 2021-08 · 2021-12 · 2022-05 · 2022-08 | 2022-12 · 2023-02 · 2023-07 · 2023-10 | 1.22.17 · 1.23.17 · 1.24.17 · 1.25.16 |
| 1.26 · 1.27 · 1.28 · 1.29 | 2022-12 · 2023-04 · 2023-08 · 2023-12 | 2024-02 · 2024-07 · 2024-10 · 2025-02 | 1.26.15 · 1.27.16 · 1.28.15 · 1.29.14 |
| 1.30 · 1.31 · 1.32 · 1.33 | 2024-04 · 2024-08 · 2024-12 · 2025-04 | 2025-07 · 2025-11 · 2026-02 · 2026-06 | 1.30.14 · 1.31.14 · 1.32.13 · 1.33.13 |
| **1.34** · **1.35** · **1.36** · **1.37** | 2025-08 · 2025-12 · 2026-04 · 2026-08 | 2026-10-27 · 2027-02-28 · 2027-06-28 · 2027-10-28 | (지원 중) |

## 이 항해도와 이어지는 곳

| 역사 속 변화 | 실습·자료 |
|---|---|
| Deployment·ReplicaSet `apps/v1` (1.9) | [기본 1 · 첫 Deployment·Service](#/item/b-lab01), [기본 2 · 롤링 업데이트](#/item/b-lab02) |
| ConfigMap(1.2) · 변경 불가 Secret(1.21) | [중급 1 · ConfigMap·Secret과 Probe](#/item/i-lab01) |
| HPA(1.1 Beta → 1.23 `autoscaling/v2` GA → 1.37 0까지 축소 Beta) | [중급 2 · 자원 요청·제한과 HPA](#/item/i-lab02) |
| RBAC(1.6 Beta → 1.8 Stable) | [고급 1 · RBAC와 ServiceAccount](#/item/a-lab01) |
| NetworkPolicy(1.7 Stable) | [고급 2 · NetworkPolicy](#/item/a-lab02) |
| PodSecurityPolicy 제거 → Pod Security Admission(1.25) | [고급 종합 과제 · 팀 네임스페이스 보안 기준선](#/item/a-cap) |
| Ingress(1.1 → 1.19 GA → 동결), ingress-nginx 은퇴 | Ingress 항해도 (허브 `/ingress/`) |
| CoreDNS 기본(1.13) · kube-dns 사용 중단(1.37) | 심화 노트 「클러스터 DNS」 |
| kube-proxy iptables → ipvs(1.11) → nftables(1.33 Stable, 1.35 ipvs 사용 중단) | 심화 노트 「kube-proxy」, CNI 항해도 |
| dockershim 제거(1.24) · CRI | 도커 항해도, 심화 노트 「kubelet」 |
| 버전 차이 n-3(1.28) · 지원 1년(1.19) | [버전 비교](#/versions) |

## 출처

- 버전별 공식 발표 글: kubernetes.io 블로그의 각 버전 릴리스 공지(1.1–1.37), 1.0은 「Kubernetes 1.0 Launch Event at OSCON」과 GitHub `v1.0.0` 릴리스
- 출시일: GitHub `kubernetes/kubernetes` 릴리스의 `v1.N.0` 게시일 (1.1은 `v1.1.1` 게시일 2015-11-09)
- 지원 종료일·마지막 패치: kubernetes/website `data/releases/eol.yaml`·`schedule.yaml`
- API 제거: [Deprecated API Migration Guide](https://kubernetes.io/docs/reference/using-api/deprecation-guide/)
- 확인일: 2026-10-23. 표의 「강조」는 발표 글이 앞세운 항목 중 일부를 고른 것이며, 전체 변경은 각 버전의 [CHANGELOG](https://github.com/kubernetes/kubernetes/tree/master/CHANGELOG)를 봅니다.
