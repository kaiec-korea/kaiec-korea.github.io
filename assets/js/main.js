/* 한국AI윤리위원회 (KAIEC) — main.js */
(function () {
  'use strict';

  /* 1. 모바일 네비게이션 -------------------------------------------------- */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('.nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* 2. 현재 페이지 메뉴 활성화 -------------------------------------------- */
  var here = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav a').forEach(function (a) {
    var href = a.getAttribute('href');
    if (href === here) a.classList.add('is-active');
  });

  /* 3. 스크롤 등장 애니메이션 --------------------------------------------- */
  var targets = document.querySelectorAll('.reveal');
  if (targets.length) {
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) {
            en.target.classList.add('is-in');
            io.unobserve(en.target);
          }
        });
      }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });
      targets.forEach(function (t, i) {
        t.style.transitionDelay = (i % 4) * 70 + 'ms';
        io.observe(t);
      });
    } else {
      targets.forEach(function (t) { t.classList.add('is-in'); });
    }
  }

  /* 4. 푸터 연도 자동 갱신 ------------------------------------------------ */
  var y = document.getElementById('year');
  if (y) y.textContent = new Date().getFullYear();

  /* 5. 숫자 카운트업 ------------------------------------------------------ */
  var nums = document.querySelectorAll('[data-count]');
  if (nums.length && 'IntersectionObserver' in window) {
    var nio = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target;
        var end = parseFloat(el.getAttribute('data-count'));
        var suffix = el.getAttribute('data-suffix') || '';
        var start = null, dur = 1100;
        function step(ts) {
          if (!start) start = ts;
          var p = Math.min((ts - start) / dur, 1);
          var eased = 1 - Math.pow(1 - p, 3);
          el.textContent = Math.round(end * eased).toLocaleString('ko-KR') + suffix;
          if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
        nio.unobserve(el);
      });
    }, { threshold: 0.4 });
    nums.forEach(function (n) { nio.observe(n); });
  }

  /* 아이콘은 빌드 시 SVG로 HTML에 직접 삽입되므로 외부 스크립트가 필요 없습니다. */
})();
