// Delegated confirm() for destructive forms, e.g. <form data-confirm="...">.
// Kept in an external file (rather than inline onsubmit="...") so it works
// under a strict script-src 'self' Content-Security-Policy with no
// 'unsafe-inline' — inline event handler attributes are blocked by that
// policy just like inline <script> blocks.
document.addEventListener(
  "submit",
  function (e) {
    var form = e.target;
    if (form && form.dataset && form.dataset.confirm) {
      if (!window.confirm(form.dataset.confirm)) {
        e.preventDefault();
      }
    }
  },
  true
);
