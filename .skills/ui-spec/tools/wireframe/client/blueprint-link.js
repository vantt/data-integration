// wireframe/client/blueprint-link.js
// BROWSER: 2-way linking between Blueprint ASCII and Interactions region-boxes.
// Called from app.js renderMain(). Safe to call multiple times — idempotent via data-linked guard.
// Globals consumed: currentSurface, switchView (app-chrome.js), esc, escAttr (region-model.js).

/**
 * Escape a string for use inside a CSS attribute selector (double-quote context).
 * Avoids CSS.escape which is unavailable in jsdom.
 */
function attrSelectorEscape(s) {
  return String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

/**
 * Post-process the Blueprint <pre> to wrap region name occurrences in clickable spans.
 * Also wires .region-label clicks in Interactions view for the reverse direction.
 * Must be called AFTER renderMain() sets blueprint-pre.textContent and view-layout.innerHTML.
 */
function initBlueprintLinks() {
  const pre = document.getElementById("blueprint-pre");
  if (!pre || pre.dataset.linked) return;
  pre.dataset.linked = "1";

  const surface = currentSurface;
  const regions = (surface && surface.meta && surface.meta.regions) ? surface.meta.regions : [];

  // ── Blueprint → Interactions direction ───────────────────────────────────────
  // Only replace if the ASCII contains any region names (skip if empty/no-region surfaces).
  const rawText = pre.textContent;
  if (regions.length && rawText) {
    // Sort longest-first to avoid partial matches (e.g. "alert_row" before "alert").
    const sorted = regions.slice().sort(function(a, b) { return b.length - a.length; });
    // Start from HTML-escaped plain text (esc handles &, <, >).
    var html = esc(rawText);
    for (var i = 0; i < sorted.length; i++) {
      var r = sorted[i];
      // Escape regex special chars in the region name.
      var rEsc = r.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      // Whole-word boundary: not preceded or followed by word chars or dot.
      // Negative lookbehind/lookahead: (?<![\w.])name(?![\w.])
      // This naturally matches parenthesized forms like (alert_row) since ( and ) are non-word.
      var pattern = new RegExp("(?<![\\w.])(" + rEsc + ")(?![\\w.])", "g");
      html = html.replace(pattern,
        "<span class=\"bp-region-span\" data-region=\"" + escAttr(r) + "\">$1</span>"
      );
    }
    pre.innerHTML = html;

    // Wire click on each inserted span → switch to Interactions + flash region box.
    var spans = pre.querySelectorAll(".bp-region-span");
    for (var j = 0; j < spans.length; j++) {
      (function(span) {
        span.addEventListener("click", function() {
          switchView("layout");
          flashRegionBox(span.dataset.region);
        });
      })(spans[j]);
    }
  }

  // ── Interactions → Blueprint direction ───────────────────────────────────────
  // Wire .region-label clicks so clicking a region header switches to Blueprint
  // and highlights the matching span(s) there.
  var labels = document.querySelectorAll("#view-layout .region-label[data-region]");
  for (var k = 0; k < labels.length; k++) {
    (function(label) {
      label.classList.add("region-label-link");
      label.addEventListener("click", function() {
        switchView("blueprint");
        flashBlueprintSpan(label.dataset.region);
      });
    })(labels[k]);
  }
}

/** Scroll to and briefly flash the region-box for the given region name in Interactions view. */
function flashRegionBox(regionName) {
  var sel = "#view-layout .region-box[data-region=\"" + attrSelectorEscape(regionName) + "\"]";
  var box = document.querySelector(sel);
  if (!box) return;
  if (typeof box.scrollIntoView === "function")
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  box.classList.add("region-box-flash");
  setTimeout(function() { box.classList.remove("region-box-flash"); }, 1600);
}

/** Scroll to and briefly highlight the bp-region-span in Blueprint view for the given region name. */
function flashBlueprintSpan(regionName) {
  var sel = "#blueprint-pre .bp-region-span[data-region=\"" + attrSelectorEscape(regionName) + "\"]";
  var span = document.querySelector(sel);
  if (!span) return;
  if (typeof span.scrollIntoView === "function")
    span.scrollIntoView({ behavior: "smooth", block: "nearest" });
  span.classList.add("bp-span-active");
  setTimeout(function() { span.classList.remove("bp-span-active"); }, 1600);
}
