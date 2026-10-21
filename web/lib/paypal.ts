/**
 * PayPal JavaScript SDK v6 helpers for the checkout work stream.
 *
 * How v6 works (verified against PayPal's docs, 2026-10):
 *  - Load the core script: sandbox https://www.sandbox.paypal.com/web-sdk/v6/core,
 *    production https://www.paypal.com/web-sdk/v6/core. No client-id in the URL.
 *    https://developer.paypal.com/sdk/js/set-up/
 *  - `await window.paypal.createInstance({ clientId | clientToken, components: ["paypal-payments"], pageType })`.
 *    The public clientId is PayPal's recommended path; a browser-safe client token (server-generated with
 *    `response_type=client_token`, see backend/api/paypal_sdk.py) also works and is our fallback.
 *  - `await sdk.findEligibleMethods({ currencyCode })` then `.isEligible("paypal")`.
 *  - `sdk.createPayPalOneTimePaymentSession({ onApprove, onCancel, onError })`.
 *  - On the `<paypal-button>` click: `session.start({ presentationMode: "auto" }, orderPromise)`, where
 *    `orderPromise` resolves to `{ orderId }`. Our order is ALREADY created by the server after brand
 *    verification, so we pass `Promise.resolve({ orderId })`. The browser never creates an order.
 *    https://docs.paypal.ai/reference/sdk/js/v6/reference
 *  - `onApprove({ orderId, payerId })` -> our server captures (`POST /checkout/{checkout_id}/capture`).
 */
import { api } from "@/lib/api";

export type PayPalMode = "mock" | "sandbox" | "live" | string;

export type SdkConfig = {
  mode: PayPalMode;
  client_id: string | null;
  currency: string;
  sdk_url: string | null;
};

export type ClientTokenResponse = { mode: PayPalMode; client_token: string; expires_in: number };

export type Receipt = {
  checkout_id: string;
  store_id: string;
  store_name: string;
  product: string;
  sku: string;
  serial: string;
  amount: number;
  verification_id: string | null;
  paypal_order_id: string | null;
  status: "AWAITING_PAYMENT" | "CAPTURED" | "BLOCKED" | string;
  brand_verified: boolean;
  created_at?: string;
};

// ---------------------------------------------------------------- v6 SDK surface we use
// PayPal ships no separate TS types for v6 that we can rely on here, so we type only what we call.
// Shapes from https://docs.paypal.ai/reference/sdk/js/v6/reference

export type OnApproveData = { orderId: string; payerId?: string; paymentId?: string };
export type OnCancelData = { orderId?: string };
export type PayPalSdkError = { code?: string; message?: string };

export type PresentationMode = "auto" | "popup" | "modal" | "redirect" | "payment-handler";

export interface PayPalOneTimePaymentSession {
  start(
    options: { presentationMode: PresentationMode },
    orderPromise: Promise<{ orderId: string }>,
  ): Promise<unknown>;
  destroy?: () => void;
  cancel?: () => void;
}

export interface PayPalSdkInstance {
  findEligibleMethods(opts: { currencyCode: string; countryCode?: string; amount?: string }): Promise<{
    isEligible(method: string): boolean;
  }>;
  createPayPalOneTimePaymentSession(opts: {
    onApprove: (data: OnApproveData) => Promise<void> | void;
    onCancel?: (data: OnCancelData) => void;
    onError?: (error: PayPalSdkError) => void;
  }): PayPalOneTimePaymentSession;
}

export interface PayPalNamespace {
  createInstance(opts: {
    clientId?: string;
    clientToken?: string;
    components: string[];
    pageType?: string;
    locale?: string;
  }): Promise<PayPalSdkInstance>;
}

declare global {
  interface Window {
    paypal?: PayPalNamespace;
  }
}

// `<paypal-button>` is a custom element registered by the SDK; we create it with
// document.createElement (as PayPal's examples do) so React never needs JSX types for it.

// ---------------------------------------------------------------- server calls

export const getSdkConfig = () => api<SdkConfig>("/paypal/sdk/config");
export const getClientToken = () => api<ClientTokenResponse>("/paypal/sdk/client-token");
export const getReceipt = (checkoutId: string) => api<Receipt>(`/receipts/${checkoutId}`);
export const capture = (checkoutId: string) =>
  api<Receipt>(`/checkout/${checkoutId}/capture`, { method: "POST" });

// ---------------------------------------------------------------- loader

let scriptPromise: Promise<PayPalNamespace> | null = null;

export function loadPayPalSdk(src: string): Promise<PayPalNamespace> {
  if (typeof window === "undefined") return Promise.reject(new Error("PayPal SDK is browser-only"));
  if (window.paypal) return Promise.resolve(window.paypal);
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise<PayPalNamespace>((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = () => (window.paypal ? resolve(window.paypal) : reject(new Error("PayPal SDK loaded without window.paypal")));
    s.onerror = () => {
      scriptPromise = null;
      s.remove();
      reject(new Error("Could not load the PayPal SDK"));
    };
    document.head.appendChild(s);
  });
  return scriptPromise;
}

let instancePromise: Promise<PayPalSdkInstance> | null = null;

/** One SDK instance per page load. Uses the public client ID, falling back to a server client token. */
export function getPayPalInstance(cfg: SdkConfig): Promise<PayPalSdkInstance> {
  if (instancePromise) return instancePromise;
  instancePromise = (async () => {
    if (!cfg.sdk_url) throw new Error("PayPal SDK URL missing (mock mode?)");
    const paypal = await loadPayPalSdk(cfg.sdk_url);
    const auth = cfg.client_id
      ? { clientId: cfg.client_id }
      : { clientToken: (await getClientToken()).client_token };
    return paypal.createInstance({ ...auth, components: ["paypal-payments"], pageType: "checkout" });
  })().catch((e) => {
    instancePromise = null;
    throw e;
  });
  return instancePromise;
}

/** Turn API errors (`409 {"detail": ...}`) into one readable line. */
export function readableError(e: unknown): string {
  const raw = e instanceof Error ? e.message : String(e);
  const m = raw.match(/^(\d{3}) (.*)$/s);
  if (!m) return raw;
  try {
    const body = JSON.parse(m[2]);
    const d = body?.detail;
    if (typeof d === "string") return d;
    if (d) return JSON.stringify(d);
  } catch {
    /* not JSON */
  }
  return `Server error ${m[1]}`;
}

export function money(amount: number | string, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(Number(amount));
}
