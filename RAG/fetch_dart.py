"""DART 정기공시 원문 XML을 내려받아 data/dart_xml/에 저장한다.

기존 코퍼스와 같은 규칙을 따른다: 파일명은 접수번호(rcept_no).xml, 인코딩은 UTF-8
(DART 원문은 EUC-KR로 내려오므로 변환해서 저장한다 — dart_parser가 UTF-8로 읽는다).

사용법:
    python RAG/fetch_dart.py 삼양홀딩스              # 2020년부터 정기공시 전부
    python RAG/fetch_dart.py 삼양홀딩스 --from 20150101
    python RAG/fetch_dart.py 삼남석유화학 --type F    # 감사보고서(외부감사관련)
"""
import io
import os
import sys
import zipfile
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "data" / "dart_xml"
CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DOC_URL = "https://opendart.fss.or.kr/api/document.xml"

load_dotenv(ROOT.parent / "dashboard" / "backend" / ".env")
KEY = os.environ["DART_API_KEY"]


def corp_code(name: str) -> str:
    """회사명으로 DART 고유번호를 찾는다. 동명이인이 있으면 상장사를 우선한다."""
    import xml.etree.ElementTree as ET

    r = requests.get(CORP_CODE_URL, params={"crtfc_key": KEY}, timeout=120)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    root = ET.fromstring(z.read(z.namelist()[0]).decode("utf-8"))

    hits = [
        (c.findtext("corp_name").strip(), c.findtext("corp_code"), (c.findtext("stock_code") or "").strip())
        for c in root.iter("list")
        if (c.findtext("corp_name") or "").strip() == name
    ]
    if not hits:
        raise SystemExit(f"DART에 '{name}' 법인이 없습니다. 상호가 다를 수 있습니다.")
    hits.sort(key=lambda h: not h[2])  # 상장사(stock_code 있음) 먼저
    corp_name, code, stock = hits[0]
    print(f"{corp_name} → {code} (상장={stock or '-'})")
    return code


def list_reports(code: str, bgn: str, pblntf_ty: str) -> list[tuple[str, str]]:
    """(접수번호, 보고서명) 목록. 정기공시는 A, 외부감사관련(감사보고서)은 F."""
    out, page = [], 1
    while True:
        r = requests.get(LIST_URL, params={
            "crtfc_key": KEY, "corp_code": code, "bgn_de": bgn, "end_de": "29991231",
            "pblntf_ty": pblntf_ty, "page_no": page, "page_count": 100,
        }, timeout=60).json()
        if r.get("status") != "000":
            raise SystemExit(f"목록 조회 실패: {r.get('message')}")
        out += [(it["rcept_no"], it["report_nm"].strip()) for it in r["list"]]
        if page >= r["total_page"]:
            return out
        page += 1


def fetch_document(rcept_no: str) -> bytes | None:
    """원문 ZIP에서 본문 XML 하나를 꺼낸다. 첨부가 여럿이면 가장 큰 파일이 본문이다."""
    r = requests.get(DOC_URL, params={"crtfc_key": KEY, "rcept_no": rcept_no}, timeout=180)
    r.raise_for_status()
    if r.content[:2] != b"PK":  # 오류는 ZIP이 아니라 XML 메시지로 온다
        print(f"    실패: {r.content[:200].decode('utf-8', 'replace')}")
        return None
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = [n for n in z.namelist() if n.lower().endswith(".xml")]
    if not names:
        return None
    return z.read(max(names, key=lambda n: z.getinfo(n).file_size))


def to_utf8(raw: bytes) -> str:
    """DART 원문은 EUC-KR(cp949)로 오고 선언도 그렇게 박혀 있다. 기존 코퍼스와 맞춰
    UTF-8로 변환하고 선언까지 바꿔 둔다 — dart_parser가 UTF-8로 읽기 때문이다."""
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("cp949", "replace")
    head, sep, rest = text.partition("?>")
    if sep and "encoding" in head:
        head = head.split("encoding")[0] + 'encoding="utf-8"'
    return head + sep + rest


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    name = args[0]
    bgn = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else "20200101"
    ty = sys.argv[sys.argv.index("--type") + 1] if "--type" in sys.argv else "A"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reports = list_reports(corp_code(name), bgn, ty)
    print(f"{bgn} 이후 {ty}유형 공시 {len(reports)}건")

    saved = skipped = failed = 0
    for rcept_no, report_nm in sorted(reports):
        path = OUT_DIR / f"{rcept_no}.xml"
        if path.exists():
            skipped += 1
            continue
        print(f"  {rcept_no}  {report_nm}")
        raw = fetch_document(rcept_no)
        if raw is None:
            failed += 1
            continue
        path.write_text(to_utf8(raw), encoding="utf-8")
        saved += 1

    print(f"\n저장 {saved}건 · 이미 있음 {skipped}건 · 실패 {failed}건 → {OUT_DIR}")


if __name__ == "__main__":
    main()
