/* streaming_dash_chat -- small, dependency-free client-side behavior.
 * Message rendering/streaming itself goes through Dash's own streaming
 * callbacks (see callbacks/messages.py); this file only handles things Dash
 * has no notion of: scroll position and clipboard access. */
(function () {
  "use strict";

  var NEAR_BOTTOM_PX = 72;

  function isNearBottom(el) {
    return el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
  }

  function watchScrollArea(el) {
    if (el.dataset.sdcWatched === "1") return;
    el.dataset.sdcWatched = "1";

    var shouldStick = true;
    el.addEventListener("scroll", function () {
      shouldStick = isNearBottom(el);
    });

    var observer = new MutationObserver(function () {
      if (shouldStick) {
        el.scrollTop = el.scrollHeight;
      }
    });
    observer.observe(el, { childList: true, subtree: true, characterData: true });
  }

  function scan() {
    document.querySelectorAll(".sdc-scroll-area").forEach(watchScrollArea);
  }

  document.addEventListener("click", function (event) {
    var btn = event.target.closest(".sdc-copy-btn");
    if (!btn) return;
    var text = btn.getAttribute("data-copy-text") || "";
    if (!navigator.clipboard || !navigator.clipboard.writeText) return;
    navigator.clipboard.writeText(text).then(function () {
      var original = btn.textContent;
      btn.textContent = "Copied";
      window.setTimeout(function () {
        btn.textContent = original;
      }, 1500);
    });
  });

  new MutationObserver(scan).observe(document.documentElement, { childList: true, subtree: true });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scan);
  } else {
    scan();
  }
})();

window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.streaming_dash_chat = {
  // Generates a per-browser-tab session_id the first time a chat's Store
  // has none yet; a no-op update thereafter. The Store itself persists in
  // sessionStorage, so this only ever fires once per tab -- see
  // ConversationManager.resolve_session_id for why conversation isolation
  // is keyed off this instead of a server-side cookie.
  ensureSessionId: function (data) {
    if (data && data.session_id) {
      return window.dash_clientside.no_update;
    }
    var next = Object.assign({}, data || {});
    next.session_id =
      window.crypto && window.crypto.randomUUID
        ? window.crypto.randomUUID()
        : Date.now() + "-" + Math.random().toString(36).slice(2);
    return next;
  },
};
