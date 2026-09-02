"use client";

import { useEffect, useState } from "react";
import { checkBackendHealth } from "@/lib/api/backend";

export default function BackendTestPage() {
  const [status, setStatus] = useState("Checking backend...");

  useEffect(() => {
    checkBackendHealth()
      .then((data) => {
        setStatus(`Backend: ${data.status}`);
      })
      .catch(() => {
        setStatus("Backend connection failed");
      });
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="rounded-xl border p-8">
        <h1 className="text-2xl font-bold">RecoverAI Backend Test</h1>
        <p className="mt-4">{status}</p>
      </div>
    </main>
  );
}