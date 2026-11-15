const $ = (id) => document.getElementById(id);
const theme = document.createElement("link");
theme.rel = "stylesheet";
theme.href = "/app.css";
document.head.append(theme);
const topbar = document.createElement("header");
topbar.id = "topbar";
topbar.innerHTML = '<a class="brand" href="#lookup"><span class="brand-mark">iB</span><span>iBanking<small>CỔNG THANH TOÁN HỌC PHÍ</small></span></a><div class="toolbar"></div>';
topbar.querySelector(".toolbar").append($("demoToggle"), $("logout"));
document.querySelector("main").prepend(topbar);
$("demoToggle").textContent = "Công cụ demo";
const title = document.querySelector("h1");
title.tabIndex = -1;
const intro = document.createElement("p");
intro.className = "intro";
title.after(intro);
const demoSection = $("demo").parentElement;
demoSection.id = "demoSection";
const accountSection = $("account").closest("section");
const lookupSection = $("lookup").closest("section");
const historySection = $("history").closest("section");
lookupSection.querySelector("h2").textContent = "Tìm sinh viên";
$("lookup").elements.mssv.placeholder = "Nhập mã sinh viên, ví dụ SV001";
const searchHelp = document.createElement("p");
searchHelp.className = "section-help";
searchHelp.textContent = "Tra cứu sinh viên để xem các khoản học phí và chọn khoản cần thanh toán.";
lookupSection.querySelector("h2").after(searchHelp);
const searchEmpty = document.createElement("div");
searchEmpty.id = "searchEmpty";
searchEmpty.className = "empty-state";
searchEmpty.textContent = "Nhập mã sinh viên ở trên để bắt đầu tra cứu.";
$("fees").before(searchEmpty);
const review = document.createElement("section");
review.id = "review";
review.hidden = true;
review.innerHTML = '<div class="eyebrow">BƯỚC 01 · THÔNG TIN GIAO DỊCH</div><h2>Xem lại thông tin thanh toán</h2><p class="section-help">Kiểm tra người nhận học phí và số tiền trước khi yêu cầu mã OTP.</p><div id="reviewDetails" class="grid"></div><p id="reviewMessage" role="status"></p><div class="form-actions"><button id="confirmPayment" type="button" disabled>Xác nhận &amp; nhận OTP</button><button id="cancelReview" type="button">Quay lại tra cứu</button></div>';
const checkout = document.createElement("div");
checkout.id = "checkoutPage";
checkout.append(review, $("payment"));
const checkoutEmpty = document.createElement("section");
checkoutEmpty.id = "checkoutEmpty";
checkoutEmpty.className = "empty-state";
checkoutEmpty.innerHTML = '<h2>Chưa chọn khoản học phí</h2><p>Tra cứu sinh viên và chọn một khoản chưa thanh toán để tiếp tục.</p><button type="button" id="startLookup">Tra cứu sinh viên</button>';
checkout.append(checkoutEmpty);
$("workspace").append(checkout);
$("payment").insertAdjacentHTML("afterbegin", '<div class="eyebrow">BƯỚC 02 · XÁC THỰC &amp; KẾT QUẢ</div>');
const resultActions = document.createElement("div");
resultActions.className = "form-actions";
resultActions.innerHTML = '<button type="button" id="toHistory">Xem lịch sử giao dịch</button><button type="button" id="newLookup" class="secondary">Tra cứu sinh viên khác</button>';
$("payment").append(resultActions);
const pages = { lookup: lookupSection, checkout, history: historySection, account: accountSection, demo: demoSection };
const pageMeta = {
  lookup: ["Tra cứu sinh viên", "Tìm thông tin học phí và thanh toán cho sinh viên bằng mã số."],
  checkout: ["Thanh toán học phí", "Kiểm tra thông tin, xác thực OTP và theo dõi kết quả giao dịch."],
  history: ["Lịch sử giao dịch", "Theo dõi các giao dịch, tiếp tục thanh toán và nhận lại biên nhận."],
  account: ["Tài khoản của bạn", "Thông tin người nộp và số dư khả dụng để thanh toán học phí."],
  demo: ["Công cụ demo", "Chuẩn bị tài khoản và học phí cho buổi trình diễn."]
};
const nav = document.createElement("nav");
nav.id = "navigation";
nav.setAttribute("aria-label", "Điều hướng chính");
for (const [key, label] of [["lookup", "Tra cứu sinh viên"], ["checkout", "Thanh toán"], ["history", "Lịch sử giao dịch"], ["account", "Tài khoản"]]) {
  const b = document.createElement("button"); b.type = "button"; b.dataset.page = key; b.textContent = label;
  b.onclick = () => { if (!busy) location.hash = key; };
  nav.append(b);
}
topbar.after(nav);
let currentPage = "lookup";
function go(page, focus = true) {
  if (!token) {
    nav.hidden = true;
    title.textContent = "Chào mừng đến với iBanking";
    intro.textContent = "Đăng nhập để tra cứu và thanh toán học phí an toàn.";
    return;
  }
  if (!pages[page]) page = "lookup";
  currentPage = page;
  for (const [key, el] of Object.entries(pages)) el.hidden = key !== page;
  nav.hidden = false;
  for (const b of nav.querySelectorAll("button")) {
    if (b.dataset.page === page) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  }
  [title.textContent, intro.textContent] = pageMeta[page];
  checkoutEmpty.hidden = !review.hidden || !$("payment").hidden;
  if (location.hash !== "#" + page) historyReplace(page);
  if (focus) { title.focus({preventScroll:true}); window.scrollTo({top:0, behavior:"smooth"}); }
}
function historyReplace(page) { window.history.replaceState(null, "", "#" + page); }
window.addEventListener("hashchange", () => go(location.hash.slice(1)));
$("startLookup").onclick = $("newLookup").onclick = () => go("lookup");
$("toHistory").onclick = () => go("history");
let token = "",
  selected = null,
  selectedFee = null,
  reviewAccount = null,
  accountRows = [],
  busy = false,
  lookupTimer,
  lookupVersion = 0;
const names = {
  pending_otp: "Chờ OTP",
  processing: "Đang xử lý",
  success: "Thành công",
  failed: "Thất bại",
  expired: "Hết hạn",
  refunded: "Đã hoàn tiền",
};
const money = (x) =>
  new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(x));
const path = (c) => "/api/payments/" + encodeURIComponent(c),
  data = (f) => Object.fromEntries(new FormData(f));
function text(p, v, t = "p") {
  const e = document.createElement(t);
  e.textContent = v;
  p.append(e);
  return e;
}
function button(p, label, fn) {
  const b = text(p, label, "button");
  b.type = "button";
  b.onclick = () => action(fn);
}
function closeReview() {
  selectedFee = null;
  reviewAccount = null;
  review.hidden = true;
  syncReview();
  checkoutEmpty.hidden = !$("payment").hidden;
}
function logout() {
  clearTimeout(lookupTimer);
  lookupVersion++;
  closeReview();
  token = "";
  selected = null;
  $("workspace").hidden = true;
  $("login").hidden = false;
  $("logout").hidden = true;
  $("payment").hidden = true;
  $("history").replaceChildren();
  $("fees").replaceChildren();
  $("account").replaceChildren();
  $("demo").hidden = true;
  $("accountForm").reset();
  go("lookup", false);
}
async function api(url, body) {
  const r = await fetch(url, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + token,
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  const d = await r.json();
  if (!r.ok) {
    if (r.status === 401) logout();
    const error = new Error(
      typeof d.detail === "string" ? d.detail : "Dữ liệu nhập chưa hợp lệ",
    );
    error.status = r.status;
    throw error;
  }
  return d;
}
async function action(fn) {
  if (busy) return;
  busy = true;
  $("notice").textContent = "";
  document.querySelectorAll("button").forEach((b) => (b.disabled = true));
  try {
    await fn();
  } catch (e) {
    $("notice").textContent = e.message;
  } finally {
    busy = false;
    document.querySelectorAll("button").forEach((b) => (b.disabled = false));
    syncReview();
  }
}
async function account() {
  const a = await api("/api/account/info");
  closeReview();
  $("account").replaceChildren();
  for (const s of [
    a.full_name,
    a.email,
    a.phone || "",
    "Số dư khả dụng: " + money(a.balance),
  ])
    text($("account"), s);
  return a;
}
function cents(value) {
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(String(value));
  return match
    ? BigInt(match[1]) * 100n + BigInt((match[2] || "").padEnd(2, "0"))
    : null;
}
function syncReview() {
  const balance = reviewAccount ? cents(reviewAccount.balance) : null,
    amount = selectedFee ? cents(selectedFee.amount) : null;
  const valid =
    selectedFee &&
    selectedFee.status === "unpaid" &&
    balance !== null &&
    amount !== null &&
    amount > 0n &&
    balance >= amount;
  $("confirmPayment").disabled = busy || !valid;
  $("reviewMessage").textContent =
    selectedFee && !valid
      ? "Số dư khả dụng không đủ hoặc thông tin thanh toán không hợp lệ."
      : "";
}
async function selectFee(f) {
  $("payment").hidden = true;
  selected = null;
  const version = lookupVersion,
    a = await account();
  if (
    version !== lookupVersion ||
    f.mssv !== $("lookup").elements.mssv.value.trim()
  )
    return;
  selectedFee = f;
  reviewAccount = a;
  const details = $("reviewDetails");
  details.replaceChildren();
  for (const [label, value] of [
    ["Người nộp", a.full_name],
    ["Số điện thoại", a.phone || "Chưa cập nhật"],
    ["Email", a.email],
    ["Mã sinh viên", f.mssv],
    ["Sinh viên", f.student_name],
    ["Học kỳ", f.semester],
    ["Số dư khả dụng", money(a.balance)],
    ["Số tiền thanh toán", money(f.amount)],
  ]) {
    const item = document.createElement("div");
    text(item, label, "small");
    text(item, value);
    details.append(item);
  }
  review.hidden = false;
  syncReview();
  go("checkout");
}
async function lookup() {
  const m = $("lookup").elements.mssv.value.trim(),
    version = ++lookupVersion;
  if (!m) {
    $("fees").replaceChildren();
    searchEmpty.hidden = false;
    return;
  }
  let rows;
  try {
    rows = await api("/api/tuition/" + encodeURIComponent(m));
  } catch (e) {
    if (version === lookupVersion) {
      $("fees").replaceChildren();
      throw e;
    }
    return;
  }
  if (version !== lookupVersion || m !== $("lookup").elements.mssv.value.trim())
    return;
  $("fees").replaceChildren();
  searchEmpty.hidden = true;
  for (const f of rows) {
    const box = document.createElement("div");
    box.className = "item";
    text(box, `${f.student_name} · ${f.mssv} · ${f.semester}`);
    text(
      box,
      money(f.amount) +
        " · " +
        (f.status === "paid" ? "Đã thanh toán" : "Chưa thanh toán"),
    );
    if (f.status === "unpaid")
      button(box, "Thanh toán toàn bộ", () => selectFee(f));
    $("fees").append(box);
  }
}
function show(tx) {
  selected = tx;
  $("payment").hidden = false;
  $("paymentInfo").textContent =
    `Khoản #${tx.tuition_fee_id} · ${money(tx.amount)} · ${names[tx.status] || tx.status}`;
  $("paymentResult").textContent =
    tx.status === "success"
      ? "Thanh toán thành công. Số dư và học phí đã cập nhật."
      : "";
  $("otpForm").hidden = !["pending_otp", "processing"].includes(tx.status);
  $("otpForm").elements.code.required = tx.status === "pending_otp";
  $("resend").hidden = tx.status !== "pending_otp";
  go("checkout");
}
async function loadHistory() {
  const rows = await api("/api/account/transactions");
  $("history").replaceChildren();
  if (!rows.length) text($("history"), "Chưa có giao dịch.");
  for (const tx of rows) {
    const box = document.createElement("div");
    box.className = "item";
    text(box, `${money(tx.amount)} · ${names[tx.status] || tx.status}`);
    text(box, tx.transaction_code, "code");
    text(box, "Khoản #" + tx.tuition_fee_id + " · " + tx.created_at);
    button(box, "Xem / tiếp tục", async () =>
      show(await api(path(tx.transaction_code))),
    );
    if (tx.status === "success")
      button(box, "Gửi lại biên nhận", async () => {
        await api(path(tx.transaction_code) + "/receipt/resend", {});
        $("notice").textContent = "Email xác nhận đã gửi.";
      });
    $("history").append(box);
  }
}
async function update() {
  await account();
  await loadHistory();
  await lookup();
}
$("loginForm").onsubmit = (e) => {
  e.preventDefault();
  action(async () => {
    const r = await api("/api/auth/login", data(e.target));
    token = r.token;
    e.target.reset();
    $("login").hidden = true;
    $("workspace").hidden = false;
    $("logout").hidden = false;
    go("lookup");
    await Promise.all([account(), loadHistory()]);
  });
};
$("lookup").elements.mssv.addEventListener("input", () => {
  clearTimeout(lookupTimer);
  lookupVersion++;
  closeReview();
  $("fees").replaceChildren();
  searchEmpty.hidden = !!$("lookup").elements.mssv.value.trim();
  $("notice").textContent = "";
  if ($("lookup").elements.mssv.value.trim())
    lookupTimer = setTimeout(
      () =>
        lookup().catch((e) => {
          $("notice").textContent = e.message;
        }),
      500,
    );
});
$("lookup").onsubmit = (e) => {
  e.preventDefault();
  clearTimeout(lookupTimer);
  closeReview();
  action(lookup);
};
$("logout").onclick = logout;
$("historyRefresh").onclick = () => action(loadHistory);
$("cancelReview").onclick = () => { closeReview(); go("lookup"); };
$("confirmPayment").onclick = () =>
  action(async () => {
    const balance = reviewAccount ? cents(reviewAccount.balance) : null,
      amount = selectedFee ? cents(selectedFee.amount) : null;
    if (
      !selectedFee ||
      selectedFee.status !== "unpaid" ||
      balance === null ||
      amount === null ||
      amount <= 0n ||
      balance < amount
    )
      return;
    let tx;
    try {
      tx = await api("/api/payments", { tuition_fee_id: selectedFee.id });
    } catch (error) {
      if (error.status === 409) {
        closeReview();
        await Promise.allSettled([account(), lookup()]);
        go("lookup");
      }
      throw error;
    }
    closeReview();
    show(tx);
    $("paymentResult").textContent = tx.otp_sent
      ? "OTP gửi tới " + tx.email + ". Kiểm tra cả Spam."
      : "Chưa gửi được OTP: " + tx.otp_error;
    await loadHistory();
  });
$("otpForm").onsubmit = (e) => {
  e.preventDefault();
  action(async () => {
    const code = selected.transaction_code;
    try {
      show(
        await api(path(code) + "/confirm", {
          code: e.target.elements.code.value || "000000",
        }),
      );
    } catch (error) {
      if (!token) throw error;
      const tx = await api(path(code));
      show(tx);
      if (tx.status !== "success")
        throw new Error(
          error.message +
            " Trạng thái: " +
            names[tx.status] +
            ". Tiếp tục giao dịch này hoặc kiểm tra lại trạng thái.",
        );
    }
    e.target.reset();
    await update();
  });
};
$("resend").onclick = () =>
  action(async () => {
    await api(path(selected.transaction_code) + "/otp/resend", {});
    $("paymentResult").textContent =
      "OTP mới đã gửi; mã cũ không còn hiệu lực.";
  });
$("checkStatus").onclick = () =>
  action(async () => {
    show(await api(path(selected.transaction_code)));
    await update();
  });
async function loadAccounts() {
  accountRows = await api("/api/demo/accounts");
  $("accounts").replaceChildren();
  text($("accounts"), "Tạo mới", "option").value = "";
  for (const row of accountRows)
    text($("accounts"), row.username + " · " + row.full_name, "option").value =
      row.id;
}
$("demoToggle").onclick = () =>
  action(async () => {
    await loadAccounts();
    $("demo").hidden = false;
    go("demo");
  });
$("accounts").onchange = () => {
  const row = accountRows.find((a) => String(a.id) === $("accounts").value),
    f = $("accountForm");
  for (const key of ["username", "full_name", "email", "phone", "balance"])
    f.elements[key].value = row?.[key] ?? "";
  f.elements.password.value = "";
  f.elements.username.readOnly = false;
};
$("accountForm").onsubmit = (e) => {
  e.preventDefault();
  action(async () => {
    if (!confirm("Lưu thông tin và số dư demo vào NeonDB?")) return;
    const body = data(e.target);
    body.id = $("accounts").value ? Number($("accounts").value) : null;
    await api("/api/demo/accounts", body);
    e.target.reset();
    await loadAccounts();
    await account();
    $("notice").textContent =
      "Đã lưu tài khoản demo. Dùng username và mật khẩu mới cho lần đăng nhập tiếp theo.";
  });
};
$("feeForm").onsubmit = (e) => {
  e.preventDefault();
  action(async () => {
    const d = data(e.target);
    await api("/api/demo/tuition", d);
    $("lookup").elements.mssv.value = d.mssv;
    await lookup();
    e.target.reset();
    $("notice").textContent = "Đã thêm học phí.";
  });
};

go("lookup", false);

