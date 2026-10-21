#!/bin/sh
# 실습 항해도 공통 배포 규칙 deploy v1.0.0 (Hands-On-Roadmap/templates에서 관리 — 항해도 저장소에서 직접 고치지 말 것)
# BASE_PATH(예: /locust)에 맞춰 nginx 설정을 만든다. 비우거나 /면 루트(/)에서 제공한다.
# 게이트웨이는 경로를 잘라 내지 않고 그대로 넘긴다 (/locust/content/catalog.json → 이 컨테이너).
# nginx 공식 이미지는 시작할 때 /docker-entrypoint.d/*.sh를 차례로 실행한다.
set -eu
SITE_DIR="${SITE_DIR:-/usr/share/nginx/site}"   # 사이트 파일 (Dockerfile에서 복사)
WWW_DIR=/tmp/www                                  # 하위 경로를 만들기 위한 문서 루트
CONF_OUT=/etc/nginx/conf.d/site.conf
LISTEN="${LISTEN_PORT:-8080}"
NAME="${SITE_NAME:-hangdo}"
VER="$(cat "$SITE_DIR/VERSION" 2>/dev/null | tr -d '[:space:]' || true)"   # 저장소 VERSION 파일 (형상관리)

bp="/$(echo "${BASE_PATH:-/}" | sed 's#^/*##; s#/*$##')"   # 앞 / 하나, 뒤 / 없음
if [ "$bp" = "/" ]; then
  root="$SITE_DIR"; loc="/"
else
  root="$WWW_DIR"; loc="$bp/"
  mkdir -p "$WWW_DIR$(dirname "$bp")"
  ln -sfn "$SITE_DIR" "$WWW_DIR$bp"               # /tmp/www/locust → 사이트 폴더
fi
health="{\"status\":\"ok\",\"site\":\"$NAME\",\"version\":\"${VER:-unknown}\",\"base\":\"$loc\"}"

{
cat <<CONF
# 콘텐츠(md·json)는 자주 고치므로 매번 확인, 화면·라이브러리는 짧게 캐시
map \$uri \$site_cache {
    ~\.(md|json)\$  "no-cache";
    default         "public, max-age=300";
}

server {
    listen $LISTEN;
    server_name _;
    root $root;
    server_tokens off;
    absolute_redirect off;                       # 게이트웨이 뒤에서도 상대 경로로 리다이렉트
    charset utf-8;
    charset_types text/plain text/css text/markdown application/json application/javascript;
    gzip on;
    gzip_types text/plain text/css text/markdown application/json application/javascript;

    # 상태 확인 (게이트웨이·쿠버네티스 프로브용). 경로 앞붙임과 상관없이 둘 다 응답
    location = /healthz { default_type application/json; return 200 '$health'; }
CONF
if [ "$bp" != "/" ]; then
cat <<CONF
    location = ${loc}healthz { default_type application/json; return 200 '$health'; }
    location = $bp { return 301 $loc; }          # /locust → /locust/
    location = / { return 302 $loc; }            # 단독 실행 시 http://localhost:<포트>/ → /locust/
CONF
fi
cat <<CONF
    location $loc {
        index index.html;
        try_files \$uri \$uri/ =404;
        add_header Cache-Control \$site_cache;
        add_header X-Content-Type-Options nosniff;
        # 마크다운만 형식 지정 (types를 서버 전체에 쓰면 html·js 형식 목록이 사라짐)
        location ~* \.md\$ {
            types { }
            default_type "text/markdown; charset=utf-8";
            add_header Cache-Control "no-cache";
            add_header X-Content-Type-Options nosniff;
        }
    }
}
CONF
} > "$CONF_OUT"
echo "10-base-path.sh: $NAME ${VER:-unknown} — $loc 경로로 제공 (포트 $LISTEN)"
