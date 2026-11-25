// =====================================================
// NEXORA - main.js
// Wishlist, Search, Sidebar, Scrolling, Gallery
// =====================================================

// ===== ١. لیستی دڵخواز (Wishlist in localStorage) =====
function getWishlist() {
    try {
        var raw = JSON.parse(localStorage.getItem("nexora_wishlist"));
        if (Array.isArray(raw)) {
            return raw.map(function (x) { return parseInt(x, 10); }).filter(function (x) { return !isNaN(x) && x > 0; });
        }
        return [];
    } catch (e) {
        return [];
    }
}

function saveWishlist(list) {
    if (!Array.isArray(list)) list = [];
    localStorage.setItem("nexora_wishlist", JSON.stringify(list));
    updateWishlistCount();
    syncWishlistButtons();
}

function updateWishlistCount() {
    var count = getWishlist().length;
    var el = document.getElementById("wishlistCount");
    if (el) {
        el.textContent = count;
        el.style.display = count > 0 ? "flex" : "none";
    }
}

function toggleWishlist(id, btn) {
    id = parseInt(id, 10);
    if (isNaN(id) || id <= 0) return;
    var list = getWishlist();
    var idx = list.indexOf(id);
    var added = false;
    if (idx === -1) {
        list.push(id);
        added = true;
        var msg = (typeof t === "function" && t("product.wishlist_add") && t("product.wishlist_add") !== "product.wishlist_add")
            ? t("product.wishlist_add") : "زیاد کرا بۆ لیستی دڵخواز ❤️";
        if (typeof showToast === "function") showToast(msg);
    } else {
        list.splice(idx, 1);
        var msg = (typeof t === "function" && t("product.wishlist_remove") && t("product.wishlist_remove") !== "product.wishlist_remove")
            ? t("product.wishlist_remove") : "لابردرا لە لیستی دڵخواز 🤍";
        if (typeof showToast === "function") showToast(msg);
    }
    saveWishlist(list);
    if (btn) {
        if (added) btn.classList.add("active");
        else btn.classList.remove("active");
    }
}

function syncWishlistButtons() {
    var list = getWishlist();
    document.querySelectorAll(".wishlist-btn").forEach(function (btn) {
        var id = parseInt(btn.dataset.id, 10);
        if (list.indexOf(id) !== -1) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
}

window.getWishlist = getWishlist;
window.saveWishlist = saveWishlist;
window.updateWishlistCount = updateWishlistCount;
window.toggleWishlist = toggleWishlist;
window.syncWishlistButtons = syncWishlistButtons;

// ===== ٢. سایدبار (Sidebar Drawer) =====
function openSidebar(e) {
    if (e) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    var sidebar = document.getElementById("sidebar");
    var overlay = document.getElementById("sidebarOverlay");
    if (sidebar) sidebar.classList.add("active");
    if (overlay) overlay.classList.add("active");
    document.body.style.overflow = "hidden";
}

function closeSidebar(e) {
    if (e) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    var sidebar = document.getElementById("sidebar");
    var overlay = document.getElementById("sidebarOverlay");
    if (sidebar) sidebar.classList.remove("active");
    if (overlay) overlay.classList.remove("active");
    document.body.style.overflow = "";
}

function toggleSidebar(e) {
    if (e) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    var sidebar = document.getElementById("sidebar");
    if (!sidebar) return;
    if (sidebar.classList.contains("active")) {
        closeSidebar();
    } else {
        openSidebar();
    }
}
window.openSidebar = openSidebar;
window.closeSidebar = closeSidebar;
window.toggleSidebar = toggleSidebar;

function toggleBrandsDropdown(btn, e) {
    if (e) {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
    }
    var parent = btn ? btn.closest(".sidebar-dropdown") : document.querySelector(".sidebar-dropdown");
    if (parent) {
        parent.classList.toggle("open");
    }
}
window.toggleBrandsDropdown = toggleBrandsDropdown;

// ===== ٣. گەڕانی خێرا (Search Modal) =====
var searchTimer = null;

function openSearch() {
    var modal = document.getElementById("searchModal");
    var input = document.getElementById("modalSearchInput");
    if (modal) {
        modal.classList.add("active");
        document.body.style.overflow = "hidden";
        if (input) {
            setTimeout(function () { input.focus(); }, 100);
        }
    }
}

function closeSearch() {
    var modal = document.getElementById("searchModal");
    if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
    }
}

function onSearchInput(val) {
    clearTimeout(searchTimer);
    var resultsBox = document.getElementById("modalSearchResults");
    if (!resultsBox) return;

    var query = val.trim();
    if (query.length < 1) {
        resultsBox.innerHTML = '<p style="color:var(--muted); text-align:center; padding:20px;">' +
            (t("search.quick_hint") || "لانی کەم پیتێک بنووسە بۆ گەڕانی خێرا") + '</p>';
        return;
    }

    searchTimer = setTimeout(function () {
        fetch("/api/search?q=" + encodeURIComponent(query))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data || data.length === 0) {
                    resultsBox.innerHTML = '<p style="color:var(--muted); text-align:center; padding:20px;">' +
                        (t("search.no_results") || "هیچ ئەنجامێک نەدۆزرایەوە.") + '</p>';
                    return;
                }
                var html = "";
                data.forEach(function (p) {
                    html += '<a href="/product/' + p.id + '" class="search-result-item">' +
                        '<img src="/static/images/products/' + p.image + '" alt="" onerror="this.onerror=null;this.src=\'/static/images/placeholder.svg\'">' +
                        '<div class="search-result-info">' +
                            '<h4>' + p.name + '</h4>' +
                            '<span class="cat-tag">' + p.brand + ' • ' + p.category + '</span>' +
                        '</div>' +
                        '<div class="search-result-price">' + p.price_iqd + '</div>' +
                    '</a>';
                });
                resultsBox.innerHTML = html;
            })
            .catch(function () {
                resultsBox.innerHTML = '<p style="color:var(--danger); text-align:center; padding:20px;">هەڵەیەک ڕوویدا لە گەڕاندا</p>';
            });
    }, 250);
}

// داخرانی سێرچ بە کلیلی Escape
document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
        closeSearch();
        var sidebar = document.getElementById("sidebar");
        if (sidebar && sidebar.classList.contains("active")) {
            toggleSidebar();
        }
    }
});

// ===== ٤. سوڕاندنی بەشە ئاسۆییەکان بە ئەنیمەیشنی نەرم و پێشکەوتوو (Smooth Category Rows) =====
function scrollCatRow(btn, direction) {
    var wrapper = btn.closest(".cat-row-wrapper");
    if (!wrapper) return;
    var container = wrapper.querySelector(".cat-row-scroll");
    if (!container) return;

    // ئەنیمەیشنی فشردن لەسەر دوگمەکە
    btn.style.transform = "scale(0.85)";
    setTimeout(function () { btn.style.transform = ""; }, 180);

    var card = container.querySelector(".cat-row-card");
    var step = card ? (card.offsetWidth + 22) : 280;
    var moveAmount = step * 2;

    var isRTL = document.documentElement.dir === "rtl" || 
                document.body.dir === "rtl" || 
                window.getComputedStyle(container).direction === "rtl";

    var delta = 0;
    if (isRTL) {
        // لە دۆخی ڕاست بۆ چەپ (RTL):
        // دوگمەی چەپ (<) هەمیشە بەرەو پێشەوە دەڕوات (کاڵا زیاترەکان پیشان دەدات)
        if (direction === "left") {
            delta = -moveAmount;
        } else {
            // دوگمەی ڕاست (>)
            // ئەگەر لە سەرەتای ڕیز بێت (scrollLeft نزیکەی 0)، کلیک لەسەر > بەرەو پێشەوە دەڕوات بۆ دیتنی کاڵاکان
            // ئەگەر کەمێک ڕۆیشتبێتە ناوەوە، دەیگەڕێنێتەوە سەرەتا
            if (Math.abs(container.scrollLeft) < 25) {
                delta = -moveAmount;
            } else {
                delta = moveAmount;
            }
        }
    } else {
        delta = (direction === "left") ? -moveAmount : moveAmount;
    }

    try {
        container.scrollBy({ left: delta, behavior: "smooth" });
    } catch (e) {
        container.scrollLeft += delta;
    }
}
window.scrollCatRow = scrollCatRow;

// زیادکردنی تایبەتمەندی ڕاکێشان بە ماوس (Drag / Swipe to Scroll)
function initDragToScroll() {
    document.querySelectorAll(".cat-row-scroll").forEach(function (slider) {
        var isDown = false;
        var startX, scrollLeft;

        slider.addEventListener("mousedown", function (e) {
            if (e.target.closest("button") || e.target.closest("a") || e.target.closest(".wishlist-btn")) return;
            isDown = true;
            slider.style.cursor = "grabbing";
            slider.style.userSelect = "none";
            startX = e.pageX - slider.offsetLeft;
            scrollLeft = slider.scrollLeft;
        });

        slider.addEventListener("mouseleave", function () {
            if (isDown) {
                isDown = false;
                slider.style.cursor = "grab";
                slider.style.userSelect = "";
            }
        });

        slider.addEventListener("mouseup", function () {
            if (isDown) {
                isDown = false;
                slider.style.cursor = "grab";
                slider.style.userSelect = "";
            }
        });

        slider.addEventListener("mousemove", function (e) {
            if (!isDown) return;
            e.preventDefault();
            var x = e.pageX - slider.offsetLeft;
            var walk = (x - startX) * 1.5;
            slider.scrollLeft = scrollLeft - walk;
        });
    });
}

// ===== ٥. بەڕێوبەرایەتی تابلەکان (Admin Tabs) =====
function switchAdminTab(tabName, btn) {
    document.querySelectorAll(".admin-tab-content").forEach(function (el) {
        el.style.display = "none";
    });
    document.querySelectorAll(".admin-tab-btn").forEach(function (b) {
        b.classList.remove("active");
    });
    var target = document.getElementById("tab-" + tabName);
    if (target) {
        target.style.display = "block";
    }
    if (btn) {
        btn.classList.add("active");
    }
    window.location.hash = tabName;
}

// ===== ٦. گەلەری وێنە لە پەیجی بەرهەم =====
function showImage(el) {
    if (!el) return;
    var btn = el.closest ? el.closest(".thumb") : el;
    var src = btn.getAttribute("data-src") || (btn.dataset ? btn.dataset.src : "");
    var main = document.getElementById("mainImage");
    if (main && src) {
        main.style.opacity = "0.35";
        main.src = src;
        setTimeout(function () {
            main.style.opacity = "1";
        }, 120);
    }
    document.querySelectorAll(".thumb").forEach(function (t) {
        t.classList.remove("active");
    });
    if (btn) btn.classList.add("active");
}
window.showImage = showImage;

// ===== ٧. تۆست نۆتفیکەیشن (Toast Notification) =====
function showToast(msg) {
    var toast = document.getElementById("nexoraToast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "nexoraToast";
        toast.style.cssText = "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:rgba(20,20,32,0.92);border:1px solid #f59e0b;box-shadow:0 10px 30px rgba(0,0,0,0.6), 0 0 20px rgba(245,158,11,0.4);color:#fff;padding:12px 24px;border-radius:30px;font-weight:700;font-size:0.95rem;box-shadow:0 10px 30px rgba(0,0,0,0.6);z-index:9999;transition:all 0.3s;opacity:0;pointer-events:none;";
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = "1";
    toast.style.transform = "translateX(-50%) translateY(-6px)";
    setTimeout(function () {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(-50%) translateY(0)";
    }, 2200);
}

// ===== ٨. گەڕانی خێرای ڕاستەوخۆ لە هێدەر (Header Live Search Dropdown) =====
var searchTimer = null;

function initHeaderSearch() {
    var searchInput = document.getElementById("headerSearchInput");
    var searchResults = document.getElementById("headerSearchResults");

    if (!searchInput || !searchResults) return;

    searchInput.addEventListener("input", function () {
        var query = this.value.trim();
        clearTimeout(searchTimer);

        if (query.length < 1) {
            searchResults.innerHTML = "";
            searchResults.classList.remove("show");
            return;
        }

        searchTimer = setTimeout(function () {
            fetch("/api/search?q=" + encodeURIComponent(query))
                .then(function (r) { return r.json(); })
                .then(function (items) {
                    if (!items || items.length === 0) {
                        searchResults.innerHTML =
                            '<div class="search-empty-item">' +
                            '<span>🔍</span> ' + (t("search.no_results") || "هیچ کاڵایەک نەدۆزرایەوە") +
                            '</div>';
                        searchResults.classList.add("show");
                        return;
                    }

                    var html = '<div class="search-results-list">';
                    items.slice(0, 8).forEach(function (p) {
                        var priceText = typeof fmtIQD === "function" && typeof toIQD === "function"
                            ? fmtIQD(toIQD(p.price))
                            : (p.price_iqd || (Number(p.price).toLocaleString() + " IQD"));

                        html +=
                            '<a href="/product/' + p.id + '" class="search-result-item">' +
                                '<div class="search-result-thumb">' +
                                    '<img src="/static/images/products/' + p.image + '" alt="' + p.name + '" onerror="this.onerror=null;this.src=\'/static/images/placeholder.svg\'">' +
                                '</div>' +
                                '<div class="search-result-info">' +
                                    (p.brand_name ? '<span class="search-result-brand">' + p.brand_name + '</span>' : '') +
                                    '<div class="search-result-name">' + p.name + '</div>' +
                                    '<div class="search-result-price">' + priceText + '</div>' +
                                '</div>' +
                            '</a>';
                    });
                    html += '</div>';
                    html +=
                        '<a href="/products?q=' + encodeURIComponent(query) + '" class="search-view-all-btn">' +
                            '<span>' + (t("sec.view_all") || "بینینی هەموو ئەنجامەکان") + ' (' + items.length + ')</span>' +
                            '<span>←</span>' +
                        '</a>';
                    searchResults.innerHTML = html;
                    searchResults.classList.add("show");
                })
                .catch(function () {
                    searchResults.classList.remove("show");
                });
        }, 120);
    });

    // داخستنی کاتی کلیک لە دەرەوە
    document.addEventListener("click", function (e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.remove("show");
        }
    });

    // داخستن بە کلیلی Escape
    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            searchResults.classList.remove("show");
        }
    });
}


// ===== ٩. سیستەمی دواین بینراوەکان (Recently Viewed Products System) =====
function recordRecentlyViewed(productId) {
    if (!productId) return;
    try {
        var raw = localStorage.getItem("nexora_recently_viewed");
        var list = raw ? JSON.parse(raw) : [];
        if (!Array.isArray(list)) list = [];
        // لابردنی ئەگەر پێشتر هەبوو
        list = list.filter(function (id) { return id !== productId && id !== String(productId); });
        // خستنە سەرەتای لیست
        list.unshift(productId);
        // هێشتنەوەی زۆرترین ٨ دانە
        list = list.slice(0, 8);
        localStorage.setItem("nexora_recently_viewed", JSON.stringify(list));
    } catch (e) {
        console.error("Error recording recently viewed:", e);
    }
}

function initRecentlyViewed() {
    var container = document.getElementById("recentlyViewedGrid");
    var section = document.getElementById("recentlyViewedSection");
    if (!container || !section) return;

    var currentProdEl = document.getElementById("currentProductMeta");
    var currentId = currentProdEl ? parseInt(currentProdEl.getAttribute("data-id")) : null;

    if (currentId) {
        recordRecentlyViewed(currentId);
    }

    try {
        var raw = localStorage.getItem("nexora_recently_viewed");
        var list = raw ? JSON.parse(raw) : [];
        if (!Array.isArray(list)) list = [];

        // فلتەرکردنی کاڵای ئێستا بۆ ئەوەی کاڵای خۆی لە ژێر خۆیدا دەرنەکەوێت
        var otherIds = list.filter(function (id) { return id !== currentId && id !== String(currentId); });

        if (otherIds.length === 0) {
            section.style.display = "none";
            return;
        }

        // داواکردنی زانیاری کاڵاکانی پێشوو لە سێرڤەر
        fetch("/api/cart-items", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(otherIds.slice(0, 4))
        })
        .then(function (res) { return res.json(); })
        .then(function (products) {
            if (!products || products.length === 0) {
                section.style.display = "none";
                return;
            }

            var html = "";
            products.forEach(function (p) {
                var priceFormatted = (p.price * 1310).toLocaleString() + " IQD";
                html += '<div class="product-card">' +
                    '<a class="card-link" href="/product/' + p.id + '" aria-label="' + p.name + '"></a>' +
                    '<div class="product-img">' +
                        '<img src="/static/images/products/' + p.image + '" alt="' + p.name + '" loading="lazy" onerror="this.onerror=null;this.src=\'/static/images/placeholder.svg\'">' +
                        '<button type="button" class="wishlist-btn" data-id="' + p.id + '" onclick="event.preventDefault();event.stopPropagation();toggleWishlist(' + p.id + ', this)" aria-label="Wishlist">' +
                            '<svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>' +
                        '</button>' +
                    '</div>' +
                    '<div class="product-info">' +
                        '<span class="brand">' + (p.brand_name || "") + '</span>' +
                        '<h3>' + p.name + '</h3>' +
                        '<div class="product-price-row">' +
                            '<div class="price">' + priceFormatted + '</div>' +
                            '<button type="button" class="add-cart-btn" onclick="event.preventDefault();event.stopPropagation();addToCart(' + p.id + ')">' +
                                '<svg class="cart-btn-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">' +
                                    '<circle cx="9" cy="20" r="1.5" fill="currentColor" stroke="none"></circle>' +
                                    '<circle cx="18" cy="20" r="1.5" fill="currentColor" stroke="none"></circle>' +
                                    '<path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>' +
                                '</svg>' +
                                '<span data-i18n="product.add_short">زیادکردن</span>' +
                            '</button>' +
                        </div>' +
                    '</div>' +
                '</div>';
            });

            container.innerHTML = html;
            section.style.display = "block";
            syncWishlistButtons();
        })
        .catch(function (err) {
            console.error("Error loading recently viewed:", err);
            section.style.display = "none";
        });
    } catch (e) {
        console.error("Error in initRecentlyViewed:", e);
    }
}

// ===== ١٠. دوگمەی گەڕانەوە بۆ سەرەوە (Scroll To Top Button) =====
function initScrollTop() {
    var btn = document.getElementById("scrollTopBtn");
    if (!btn) return;
    window.addEventListener("scroll", function () {
        if (window.scrollY > 280) {
            btn.classList.add("show");
        } else {
            btn.classList.remove("show");
        }
    }, { passive: true });
}

// ===== ١١. بەڕێوەبردنی پەیوەندی ئیمەیڵ و تەلەفۆن (Contact Handlers) =====
function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).catch(function () {
            fallbackCopy(text);
        });
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    try {
        var textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
    } catch (e) {}
}

function handleContactEmail(e) {
    if (e) {
        try { e.preventDefault(); } catch (err) {}
    }
    var email = "manesalar127@gmail.com";
    var isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent || navigator.vendor || window.opera);

    copyToClipboard(email);

    if (isMobile) {
        // لەسەر مۆبایل ڕاستەوخۆ بەرنامەی ئیمەیڵ (Gmail / Mail) دەکرێتەوە
        window.location.href = "mailto:" + email;
    } else {
        // لەسەر کۆمپیوتەر ڕاستەوخۆ وێبی جیمەیڵ (Gmail Web Compose) لە تابی نوێ دەکرێتەوە
        var gmailUrl = "https://mail.google.com/mail/?view=cm&fs=1&to=" + encodeURIComponent(email);
        var win = window.open(gmailUrl, "_blank");
        if (!win || win.closed || typeof win.closed === "undefined") {
            window.location.href = "mailto:" + email;
        }
    }

    if (typeof showToast === "function") {
        showToast("✉️ ئیمەیڵ کرایەوە: " + email);
    }
}

function handleContactPhone(e) {
    var phoneClean = "+9647512719296";
    var phoneDisplay = "+964 751 271 9296";
    var isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent || navigator.vendor || window.opera);

    copyToClipboard(phoneClean);

    if (isMobile) {
        // لەسەر مۆبایل ڕاستەوخۆ بەرنامەی پەیوەندی مۆبایل (Phone Dialer) دەکرێتەوە
        window.location.href = "tel:" + phoneClean;
    } else {
        if (e) {
            try { e.preventDefault(); } catch (err) {}
        }
        // لەسەر کۆمپیوتەر واتساپ لە تابی نوێ دەکرێتەوە و ژمارەکەش تاقی دەکرێتەوە لە سیستەم
        try {
            window.location.href = "tel:" + phoneClean;
        } catch (err) {}
        window.open("https://wa.me/9647512719296", "_blank");
    }

    if (typeof showToast === "function") {
        showToast("📞 پەیوەندیکردن بە: " + phoneDisplay);
    }
}

window.handleContactEmail = handleContactEmail;
window.handleContactPhone = handleContactPhone;

// کاتی باربوونی لاپەڕە
document.addEventListener("DOMContentLoaded", function () {
    updateWishlistCount();
    syncWishlistButtons();
    initHeaderSearch();
    initDragToScroll();
    initRecentlyViewed();
    initScrollTop();

    // ئەگەر لە داشبۆرد بووین و هاش لە URL هەبوو
    if (window.location.hash) {
        var tab = window.location.hash.replace("#", "");
        var btn = document.querySelector('[data-tab="' + tab + '"]');
        if (btn) {
            switchAdminTab(tab, btn);
        }
    }
});
