"use client";

import { AuthGate } from "@/components/auth-gate";
import { GuidedCapture } from "@/components/guided-capture";

export default function SkinScanPage() {
  return (
    <AuthGate>
      <GuidedCapture domain="skin" />
    </AuthGate>
  );
}
