# 쿠버네티스 — 실습 항해도 시리즈 사이트 이미지 (공통 배포 규칙)
# (Hands-On-Roadmap/templates에서 관리 — 항해도 저장소에서 직접 고치지 말고 허브의 tools/apply_series.py로 갱신)
#
#   저장소 최상위에서:
#   docker build -f deploy/Dockerfile -t hands-on-roadmap/k8s .
#   docker run --rm -p 8100:8080 hands-on-roadmap/k8s      → http://localhost:8100/k8s/
#
# 규칙: 컨테이너 포트 8080 · BASE_PATH 경로로 제공(게이트웨이는 경로를 그대로 전달) · /healthz 상태 확인
FROM nginx:1.30.6-alpine

COPY deploy/nginx/10-base-path.sh /docker-entrypoint.d/10-base-path.sh
RUN chmod +x /docker-entrypoint.d/10-base-path.sh && rm -f /etc/nginx/conf.d/default.conf

# 사이트 파일만 담음 (검증 도구·실습 키트·배포 파일 제외)
COPY index.html /usr/share/nginx/site/index.html
COPY content/ /usr/share/nginx/site/content/
COPY vendor/ /usr/share/nginx/site/vendor/

ENV BASE_PATH=/k8s \
    SITE_NAME=k8s-hangdo
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
