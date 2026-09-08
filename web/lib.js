export const DEFAULT_BOOK_TEXT = "send $400 to three people monthly, 80% to spend, 20% held";

function storedDraft() { try { return sessionStorage.getItem("allot-draft"); } catch { return null; } }
export const appState = {
  instructionText: storedDraft() || DEFAULT_BOOK_TEXT,
  parsedInstruction: null,
  currentReceipt: null,
  requestStatus: "idle",
  lastError: null,
};

export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

export function attr(value) {
  return esc(value).replace(/`/g, "&#96;");
}

export async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45000);
  let response;
  try {
    response = await fetch(path, { ...options, signal: controller.signal });
  } catch (cause) {
    clearTimeout(timeout);
    const error = new Error(cause.name === "AbortError" ? "The demo service took too long to respond. Check activity before retrying a preparation." : "Allot could not reach the demo service. Check your connection and try again.");
    error.cause = cause;
    error.status = 0;
    throw error;
  }
  let data = null;
  try { data = await response.json(); } catch { data = null; } finally { clearTimeout(timeout); }
  if (!response.ok) {
    const message = data?.error || data?.errors?.join(" ") || `The request failed with status ${response.status}.`;
    const error = new Error(message);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  if (data === null) throw new Error("The demo service returned an unreadable response. Please retry.");
  return data;
}

export function postJson(path, payload) {
  return api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
}

function centsFrom(value) {
  const text = String(value ?? "0");
  const negative = text.startsWith("-");
  const clean = negative ? text.slice(1) : text;
  const [whole = "0", fraction = ""] = clean.split(".");
  const cents = BigInt(`${whole.replace(/\D/g, "") || "0"}${fraction.padEnd(2, "0").slice(0, 2)}`);
  return negative ? -cents : cents;
}

function formatCents(cents) {
  const negative = cents < 0n;
  const absolute = negative ? -cents : cents;
  const major = absolute / 100n;
  const minor = String(absolute % 100n).padStart(2, "0");
  const grouped = major.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${negative ? "-" : ""}$${grouped}.${minor}`;
}

export function usd(value) { return formatCents(centsFrom(value)); }
export function amountForBps(value, basisPoints) { return formatCents((centsFrom(value) * BigInt(basisPoints)) / 10000n); }

export function numeric(value, maximumFractionDigits = 8) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number)) return String(value ?? "0");
  return number.toLocaleString("en-US", { maximumFractionDigits });
}

export function percent(bps) { return `${Number(bps || 0) / 100}%`; }
export function shortHash(value, length = 14) { const text = String(value || ""); return text.length > length ? `${text.slice(0, length)}...` : text; }

export function formatUtc(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value || "Unknown time");
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(date) + " UTC";
}

export function humanStatus(value) {
  if (value === "payment-requirements-created") return "Payment requirements created";
  if (value === "payment-required") return "Requirement prepared";
  if (value === "held") return "Excluded from preparation";
  return String(value || "Unknown").replace(/-/g, " ");
}

export async function copyText(value, button, message = "Copied") {
  await navigator.clipboard.writeText(String(value));
  const original = button.textContent;
  button.textContent = message;
  document.getElementById("global-live").textContent = message;
  window.setTimeout(() => { button.textContent = original; document.getElementById("global-live").textContent = ""; }, 2000);
}

export function downloadJson(receipt, stored = false) {
  const blob = new Blob([`${JSON.stringify(receipt, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = stored ? `/api/receipts/${encodeURIComponent(receipt.receipt_id)}?download=1` : url;
  link.download = `${receipt.receipt_id || "allot-receipt"}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 10000);
}

export function setDraft(value) {
  appState.instructionText = value;
  appState.parsedInstruction = null;
  try { sessionStorage.setItem("allot-draft", value); } catch { /* Draft still works in memory. */ }
}
