#!/usr/bin/env python3
"""콘텐츠 점검 도구.

사용법:
  python3 tools/check_content.py            # 카탈로그·마크다운 일관성 점검
  python3 tools/check_content.py --extract DIR   # 실습별 YAML을 DIR/<실습 id>/ 아래에 파일로 추출
  python3 tools/check_content.py --checks   # 성공 판정(verify) 블록 목록을 JSON으로 출력

점검 항목
- catalog.json의 published 항목마다 file이 존재하는가
- prereq, 용어 링크([[id]])가 실제로 있는가
- verify 블록에 id·command·expect가 있고, id가 사이트 전체에서 유일한가
- verify의 expect가 정규식으로 컴파일되는가
- yaml file= 블록이 YAML로 파싱되는가 (PyYAML이 설치된 경우)
- catalog의 checks·yamlFiles 값을 마크다운에서 다시 계산해 catalog.json에 기록 (--write)
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FENCE = re.compile(r"^```([^\n]*)\n(.*?)^```", re.S | re.M)
ATTR = re.compile(r'(\w+)=("([^"]*)"|(\S+))')


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def blocks(md):
    for m in FENCE.finditer(md):
        info, body = m.group(1).strip(), m.group(2)
        kind = info.split()[0] if info else ""
        attrs = {m2.group(1): (m2.group(3) if m2.group(3) is not None else m2.group(4)) for m2 in ATTR.finditer(info)}
        yield kind, attrs, body


def parse_verify(body):
    f = {}
    for line in body.splitlines():
        m = re.match(r"^(\w+):\s?(.*)$", line)
        if m:
            f[m.group(1)] = (f[m.group(1)] + "\n" if m.group(1) in f else "") + m.group(2)
    return f


def main():
    args = sys.argv[1:]
    cat = json.loads(load("content/catalog.json"))
    glossary = {t["id"] for t in json.loads(load("content/glossary.json"))["terms"]}
    ids = {i["id"] for i in cat["items"]}
    errors, checks_all, seen = [], [], set()
    yaml_mod = None
    try:
        import yaml as yaml_mod  # noqa
    except ImportError:
        pass
    files = [(i["id"], i["file"]) for i in cat["items"] if i.get("status") == "published"]
    files += [("guide-" + L["id"], L["guide"]) for L in cat["levels"]] + [("page", p["file"]) for p in cat["pages"]]
    per_item = {}
    for item_id, path in files:
        if not os.path.exists(os.path.join(ROOT, path)):
            errors.append(f"{item_id}: 파일 없음 {path}")
            continue
        md = load(path)
        for t in re.findall(r"\[\[([\w-]+)(?:\|[^\]]+)?\]\]", md):
            if t not in glossary:
                errors.append(f"{path}: 용어집에 없는 용어 [[{t}]]")
        for ref in re.findall(r"\(#/item/([\w-]+)\)", md):
            if ref not in ids:
                errors.append(f"{path}: 없는 항목 링크 #/item/{ref}")
        chk, yfiles = [], set()
        for kind, attrs, body in blocks(md):
            if kind == "verify":
                v = parse_verify(body)
                for k in ("id", "command", "expect"):
                    if k not in v:
                        errors.append(f"{path}: verify 블록에 {k} 없음")
                if v.get("id") in seen:
                    errors.append(f"{path}: verify id 중복 {v.get('id')}")
                seen.add(v.get("id"))
                try:
                    re.compile(v.get("expect", ""), re.M)
                except re.error as e:
                    errors.append(f"{path}: expect 정규식 오류 {e}")
                chk.append(v.get("id"))
                checks_all.append({"item": item_id, **v})
            if kind == "yaml" and "file" in attrs:
                yfiles.add(attrs["file"])
                if yaml_mod:
                    try:
                        list(yaml_mod.safe_load_all(body))
                    except Exception as e:  # noqa
                        errors.append(f"{path}: {attrs['file']} YAML 파싱 오류 {e}")
                if "--extract" in args:
                    out = os.path.join(args[args.index("--extract") + 1], item_id)
                    os.makedirs(out, exist_ok=True)
                    with open(os.path.join(out, attrs["file"]), "w", encoding="utf-8") as f:
                        f.write(body)
        per_item[item_id] = (chk, len(yfiles))
    for i in cat["items"]:
        for p in i.get("prereq", []):
            if p not in ids:
                errors.append(f"{i['id']}: 없는 선수 과정 {p}")
        if i["id"] in per_item:
            i["checks"], i["yamlFiles"] = per_item[i["id"]][0], per_item[i["id"]][1]
    if "--write" in args:
        with open(os.path.join(ROOT, "content/catalog.json"), "w", encoding="utf-8") as f:
            json.dump(cat, f, ensure_ascii=False, indent=2)
            f.write("\n")
    if "--checks" in args:
        print(json.dumps(checks_all, ensure_ascii=False, indent=1))
        return
    for e in errors:
        print("오류:", e)
    print(f"점검 완료: 항목 {len(cat['items'])}개, 성공 판정 {len(checks_all)}개, 오류 {len(errors)}개")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
