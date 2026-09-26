(function () {
  "use strict";

  var data = window.MONITOR_DATA || { runs: [] };
  var runs = data.runs.slice().sort(function (a, b) {
    return a.ts < b.ts ? -1 : 1;
  }); // 旧 → 新

  var PAGE_SIZE = 18; // 3 行 × 6 列
  var page = 1;

  function fmtTime(iso) {
    var d = new Date(iso);
    function p(n) { return String(n).padStart(2, "0"); }
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) +
      " " + p(d.getHours()) + ":" + p(d.getMinutes());
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  /* ---------- 顶部信息 ---------- */
  if (runs.length) {
    document.getElementById("model-name").textContent = runs[runs.length - 1].model || "gpt-6-astra";
    document.getElementById("last-updated").textContent =
      "共 " + runs.length + " 轮 · 最近更新 " + fmtTime(runs[runs.length - 1].ts);
  }

  /* ---------- 测试一：24 小时 Timeline ---------- */
  (function renderTimeline() {
    var box = document.getElementById("timeline");
    var stats = document.getElementById("timeline-stats");
    var cutoff = Date.now() - 24 * 3600 * 1000;
    var recent = runs.filter(function (r) {
      return new Date(r.ts).getTime() >= cutoff;
    });

    if (!recent.length) {
      box.innerHTML = '<span class="empty">最近 24 小时暂无检测记录。</span>';
      stats.textContent = "最近 24 小时：0 轮检测。";
      return;
    }

    var passed = recent.filter(function (r) { return r.test1 && r.test1.passed; }).length;
    var rate = (passed / recent.length * 100).toFixed(1);
    var rateClass = passed === recent.length ? "rate-pass" : "rate-fail";
    stats.innerHTML = "最近 24 小时共 <b>" + recent.length + "</b> 轮检测，通过 <b>" +
      passed + "</b> 轮，通过率 <b class=\"" + rateClass + "\">" + rate + "%</b>";

    var latestId = recent[recent.length - 1].id;
    box.innerHTML = recent.map(function (r) {
      var ok = r.test1 && r.test1.passed;
      var ans = r.test1 && r.test1.answer != null ? r.test1.answer : "无";
      var err = r.test1 && r.test1.error ? " · " + r.test1.error : "";
      return '<span class="t-block ' + (ok ? "pass" : "fail") +
        (r.id === latestId ? " latest" : "") + '">' +
        '<span class="tip">' + fmtTime(r.ts) +
        " · 答案 " + esc(ans) + " · " + (ok ? "通过" : "未通过") + esc(err) +
        "</span></span>";
    }).join("");
  })();

  /* ---------- 测试二：3×6 预览 + 分页 ---------- */
  function renderGallery() {
    var box = document.getElementById("gallery");
    var stats = document.getElementById("gallery-stats");
    var pager = document.getElementById("pager");

    var newestFirst = runs.slice().reverse();
    var total = newestFirst.length;
    var pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (page > pages) page = pages;

    var okCount = newestFirst.filter(function (r) { return r.test2 && r.test2.passed; }).length;
    stats.innerHTML = "累计 <b>" + total + "</b> 轮，成功生成 <b>" + okCount +
      "</b> 轮（生成率 " + (total ? (okCount / total * 100).toFixed(1) : "0.0") +
      "%）· 每页 3×6 共 " + PAGE_SIZE + " 个";

    if (!total) {
      box.innerHTML = '<span class="empty">暂无生成记录。</span>';
      pager.innerHTML = "";
      return;
    }

    var slice = newestFirst.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    box.innerHTML = slice.map(function (r) {
      var ok = r.test2 && r.test2.passed && r.test2.preview;
      var body = ok
        ? '<div class="g-frame-wrap"><iframe loading="lazy" sandbox="allow-scripts" src="../' +
          esc(r.test2.preview) + '" title="预览 ' + esc(r.id) + '"></iframe></div>'
        : '<div class="g-missing">未生成' +
          (r.test2 && r.test2.error ? "<br>" + esc(r.test2.error) : "") + "</div>";
      return '<div class="g-card">' + body +
        '<div class="g-meta"><span>' + fmtTime(r.ts) + "</span>" +
        '<span class="' + (ok ? "ok" : "bad") + '">' +
        (ok ? "已生成" : "失败") + "</span></div></div>";
    }).join("");

    // 分页
    var html = '<button id="pg-prev" ' + (page <= 1 ? "disabled" : "") + ">上一页</button>";
    for (var i = 1; i <= pages; i++) {
      html += '<button data-page="' + i + '" class="' +
        (i === page ? "active" : "") + '">' + i + "</button>";
    }
    html += '<button id="pg-next" ' + (page >= pages ? "disabled" : "") + ">下一页</button>";
    html += '<span class="info">第 ' + page + " / " + pages + " 页</span>";
    pager.innerHTML = html;

    pager.querySelectorAll("button[data-page]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        page = parseInt(btn.getAttribute("data-page"), 10);
        renderGallery();
      });
    });
    var prev = document.getElementById("pg-prev");
    var next = document.getElementById("pg-next");
    if (prev) prev.addEventListener("click", function () { if (page > 1) { page--; renderGallery(); } });
    if (next) next.addEventListener("click", function () { if (page < pages) { page++; renderGallery(); } });
  }
  renderGallery();

  // 每 5 分钟自动刷新，获取新一轮检测结果
  setTimeout(function () { location.reload(); }, 5 * 60 * 1000);
})();
