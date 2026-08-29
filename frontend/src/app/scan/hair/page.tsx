"use client";

import { AuthGate } from "@/components/auth-gate";
import { GuidedCapture } from "@/components/guided-capture";

export default function HairScanPage() {
  return (
    <AuthGate>
      <GuidedCapture domain="hair" />
    </AuthGate>
  );
}
