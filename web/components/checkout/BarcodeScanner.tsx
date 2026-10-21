"use client";
import { useEffect, useRef, useState } from "react";
import type { IScannerControls } from "@zxing/browser";
import s from "./checkout.module.css";

/**
 * Camera barcode scanner (Code128, QR, DataMatrix and the other formats BrowserMultiFormatReader supports).
 * Client-only: @zxing/browser is imported inside the effect. The camera stops on detect, close or unmount.
 */
export default function BarcodeScanner({ onDetected, onClose }: {
  onDetected: (text: string) => void;
  onClose: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [message, setMessage] = useState("Requesting camera permission…");
  const [failed, setFailed] = useState(false);
  const detectedRef = useRef(onDetected);
  detectedRef.current = onDetected;

  useEffect(() => {
    let controls: IScannerControls | null = null;
    let cancelled = false;

    (async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setFailed(true);
        setMessage("This browser can't use the camera here (camera needs HTTPS or localhost). Type the serial instead.");
        return;
      }
      try {
        const { BrowserMultiFormatReader } = await import("@zxing/browser");
        if (cancelled || !videoRef.current) return;
        const reader = new BrowserMultiFormatReader();
        const c = await reader.decodeFromConstraints(
          { video: { facingMode: { ideal: "environment" } }, audio: false },
          videoRef.current,
          (result, _err, ctl) => {
            if (!result) return;
            const text = result.getText().trim();
            if (!text) return;
            ctl.stop();
            detectedRef.current(text);
          },
        );
        if (cancelled) c.stop();
        else {
          controls = c;
          setMessage("Point the camera at the serial barcode or QR code.");
        }
      } catch (e) {
        if (cancelled) return;
        const name = (e as { name?: string })?.name;
        setFailed(true);
        setMessage(
          name === "NotAllowedError" ? "Camera permission was denied. Type the serial instead."
            : name === "NotFoundError" ? "No camera found. Type the serial instead."
              : "Couldn't start the camera. Type the serial instead.",
        );
      }
    })();

    return () => {
      cancelled = true;
      controls?.stop();
    };
  }, []);

  return (
    <div>
      {!failed && (
        <div className={s.scanner}>
          <video ref={videoRef} muted playsInline aria-label="Camera preview for barcode scanning" />
          <div className={s.reticle} />
          <div className={s.scannerBar}>
            <span className="muted">{message}</span>
            <button type="button" className={s.ghost} onClick={onClose}>Stop camera</button>
          </div>
        </div>
      )}
      {failed && (
        <div className={s.info} role="status">
          {message} <button type="button" className={s.ghost} onClick={onClose}>OK</button>
        </div>
      )}
    </div>
  );
}
