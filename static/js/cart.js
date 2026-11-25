// =====================================================
// NEXORA - cart.js
// Shopping Cart & Wishlist Logic
// Delivery fee: 5,000 IQD
// =====================================================

var USD_TO_IQD = 1310;
var DELIVERY_FEE_IQD = 5000;

function toIQD(usd) {
    return Math.round((usd * USD_TO_IQD) / 1000) * 1000;
}

function fmtIQD(iqd) {
    return Number(iqd).toLocaleString("en-US") + " IQD";
}

// ===== سەبەتە لە localStorage =====
function getCart() {
    try {
        return JSON.parse(localStorage.getItem("nexora_cart")) || [];
    } catch (e) {
        return [];
    }
}

function saveCart(cart) {
    localStorage.setItem("nexora_cart", JSON.stringify(cart));
    updateCartCount();
}

function updateCartCount() {
    var el = document.getElementById("cartCount");
    if (!el) return;
    var total = getCart().reduce(function (sum, i) { return sum + i.qty; }, 0);
    el.textContent = total;
    el.style.display = total > 0 ? "flex" : "none";
}

function addToCart(id) {
    var cart = getCart();
    var found = cart.find(function (i) { return i.id === id; });
    if (found) {
        found.qty += 1;
    } else {
        cart.push({ id: id, qty: 1 });
    }
    saveCart(cart);

    showToast(t("product.added") || "✅ زیاد کرا بۆ سەبەتە");

    // ئەگەر لە پەیجی بەرهەم بوو
    var span = document.querySelector("#addToCart span");
    if (span) {
        var original = span.textContent;
        span.textContent = t("product.added") || "✅ زیاد کرا";
        setTimeout(function () { span.textContent = original; }, 1200);
    }
}

function changeQty(id, delta) {
    var cart = getCart();
    var item = cart.find(function (i) { return i.id === id; });
    if (!item) return;
    item.qty += delta;
    if (item.qty <= 0) {
        cart = cart.filter(function (i) { return i.id !== id; });
    }
    saveCart(cart);
    renderCart();
}

function removeItem(id) {
    saveCart(getCart().filter(function (i) { return i.id !== id; }));
    renderCart();
}

// ===== لاپەڕەی سەبەتە =====
var cartData = [];

function renderCart() {
    var box = document.getElementById("cartItems");
    if (!box) return;

    var cart = getCart();
    var summaryBox = document.getElementById("cartSummary");

    if (cart.length === 0) {
        box.innerHTML = '<div style="text-align:center; padding: 60px 20px;"><div style="font-size:3.5rem; margin-bottom:12px;">🛒</div><p style="color:var(--muted); font-size:1.1rem; margin-bottom:20px;">' + (t("cart.empty") || "سەبەتەکەت بەتاڵە") + '</p><a href="/products" class="btn-checkout" style="display:inline-block; padding:10px 24px;">' + (t("cart.continue") || "بەردەوام بە لە کڕین") + '</a></div>';
        if (summaryBox) summaryBox.style.display = "none";
        return;
    }

    if (summaryBox) summaryBox.style.display = "block";

    var html = "";
    var subtotal = 0;

    cart.forEach(function (item) {
        var p = cartData.find(function (d) { return d.id === item.id; });
        if (!p) return;
        var unit = toIQD(p.price);
        var line = unit * item.qty;
        subtotal += line;

        html +=
            '<div class="cart-row">' +
              '<img src="/static/images/products/' + p.image + '" alt="" onerror="this.onerror=null;this.src=\'/static/images/placeholder.svg\'">' +
              '<div class="cart-name">' +
                  '<span class="brand">' + p.brand_name + '</span>' +
                  '<strong>' + p.name + '</strong>' +
                  '<span class="cart-unit">' + fmtIQD(unit) + '</span>' +
              '</div>' +
              '<div class="qty-control">' +
                  '<button type="button" onclick="changeQty(' + p.id + ', -1)">−</button>' +
                  '<span>' + item.qty + '</span>' +
                  '<button type="button" onclick="changeQty(' + p.id + ', 1)">+</button>' +
              '</div>' +
              '<div class="cart-line-price">' + fmtIQD(line) + '</div>' +
              '<button type="button" class="remove-btn" onclick="removeItem(' + p.id + ')">✕</button>' +
            '</div>';
    });

    box.innerHTML = html;

    var grandTotal = subtotal + DELIVERY_FEE_IQD;

    var subEl = document.getElementById("cartSubtotal");
    if (subEl) subEl.textContent = fmtIQD(subtotal);

    var delEl = document.getElementById("cartDelivery");
    if (delEl) delEl.textContent = fmtIQD(DELIVERY_FEE_IQD);

    var totEl = document.getElementById("cartGrandTotal");
    if (totEl) totEl.textContent = fmtIQD(grandTotal);
}

function loadCartPage() {
    if (!document.getElementById("cartItems")) return;
    var cart = getCart();
    if (cart.length === 0) { renderCart(); return; }

    fetch("/api/cart-items", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cart.map(function (i) { return i.id; }))
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        cartData = data;
        var ids = data.map(function (d) { return d.id; });
        saveCart(getCart().filter(function (i) { return ids.indexOf(i.id) !== -1; }));
        renderCart();
    });
}

function toggleCheckoutForm() {
    var form = document.getElementById("checkoutFormBox");
    if (form) {
        form.classList.toggle("active");
        if (form.classList.contains("active")) {
            form.scrollIntoView({ behavior: "smooth" });
        }
    }
}

// ===== ناردنی داواکاری =====
function submitOrder(event) {
    event.preventDefault();

    var form = event.target;
    var msg = document.getElementById("orderMsg");
    var btn = document.getElementById("submitOrderBtn");

    var payload = {
        full_name: form.full_name.value,
        phone: form.phone.value,
        city: form.city.value,
        neighborhood: form.neighborhood.value,
        items: getCart()
    };

    btn.disabled = true;
    msg.className = "order-msg";
    msg.textContent = t("cart.wait") || "تکایە چاوەڕێ بکە...";

    fetch("/api/order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(function (r) { return r.json(); })
    .then(function (res) {
        if (res.ok) {
            localStorage.removeItem("nexora_cart");
            updateCartCount();
            document.getElementById("cartPage").innerHTML =
                '<div style="text-align:center; padding: 70px 20px;">' +
                  '<div style="font-size:4rem; margin-bottom:12px;">✅</div>' +
                  '<h2 style="font-size:2rem; margin-bottom:10px; color:var(--cyan);">' + (t("cart.success") || "داواکارییەکەت نێردرا") + '</h2>' +
                  '<p style="color:var(--muted); font-size:1.1rem; margin-bottom:8px;">' + (t("cart.order_no") || "ژمارەی داواکاری:") + ' <strong>#' + res.order_id + '</strong></p>' +
                  '<p style="color:var(--muted); margin-bottom:24px;">' + (t("cart.contact_soon") || "بەمزووانە پەیوەندیت پێوە دەکەین بۆ گەیاندن.") + '</p>' +
                  '<a href="/" class="btn-checkout" style="display:inline-block; padding:12px 30px;">' + (t("cart.back") || "گەڕانەوە بۆ سەرەکی") + '</a>' +
                '</div>';
        } else {
            msg.className = "order-msg error";
            msg.textContent = res.error || (t("cart.error") || "هەڵەیەک ڕوویدا");
            btn.disabled = false;
        }
    })
    .catch(function () {
        msg.className = "order-msg error";
        msg.textContent = t("cart.error") || "هەڵەیەک ڕوویدا";
        btn.disabled = false;
    });
}

// ===== لاپەڕەی لیستی دڵخواز (Wishlist Page) =====
function getWishlistSafe() {
    if (typeof getWishlist === "function") return getWishlist();
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

function saveWishlistSafe(list) {
    if (typeof saveWishlist === "function") {
        saveWishlist(list);
    } else {
        localStorage.setItem("nexora_wishlist", JSON.stringify(list));
        if (typeof updateWishlistCount === "function") updateWishlistCount();
        if (typeof syncWishlistButtons === "function") syncWishlistButtons();
    }
}

function loadWishlistPage() {
    var box = document.getElementById("wishlistItems");
    if (!box) return;

    var list = getWishlistSafe();
    if (list.length === 0) {
        box.innerHTML = '<div class="wishlist-empty" style="text-align:center; padding:60px 20px;">' +
            '<div class="wishlist-empty-icon" style="font-size:3.5rem; margin-bottom:12px;">💔</div>' +
            '<h2 style="margin-bottom:10px; font-size:1.5rem; color:var(--text);">' + (t("wishlist.empty") || "هیچ کاڵایەکت لە لیستی دڵخواز نییە") + '</h2>' +
            '<p style="color:var(--muted); margin-bottom:24px;">دەتوانی بە کلیک لەسەر دڵی هەر بەرهەمێک زیادی بکەیت بۆ ئێرە</p>' +
            '<a href="/products" class="btn-checkout" style="display:inline-block; padding:12px 28px;">' + (t("wishlist.explore") || "گەڕان لە بەرهەمەکان") + '</a>' +
        '</div>';
        return;
    }

    fetch("/api/cart-items", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(list)
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (!data || data.length === 0) {
            box.innerHTML = '<div class="wishlist-empty" style="text-align:center; padding:60px 20px;"><div style="font-size:3.5rem; margin-bottom:12px;">💔</div><p style="color:var(--muted);">' + (t("wishlist.empty") || "بەتاڵە") + '</p></div>';
            return;
        }

        var html = '<div class="products-grid-4">';
        data.forEach(function (p) {
            var priceDisplay = p.has_discount ?
                '<div class="price-discount-box">' +
                    '<span class="old-price-strikethrough">' + fmtIQD(toIQD(p.original_price)) + '</span>' +
                    '<span class="price new-discount-price">' + fmtIQD(toIQD(p.price)) + '</span>' +
                '</div>' :
                '<div class="price">' + fmtIQD(toIQD(p.price)) + '</div>';

            html +=
                '<div class="product-card">' +
                    '<a class="card-link" href="/product/' + p.id + '" aria-label="' + p.name + '"></a>' +
                    '<div class="product-img">' +
                        '<img src="/static/images/products/' + p.image + '" alt="' + p.name + '" onerror="this.onerror=null;this.src=\'/static/images/placeholder.svg\'">' +
                        '<button class="wishlist-btn active" onclick="event.preventDefault();event.stopPropagation();removeFromWishlistPage(' + p.id + ')" aria-label="Remove" title="لابردن">' +
                            '<svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>' +
                        '</button>' +
                    '</div>' +
                    '<div class="product-info">' +
                        '<span class="brand">' + p.brand_name + '</span>' +
                        '<h3>' + p.name + '</h3>' +
                        '<div class="product-price-row">' +
                            priceDisplay +
                            '<button type="button" class="add-cart-btn" onclick="event.preventDefault();event.stopPropagation();addToCart(' + p.id + ')">' +
                                '<svg class="cart-btn-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">' +
                                    '<circle cx="9" cy="20" r="1.5" fill="currentColor" stroke="none"></circle>' +
                                    '<circle cx="18" cy="20" r="1.5" fill="currentColor" stroke="none"></circle>' +
                                    '<path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>' +
                                '</svg>' +
                                '<span>' + (t("product.add_short") || "زیادکردن") + '</span>' +
                            '</button>' +
                        '</div>' +
                    '</div>' +
                '</div>';
        });
        html += '</div>';
        box.innerHTML = html;
    })
    .catch(function(err) {
        console.error("Error loading wishlist:", err);
    });
}

function removeFromWishlistPage(id) {
    id = parseInt(id, 10);
    var list = getWishlistSafe();
    var idx = list.indexOf(id);
    if (idx !== -1) {
        list.splice(idx, 1);
        saveWishlistSafe(list);
        loadWishlistPage();
        if (typeof showToast === "function") showToast("لابردرا لە لیستی دڵخواز 🤍");
    }
}

window.loadWishlistPage = loadWishlistPage;
window.removeFromWishlistPage = removeFromWishlistPage;

document.addEventListener("DOMContentLoaded", function () {
    updateCartCount();
    loadCartPage();
    loadWishlistPage();
});

document.addEventListener("langchange", function () {
    renderCart();
    loadWishlistPage();
});
