/* ── Changelog notification dot ─────────────────────────────────────────────
   HOW TO UPDATE: change LATEST to the date of the newest changelog entry
   Format: 'YYYY-MM-DD'
   ─────────────────────────────────────────────────────────────────────────── */
(function () {
  var LATEST = '2026-06-18';   // ← update this when adding a new entry
  var KEY    = 'clSeen';
  var onCL   = window.location.pathname.indexOf('changelog.html') !== -1;

  if (onCL) {
    /* ── On changelog page: show NEW badges, then mark all as seen ── */
    var prev = localStorage.getItem(KEY) || '0000-00-00';

    document.addEventListener('DOMContentLoaded', function () {
      document.querySelectorAll('.cl-entry[data-date]').forEach(function (el) {
        if (el.dataset.date > prev) {
          var top = el.querySelector('.cl-card-top');
          if (top) {
            var b = document.createElement('span');
            b.className = 'cl-new-badge';
            b.textContent = 'NEW';
            top.appendChild(b);
          }
        }
      });
    });

    /* Save immediately so badge is hidden on next visit */
    localStorage.setItem(KEY, LATEST);

  } else {
    /* ── On every other page: check if unseen entries exist ── */
    var lastSeen = localStorage.getItem(KEY) || '0000-00-00';
    if (lastSeen < LATEST) {
      document.addEventListener('DOMContentLoaded', function () {
        /* Matches both 'changelog.html' and '../changelog.html' */
        document.querySelectorAll('a[href*="changelog.html"]').forEach(function (a) {
          a.classList.add('has-notif');
        });
      });
    }
  }
}());
