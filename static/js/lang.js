// =====================================================
// NEXORA - lang.js
// Multilingual system (Kurdish, English, Arabic)
// =====================================================

var currentLang = localStorage.getItem("nexora_lang") || "ku";
var dict = {};

function t(key) {
    return dict[key] !== undefined ? dict[key] : key;
}

function applyLang() {
    var html = document.documentElement;
    html.lang = currentLang;
    html.dir = (currentLang === "en") ? "ltr" : "rtl";

    // نووسینی ناو توخمەکان: data-i18n="کلیل"
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
        var key = el.getAttribute("data-i18n");
        if (dict[key] !== undefined) {
            el.textContent = dict[key];
        }
    });

    // نووسینی placeholder فۆرمەکان: data-i18n-ph="کلیل"
    document.querySelectorAll("[data-i18n-ph]").forEach(function (el) {
        var key = el.getAttribute("data-i18n-ph");
        if (dict[key] !== undefined) {
            el.placeholder = dict[key];
        }
    });

    // ناوەڕۆکی داتابەیس: data-ku / data-ar / data-en
    document.querySelectorAll("[data-ku]").forEach(function (el) {
        var v = el.getAttribute("data-" + currentLang);
        if (v) el.textContent = v;
    });

    // نوێکردنەوەی سلێکت ئەگەر هەبێت
    var sel = document.getElementById("langSelect");
    if (sel) sel.value = currentLang;

    // ئاگادارکردنەوەی فەنکشنەکانی سەبەتە و مێنوو
    document.dispatchEvent(new Event("langchange"));
}

function loadLang() {
    fetch("/static/lang/" + currentLang + ".json")
        .then(function (r) { return r.json(); })
        .then(function (data) {
            dict = data;
            applyLang();
        })
        .catch(function (e) {
            console.error("هەڵەی فایلی زمان:", e);
        });
}

function setLang(lang) {
    currentLang = lang;
    localStorage.setItem("nexora_lang", lang);
    loadLang();
}

function cycleLang() {
    var order = ["ku", "en", "ar"];
    var nextIdx = (order.indexOf(currentLang) + 1) % order.length;
    setLang(order[nextIdx]);
}

function toggleLangMenu(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    var wrap = document.getElementById("langDropdownWrap");
    if (wrap) wrap.classList.toggle("open");
}

function chooseLang(lang, e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    var wrap = document.getElementById("langDropdownWrap");
    if (wrap) wrap.classList.remove("open");

    if (lang === currentLang) return;

    // دروستکردنی شاشەی ڕەش بۆ ترانزیشنی نەرم (Smooth Black Fade)
    var overlay = document.getElementById("langTransitionOverlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "langTransitionOverlay";
        overlay.style.cssText = "position:fixed;inset:0;background:#000000;z-index:999999;opacity:0;pointer-events:none;transition:opacity 0.24s cubic-bezier(0.4, 0, 0.2, 1);";
        document.body.appendChild(overlay);
    }

    // ١. ڕەشبوونی شاشە
    overlay.style.pointerEvents = "auto";
    overlay.style.opacity = "1";

    // ٢. کاتێک ڕەش بوو، گۆڕینی زمان
    setTimeout(function () {
        setLang(lang);

        // ٣. دووبارە ڕووناکبوونەوەی شاشە بە نەرمی لەگەڵ زمانی نوێ
        setTimeout(function () {
            overlay.style.opacity = "0";
            setTimeout(function () {
                overlay.style.pointerEvents = "none";
            }, 260);
        }, 120);
    }, 240);
}

document.addEventListener("click", function (e) {
    var wrap = document.getElementById("langDropdownWrap");
    if (wrap && !wrap.contains(e.target)) {
        wrap.classList.remove("open");
    }
});

document.addEventListener("DOMContentLoaded", loadLang);
