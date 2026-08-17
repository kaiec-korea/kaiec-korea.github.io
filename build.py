# -*- coding: utf-8 -*-
"""
한국AI윤리위원회(KAIEC) 정적 사이트 빌더
- 공통 헤더/푸터를 각 HTML에 그대로 박아 넣어 완전한 정적 파일을 생성합니다.
  (JS로 헤더를 그리면 네이버 크롤러가 메뉴를 못 읽는 경우가 있어 이렇게 처리)
- 메뉴나 푸터를 바꾸려면 이 파일을 수정하고 `python3 build.py`를 다시 실행하세요.
"""
import os, io, re, glob, datetime
import html as _html
from icons import ICONS

BASE = os.path.dirname(os.path.abspath(__file__))

_ICON_RE = re.compile(r'<i data-lucide="([a-z0-9\-]+)"([^>]*)></i>')


def inline_icons(html):
    """<i data-lucide="x"> 를 실제 SVG로 치환합니다.
    외부 CDN(unpkg 등)에 의존하지 않으므로 인터넷 상황과 무관하게 아이콘이 항상 표시됩니다."""
    def rep(m):
        name, attrs = m.group(1), m.group(2)
        inner = ICONS.get(name)
        if inner is None:
            return ""
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
                'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                'stroke-linejoin="round" aria-hidden="true"%s>%s</svg>' % (attrs, inner))
    return _ICON_RE.sub(rep, html)
SITE_URL = "https://kaiec-korea.github.io"    # 실제 배포 주소 (확정)
SITE_NAME = "한국AI윤리위원회"
SITE_EN = "Korea AI Ethics Committee"
EMAIL = "kaiec.korea@gmail.com"                # ← 대표 문의 메일
# 위원 지원서 구글폼 — 바꾸려면 이 주소만 교체 후 python3 build.py 재실행
GOOGLE_FORM = "https://docs.google.com/forms/d/e/1FAIpQLSezVLiJJVsieoUS2gLRt2Y22MmwhO3MtWevR-tPaJPmoYra4Q/viewform"
# 카피클린 문서검사 바로가기 (모든 카피클린 CTA가 이 주소로 연결됨)
COPYCLEAN_URL = "https://skkc.co.kr/shop_view?idx=6"

# =============================================================================
#  소식 게시판 (블로그) 엔진
#  - posts-src/ 폴더의 .md 파일 1개 = 게시글 1개 (개별 HTML 페이지로 생성 → SEO 최적)
#  - 파일명이 곧 주소가 됩니다: posts-src/2026-08-17-open.md → post-2026-08-17-open.html
#  - 작성법은 posts-src/_작성방법.txt 참고
# =============================================================================
CATEGORIES = ["공지", "캠페인", "활동", "연구·정책"]

# 빌드할 때마다 바뀌는 버전 태그 — CSS/JS 주소 뒤에 붙여 방문자 브라우저 캐시를 자동 갱신
BUILD_V = datetime.datetime.now().strftime("%Y%m%d%H%M")


def _inline(s):
    """굵게 **텍스트**, 링크 [텍스트](주소) 변환"""
    s = _html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    def _link(m):
        txt, url = m.group(1), m.group(2)
        ext = ' target="_blank" rel="noopener"' if url.startswith('http') else ''
        return f'<a href="{url}"{ext} style="color:var(--blue);font-weight:600">{txt}</a>'
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', _link, s)
    return s


def md_to_html(body):
    """간단 마크다운 → HTML (##소제목, ###소소제목, -목록, ![설명](이미지), 문단)"""
    out, buf = [], []
    inlist = False

    def flush_p():
        if buf:
            out.append('<p>' + _inline(' '.join(buf)) + '</p>')
            buf.clear()

    def close_list():
        nonlocal inlist
        if inlist:
            out.append('</ul>')
            inlist = False

    for raw in body.strip().splitlines():
        line = raw.strip()
        if not line:
            flush_p(); close_list(); continue
        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)$', line)
        if m:
            flush_p(); close_list()
            alt, src = m.group(1), m.group(2)
            if not src.startswith('http'):
                src = 'assets/img/posts/' + src
            cap = f'<figcaption>{_inline(alt)}</figcaption>' if alt else ''
            out.append(f'<figure><img src="{src}" alt="{_html.escape(alt)}" loading="lazy">{cap}</figure>')
            continue
        if line.startswith('### '):
            flush_p(); close_list(); out.append('<h3>' + _inline(line[4:]) + '</h3>'); continue
        if line.startswith('## '):
            flush_p(); close_list(); out.append('<h2>' + _inline(line[3:]) + '</h2>'); continue
        if line.startswith('- '):
            flush_p()
            if not inlist:
                out.append('<ul>'); inlist = True
            out.append('<li>' + _inline(line[2:]) + '</li>'); continue
        close_list()
        buf.append(line)
    flush_p(); close_list()
    return '\n'.join(out)


def load_posts():
    """posts-src/*.md 읽어 게시글 목록(최신순) 반환"""
    posts = []
    for path in glob.glob(os.path.join(BASE, "posts-src", "*.md")):
        raw = io.open(path, encoding='utf-8').read()
        head, sep, body = raw.partition('\n---')
        if not sep:
            print("  ⚠ 건너뜀(--- 구분선 없음):", os.path.basename(path)); continue
        meta = {}
        for line in head.strip().splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip()
        slug = os.path.splitext(os.path.basename(path))[0]
        date = meta.get('날짜', '2026.01.01')
        try:
            dt = datetime.datetime.strptime(date, "%Y.%m.%d")
        except ValueError:
            dt = datetime.datetime(2026, 1, 1)
        posts.append({
            "slug": slug,
            "file": f"post-{slug}.html",
            "title": meta.get('제목', slug),
            "date": date,
            "dt": dt,
            "category": meta.get('분류', '공지'),
            "keywords": [k.strip() for k in meta.get('키워드', '').split(',') if k.strip()],
            "image": meta.get('이미지', '').strip(),
            "summary": meta.get('요약', ''),
            "body": body.strip(),
        })
    posts.sort(key=lambda p: (p["dt"], p["slug"]), reverse=True)
    return posts


def board_card(p):
    """게시판 목록 카드 1개"""
    if p["image"]:
        thumb = f'<div class="board-thumb"><img src="assets/img/posts/{p["image"]}" alt="{_html.escape(p["title"])}" loading="lazy"></div>'
    else:
        thumb = f'''<div class="board-thumb board-thumb--ph">
            <span class="ph-mark">K<em>AI</em>EC</span><span class="ph-cat">{p["category"]}</span></div>'''
    badge = 'badge--teal' if p["category"] == '캠페인' else ('badge--gray' if p["category"] in ('활동', '연구·정책') else '')
    return f'''        <a class="board-card" href="{p["file"]}" data-cat="{p["category"]}">
          {thumb}
          <div class="board-body">
            <div class="board-meta"><span class="badge {badge}">{p["category"]}</span><span class="board-date">{p["date"]}</span></div>
            <div class="board-title">{p["title"]}</div>
            <p class="board-sum">{p["summary"]}</p>
            <span class="board-more">자세히 보기 →</span>
          </div>
        </a>'''

NAV = [
    ("about.html", "위원회 소개"),
    ("business.html", "주요사업"),
    ("members.html", "조직·위원"),
    ("lecture.html", "강의 신청"),
    ("partner.html", "AI 윤리 파트너"),
    ("copyclean.html", "카피클린"),
    ("news.html", "캠페인·소식"),
    ("mou.html", "MOU·대외협력"),
]

LOGO_SVG = """<svg class="brand-mark" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="kgBg" x1="4" y1="2" x2="46" y2="46" gradientUnits="userSpaceOnUse">
      <stop stop-color="#1E56D6"/><stop offset=".52" stop-color="#12336F"/><stop offset="1" stop-color="#0A1628"/>
    </linearGradient>
    <linearGradient id="kgShield" x1="14" y1="10" x2="36" y2="40" gradientUnits="userSpaceOnUse">
      <stop stop-color="#CFE0FF"/><stop offset="1" stop-color="#6FE3D8"/>
    </linearGradient>
    <linearGradient id="kgSheen" x1="0" y1="0" x2="20" y2="26" gradientUnits="userSpaceOnUse">
      <stop stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="kgGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
      gradientTransform="translate(24 19.5) scale(7.5)">
      <stop stop-color="#6FE3D8" stop-opacity=".55"/><stop offset="1" stop-color="#6FE3D8" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="48" height="48" rx="12.5" fill="url(#kgBg)"/>
  <rect x="1" y="1" width="46" height="46" rx="11.5" stroke="#fff" stroke-opacity=".14"/>
  <path d="M0 12.5C0 5.6 5.6 0 12.5 0h23C42.4 0 48 5.6 48 12.5V17C40 8.8 26 4.6 0 15.5v-3Z" fill="url(#kgSheen)"/>
  <path d="M24 8.6 36.4 14v10.3c0 7-5 12-12.4 13.9C16.6 36.3 11.6 31.3 11.6 24.3V14L24 8.6Z"
        stroke="url(#kgShield)" stroke-width="2.1" stroke-linejoin="round"/>
  <circle cx="24" cy="19.5" r="7.5" fill="url(#kgGlow)"/>
  <circle cx="24" cy="19.5" r="2.7" fill="#6FE3D8"/>
  <circle cx="17.9" cy="28.6" r="2.2" fill="#F2F7FF"/>
  <circle cx="30.1" cy="28.6" r="2.2" fill="#F2F7FF"/>
  <path d="M22.6 21.6 18.9 26.7M25.4 21.6 29.1 26.7M20.1 28.6h7.8"
        stroke="#DCE9FF" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M24 12.2v3.2M16 16l2.6 1.6M32 16l-2.6 1.6" stroke="#8FB7FF" stroke-width="1.3" stroke-linecap="round" opacity=".8"/>
</svg>"""

BRAND = f"""<a class="brand" href="index.html" aria-label="{SITE_NAME} 홈">
        <span class="brand-badge">KAIEC</span>
        <span class="brand-text">
          <span class="brand-ko">{SITE_NAME}</span>
          <span class="brand-en">{SITE_EN}</span>
        </span>
      </a>"""


def header():
    links = "\n          ".join(
        f'<a href="{h}">{t}</a>' for h, t in NAV
    )
    return f"""<header class="site-header">
    <div class="topbar">
      <div class="topbar-inner">
        <span class="topbar-left">KOREA AI ETHICS COMMITTEE</span>
        <span class="topbar-right">
          <a href="mailto:{EMAIL}">{EMAIL}</a><span class="tsep">|</span>
          <a href="apply.html">위원 지원</a><span class="tsep">|</span>
          <a href="{COPYCLEAN_URL}" target="_blank" rel="noopener" style="color:#6FE3D8">카피클린</a><span class="tsep">|</span>
          <a href="mou.html#inquiry">제휴·MOU 문의</a>
        </span>
      </div>
    </div>
    <div class="header-inner">
      {BRAND}
      <nav class="nav" id="nav">
          {links}
          <span class="header-cta"><a class="btn btn-primary btn-sm" href="{GOOGLE_FORM}" target="_blank" rel="noopener">위원 지원</a><a class="btn btn-teal btn-sm" href="{COPYCLEAN_URL}" target="_blank" rel="noopener">문서 검사</a></span>
      </nav>
      <button class="nav-toggle" id="navToggle" aria-label="메뉴 열기" aria-expanded="false" aria-controls="nav">
        <i data-lucide="menu"></i>
      </button>
    </div>
  </header>"""


def footer():
    col1 = "\n            ".join(f'<li><a href="{h}">{t}</a></li>' for h, t in NAV[:4])
    col2 = "\n            ".join(f'<li><a href="{h}">{t}</a></li>' for h, t in NAV[4:])
    return f"""<footer class="site-footer">
    <div class="wrap">
      <div class="footer-top">
        <div class="footer-brand">
          {BRAND}
          <p class="footer-desc">생성형 AI 시대의 책임 있는 AI 활용과 건전한 AI 윤리 문화 확산을 위해 교육·연구·캠페인·대외협력 활동을 수행하는 AI 윤리 전문 위원회입니다.</p>
        </div>
        <div class="footer-col">
          <h4>위원회</h4>
          <ul>
            {col1}
          </ul>
        </div>
        <div class="footer-col">
          <h4>활동</h4>
          <ul>
            {col2}
            <li><a href="apply.html">위원 지원</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h4>문의</h4>
          <ul>
            <li><a href="mailto:{EMAIL}">{EMAIL}</a></li>
            <li><a href="apply.html">위원·파트너 지원</a></li>
            <li><a href="mou.html#inquiry">제휴·MOU 문의</a></li>
          </ul>
        </div>
      </div>
      <div class="footer-bottom">
        <span>© <span id="year">2026</span> {SITE_NAME} (Korea AI Ethics Committee). All rights reserved.</span>
        <span>문의 {EMAIL}</span>
      </div>
    </div>
  </footer>"""


def page(filename, title, desc, body, extra_head="", extra_script="", keywords=None, og_image=None):
    canonical = f"{SITE_URL}/{filename}" if filename != "index.html" else f"{SITE_URL}/"
    full_title = title if filename == "index.html" else f"{title} | {SITE_NAME}"
    kw = ", ".join(keywords) if keywords else "AI윤리, 인공지능 윤리, 한국AI윤리위원회, 생성형 AI, AI 윤리 파트너, AI 윤리 교육, 카피클린, AI 활용 점검"
    ogimg = og_image or f"{SITE_URL}/assets/img/og-image.png"
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{desc}">
<meta name="keywords" content="{kw}">
<meta name="author" content="{SITE_NAME}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="index, follow">
<meta name="naver-site-verification" content="">
<meta name="google-site-verification" content="">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="ko_KR">
<meta property="og:image" content="{ogimg}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" as="style" crossorigin
  href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=Noto+Serif+KR:wght@600;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/style.css?v={BUILD_V}">
<script>document.documentElement.className+=' js';</script>
{extra_head}</head>
<body>
  {header()}
  <main>
{body}
  </main>
  {footer()}
  <script src="assets/js/main.js?v={BUILD_V}"></script>
{extra_script}</body>
</html>
"""
    html = inline_icons(html)
    with io.open(os.path.join(BASE, filename), "w", encoding="utf-8") as f:
        f.write(html)
    print("  ✓", filename)


def hero_sub(title, desc, crumb):
    return f"""    <section class="page-hero">
      <div class="wrap page-hero-inner">
        <p class="crumb"><a href="index.html">홈</a> &nbsp;›&nbsp; {crumb}</p>
        <h1>{title}</h1>
        <p>{desc}</p>
      </div>
    </section>"""


# =============================================================================
#  콘텐츠
# =============================================================================

BUSINESS = [
    ("shield-check", "책임 있는 생성형 AI 활용 확산",
     "생성형 AI를 활용하는 개인과 조직이 지켜야 할 기본 원칙을 정리하고 확산합니다. 학습·연구·업무 현장에서 AI를 '숨기는 도구'가 아니라 '밝히고 검증하는 도구'로 쓰는 문화를 만드는 것을 목표로 합니다.",
     ["AI 활용 원칙 및 자율 가이드라인 정리", "분야별 AI 활용 체크리스트 배포", "AI 윤리 인식 개선 활동"]),
    ("megaphone", "AI 윤리 캠페인 및 교육·콘텐츠",
     "온라인 캠페인, 카드뉴스, 영상, 강의 자료 등 누구나 쉽게 접근할 수 있는 형태로 AI 윤리 콘텐츠를 제작·배포합니다. 대학생·대학원생·연구자·직장인 등 실사용자 눈높이에 맞춘 실용적 내용을 지향합니다.",
     ["온·오프라인 AI 윤리 캠페인 기획", "교육 자료 및 강의 콘텐츠 제작", "SNS 기반 인식 개선 콘텐츠 운영"]),
    ("users", "AI 윤리 파트너 및 전문위원 운영",
     "AI 윤리에 관심 있는 개인이 온라인·재택 방식으로 참여할 수 있는 「AI 윤리 파트너」 제도와, 분야별 전문성을 바탕으로 자문하는 전문위원 제도를 운영합니다.",
     ["AI 윤리 파트너 모집 및 활동 지원", "전문위원 위촉 및 분과 운영", "위촉장·활동증명서 발급"]),
    ("handshake", "대학·기업·협회와의 MOU 및 제휴",
     "대학, 기업, 협회, 연구기관 등과 업무협약을 체결하고 공동 캠페인·교육·연구를 추진합니다. 각 기관의 현장 상황에 맞는 AI 윤리 실천 방안을 함께 설계합니다.",
     ["기관 간 업무협약(MOU) 체결", "공동 캠페인 및 세미나 개최", "기관 맞춤형 AI 윤리 자문"]),
    ("file-search", "AI 활용 문서의 책임 있는 사전점검",
     "논문·과제·보고서 등 AI를 활용해 작성한 문서를 제출 전에 스스로 점검하는 문화를 확산합니다. 제재가 아닌 <strong>자기 점검</strong>을 통해 불필요한 오해와 분쟁을 예방하는 것이 목적입니다.",
     ["사전점검 문화 확산 캠페인", "제휴 서비스 「카피클린」과의 공동 활동", "점검 가이드라인 안내"]),
    ("book-open", "AI 윤리 연구 및 정책·사회적 이슈 공유",
     "국내외 AI 윤리 기준, 관련 정책 동향, 사회적 쟁점을 정리해 공유합니다. 특정 입장을 대변하기보다 논의에 필요한 정보를 정리해 전달하는 데 초점을 둡니다.",
     ["국내외 AI 윤리 동향 정리", "이슈 브리프 및 리포트 발행", "연구·토론 모임 운영"]),
]

VALUES = [
    ("scale", "책임성", "AI가 만든 결과에 대한 책임은 사람에게 있습니다. 활용 과정과 결과를 설명할 수 있어야 합니다."),
    ("eye", "투명성", "AI를 사용했다면 숨기지 않고 밝힙니다. 어디에, 어떻게 썼는지 드러내는 것이 신뢰의 출발점입니다."),
    ("scale-3d", "공정성", "AI 활용이 특정 집단에 불리하게 작동하지 않도록 살피고, 편향을 인식하며 사용합니다."),
    ("heart-handshake", "포용성", "기술 접근성의 차이가 새로운 격차가 되지 않도록, 누구나 이해할 수 있는 언어로 알립니다."),
]

CHARTER = [
    "AI가 만든 결과물의 최종 책임은 이를 사용한 사람에게 있음을 인식한다.",
    "학습·연구·업무에 AI를 활용한 경우, 요구되는 범위에서 그 사실과 활용 정도를 밝힌다.",
    "AI가 생성한 내용을 그대로 신뢰하지 않고, 사실관계와 출처를 스스로 확인한다.",
    "타인의 저작물과 개인정보가 AI 입력·출력 과정에서 침해되지 않도록 주의한다.",
    "AI를 이용해 타인을 기만하거나 허위 정보를 유포하지 않는다.",
    "제출·공표를 앞둔 문서는 사전에 스스로 점검하여 불필요한 분쟁을 예방한다.",
    "AI 윤리에 대해 배운 것을 주변과 나누어 건전한 활용 문화를 함께 넓혀간다.",
]


# ---------------------------------------------------------------- index.html
def build_index(posts):
    biz_cards = "\n".join(f"""        <article class="card reveal">
          <div class="card-icon"><i data-lucide="{ic}"></i></div>
          <h3>{t}</h3>
          <p>{d.split('.')[0]}.</p>
        </article>""" for ic, t, d, _ in BUSINESS)

    val_cards = "\n".join(f"""        <article class="card reveal">
          <div class="card-icon card-icon--teal"><i data-lucide="{ic}"></i></div>
          <h3>{t}</h3>
          <p>{d}</p>
        </article>""" for ic, t, d in VALUES)

    body = f"""    <section class="hero">
      <div class="wrap hero-inner">
        <span class="hero-badge"><span class="dot"></span>KAIEC · Korea AI Ethics Committee</span>
        <h1>AI를 잘 쓰는 것보다<br><span class="accent">책임 있게 쓰는 것</span>이 먼저입니다</h1>
        <p>한국AI윤리위원회는 생성형 AI 시대의 책임 있는 AI 활용과 건전한 AI 윤리 문화 확산을 위해
           교육·연구·캠페인·대외협력 활동을 수행합니다.</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="about.html">위원회 소개 <i data-lucide="arrow-right"></i></a>
          <a class="btn btn-light" href="lecture.html">교육·강사 파견 <i data-lucide="arrow-right"></i></a>
          <a class="btn btn-light" href="partner.html">AI 윤리 파트너 참여 <i data-lucide="arrow-right"></i></a>
          <a class="btn btn-teal" href="{COPYCLEAN_URL}" target="_blank" rel="noopener">카피클린 문서검사 <i data-lucide="external-link"></i></a>
        </div>
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="stats reveal">
          <div class="stat"><div class="stat-num"><span data-count="6">6</span></div><div class="stat-label">주요사업 영역</div></div>
          <div class="stat"><div class="stat-num"><span data-count="4">4</span></div><div class="stat-label">윤리 핵심가치</div></div>
          <div class="stat"><div class="stat-num"><span data-count="7">7</span></div><div class="stat-label">윤리헌장 실천조항</div></div>
          <div class="stat"><div class="stat-num">상시</div><div class="stat-label">위원·파트너 모집</div></div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="center" style="margin-bottom:44px">
          <span class="eyebrow">Our Mission</span>
          <h2 class="h-sec">기술의 속도를 따라가는 윤리의 기준</h2>
          <p class="h-sub">생성형 AI는 이미 학습·연구·업무의 일상이 되었습니다. 그러나 '어디까지 써도 되는가'에 대한
             기준은 아직 정리되지 않았습니다. 위원회는 그 기준을 함께 만들고 알리는 일을 합니다.</p>
        </div>
        <div class="grid grid-4">
{val_cards}
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap">
        <div class="center" style="margin-bottom:44px">
          <span class="eyebrow">Main Business</span>
          <h2 class="h-sec">6대 주요사업</h2>
          <p class="h-sub">선언에 머무르지 않고 현장에서 실제로 작동하는 활동을 지향합니다.</p>
        </div>
        <div class="grid grid-3">
{biz_cards}
        </div>
        <div class="center" style="margin-top:38px">
          <a class="btn btn-ghost" href="business.html">주요사업 자세히 보기 <i data-lucide="arrow-right"></i></a>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="split">
          <div class="reveal">
            <span class="eyebrow">Partner Program</span>
            <h2 class="h-sec">AI 윤리 파트너</h2>
            <p class="lead" style="margin-bottom:20px">AI 윤리에 관심 있는 누구나 온라인·재택 방식으로 참여할 수 있는
               위원회의 대표 참여 제도입니다.</p>
            <ul style="display:grid;gap:12px;margin-bottom:26px">
              <li style="display:flex;gap:10px;align-items:flex-start"><i data-lucide="check-circle-2" style="width:19px;height:19px;color:#00B4A6;flex-shrink:0;margin-top:4px"></i><span>AI 윤리 문화 확산 캠페인 참여</span></li>
              <li style="display:flex;gap:10px;align-items:flex-start"><i data-lucide="check-circle-2" style="width:19px;height:19px;color:#00B4A6;flex-shrink:0;margin-top:4px"></i><span>공식 위촉장 및 활동증명서 발급</span></li>
              <li style="display:flex;gap:10px;align-items:flex-start"><i data-lucide="check-circle-2" style="width:19px;height:19px;color:#00B4A6;flex-shrink:0;margin-top:4px"></i><span>활동 실적에 따른 인센티브 지급</span></li>
              <li style="display:flex;gap:10px;align-items:flex-start"><i data-lucide="check-circle-2" style="width:19px;height:19px;color:#00B4A6;flex-shrink:0;margin-top:4px"></i><span>전 과정 온라인·재택 진행</span></li>
            </ul>
            <a class="btn btn-primary" href="partner.html">파트너 제도 알아보기 <i data-lucide="arrow-right"></i></a>
          </div>
          <div class="split-visual reveal">
            <span class="badge badge--teal" style="align-self:flex-start">ONLINE · 재택</span>
            <h3 style="font-size:26px;letter-spacing:-.035em">함께 알리는 사람이<br>문화를 만듭니다</h3>
            <p style="color:#B8CBE8;font-size:15px;line-height:1.8">
              거창한 자격이나 경력이 필요하지 않습니다. AI를 쓰는 사람이라면 누구나
              AI 윤리를 알리는 주체가 될 수 있습니다.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap">
        <div class="split">
          <div class="split-visual reveal" style="background:linear-gradient(150deg,#0A1628,#00857A)">
            <span class="badge" style="align-self:flex-start;background:rgba(255,255,255,.16);color:#fff">제휴 서비스</span>
            <h3 style="font-size:26px;letter-spacing:-.035em">카피클린<br><span style="font-size:16px;font-weight:600;opacity:.8">CopyClean</span></h3>
            <p style="color:#CDE9E5;font-size:15px;line-height:1.8">
              논문·과제·보고서·자기소개서 등 다양한 문서를 대상으로
              AI 활용 여부를 사전에 확인할 수 있도록 지원하는 AI 문서 분석 서비스입니다.</p>
          </div>
          <div class="reveal">
            <span class="eyebrow">Affiliated Service</span>
            <h2 class="h-sec">제휴 서비스 「카피클린」</h2>
            <p class="lead" style="margin-bottom:18px">
              위원회는 카피클린과 함께 <strong>AI 활용 문서의 사전점검</strong>과
              <strong>책임 있는 AI 활용 문화 확산</strong>을 위한 캠페인·제휴 활동을 진행합니다.</p>
            <div class="notice notice--teal" style="margin-bottom:24px">
              위원회가 <strong>윤리 기준과 캠페인</strong>을, 카피클린이 <strong>AI 문서 분석 기술</strong>을 맡아
              "제출 전에 스스로 확인하는 문화"를 함께 만들어갑니다.
            </div>
            <div style="display:flex;gap:11px;flex-wrap:wrap">
              <a class="btn btn-teal" href="{COPYCLEAN_URL}" target="_blank" rel="noopener">카피클린 바로가기 <i data-lucide="external-link"></i></a>
              <a class="btn btn-ghost" href="copyclean.html">제휴 내용 자세히 보기 <i data-lucide="arrow-right"></i></a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:32px;flex-wrap:wrap">
          <div>
            <span class="eyebrow">News &amp; Campaign</span>
            <h2 class="h-sec" style="margin-bottom:0">최근 소식</h2>
          </div>
          <a class="btn btn-ghost btn-sm" href="news.html">전체 보기 <i data-lucide="arrow-right"></i></a>
        </div>
        <div class="board-grid">
{chr(10).join(board_card(p) for p in posts[:3])}
        </div>
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="cta-band reveal">
          <div>
            <h2>AI 윤리 활동에 함께하실 분을 기다립니다</h2>
            <p>전문위원 · 활동위원 · AI 윤리 파트너 상시 모집 중입니다. 온라인으로 간편하게 지원하실 수 있습니다.</p>
          </div>
          <div class="btns">
            <a class="btn btn-white" href="{GOOGLE_FORM}" target="_blank" rel="noopener">위원 지원하기</a>
            <a class="btn btn-light" href="lecture.html">강의·교육 신청</a>
            <a class="btn btn-light" href="mou.html#inquiry">제휴 문의</a>
          </div>
        </div>
      </div>
    </section>"""

    page("index.html",
         f"{SITE_NAME} | 책임 있는 AI 활용과 AI 윤리 문화 확산",
         "한국AI윤리위원회는 생성형 AI 시대의 책임 있는 AI 활용과 건전한 AI 윤리 문화 확산을 위해 교육·연구·캠페인·대외협력 및 AI 윤리 파트너 활동을 추진하는 AI 윤리 전문 위원회입니다.",
         body)


# ---------------------------------------------------------------- about.html
def build_about():
    val_rows = "\n".join(f"""        <article class="card reveal">
          <div class="card-icon"><i data-lucide="{ic}"></i></div>
          <h3>{t}</h3>
          <p>{d}</p>
        </article>""" for ic, t, d in VALUES)

    charter = "\n".join(f"""          <li style="display:flex;gap:16px;padding:18px 0;border-bottom:1px solid var(--gray-200)">
            <span style="flex-shrink:0;width:30px;height:30px;border-radius:9px;background:var(--blue-050);color:var(--blue);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px">{i+1}</span>
            <span style="font-size:16px;line-height:1.75;color:var(--gray-700);padding-top:2px">{c}</span>
          </li>""" for i, c in enumerate(CHARTER))

    body = hero_sub("위원회 소개",
                    "생성형 AI 시대에 필요한 것은 더 빠른 기술이 아니라, 그 기술을 다루는 사람의 기준입니다.",
                    "위원회 소개") + f"""

    <section class="section">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:36px">
          <span class="eyebrow">Message</span>
          <h2 class="h-sec serif">위원장 인사말</h2>
        </div>
        <div class="greeting serif">
          <div class="greeting-body">
            <p><strong>안녕하십니까.</strong><br>
            한국AI윤리위원회 홈페이지를 찾아주신 여러분께 깊은 감사의 말씀을 드립니다.</p>
            <p>생성형 인공지능은 어느새 우리의 학습과 연구, 그리고 일하는 방식 깊숙이 들어와 있습니다.
            그러나 기술이 일상이 된 속도에 비해, 그 기술을 <strong>어떻게 사용하는 것이 바람직한가</strong>에 대한
            사회적 기준은 아직 충분히 자리 잡지 못했습니다. 기준의 공백은 두 가지 그림자를 남깁니다.
            AI를 활용하고도 떳떳하게 밝히지 못하는 문화, 그리고 막연한 불안 속에 정당한 활용마저
            주저하게 되는 위축이 그것입니다.</p>
            <p>한국AI윤리위원회는 이 공백을 메우고자 뜻을 모은 <strong>AI 윤리 전문 기구</strong>입니다.
            우리는 규제와 처벌이 아니라, AI를 쓰는 사람이라면 누구나 스스로 지킬 수 있는
            기준과 문화의 힘을 믿습니다. 제출 전에 한 번 더 점검하고, 활용했다면 숨기지 않고 밝히며,
            결과에 책임지는 태도 — 그 작은 실천들이 모여 신뢰할 수 있는 AI 시대를 만든다고 확신합니다.</p>
            <p>위원회는 교육과 연구, 캠페인과 대외협력을 통해 이 실천을 넓혀가고자 합니다.
            대학과 기업, 연구 현장의 목소리에 귀 기울이고, 전문위원과 활동위원, 그리고 전국의
            AI 윤리 파트너와 함께 걸어가겠습니다.</p>
            <p>여러분의 관심과 참여가 건강한 AI 문화를 만드는 가장 큰 힘입니다.<br>감사합니다.</p>
          </div>
          <div class="greeting-sign">
            <span class="gs-org">한국AI윤리위원회 위원장</span>
            <span class="gs-name" id="chairName">&nbsp;</span>
          </div>
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap-narrow">
        <span class="eyebrow">Foundation</span>
        <h2 class="h-sec">설립 취지</h2>
        <p class="lead" style="margin-bottom:20px">
          생성형 AI는 몇 년 사이 학습, 연구, 업무의 기본 도구가 되었습니다. 그러나 기술이 퍼지는 속도에 비해
          <strong>“어디까지 활용해도 되는가”</strong>에 대한 사회적 합의는 아직 충분히 마련되지 않았습니다.
        </p>
        <p class="lead" style="margin-bottom:20px">
          그 결과 현장에서는 두 가지 문제가 동시에 발생합니다. 하나는 AI를 활용하고도 이를 밝히지 못해 생기는
          불필요한 오해와 분쟁이고, 다른 하나는 막연한 불안 때문에 정당한 활용마저 위축되는 상황입니다.
          두 문제 모두 <strong>명확한 기준의 부재</strong>에서 비롯됩니다.
        </p>
        <p class="lead">
          한국AI윤리위원회는 이 공백을 메우기 위해 출발했습니다. 규제하거나 처벌하는 기구가 아니라,
          AI를 쓰는 사람들이 <strong>스스로 지킬 수 있는 기준</strong>을 정리하고 알리며,
          함께 실천할 사람들을 모으는 자율 위원회입니다.
        </p>
      </div>
    </section>

    <section class="section section--ink">
      <div class="wrap">
        <div class="grid grid-2" style="gap:48px">
          <div>
            <span class="eyebrow">Mission</span>
            <h2 class="h-sec" style="color:#fff">미션</h2>
            <p class="h-sub" style="font-size:17px">
              생성형 AI를 활용하는 모든 사람이 <strong style="color:#6FE3D8">책임 있게, 투명하게, 공정하게</strong>
              AI를 사용할 수 있도록 실천 가능한 기준을 만들고 확산한다.
            </p>
          </div>
          <div>
            <span class="eyebrow">Vision</span>
            <h2 class="h-sec" style="color:#fff">비전</h2>
            <p class="h-sub" style="font-size:17px">
              AI 활용 사실을 <strong style="color:#6FE3D8">숨기지 않아도 되는 사회</strong>,
              사전 점검이 제재가 아니라 상식이 되는 문화를 만든다.
            </p>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="center" style="margin-bottom:42px">
          <span class="eyebrow">Core Values</span>
          <h2 class="h-sec">4대 핵심가치</h2>
        </div>
        <div class="grid grid-4">
{val_rows}
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:34px">
          <span class="eyebrow">Charter</span>
          <h2 class="h-sec">AI 윤리 실천 헌장</h2>
          <p class="h-sub">위원회와 위원, 파트너가 공유하는 7개 실천 조항입니다.</p>
        </div>
        <div style="background:#fff;border:1px solid var(--gray-200);border-radius:var(--radius-lg);padding:14px 32px">
          <ul>
{charter}
          </ul>
        </div>
        <div class="notice notice--teal" style="margin-top:26px">
          본 헌장은 <strong>자율적 실천 규범</strong>이며 법적 구속력을 가지지 않습니다.
          위원회의 모든 활동과 위원·파트너의 활동은 이 헌장을 기준으로 삼습니다.
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="grid grid-2" style="gap:52px;align-items:start">
          <div>
            <span class="eyebrow">History</span>
            <h2 class="h-sec">주요 연혁</h2>
            <p class="h-sub" style="margin-bottom:30px">위원회의 활동 기록입니다.</p>
            <div class="timeline" id="historyList"></div>
          </div>
          <div>
            <span class="eyebrow">Overview</span>
            <h2 class="h-sec">위원회 개요</h2>
            <p class="h-sub" style="margin-bottom:26px">기본 정보입니다.</p>
            <div class="table-wrap">
              <table class="tbl" style="min-width:auto">
                <tbody>
                  <tr><th style="width:34%">명칭</th><td>한국AI윤리위원회<br><span style="color:var(--gray-500);font-size:13.5px">Korea AI Ethics Committee (KAIEC)</span></td></tr>
                  <tr><th>성격</th><td>AI 윤리 전문 위원회</td></tr>
                  <tr><th>목적</th><td>책임 있는 생성형 AI 활용 및 AI 윤리 문화 확산</td></tr>
                  <tr><th>주요 활동</th><td>교육 · 연구 · 캠페인 · 대외협력 · AI 윤리 파트너 운영</td></tr>
                  <tr><th>운영 방식</th><td>온라인 기반 (위원·파트너 활동 재택 가능)</td></tr>
                  <tr><th>대표 문의</th><td><a href="mailto:{EMAIL}" style="color:var(--blue);font-weight:600">{EMAIL}</a></td></tr>
                </tbody>
              </table>
            </div>
            <div class="notice notice--teal" style="margin-top:22px">
              위원회 활동에 관한 문의는 언제든 환영합니다. 대표 메일로 보내주시면 담당자가 신속히 회신드립니다.
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="cta-band">
          <div>
            <h2>위원회 활동에 참여하시겠습니까?</h2>
            <p>전문위원 · 활동위원 · AI 윤리 파트너를 상시 모집하고 있습니다.</p>
          </div>
          <div class="btns"><a class="btn btn-white" href="apply.html">지원 안내 보기</a></div>
        </div>
      </div>
    </section>"""

    script = """  <script src="assets/js/history-data.js"></script>
  <script src="assets/js/members-data.js"></script>
  <script>
  (function(){
    var box=document.getElementById('historyList');
    if(box&&window.KAIEC_HISTORY){
      box.innerHTML=window.KAIEC_HISTORY.map(function(h){
        return '<div class="tl-item"><div class="tl-date">'+h.date+'</div>'
          +'<div class="tl-title">'+h.title+'</div>'
          +(h.desc?'<div class="tl-desc">'+h.desc+'</div>':'')+'</div>';
      }).join('');
    }
    /* 위원장 성함은 members-data.js의 위원장 항목에서 자동으로 가져옵니다 */
    var sign=document.getElementById('chairName');
    if(sign&&window.KAIEC_MEMBERS){
      var chair=window.KAIEC_MEMBERS.filter(function(m){return m.group==='위원장'})[0];
      if(chair)sign.textContent=chair.name;
    }
  })();
  </script>
"""
    page("about.html", "위원회 소개",
         "한국AI윤리위원회 위원장 인사말, 설립 취지, 미션과 비전, 4대 핵심가치, AI 윤리 실천 헌장 7개 조항과 위원회 개요를 안내합니다.",
         body, extra_script=script)


# ------------------------------------------------------------- business.html
def build_business():
    blocks = []
    for i, (ic, t, d, items) in enumerate(BUSINESS):
        lis = "\n".join(f"""              <li style="display:flex;gap:10px;align-items:flex-start;padding:7px 0">
                <i data-lucide="chevron-right" style="width:17px;height:17px;color:var(--blue);flex-shrink:0;margin-top:5px"></i>
                <span style="font-size:15px;color:var(--gray-700)">{x}</span></li>""" for x in items)
        rev = "direction:rtl" if i % 2 else ""
        inner = "direction:ltr" if i % 2 else ""
        blocks.append(f"""      <div class="split reveal" style="margin-bottom:64px;{rev}">
          <div style="{inner}">
            <span class="card-num">사업 {i+1:02d}</span>
            <h2 style="font-size:26px;letter-spacing:-.035em;margin-bottom:14px">{t}</h2>
            <p style="font-size:16px;color:var(--gray-600);line-height:1.8;margin-bottom:18px">{d}</p>
            <ul>
{lis}
            </ul>
          </div>
          <div class="split-visual" style="{inner};min-height:250px{';background:linear-gradient(150deg,#0A1628,#00857A)' if i%3==2 else ''}">
            <div class="card-icon" style="background:rgba(255,255,255,.14);color:#fff;width:58px;height:58px">
              <i data-lucide="{ic}" style="width:27px;height:27px"></i>
            </div>
            <h3 style="font-size:22px;letter-spacing:-.035em">{t}</h3>
          </div>
        </div>""")

    body = hero_sub("주요사업",
                    "선언에 머무르지 않고 현장에서 작동하는 6개 영역의 활동을 추진합니다.",
                    "주요사업") + f"""

    <section class="section">
      <div class="wrap">
        <div class="center" style="margin-bottom:52px">
          <span class="eyebrow">Main Business</span>
          <h2 class="h-sec">6대 주요사업</h2>
          <p class="h-sub">교육 · 연구 · 캠페인 · 대외협력을 축으로, AI를 쓰는 사람이 실제로 활용할 수 있는 결과물을 만드는 데 집중합니다.</p>
        </div>
{"".join(blocks)}
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap">
        <div class="center" style="margin-bottom:40px">
          <span class="eyebrow">How We Work</span>
          <h2 class="h-sec">추진 방식</h2>
        </div>
        <div class="grid grid-4">
          <article class="card reveal"><span class="card-num">STEP 01</span><h3>현장 확인</h3>
            <p>대학·기업·연구 현장에서 실제로 어떤 어려움이 있는지 확인하는 것에서 출발합니다.</p></article>
          <article class="card reveal"><span class="card-num">STEP 02</span><h3>기준 정리</h3>
            <p>국내외 AI 윤리 기준과 정책 동향을 참고해 실천 가능한 형태로 정리합니다.</p></article>
          <article class="card reveal"><span class="card-num">STEP 03</span><h3>확산·교육</h3>
            <p>캠페인·콘텐츠·강의 등 접근하기 쉬운 형태로 만들어 널리 알립니다.</p></article>
          <article class="card reveal"><span class="card-num">STEP 04</span><h3>협력 확대</h3>
            <p>대학·기업·협회와의 MOU 및 파트너 활동으로 실천 범위를 넓힙니다.</p></article>
        </div>
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="cta-band">
          <div><h2>사업 참여 및 협력 문의</h2>
            <p>공동 캠페인, 교육 프로그램, 기관 협약 등 협력을 원하시면 언제든 문의해 주세요.</p></div>
          <div class="btns">
            <a class="btn btn-white" href="lecture.html">강의·교육 신청</a>
            <a class="btn btn-light" href="mou.html#inquiry">제휴 문의하기</a>
            <a class="btn btn-light" href="apply.html">위원 지원</a>
          </div>
        </div>
      </div>
    </section>"""

    page("business.html", "주요사업",
         "책임 있는 생성형 AI 활용 확산, AI 윤리 캠페인·교육, AI 윤리 파트너 운영, 대학·기업 MOU, AI 활용 문서 사전점검, AI 윤리 연구 등 한국AI윤리위원회의 6대 주요사업을 소개합니다.",
         body)


# -------------------------------------------------------------- members.html
def build_members():
    body = hero_sub("조직 · 위원",
                    "위원장, 운영진, 전문위원, 활동위원이 각자의 전문성을 바탕으로 위원회 활동을 함께 만들어갑니다.",
                    "조직 · 위원") + f"""

    <section class="section">
      <div class="wrap">
        <div class="center" style="margin-bottom:46px">
          <span class="eyebrow">Organization Chart</span>
          <h2 class="h-sec">조직도</h2>
          <p class="h-sub">위원회는 위원장을 중심으로 사무국과 6개 전문분과, 활동위원회를 두고,
             전국 단위의 지역 운영위원회·캠퍼스 위원회와 AI 윤리 파트너 조직으로 구성됩니다.</p>
        </div>

        <div class="org-chart">
          <!-- 위원장 -->
          <div class="oc-node oc-lv1">
            <div class="oc-tag">CHAIRPERSON</div>
            <div class="oc-title">위원장</div>
            <div class="oc-desc">위원회 대표 · 전체 활동 총괄</div>
          </div>

          <!-- 감사 / 고문·자문위원단 (독립 기구) -->
          <div class="oc-siderow">
            <div class="oc-node oc-side">
              <div class="oc-tag" style="color:var(--gray-500)">AUDIT</div>
              <div class="oc-title" style="font-size:15.5px">감사</div>
              <div class="oc-desc">운영·회계 독립 감사</div>
            </div>
            <div class="oc-dash"></div>
            <div class="oc-spine"></div>
            <div class="oc-dash"></div>
            <div class="oc-node oc-side">
              <div class="oc-tag" style="color:var(--gray-500)">ADVISORY BOARD</div>
              <div class="oc-title" style="font-size:15.5px">고문 · 자문위원단</div>
              <div class="oc-desc">학계·산업계·법조계 자문</div>
            </div>
          </div>

          <!-- 부위원장 · 운영위원장 -->
          <div class="oc-node oc-lv2">
            <div class="oc-tag">VICE CHAIR · STEERING</div>
            <div class="oc-title">부위원장 · 운영위원장</div>
            <div class="oc-desc">위원장 보좌 · 운영 총괄</div>
          </div>

          <div class="oc-vline"></div>
          <div class="oc-hline"></div>

          <!-- 3대 축: 사무국 / 전문위원회 / 활동위원회 -->
          <div class="oc-branches">
            <div class="oc-branch">
              <div class="oc-stub"></div>
              <div class="oc-node oc-pillar">
                <div class="oc-tag">SECRETARIAT</div>
                <div class="oc-title">사무국</div>
                <div class="oc-desc">행정 · 운영 실무 총괄</div>
              </div>
              <div class="oc-childs">
                <div class="oc-child">기획운영팀 <small>사업 기획 · 총무 · 회의 운영</small></div>
                <div class="oc-child">대외협력팀 <small>MOU · 기관 제휴 · 파트너십</small></div>
                <div class="oc-child">콘텐츠·홍보팀 <small>캠페인 · 콘텐츠 · 채널 운영</small></div>
              </div>
            </div>
            <div class="oc-branch">
              <div class="oc-stub"></div>
              <div class="oc-node oc-pillar oc-pillar--teal">
                <div class="oc-tag" style="color:#00857A">EXPERT COMMITTEES</div>
                <div class="oc-title">전문위원회</div>
                <div class="oc-desc">6개 분과 · 분야별 자문과 기준 검토</div>
              </div>
              <div class="oc-childs">
                <div class="oc-child">AI·기술 분과 <small>생성형 AI 기술 동향 · 판별 기술</small></div>
                <div class="oc-child">법·정책 분과 <small>AI 관련 법제 · 정책 동향</small></div>
                <div class="oc-child">교육·리터러시 분과 <small>AI 윤리 교육 · 교안 개발</small></div>
                <div class="oc-child">연구·출판윤리 분과 <small>논문·연구물 AI 활용 기준</small></div>
                <div class="oc-child">데이터·개인정보 분과 <small>데이터 윤리 · 프라이버시</small></div>
                <div class="oc-child">미디어·콘텐츠 분과 <small>허위정보 · 콘텐츠 윤리</small></div>
              </div>
            </div>
            <div class="oc-branch">
              <div class="oc-stub"></div>
              <div class="oc-node oc-pillar oc-pillar--gray">
                <div class="oc-tag" style="color:var(--gray-500)">ACTIVITY COMMITTEE</div>
                <div class="oc-title">활동위원회</div>
                <div class="oc-desc">현장 활동 조직</div>
              </div>
              <div class="oc-childs">
                <div class="oc-child">운영위원 <small>프로그램 운영 · 활동 관리</small></div>
                <div class="oc-child">홍보위원단 <small>채널 홍보 · 콘텐츠 확산</small></div>
                <div class="oc-child">서포터즈 <small>대학생·대학원생 참여 조직</small></div>
              </div>
            </div>
          </div>

          <div class="oc-vline"></div>

          <!-- 지역 · 캠퍼스 조직 -->
          <div class="oc-band">
            <span class="badge">전국 조직</span>
            <div>
              <div class="oc-title">지역 운영위원회 · 캠퍼스 위원회</div>
              <div class="oc-desc">권역별 지역 운영위원과 대학별 캠퍼스 위원장을 중심으로 한 현장 확산 조직</div>
            </div>
          </div>

          <div class="oc-vline"></div>

          <!-- AI 윤리 파트너 -->
          <div class="oc-band oc-band--accent">
            <span class="badge badge--teal">온라인 · 전국</span>
            <div>
              <div class="oc-title">AI 윤리 파트너</div>
              <div class="oc-desc">온라인·재택 기반으로 AI 윤리 문화 확산 활동에 참여하는 개방형 파트너 조직</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap">
        <div class="center" style="margin-bottom:40px">
          <span class="eyebrow">Expert Committees</span>
          <h2 class="h-sec">6개 전문분과</h2>
          <p class="h-sub">각 분과는 해당 분야의 전문위원으로 구성되며, 위원회가 발표하는 기준과 콘텐츠를 검토·자문합니다.</p>
        </div>
        <div class="grid grid-3">
          <article class="card reveal"><div class="card-icon"><i data-lucide="cpu"></i></div>
            <h3>AI·기술 분과</h3><p>생성형 AI 기술 동향 분석, AI 생성물 판별 기술 검토, 기술적 쟁점 자문을 담당합니다.</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="scale"></i></div>
            <h3>법·정책 분과</h3><p>AI 관련 국내외 법제와 정책 동향을 검토하고, 위원회 기준의 법적 정합성을 자문합니다.</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="graduation-cap"></i></div>
            <h3>교육·리터러시 분과</h3><p>AI 윤리 교육 프로그램과 교안을 개발하고, 세대별 눈높이에 맞는 교육 방식을 연구합니다.</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="book-open-check"></i></div>
            <h3>연구·출판윤리 분과</h3><p>논문·과제·연구물에서의 AI 활용 표기 기준과 사전점검 가이드라인을 검토합니다.</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="database"></i></div>
            <h3>데이터·개인정보 분과</h3><p>AI 학습·활용 과정의 데이터 윤리와 개인정보 보호 쟁점을 다룹니다.</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="monitor-play"></i></div>
            <h3>미디어·콘텐츠 분과</h3><p>AI 생성 콘텐츠와 허위정보 문제, 미디어 환경에서의 책임 있는 활용을 다룹니다.</p></article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:34px">
          <span class="eyebrow">Operation</span>
          <h2 class="h-sec">운영 개요</h2>
        </div>
        <div class="table-wrap">
          <table class="tbl" style="min-width:auto">
            <tbody>
              <tr><th style="width:30%">기수</th><td>제1기 위원회 (2026. 8 ~ )</td></tr>
              <tr><th>위원 임기</th><td>2년 (연임 가능)</td></tr>
              <tr><th>회의</th><td>정기회의 분기 1회 · 임시회의 수시 (온라인 병행)</td></tr>
              <tr><th>의결</th><td>재적위원 과반수 출석과 출석위원 과반수 찬성</td></tr>
              <tr><th>분과</th><td>6개 전문분과 (AI·기술, 법·정책, 교육·리터러시, 연구·출판윤리, 데이터·개인정보, 미디어·콘텐츠)</td></tr>
              <tr><th>전국 조직</th><td>지역 운영위원회 · 캠퍼스 위원회 · AI 윤리 파트너</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap">
        <div class="center" style="margin-bottom:40px">
          <span class="eyebrow">Members</span>
          <h2 class="h-sec">위원 명단</h2>
          <p class="h-sub">직책과 전문분야를 기준으로 구분해 안내합니다.</p>
        </div>
        <div id="memberSections"></div>

        <div class="notice notice--gray" style="margin-top:34px">
          <strong>명단 추가 방법 —</strong> <code>assets/js/members-data.js</code> 파일을 열어 배열에 항목을 추가하면
          이 페이지에 자동으로 반영됩니다. HTML을 수정할 필요가 없습니다.
        </div>
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="cta-band">
          <div><h2>위원으로 함께하시겠습니까?</h2>
            <p>전문위원 · 활동위원을 상시 모집합니다. 전공과 경력에 관계없이 지원하실 수 있습니다.</p></div>
          <div class="btns"><a class="btn btn-white" href="{GOOGLE_FORM}" target="_blank" rel="noopener">위원 지원하기</a><a class="btn btn-light" href="apply.html">모집 안내</a></div>
        </div>
      </div>
    </section>"""

    script = """  <script src="assets/js/members-data.js"></script>
  <script>
  (function(){
    var box=document.getElementById('memberSections');
    if(!box||!window.KAIEC_MEMBERS)return;
    var groups=['위원장','부위원장','감사','고문·자문위원','운영위원','전문위원','지역 운영위원','캠퍼스 위원장','홍보위원','활동위원','서포터즈'];
    var html='';
    groups.forEach(function(g){
      var list=window.KAIEC_MEMBERS.filter(function(m){return m.group===g});
      if(!list.length)return;
      html+='<div style="margin-bottom:44px">'
        +'<h3 style="font-size:19px;margin-bottom:18px;display:flex;align-items:center;gap:10px">'
        +'<span style="width:4px;height:19px;background:var(--blue);border-radius:2px"></span>'+g
        +' <span style="font-size:13px;font-weight:600;color:var(--gray-500)">('+list.length+'명)</span></h3>'
        +'<div class="member-grid">'
        +list.map(function(m){
          var initial=(m.name||'?').replace(/[^가-힣A-Za-z]/g,'').slice(0,1)||'·';
          return '<div class="member">'
            +'<div class="member-avatar">'+initial+'</div>'
            +'<div class="member-role">'+(m.role||g)+'</div>'
            +'<div class="member-name">'+m.name+'</div>'
            +'<div class="member-field">'+(m.field||'')+'</div>'
            +'</div>';
        }).join('')
        +'</div></div>';
    });
    box.innerHTML=html||'<p style="text-align:center;color:var(--gray-500);padding:40px 0">위원 명단은 준비 중입니다.</p>';
  })();
  </script>
"""
    page("members.html", "조직 · 위원",
         "한국AI윤리위원회의 조직 구성과 위원장·운영위원·전문위원·활동위원 명단, 직책 및 전문분야를 안내합니다.",
         body, extra_script=script)


# -------------------------------------------------------------- partner.html
def build_partner():
    faqs = [
        ("AI나 윤리 전공자가 아니어도 지원할 수 있나요?",
         "네, 가능합니다. AI 윤리 파트너는 전공이나 경력 요건이 없습니다. 생성형 AI를 사용해 본 경험이 있고 책임 있는 활용에 관심이 있다면 누구나 지원하실 수 있습니다."),
        ("활동은 어디에서 하나요? 정해진 근무 시간이 있나요?",
         "모든 활동은 온라인·재택으로 진행되며 정해진 출근 시간이나 장소가 없습니다. 각자의 일정에 맞춰 배정된 활동을 수행하시면 됩니다."),
        ("위촉장과 활동증명서는 어떤 문서인가요?",
         "위원회가 파트너의 위촉 사실과 활동 내역을 확인해 위원회 명의로 발급하는 문서입니다. 대외활동 이력서나 포트폴리오의 증빙 자료로 활용하실 수 있습니다."),
        ("인센티브는 어떤 기준으로 지급되나요?",
         "활동 실적(캠페인 참여, 콘텐츠 제작, 제휴 캠페인 기여 등)을 기준으로 산정합니다. 구체적인 기준과 지급 방식은 위촉 시 개별 안내드립니다."),
        ("활동 기간은 어떻게 되나요?",
         "기본 위촉 기간은 6개월이며, 상호 협의에 따라 연장할 수 있습니다. 개인 사정으로 중도 종료를 원하실 경우 언제든 알려주시면 됩니다."),
        ("비용이 드나요?",
         "가입비·교육비·연회비 등 파트너가 위원회에 지불하는 비용은 일절 없습니다."),
    ]
    faq_html = "\n".join(f"""        <details class="acc">
          <summary>{q}</summary>
          <div class="acc-body">{a}</div>
        </details>""" for q, a in faqs)

    body = hero_sub("AI 윤리 파트너",
                    "온라인·재택으로 AI 윤리 문화 확산에 참여하는 위원회의 대표 참여 제도입니다.",
                    "AI 윤리 파트너") + f"""

    <section class="section">
      <div class="wrap-narrow center">
        <span class="eyebrow">Partner Program</span>
        <h2 class="h-sec">AI를 쓰는 사람이<br>AI 윤리를 알리는 사람이 됩니다</h2>
        <p class="h-sub" style="margin:0 auto">
          AI 윤리는 전문가 몇 명이 만드는 것이 아니라, AI를 실제로 사용하는 사람들이 함께 만들어가는 것입니다.
          AI 윤리 파트너는 그 확산을 현장에서 담당하는 위원회의 파트너입니다.
        </p>
        <div style="display:flex;gap:11px;justify-content:center;flex-wrap:wrap;margin-top:28px">
          <a class="btn btn-primary" href="{GOOGLE_FORM}" target="_blank" rel="noopener">파트너 지원하기 <i data-lucide="external-link"></i></a>
          <a class="btn btn-ghost" href="#apply-info">활동·혜택 먼저 보기</a>
        </div>
      </div>
    </section>

    <section class="section section--gray section--tight" id="apply-info">
      <div class="wrap">
        <div class="grid grid-4">
          <div class="card reveal center"><div class="card-icon" style="margin:0 auto 16px"><i data-lucide="wifi"></i></div>
            <h3>100% 온라인</h3><p>출근·대면 없이 재택으로 참여</p></div>
          <div class="card reveal center"><div class="card-icon" style="margin:0 auto 16px"><i data-lucide="award"></i></div>
            <h3>공식 위촉장</h3><p>위원회 명의 위촉장 발급</p></div>
          <div class="card reveal center"><div class="card-icon" style="margin:0 auto 16px"><i data-lucide="file-check"></i></div>
            <h3>활동증명서</h3><p>활동 내역 확인 문서 발급</p></div>
          <div class="card reveal center"><div class="card-icon card-icon--teal" style="margin:0 auto 16px"><i data-lucide="gift"></i></div>
            <h3>활동 인센티브</h3><p>실적에 따른 인센티브 지급</p></div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="center" style="margin-bottom:42px">
          <span class="eyebrow">Activities</span>
          <h2 class="h-sec">파트너 활동 내용</h2>
          <p class="h-sub">본인의 관심과 여건에 맞는 활동을 선택해 참여하실 수 있습니다.</p>
        </div>
        <div class="grid grid-3">
          <article class="card reveal">
            <div class="card-icon"><i data-lucide="megaphone"></i></div>
            <h3>AI 윤리 문화 확산 캠페인</h3>
            <p>온라인 캠페인, 카드뉴스·영상 등 AI 윤리 콘텐츠를 공유하고 주변에 알리는 활동입니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon"><i data-lucide="pen-line"></i></div>
            <h3>콘텐츠 기획 및 제작</h3>
            <p>사례 정리, 글·이미지·영상 제작 등 위원회 콘텐츠 제작에 참여합니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon card-icon--teal"><i data-lucide="handshake"></i></div>
            <h3>카피클린 제휴 캠페인</h3>
            <p>제휴 서비스 「카피클린」과 함께하는 AI 활용 문서 사전점검 캠페인에 참여합니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon"><i data-lucide="school"></i></div>
            <h3>대학·커뮤니티 알림 활동</h3>
            <p>소속 대학, 학과, 온라인 커뮤니티 등에 AI 윤리 활동을 안내합니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon"><i data-lucide="clipboard-list"></i></div>
            <h3>현장 의견 수집</h3>
            <p>AI 활용 현장에서 겪는 어려움과 사례를 수집해 위원회에 전달합니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon"><i data-lucide="users-round"></i></div>
            <h3>파트너 네트워크 참여</h3>
            <p>온라인 모임과 스터디에 참여해 다른 파트너들과 정보를 나눕니다.</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section section--ink">
      <div class="wrap">
        <div class="center" style="margin-bottom:40px">
          <span class="eyebrow">Benefits</span>
          <h2 class="h-sec" style="color:#fff">파트너 혜택</h2>
        </div>
        <div class="grid grid-3">
          <div style="background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:30px">
            <div style="width:46px;height:46px;border-radius:13px;background:rgba(111,227,216,.16);color:#6FE3D8;display:flex;align-items:center;justify-content:center;margin-bottom:16px"><i data-lucide="award"></i></div>
            <h3 style="color:#fff;font-size:18px;margin-bottom:9px">공식 위촉장 발급</h3>
            <p style="color:#9FB3D1;font-size:14.5px;line-height:1.75">위촉 시 위원회 명의의 「AI 윤리 파트너」 위촉장을 발급합니다.</p>
          </div>
          <div style="background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:30px">
            <div style="width:46px;height:46px;border-radius:13px;background:rgba(111,227,216,.16);color:#6FE3D8;display:flex;align-items:center;justify-content:center;margin-bottom:16px"><i data-lucide="file-check"></i></div>
            <h3 style="color:#fff;font-size:18px;margin-bottom:9px">활동증명서 발급</h3>
            <p style="color:#9FB3D1;font-size:14.5px;line-height:1.75">활동 종료 또는 요청 시 활동 기간과 내역을 담은 증명서를 발급합니다.</p>
          </div>
          <div style="background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:30px">
            <div style="width:46px;height:46px;border-radius:13px;background:rgba(111,227,216,.16);color:#6FE3D8;display:flex;align-items:center;justify-content:center;margin-bottom:16px"><i data-lucide="trending-up"></i></div>
            <h3 style="color:#fff;font-size:18px;margin-bottom:9px">활동 인센티브</h3>
            <p style="color:#9FB3D1;font-size:14.5px;line-height:1.75">캠페인 참여·콘텐츠 제작 등 활동 실적에 따라 인센티브를 지급합니다.</p>
          </div>
        </div>
        <div class="footer-disclaimer" style="margin-top:26px">
          인센티브의 구체적 기준과 지급 방식은 위촉 시 개별 안내드립니다.
          위촉장·활동증명서는 요청 시 즉시 발급해 드립니다.
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:38px">
          <span class="eyebrow">How to Join</span>
          <h2 class="h-sec">지원 자격 및 절차</h2>
        </div>
        <div class="table-wrap" style="margin-bottom:34px">
          <table class="tbl" style="min-width:auto">
            <tbody>
              <tr><th style="width:28%">지원 자격</th><td>AI 윤리에 관심 있는 만 19세 이상 누구나 (전공·경력 무관)</td></tr>
              <tr><th>활동 방식</th><td>온라인 · 재택</td></tr>
              <tr><th>위촉 기간</th><td>6개월 (협의 시 연장 가능)</td></tr>
              <tr><th>모집 시기</th><td>상시</td></tr>
              <tr><th>지원 비용</th><td>없음 (가입비·교육비 일절 없음)</td></tr>
            </tbody>
          </table>
        </div>
        <div class="grid grid-4">
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 01</span><h3 style="font-size:16px">온라인 지원</h3><p style="font-size:14px">지원서 작성·제출</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 02</span><h3 style="font-size:16px">서류 검토</h3><p style="font-size:14px">약 3~5일 소요</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 03</span><h3 style="font-size:16px">위촉 안내</h3><p style="font-size:14px">위촉장 발급 · 오리엔테이션</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 04</span><h3 style="font-size:16px">활동 시작</h3><p style="font-size:14px">활동 배정 및 수행</p></div>
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:34px">
          <span class="eyebrow">FAQ</span>
          <h2 class="h-sec">자주 묻는 질문</h2>
        </div>
{faq_html}
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="cta-band">
          <div><h2>AI 윤리 파트너로 함께해 주세요</h2>
            <p>온라인으로 간편하게 지원하실 수 있습니다. 궁금한 점은 언제든 문의해 주세요.</p></div>
          <div class="btns">
            <a class="btn btn-white" href="{GOOGLE_FORM}" target="_blank" rel="noopener">파트너 지원하기</a>
            <a class="btn btn-light" href="mailto:{EMAIL}">문의하기</a>
          </div>
        </div>
      </div>
    </section>"""

    page("partner.html", "AI 윤리 파트너",
         "한국AI윤리위원회 AI 윤리 파트너는 온라인·재택으로 AI 윤리 문화 확산 캠페인에 참여하며, 공식 위촉장과 활동증명서 발급, 활동 실적에 따른 인센티브 혜택을 받을 수 있습니다.",
         body)


# ------------------------------------------------------------- copyclean.html
def build_copyclean():
    body = hero_sub("제휴 서비스 「카피클린」",
                    "AI 활용 문서의 책임 있는 사전점검 문화를 함께 만들어가는 위원회의 협력 서비스입니다.",
                    "카피클린") + f"""

    <section class="section">
      <div class="wrap">
        <div class="notice" style="margin-bottom:48px">
          <strong>파트너십 —</strong> 한국AI윤리위원회와 「카피클린(CopyClean)」은
          AI 활용 문서의 <strong>사전점검 문화 확산</strong>을 위해 협력하는 파트너입니다.
          위원회는 윤리 기준·캠페인·교육을, 카피클린은 AI 문서 분석 기술을 담당합니다.
        </div>

        <div class="split">
          <div class="reveal">
            <span class="eyebrow">Affiliated Service</span>
            <h2 class="h-sec">카피클린 (CopyClean)</h2>
            <p class="lead" style="margin-bottom:18px">
              논문 · 과제 · 보고서 · 자기소개서 등 다양한 문서를 대상으로
              <strong>AI 활용 여부를 사전에 확인</strong>할 수 있도록 지원하는 AI 문서 분석 서비스입니다.
            </p>
            <p style="font-size:16px;color:var(--gray-600);line-height:1.8;margin-bottom:24px">
              제출하기 전에 스스로 확인해 볼 수 있다는 점이 핵심입니다.
              문제를 사후에 지적하는 것이 아니라, 사전에 점검해 불필요한 오해와 분쟁을 예방하는 데 목적이 있습니다.
            </p>
            <a class="btn btn-teal" href="{COPYCLEAN_URL}" target="_blank" rel="noopener">카피클린 공식 사이트 바로가기 <i data-lucide="external-link"></i></a>
          </div>
          <div class="split-visual reveal" style="background:linear-gradient(150deg,#0A1628,#00857A)">
            <div class="card-icon" style="background:rgba(255,255,255,.15);color:#fff;width:56px;height:56px">
              <i data-lucide="file-search" style="width:26px;height:26px"></i>
            </div>
            <h3 style="font-size:25px;letter-spacing:-.035em">제출 전에<br>스스로 확인하는 습관</h3>
            <p style="color:#CDE9E5;font-size:15px;line-height:1.8">
              논문 · 과제 · 보고서 · 자기소개서<br>다양한 문서의 AI 활용 여부 사전 확인</p>
            <a class="btn btn-white btn-sm" href="{COPYCLEAN_URL}" target="_blank" rel="noopener" style="align-self:flex-start">skkc.co.kr <i data-lucide="external-link"></i></a>
          </div>
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap">
        <div class="center" style="margin-bottom:42px">
          <span class="eyebrow">Collaboration</span>
          <h2 class="h-sec">위원회 × 카피클린 제휴 활동</h2>
          <p class="h-sub">위원회는 카피클린과 함께 AI 활용 문서의 사전점검 및 책임 있는 AI 활용 문화 확산을 위한
             캠페인과 제휴 활동을 진행합니다.</p>
        </div>
        <div class="grid grid-3">
          <article class="card reveal">
            <div class="card-icon card-icon--teal"><i data-lucide="megaphone"></i></div>
            <h3>사전점검 캠페인</h3>
            <p>“제출 전에 한 번 확인하기”를 주제로 한 공동 캠페인을 기획·운영합니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon card-icon--teal"><i data-lucide="book-open-check"></i></div>
            <h3>가이드라인 공동 개발</h3>
            <p>문서 유형별 AI 활용 표기 및 점검 가이드라인을 함께 정리해 배포합니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon card-icon--teal"><i data-lucide="graduation-cap"></i></div>
            <h3>대학·기관 대상 안내</h3>
            <p>대학과 기관을 대상으로 사전점검 문화의 필요성을 함께 알립니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon card-icon--teal"><i data-lucide="users"></i></div>
            <h3>파트너 연계 활동</h3>
            <p>AI 윤리 파트너가 참여하는 제휴 캠페인을 공동으로 운영합니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon card-icon--teal"><i data-lucide="bar-chart-3"></i></div>
            <h3>사례 수집 및 공유</h3>
            <p>현장에서 실제로 발생하는 AI 활용 관련 사례를 수집해 공유합니다.</p>
          </article>
          <article class="card reveal">
            <div class="card-icon card-icon--teal"><i data-lucide="shield-check"></i></div>
            <h3>윤리 기준 자문</h3>
            <p>위원회가 정리한 AI 윤리 기준을 서비스 운영에 참고할 수 있도록 자문합니다.</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="cta-band reveal" style="background:linear-gradient(140deg,#03231F,#00857A)">
          <div>
            <h2>제출 전, 카피클린에서 직접 확인해 보세요</h2>
            <p style="color:#BFE8E3">논문 · 과제 · 보고서 · 자기소개서의 AI 활용 여부를 제출 전에 스스로 점검할 수 있습니다.</p>
          </div>
          <div class="btns">
            <a class="btn btn-white" href="{COPYCLEAN_URL}" target="_blank" rel="noopener">카피클린 바로가기 <i data-lucide="external-link"></i></a>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:34px">
          <span class="eyebrow">Roles</span>
          <h2 class="h-sec">역할 구분</h2>
          <p class="h-sub">두 주체의 역할을 명확히 구분해 안내드립니다.</p>
        </div>
        <div class="table-wrap">
          <table class="tbl">
            <thead>
              <tr><th style="width:22%">구분</th><th>한국AI윤리위원회</th><th>카피클린 (CopyClean)</th></tr>
            </thead>
            <tbody>
              <tr><th>성격</th><td>AI 윤리 전문 위원회</td><td>AI 문서 분석 서비스</td></tr>
              <tr><th>역할</th><td>AI 윤리 문화 확산, 교육·연구·캠페인, 대외협력</td><td>문서의 AI 활용 여부 사전 확인 지원</td></tr>
              <tr><th>관계</th><td colspan="2" style="text-align:center;font-weight:700;color:var(--blue)">캠페인·제휴 활동을 함께하는 협력 파트너</td></tr>
              <tr><th>대상</th><td>개인 · 대학 · 기업 · 협회 등</td><td>논문 · 과제 · 보고서 · 자기소개서 등 문서</td></tr>
            </tbody>
          </table>
        </div>
        <div class="notice notice--teal" style="margin-top:24px">
          두 파트너는 "제출 전에 스스로 확인하는 문화"라는 공동의 목표 아래
          캠페인 · 교육 · 가이드라인 개발을 함께 진행하고 있습니다.
        </div>
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="cta-band">
          <div><h2>사전점검 캠페인에 함께하시겠습니까?</h2>
            <p>대학·기관 단위 공동 캠페인 및 제휴 문의를 환영합니다.</p></div>
          <div class="btns">
            <a class="btn btn-white" href="mou.html#inquiry">제휴 문의하기</a>
            <a class="btn btn-light" href="partner.html">파트너 참여</a>
          </div>
        </div>
      </div>
    </section>"""

    page("copyclean.html", "카피클린 제휴",
         "한국AI윤리위원회의 제휴 서비스 「카피클린(CopyClean)」은 논문·과제·보고서·자기소개서 등의 AI 활용 여부를 사전에 확인할 수 있도록 지원하는 AI 문서 분석 서비스입니다. 위원회는 카피클린과 사전점검 캠페인을 함께 진행합니다.",
         body)


# ----------------------------------------------------------------- news.html
def build_news(posts):
    cat_btns = '<button class="btn btn-sm btn-primary" data-cat="전체">전체</button>' + "".join(
        f'<button class="btn btn-sm btn-ghost" data-cat="{c}">{c}</button>' for c in CATEGORIES)
    cards = "\n".join(board_card(p) for p in posts) if posts else \
        '<p style="text-align:center;color:var(--gray-500);padding:50px 0">등록된 소식이 없습니다.</p>'

    body = hero_sub("캠페인 · 소식",
                    "위원회의 캠페인, 활동 소식, 공지사항과 AI 윤리 이슈를 전합니다.",
                    "캠페인 · 소식") + f"""

    <section class="section">
      <div class="wrap">
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:30px" id="newsFilter">
          {cat_btns}
        </div>
        <div class="board-grid" id="boardGrid">
{cards}
        </div>
      </div>
    </section>"""

    script = """  <script>
  /* 분류 필터 — 게시글 자체는 정적 HTML이라 검색엔진이 전부 읽습니다 */
  (function(){
    var filter=document.getElementById('newsFilter');
    var cards=document.querySelectorAll('#boardGrid .board-card');
    if(!filter)return;
    filter.addEventListener('click',function(e){
      var b=e.target.closest('button[data-cat]');if(!b)return;
      filter.querySelectorAll('button').forEach(function(x){x.className='btn btn-sm btn-ghost'});
      b.className='btn btn-sm btn-primary';
      var cat=b.getAttribute('data-cat');
      cards.forEach(function(c){
        c.style.display=(cat==='전체'||c.getAttribute('data-cat')===cat)?'':'none';
      });
    });
  })();
  </script>
"""
    page("news.html", "캠페인 · 소식",
         "한국AI윤리위원회의 AI 윤리 캠페인, 활동 소식, 공지사항, 연구·정책 이슈를 안내합니다.",
         body, extra_script=script)


# ------------------------------------------------------------- 게시글 페이지
def build_post(p, posts):
    idx = posts.index(p)
    prev_p = posts[idx + 1] if idx + 1 < len(posts) else None   # 이전 글(더 오래된 글)
    next_p = posts[idx - 1] if idx > 0 else None                # 다음 글(더 새 글)

    cover = ""
    ogimg = None
    if p["image"]:
        cover = f'''        <div class="post-cover"><img src="assets/img/posts/{p["image"]}" alt="{_html.escape(p["title"])}"></div>\n'''
        ogimg = f'{SITE_URL}/assets/img/posts/{p["image"]}'

    tags = "".join(f'<span class="chip">#{k}</span>' for k in p["keywords"])
    badge = 'badge--teal' if p["category"] == '캠페인' else ''

    nav_html = '<div class="post-nav">'
    nav_html += (f'<a class="btn btn-ghost btn-sm" href="{prev_p["file"]}"><i data-lucide="arrow-left"></i> 이전 글</a>'
                 if prev_p else '<span></span>')
    nav_html += '<a class="btn btn-primary btn-sm" href="news.html">목록으로</a>'
    nav_html += (f'<a class="btn btn-ghost btn-sm" href="{next_p["file"]}">다음 글 <i data-lucide="arrow-right"></i></a>'
                 if next_p else '<span></span>')
    nav_html += '</div>'

    body = f"""    <section class="page-hero">
      <div class="wrap page-hero-inner" style="max-width:var(--wrap)">
        <p class="crumb"><a href="index.html">홈</a> &nbsp;›&nbsp; <a href="news.html" style="color:inherit">캠페인 · 소식</a></p>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
          <span class="badge {badge}">{p["category"]}</span>
          <span style="font-size:13.5px;color:#7E9AC0;font-weight:600">{p["date"]}</span>
        </div>
        <h1 style="max-width:820px">{p["title"]}</h1>
        <p>{p["summary"]}</p>
      </div>
    </section>

    <section class="section">
      <div class="post-wrap">
{cover}        <article class="post-body">
{md_to_html(p["body"])}
        </article>
        <div class="post-tags">{tags}</div>
{nav_html}
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="cta-band">
          <div><h2>한국AI윤리위원회와 함께하세요</h2>
            <p>위원 · AI 윤리 파트너 모집, 강의·교육 신청, 기관 제휴 문의를 환영합니다.</p></div>
          <div class="btns">
            <a class="btn btn-white" href="{GOOGLE_FORM}" target="_blank" rel="noopener">위원 지원</a>
            <a class="btn btn-light" href="lecture.html">강의 신청</a>
          </div>
        </div>
      </div>
    </section>"""

    iso_date = p["dt"].strftime("%Y-%m-%d")
    ld = f"""<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": {_json_str(p["title"])},
  "description": {_json_str(p["summary"])},
  "datePublished": "{iso_date}",
  "dateModified": "{iso_date}",
  "keywords": {_json_str(", ".join(p["keywords"]))},
  {'"image": ["' + ogimg + '"],' if ogimg else ''}
  "author": {{"@type": "Organization", "name": "{SITE_NAME}", "url": "{SITE_URL}"}},
  "publisher": {{"@type": "Organization", "name": "{SITE_NAME}"}},
  "mainEntityOfPage": "{SITE_URL}/{p["file"]}"
}}
</script>
"""
    page(p["file"], p["title"],
         (p["summary"] or p["title"])[:150],
         body, extra_head=ld,
         keywords=p["keywords"] or None, og_image=ogimg)


def _json_str(s):
    import json
    return json.dumps(s, ensure_ascii=False)


# --------------------------------------------------------- sitemap.xml / rss
def build_sitemap(posts):
    today = datetime.date.today().strftime("%Y-%m-%d")
    core = [("", "1.0", "weekly"), ("about.html", "0.9", "monthly"), ("business.html", "0.9", "monthly"),
            ("members.html", "0.8", "monthly"), ("lecture.html", "0.9", "monthly"),
            ("partner.html", "0.9", "monthly"), ("copyclean.html", "0.8", "monthly"),
            ("news.html", "0.8", "daily"), ("mou.html", "0.8", "monthly"), ("apply.html", "0.9", "monthly")]
    urls = []
    for path, pri, freq in core:
        loc = f"{SITE_URL}/{path}" if path else f"{SITE_URL}/"
        urls.append(f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{today}</lastmod>\n"
                    f"    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>\n  </url>")
    for p in posts:
        urls.append(f"  <url>\n    <loc>{SITE_URL}/{p['file']}</loc>\n    <lastmod>{p['dt'].strftime('%Y-%m-%d')}</lastmod>\n"
                    f"    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    io.open(os.path.join(BASE, "sitemap.xml"), "w", encoding="utf-8").write(xml)
    print("  ✓ sitemap.xml (게시글 포함 자동 생성)")


def build_rss(posts):
    items = []
    for p in posts[:20]:
        pub = p["dt"].strftime("%a, %d %b %Y 09:00:00 +0900")
        desc = _html.escape(p["summary"])
        items.append(f"""    <item>
      <title>{_html.escape(p["title"])}</title>
      <link>{SITE_URL}/{p["file"]}</link>
      <guid>{SITE_URL}/{p["file"]}</guid>
      <pubDate>{pub}</pubDate>
      <category>{_html.escape(p["category"])}</category>
      <description>{desc}</description>
    </item>""")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{SITE_NAME} 소식</title>
    <link>{SITE_URL}</link>
    <description>한국AI윤리위원회의 캠페인, 활동 소식, AI 윤리 이슈</description>
    <language>ko</language>
{chr(10).join(items)}
  </channel>
</rss>
"""
    io.open(os.path.join(BASE, "rss.xml"), "w", encoding="utf-8").write(rss)
    print("  ✓ rss.xml (네이버 서치어드바이저 RSS 제출용)")


# ------------------------------------------------------------------ mou.html
def build_mou():
    body = hero_sub("MOU · 대외협력",
                    "대학·기업·협회·연구기관과 함께 AI 윤리 문화를 현장으로 넓혀갑니다.",
                    "MOU · 대외협력") + f"""

    <section class="section">
      <div class="wrap">
        <div class="center" style="margin-bottom:42px">
          <span class="eyebrow">Partnership</span>
          <h2 class="h-sec">제휴 유형</h2>
          <p class="h-sub">기관의 상황과 필요에 맞춰 협력 형태를 함께 설계합니다.</p>
        </div>
        <div class="grid grid-4">
          <article class="card reveal"><div class="card-icon"><i data-lucide="graduation-cap"></i></div>
            <h3>대학 · 학과</h3><p>학생 대상 AI 윤리 교육, 캠페인, 사전점검 문화 안내</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="building-2"></i></div>
            <h3>기업</h3><p>임직원 AI 활용 가이드라인 자문 및 사내 교육 협력</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="users"></i></div>
            <h3>협회 · 단체</h3><p>공동 캠페인, 세미나, 회원 대상 콘텐츠 제공</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="flask-conical"></i></div>
            <h3>연구기관</h3><p>AI 윤리 연구 협력 및 이슈 브리프 공동 발행</p></article>
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap">
        <div class="center" style="margin-bottom:40px">
          <span class="eyebrow">Partners</span>
          <h2 class="h-sec">제휴 기관</h2>
          <p class="h-sub">위원회와 함께하는 기관입니다.</p>
        </div>
        <div class="logo-grid" id="partnerLogos"></div>
        <div class="notice notice--gray" style="margin-top:30px">
          <strong>제휴 기관 추가 방법 —</strong> <code>assets/js/partners-data.js</code> 파일의 배열에 기관명을 추가하고,
          로고 이미지는 <code>assets/img/</code> 폴더에 올린 뒤 파일명을 지정하면 됩니다.
          로고가 없으면 기관명이 텍스트로 표시됩니다.
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:38px">
          <span class="eyebrow">Process</span>
          <h2 class="h-sec">제휴 절차</h2>
        </div>
        <div class="grid grid-4">
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 01</span><h3 style="font-size:16px">온라인 문의</h3><p style="font-size:14px">아래 양식으로 접수</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 02</span><h3 style="font-size:16px">협의</h3><p style="font-size:14px">협력 범위·내용 논의</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 03</span><h3 style="font-size:16px">협약 체결</h3><p style="font-size:14px">MOU 서명</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 04</span><h3 style="font-size:16px">공동 활동</h3><p style="font-size:14px">캠페인·교육 진행</p></div>
        </div>
      </div>
    </section>

    <section class="section section--gray" id="inquiry">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:34px">
          <span class="eyebrow">Contact</span>
          <h2 class="h-sec">제휴 문의</h2>
          <p class="h-sub" style="margin:0 auto">아래 양식을 작성해 주시면 담당자가 확인 후 회신드립니다.</p>
        </div>

        <form class="form" id="mouForm" action="#">
          <div class="form-row">
            <div class="field">
              <label for="org">기관·기업명<span class="req">*</span></label>
              <input type="text" id="org" name="기관명" required placeholder="예) ○○대학교 ○○학과">
            </div>
            <div class="field">
              <label for="name">담당자 성함<span class="req">*</span></label>
              <input type="text" id="name" name="담당자" required>
            </div>
          </div>
          <div class="field">
            <label for="contact">연락처<span class="req">*</span></label>
            <input type="text" id="contact" name="연락처" required placeholder="전화번호 또는 이메일">
            <p class="field-hint">회신받으실 연락처 하나만 남겨주시면 됩니다.</p>
          </div>
          <div class="field">
            <label for="msg">문의 내용<span class="req">*</span></label>
            <textarea id="msg" name="문의내용" required placeholder="협력을 희망하시는 내용을 자유롭게 적어 주세요."></textarea>
          </div>
          <button type="submit" class="btn btn-primary" style="justify-self:start">
            제휴 문의 보내기 <i data-lucide="send"></i>
          </button>
          <p class="field-hint">
            버튼을 누르면 메일 앱이 열리고 작성 내용이 자동으로 담깁니다.
            직접 보내실 경우: <a href="mailto:{EMAIL}" style="color:var(--blue);font-weight:600">{EMAIL}</a>
          </p>
        </form>
      </div>
    </section>"""

    script = """  <script src="assets/js/partners-data.js"></script>
  <script>
  (function(){
    var box=document.getElementById('partnerLogos');
    if(!box||!window.KAIEC_PARTNERS)return;
    if(!window.KAIEC_PARTNERS.length){
      box.outerHTML='<p style="text-align:center;color:var(--gray-500);padding:40px 0">제휴 기관을 모집하고 있습니다.</p>';return;
    }
    box.innerHTML=window.KAIEC_PARTNERS.map(function(p){
      var inner=p.logo?'<img src="assets/img/'+p.logo+'" alt="'+p.name+' 로고" loading="lazy">'
                      :'<span class="logo-fallback">'+p.name+'</span>';
      var body='<div class="logo-item">'+inner+'</div>';
      return p.url?'<a href="'+p.url+'" target="_blank" rel="noopener">'+body+'</a>':body;
    }).join('');
  })();
  /* 제휴 문의 폼 — 작성 내용을 담아 메일 앱을 엽니다 (별도 서버 불필요) */
  (function(){
    var f=document.getElementById('mouForm');
    if(!f)return;
    f.addEventListener('submit',function(e){
      e.preventDefault();
      function v(n){var el=f.querySelector('[name="'+n+'"]');return el?el.value.trim():''}
      var subject='[제휴·MOU 문의] '+v('기관명');
      var lines=[
        '■ 기관·기업명 : '+v('기관명'),
        '■ 담당자      : '+v('담당자'),
        '■ 연락처      : '+v('연락처'),
        '',
        '■ 문의 내용',
        v('문의내용'),
        '',
        '--- 한국AI윤리위원회 홈페이지 제휴 문의 양식에서 작성됨 ---'
      ];
      location.href='mailto:__EMAIL__?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(lines.join('\\n'));
    });
  })();
  </script>
""".replace('__EMAIL__', EMAIL)
    page("mou.html", "MOU · 대외협력",
         "한국AI윤리위원회는 대학·기업·협회·연구기관과 업무협약(MOU)을 체결하고 공동 캠페인, 교육, 연구를 추진합니다. 온라인으로 제휴를 문의하실 수 있습니다.",
         body, extra_script=script)


# -------------------------------------------------------------- lecture.html
def build_lecture():
    topics = [
        ("sparkles", "생성형 AI와 AI 윤리 기초", "생성형 AI의 원리와 한계, 책임 있는 활용 원칙을 다루는 입문 특강입니다.", "전 대상 · 입문"),
        ("book-open-check", "연구·출판윤리와 AI 활용 표기", "논문·과제·연구물에서의 AI 활용 기준과 표기 방법, 사전점검 요령을 다룹니다.", "대학원 · 연구기관"),
        ("graduation-cap", "캠퍼스 AI 리터러시", "대학생·교직원을 위한 AI 활용 역량과 윤리 감수성 교육입니다.", "대학 · 교직원"),
        ("building-2", "기업의 책임 있는 AI 활용", "임직원 AI 활용 가이드라인, 보안·저작권·표기 이슈를 실무 중심으로 다룹니다.", "기업 · 임직원"),
        ("landmark", "공공부문 AI 윤리", "공무원·공공기관 구성원을 위한 AI 행정 활용과 윤리 기준 교육입니다.", "공공기관 · 지자체"),
        ("file-search", "AI 생성물 판별과 사전점검 실무", "AI 생성물 판별 원리와 제출 전 사전점검 방법을 실습형으로 진행합니다.", "실습 워크숍"),
    ]
    topic_cards = "\n".join(f"""          <article class="card reveal">
            <div class="card-icon"><i data-lucide="{ic}"></i></div>
            <h3>{t}</h3>
            <p style="margin-bottom:14px">{d}</p>
            <div class="chips"><span class="chip">{tag}</span></div>
          </article>""" for ic, t, d, tag in topics)

    body = hero_sub("강의 · 교육 신청",
                    "위원회 전문위원과 협력 강사진이 대학·기업·공공기관 어디든 찾아갑니다.",
                    "강의 신청") + f"""

    <section class="section section--tight">
      <div class="wrap">
        <div class="stats reveal">
          <div class="stat"><div class="stat-num">6</div><div class="stat-label">강의 분야</div></div>
          <div class="stat"><div class="stat-num">4</div><div class="stat-label">진행 형태</div></div>
          <div class="stat"><div class="stat-num">전국</div><div class="stat-label">출강 지역 (온라인 병행)</div></div>
          <div class="stat"><div class="stat-num">상시</div><div class="stat-label">신청 접수</div></div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="center" style="margin-bottom:42px">
          <span class="eyebrow">Lecture Topics</span>
          <h2 class="h-sec">강의 분야</h2>
          <p class="h-sub">기관의 목적과 대상에 맞춰 주제와 난이도를 조정해 드립니다. 두 개 이상 주제를 묶은 맞춤 과정도 가능합니다.</p>
        </div>
        <div class="grid grid-3">
{topic_cards}
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap">
        <div class="center" style="margin-bottom:40px">
          <span class="eyebrow">Who We Visit</span>
          <h2 class="h-sec">출강 대상</h2>
          <p class="h-sub">아래 기관의 교육 프로그램에 강사를 파견합니다.</p>
        </div>
        <div class="grid grid-3">
          <article class="card reveal"><div class="card-icon"><i data-lucide="graduation-cap"></i></div>
            <h3>대학 · 대학원</h3><p>신입생 교육, 연구윤리 특강, 논문작성 세미나, 교직원 연수</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="building-2"></i></div>
            <h3>기업</h3><p>임직원 AI 활용 교육, 신입사원 연수, 리더십 대상 브리핑</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="landmark"></i></div>
            <h3>공공기관 · 지자체</h3><p>공무원 교육, 시민 대상 AI 리터러시 강좌, 기관 초청 특강</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="briefcase"></i></div>
            <h3>정부지원사업 운영기관</h3><p>정부·지자체 지원사업의 교육 프로그램, 창업지원기관·평생교육기관 연계 강의</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="school"></i></div>
            <h3>초·중·고 및 교원연수</h3><p>학생 눈높이 AI 윤리 교육, 교사 대상 생성형 AI 지도법 연수</p></article>
          <article class="card reveal"><div class="card-icon"><i data-lucide="users"></i></div>
            <h3>학회 · 협회 · 단체</h3><p>학술대회 초청 강연, 회원 대상 세미나, 공동 교육 프로그램</p></article>
        </div>
        <div class="notice" style="margin-top:28px">
          <strong>공공·정부 연계 프로그램 —</strong> 정부·지자체·공공기관 주관 교육과
          정부지원사업 연계 프로그램은 주관 기관과의 협의를 통해
          일정 · 내용 · 증빙 서류를 맞춤으로 준비해 드립니다.
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="center" style="margin-bottom:40px">
          <span class="eyebrow">Format</span>
          <h2 class="h-sec">진행 형태</h2>
        </div>
        <div class="grid grid-4">
          <article class="card reveal center"><div class="card-icon" style="margin:0 auto 16px"><i data-lucide="mic"></i></div>
            <h3>특강</h3><p>1~2시간 · 전체 대상 강연형</p></article>
          <article class="card reveal center"><div class="card-icon" style="margin:0 auto 16px"><i data-lucide="users-round"></i></div>
            <h3>워크숍</h3><p>반나절 · 실습·토론 중심</p></article>
          <article class="card reveal center"><div class="card-icon" style="margin:0 auto 16px"><i data-lucide="calendar-days"></i></div>
            <h3>정기 과정</h3><p>4~8회차 · 커리큘럼형 교육</p></article>
          <article class="card reveal center"><div class="card-icon card-icon--teal" style="margin:0 auto 16px"><i data-lucide="laptop"></i></div>
            <h3>온라인</h3><p>실시간 화상 · 녹화 강의 병행</p></article>
        </div>
        <div class="grid grid-2" style="margin-top:22px">
          <div class="notice">
            <strong>발급 문서 —</strong> 출강확인서, 교육 결과 요약(요청 시), 위원회 명의 교육 이수확인서(요청 시)를
            발급해 드립니다. 기관 내부 증빙과 사업 결과 보고에 활용하실 수 있습니다.
          </div>
          <div class="notice notice--teal">
            <strong>강의료 —</strong> 대상·시간·지역·형태에 따라 협의하여 결정합니다.
            비영리·교육기관 및 공익 목적 프로그램은 협의 시 말씀해 주세요.
          </div>
        </div>
      </div>
    </section>

    <section class="section section--gray">
      <div class="wrap">
        <div class="center" style="margin-bottom:38px">
          <span class="eyebrow">Instructors</span>
          <h2 class="h-sec">강사진</h2>
          <p class="h-sub">위원회 전문위원과 분과별 협력 강사진이 출강합니다. 강사 프로필과 커리큘럼 소개서는 신청 시 함께 보내드립니다.</p>
        </div>
        <div class="member-grid" id="lecturerGrid"></div>
        <p class="field-hint" style="text-align:center;margin-top:18px">
          전체 위원 명단은 <a href="members.html" style="color:var(--blue);font-weight:600">조직·위원</a> 페이지에서 확인하실 수 있습니다.
        </p>
      </div>
    </section>

    <section class="section">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:38px">
          <span class="eyebrow">Process</span>
          <h2 class="h-sec">신청 절차</h2>
        </div>
        <div class="grid grid-4">
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 01</span><h3 style="font-size:16px">신청서 접수</h3><p style="font-size:14px">아래 양식 작성</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 02</span><h3 style="font-size:16px">협의</h3><p style="font-size:14px">주제 · 일정 · 강의료</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 03</span><h3 style="font-size:16px">확정 · 준비</h3><p style="font-size:14px">강사 배정 · 자료 준비</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 04</span><h3 style="font-size:16px">강의 · 증빙</h3><p style="font-size:14px">진행 후 확인서 발급</p></div>
        </div>
      </div>
    </section>

    <section class="section section--gray" id="request">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:34px">
          <span class="eyebrow">Request</span>
          <h2 class="h-sec">강의 신청</h2>
          <p class="h-sub" style="margin:0 auto">작성해 주시면 담당자가 확인 후 1~3일 내 회신드립니다.</p>
        </div>

        <form class="form" id="lectureForm" action="#">
          <div class="form-row">
            <div class="field">
              <label for="l-org">기관·기업명<span class="req">*</span></label>
              <input type="text" id="l-org" name="기관명" required placeholder="예) ○○대학교 교육혁신원">
            </div>
            <div class="field">
              <label for="l-name">담당자 성함<span class="req">*</span></label>
              <input type="text" id="l-name" name="담당자" required>
            </div>
          </div>
          <div class="form-row">
            <div class="field">
              <label for="l-contact">연락처<span class="req">*</span></label>
              <input type="text" id="l-contact" name="연락처" required placeholder="전화번호 또는 이메일">
              <p class="field-hint">회신받으실 연락처 하나만 남겨주시면 됩니다.</p>
            </div>
            <div class="field">
              <label for="l-topic">희망 강의 분야<span class="req">*</span></label>
              <select id="l-topic" name="희망강의분야" required>
                <option value="">선택해 주세요</option>
                <option>생성형 AI와 AI 윤리 기초</option>
                <option>연구·출판윤리와 AI 활용 표기</option>
                <option>캠퍼스 AI 리터러시</option>
                <option>기업의 책임 있는 AI 활용</option>
                <option>공공부문 AI 윤리</option>
                <option>AI 생성물 판별과 사전점검 실무</option>
                <option>맞춤 과정 (협의)</option>
              </select>
            </div>
          </div>
          <div class="field">
            <label for="l-msg">요청 사항 (선택)</label>
            <textarea id="l-msg" name="요청사항" style="min-height:100px" placeholder="희망 일정, 예상 인원, 진행 방식 등을 간단히 적어주셔도 좋습니다."></textarea>
          </div>
          <button type="submit" class="btn btn-primary" style="justify-self:start">
            강의 신청 보내기 <i data-lucide="send"></i>
          </button>
          <p class="field-hint">
            버튼을 누르면 메일 앱이 열리고 작성 내용이 자동으로 담깁니다.
            직접 보내실 경우: <a href="mailto:{EMAIL}" style="color:var(--blue);font-weight:600">{EMAIL}</a>
          </p>
        </form>
      </div>
    </section>

    <section class="section section--tight">
      <div class="wrap">
        <div class="cta-band">
          <div><h2>기관 협약과 함께라면 더 깊이 있게</h2>
            <p>MOU 체결 기관에는 정기 교육 과정과 공동 캠페인을 우선 지원합니다.</p></div>
          <div class="btns">
            <a class="btn btn-white" href="mou.html#inquiry">MOU·제휴 문의</a>
            <a class="btn btn-light" href="business.html">주요사업 보기</a>
          </div>
        </div>
      </div>
    </section>"""

    script = """  <script src="assets/js/members-data.js"></script>
  <script>
  /* 강사진 — 조직·위원 데이터의 '전문위원'을 자동으로 표시합니다 */
  (function(){
    var box=document.getElementById('lecturerGrid');
    if(!box||!window.KAIEC_MEMBERS)return;
    var list=window.KAIEC_MEMBERS.filter(function(m){return m.group==='전문위원'});
    if(!list.length){box.outerHTML='<p style="text-align:center;color:var(--gray-500)">강사진 명단은 준비 중입니다.</p>';return}
    box.innerHTML=list.map(function(m){
      var initial=(m.name||'?').replace(/[^가-힣A-Za-z]/g,'').slice(0,1)||'·';
      return '<div class="member"><div class="member-avatar">'+initial+'</div>'
        +'<div class="member-role">'+(m.role||'전문위원')+'</div>'
        +'<div class="member-name">'+m.name+'</div>'
        +'<div class="member-field">'+(m.field||'')+'</div></div>';
    }).join('');
  })();
  /* 강의 신청 폼 — 작성 내용을 담아 메일 앱을 엽니다 */
  (function(){
    var f=document.getElementById('lectureForm');
    if(!f)return;
    f.addEventListener('submit',function(e){
      e.preventDefault();
      function v(n){var el=f.querySelector('[name="'+n+'"]');return el?el.value.trim():''}
      var subject='[강의 신청] '+v('기관명')+' — '+v('희망강의분야');
      var lines=[
        '■ 기관·기업명 : '+v('기관명'),
        '■ 담당자      : '+v('담당자'),
        '■ 연락처      : '+v('연락처'),
        '■ 희망 강의 분야 : '+v('희망강의분야'),
        '',
        '■ 요청 사항',
        v('요청사항'),
        '',
        '--- 한국AI윤리위원회 홈페이지 강의 신청 양식에서 작성됨 ---'
      ];
      location.href='mailto:__EMAIL__?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(lines.join('\\n'));
    });
  })();
  </script>
""".replace('__EMAIL__', EMAIL)

    page("lecture.html", "강의 · 교육 신청",
         "한국AI윤리위원회 전문위원·협력 강사진의 AI 윤리 강의 신청. 대학·기업·공공기관·지자체·정부지원사업 연계 프로그램에 생성형 AI 윤리, 연구·출판윤리, AI 리터러시 강사를 파견합니다.",
         body, extra_script=script)


# ---------------------------------------------------------------- apply.html
def build_apply():
    roles = [
        ("crown", "대표위원", "위원회를 대표해 대외 활동과 주요 의사결정에 참여합니다.", "리더십 · 대외 활동"),
        ("briefcase", "운영위원장 · 운영위원", "사업 기획과 프로그램 운영, 활동 관리를 총괄·수행합니다.", "기획 · 운영"),
        ("map-pin", "지역 운영위원", "권역별 지역 조직을 이끌며 지역 단위 캠페인과 활동을 운영합니다.", "지역 조직"),
        ("school", "캠퍼스 위원장", "소속 대학의 캠퍼스 위원회를 이끌며 교내 확산 활동을 담당합니다.", "대학 조직"),
        ("megaphone", "홍보위원", "위원회 채널과 콘텐츠를 통해 AI 윤리 캠페인을 알립니다.", "홍보 · 콘텐츠"),
        ("sparkles", "서포터즈", "대학생·대학원생 중심으로 캠페인과 콘텐츠 활동에 참여합니다.", "참여 조직"),
    ]
    role_cards = "\n".join(f"""          <article class="card reveal">
            <div class="card-icon"><i data-lucide="{ic}"></i></div>
            <h3>{t}</h3>
            <p style="margin-bottom:14px">{d}</p>
            <div class="chips"><span class="chip">{tag}</span></div>
          </article>""" for ic, t, d, tag in roles)

    body = hero_sub("위원 지원",
                    "대표위원 · 운영위원 · 지역 운영위원 · 캠퍼스 위원장 · 홍보위원 · 서포터즈를 상시 모집합니다.",
                    "위원 지원") + f"""

    <section class="section">
      <div class="wrap">
        <div class="center" style="margin-bottom:42px">
          <span class="eyebrow">Recruitment</span>
          <h2 class="h-sec">모집 분야</h2>
          <p class="h-sub">본인의 상황과 관심에 맞는 분야를 선택해 지원하실 수 있습니다. 전공·경력 제한이 없으며, 모든 활동은 온라인 병행이 가능합니다.</p>
        </div>
        <div class="grid grid-3">
{role_cards}
        </div>
        <div class="center" style="margin-top:26px">
          <a class="btn btn-ghost btn-sm" href="partner.html">AI 윤리 파트너 제도 안내 보기 <i data-lucide="arrow-right"></i></a>
        </div>
      </div>
    </section>

    <section class="section section--gray section--tight">
      <div class="wrap-narrow">
        <div class="grid grid-4">
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 01</span><h3 style="font-size:16px">지원서 제출</h3><p style="font-size:14px">아래 지원서 작성</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 02</span><h3 style="font-size:16px">서류 검토</h3><p style="font-size:14px">약 3~5일</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 03</span><h3 style="font-size:16px">개별 연락</h3><p style="font-size:14px">이메일 · 유선 안내</p></div>
          <div class="card center reveal" style="padding:24px 18px"><span class="card-num">STEP 04</span><h3 style="font-size:16px">위촉 · 활동</h3><p style="font-size:14px">위촉장 발급 후 시작</p></div>
        </div>
      </div>
    </section>

    <section class="section" id="form">
      <div class="wrap-narrow">
        <div class="center" style="margin-bottom:30px">
          <span class="eyebrow">Application</span>
          <h2 class="h-sec">온라인 지원서</h2>
          <p class="h-sub" style="margin:0 auto 24px">아래 지원서를 작성해 주시면 검토 후 개별 연락드립니다.
             AI 윤리 파트너 참여를 원하시는 분도 본 지원서로 접수하실 수 있습니다.</p>
          <a class="btn btn-primary" href="{GOOGLE_FORM}" target="_blank" rel="noopener">
            새 창에서 지원서 작성하기 <i data-lucide="external-link"></i>
          </a>
        </div>

        <div class="gform-wrap">
          <iframe src="{GOOGLE_FORM}?embedded=true" title="한국 AI 윤리위원회 위원 지원서" loading="lazy">지원서를 불러오는 중입니다…</iframe>
        </div>
        <p class="field-hint" style="margin-top:14px;text-align:center">
          지원서가 표시되지 않으면 위의 <strong>‘새 창에서 지원서 작성하기’</strong> 버튼을 이용해 주세요.
          기타 문의는 <a href="mailto:{EMAIL}" style="color:var(--blue);font-weight:600">{EMAIL}</a>
        </p>
      </div>
    </section>

    <section class="section section--gray section--tight">
      <div class="wrap-narrow">
        <div class="notice notice--teal">
          <strong>안내 —</strong> 위원·파트너 지원과 활동 과정에서 가입비, 교육비 등
          어떠한 비용도 요구하지 않습니다. 지원서 검토 결과는 개별적으로 안내드립니다.
        </div>
      </div>
    </section>"""

    page("apply.html", "위원 지원",
         "한국AI윤리위원회 전문위원·활동위원·AI 윤리 파트너 상시 모집. 온라인으로 간편하게 지원하실 수 있습니다.",
         body)


if __name__ == "__main__":
    print("한국AI윤리위원회 사이트 빌드 중...")
    posts = load_posts()
    print(f"  게시글 {len(posts)}건 발견")
    build_index(posts)
    build_about()
    build_business()
    build_members()
    build_lecture()
    build_partner()
    build_copyclean()
    build_news(posts)
    build_mou()
    build_apply()
    for p in posts:
        build_post(p, posts)
    build_sitemap(posts)
    build_rss(posts)
    print("완료!")
