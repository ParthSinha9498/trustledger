"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import {
  capture, getPayPalInstance, payWithTestCard, getSdkConfig, readableError,
  type OnApproveData, type PayPalSdkError, type Receipt, type SdkConfig,
} from "@/lib/paypal";
import s from "./checkout.module.css";

type Phase = "loading" | "ready" | "paying" | "capturing" | "done" | "unavailable";

/**
 * Pays for an order the SERVER already created (after brand verification). Never creates an order.
 *
 * Sandbox/live: PayPal JS SDK v6 one-time payment session, started from a `<paypal-button>` click with
 * `Promise.resolve({ orderId })`. https://developer.paypal.com/sdk/js/set-up/
 * Sandbox with a test card configured: a primary "Pay with test card (sandbox)" button; the server confirms the
 * same order with a PayPal sandbox test card and captures it (no login). The PayPal button stays as the second option.
 * Mock: a plainly labelled mock button that captures directly.
 */
export default function PayPalPay({ checkoutId, paypalOrderId, onPaid }: {
  checkoutId: string;
  paypalOrderId: string;
  onPaid: (receipt: Receipt) => void;
}) {
  const [cfg, setCfg] = useState<SdkConfig | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const slotRef = useRef<HTMLDivElement>(null);
  const paidRef = useRef(onPaid);
  paidRef.current = onPaid;

  async function doCapture() {
    setPhase("capturing"); setError(null); setInfo(null);
    try {
      const receipt = await capture(checkoutId);
      setPhase("done");
      paidRef.current(receipt);
    } catch (e) {
      setError(`Payment approved but capture failed: ${readableError(e)}`);
      setPhase("ready");
    }
  }
  const [cardOff, setCardOff] = useState(false);
  const [cardPaying, setCardPaying] = useState(false);
  const cardBusy = useRef(false);

  async function doTestCard() {
    if (cardBusy.current) return; // no double submit
    cardBusy.current = true;
    setCardPaying(true);
    setPhase("capturing"); setError(null); setInfo(null);
    try {
      const receipt = await payWithTestCard(checkoutId);
      setPhase("done");
      paidRef.current(receipt);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 503 || e.status === 403)) setCardOff(true);
      setError(`Test card payment failed: ${readableError(e)}`);
      setPhase("ready");
      setCardPaying(false);
      cardBusy.current = false;
    }
  }

  const captureRef = useRef(doCapture);
  captureRef.current = doCapture;

  useEffect(() => {
    getSdkConfig().then(setCfg).catch((e) => {
      setError(`Couldn't load PayPal settings: ${readableError(e)}`);
      setPhase("unavailable");
    });
  }, []);

  // Sandbox/live: render the v6 button once config is known.
  useEffect(() => {
    if (!cfg) return;
    if (cfg.mode === "mock") { setPhase("ready"); return; }
    let cancelled = false;
    let button: HTMLElement | null = null;
    let onClick: (() => void) | null = null;

    (async () => {
      try {
        const sdk = await getPayPalInstance(cfg);
        const methods = await sdk.findEligibleMethods({ currencyCode: cfg.currency || "USD", countryCode: "US" });
        if (cancelled) return;
        if (!methods.isEligible("paypal")) {
          setError("PayPal isn't available for this buyer or currency.");
          setPhase("unavailable");
          return;
        }
        const session = sdk.createPayPalOneTimePaymentSession({
          onApprove: async (data: OnApproveData) => {
            if (data.orderId && data.orderId !== paypalOrderId) {
              setError("PayPal approved a different order than this checkout. Not capturing.");
              setPhase("ready");
              return;
            }
            await captureRef.current();
          },
          onCancel: () => {
            setInfo("Payment cancelled. Nothing was charged. You can try again.");
            setPhase("ready");
          },
          onError: (err: PayPalSdkError) => {
            setError(`PayPal error${err?.code ? ` (${err.code})` : ""}: ${err?.message ?? "unknown"}`);
            setPhase("ready");
          },
        });
        button = document.createElement("paypal-button");
        button.setAttribute("type", "pay");
        button.setAttribute("currency", cfg.currency || "USD");
        button.setAttribute("buyer-country", "US");
        button.setAttribute("locale", "en_US");
        button.className = "paypal-gold";
        onClick = () => {
          setError(null); setInfo(null); setPhase("paying");
          // Order already exists server-side; start() must be called synchronously in the click handler.
          session.start({ presentationMode: "auto" }, Promise.resolve({ orderId: paypalOrderId }))
            .catch((e: unknown) => { setError(`Couldn't open PayPal: ${readableError(e)}`); setPhase("ready"); });
        };
        button.addEventListener("click", onClick);
        slotRef.current?.replaceChildren(button);
        setPhase("ready");
      } catch (e) {
        if (cancelled) return;
        setError(`Couldn't start PayPal: ${readableError(e)}`);
        setPhase("unavailable");
      }
    })();

    return () => {
      cancelled = true;
      if (button && onClick) button.removeEventListener("click", onClick);
      button?.remove();
    };
  }, [cfg, paypalOrderId]);

  const busy = phase === "paying" || phase === "capturing" || phase === "done";
  const isMock = cfg?.mode === "mock";
  const showCard = cfg?.mode === "sandbox" && cfg.test_card === true && !cardOff;

  return (
    <div>
      {isMock ? (
        <>
          <button type="button" className={s.mockPay} onClick={doCapture} disabled={busy || phase === "loading"}>
            {phase === "capturing" ? "Capturing…" : "Demo payment (sandbox off)"}
          </button>
          <p className={s.note}>Mock mode: no PayPal account involved. The button captures order {paypalOrderId} directly.</p>
        </>
      ) : (
        <>
          {showCard && (
            <div className={s.testCard}>
              <button type="button" className={`${s.primary} ${s.testCardBtn}`} onClick={doTestCard}
                disabled={busy || phase === "loading"} aria-busy={cardPaying}>
                {cardPaying ? "Paying with test card…" : "Pay with test card (sandbox)"}
              </button>
              <p className={s.note}>Sandbox test card, no login, no real money.</p>
              <p className={s.orDivider}><span>or pay with a PayPal sandbox account</span></p>
            </div>
          )}
          <div ref={slotRef} className={s.paypalSlot} aria-busy={phase === "loading"} />
          {phase === "loading" && <p className={s.note}>Loading PayPal…</p>}
          {phase === "paying" && <p className={s.note}>Waiting for the buyer to approve in PayPal…</p>}
          {phase === "capturing" && !cardPaying && <p className={s.note}>Approved. Capturing payment…</p>}
          {cfg && <p className={s.note}>PayPal {cfg.mode}. Order {paypalOrderId} was created by the server after brand verification.</p>}
        </>
      )}
      {info && <div className={s.info} role="status">{info}</div>}
      {error && <div className={s.error} role="alert">{error}</div>}
    </div>
  );
}
