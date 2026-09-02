"use client";

import { useState } from "react";
import {
  analyzePayment,
  executeRecovery,
} from "@/lib/api/backend";

interface Decision {
  recommended_action: string;
  reason: string;
  confidence: number;
  source?: string;
}

interface AIResponse {
  model: string | null;
  decision: Decision;
  payment_id: number;
}

export default function AITestPage() {
  const [loading, setLoading] = useState(false);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [error, setError] = useState("");

  const [executing, setExecuting] = useState(false);

  const [paymentId, setPaymentId] = useState<number | null>(null);

  const [actionResult, setActionResult] = useState<{
    status: string;
    message: string;
  } | null>(null);

  // -----------------------------
  // AI ANALYSIS
  // -----------------------------
  const testAI = async () => {
    setLoading(true);
    setDecision(null);
    setError("");
    setActionResult(null);

    try {
      const response: AIResponse = await analyzePayment({
        amount: 18500,
        failure_reason: "Bank timeout",
        customer_type: "Returning customer",
      });

      setDecision(response.decision);
      setPaymentId(response.payment_id);
    } catch (err) {
      console.error(err);
      setError("AI analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // -----------------------------
  // EXECUTE RECOVERY
  // -----------------------------
  const handleRecovery = async () => {
    if (!decision) return;

    setExecuting(true);
    setActionResult(null);

    try {
      if (!paymentId) {
          throw new Error("Payment ID is missing");
        }

        const result = await executeRecovery(
          paymentId,
          decision.recommended_action
        );

      setActionResult(result);
    } catch (err) {
      console.error(err);

      setActionResult({
        status: "FAILED",
        message: "Recovery action failed.",
      });
    } finally {
      setExecuting(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center p-8">
      <div className="w-full max-w-2xl rounded-2xl border p-8">

        <h1 className="text-2xl font-bold">
          RecoverAI — AI Test
        </h1>

        {/* Payment Information */}
        <div className="mt-6 rounded-xl border p-5">
          <p>
            <strong>Amount:</strong> ₹18,500
          </p>

          <p className="mt-2">
            <strong>Failure:</strong> Bank timeout
          </p>

          <p className="mt-2">
            <strong>Customer:</strong> Returning customer
          </p>
        </div>

        {/* Analyze Button */}
        <button
          onClick={testAI}
          disabled={loading}
          className="mt-6 rounded-xl border px-6 py-3 font-semibold disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Analyze Payment"}
        </button>

        {/* Error */}
        {error && (
          <div className="mt-6 rounded-xl border p-5">
            {error}
          </div>
        )}

        {/* AI Decision */}
        {decision && (
          <div className="mt-6 rounded-2xl border p-6">

            <p className="text-sm font-medium">
              AI RECOVERY DECISION
            </p>

            <h2 className="mt-4 text-3xl font-bold">
              {decision.recommended_action}
            </h2>

            {/* Decision Source */}
            <div className="mt-3 text-sm opacity-70">
              {decision.source === "RULE_ENGINE"
                ? "⚡ Fast Rule Engine"
                : "🧠 Qwen3 AI Analysis"}
            </div>

            {/* Confidence */}
            <div className="mt-6">
              <div className="flex justify-between text-sm">
                <span>Confidence</span>

                <span>
                  {Math.round(decision.confidence * 100)}%
                </span>
              </div>

              <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
                <div
                  className="h-2 rounded-full bg-black"
                  style={{
                    width: `${decision.confidence * 100}%`,
                  }}
                />
              </div>
            </div>

            {/* Reason */}
            <div className="mt-6">
              <p className="text-sm font-medium">
                Why?
              </p>

              <p className="mt-2 text-sm opacity-80">
                {decision.reason}
              </p>
            </div>

            {/* Execute Recovery */}
            <button
              onClick={handleRecovery}
              disabled={executing}
              className="mt-6 w-full rounded-xl border px-6 py-3 font-semibold disabled:opacity-50"
            >
              {executing
                ? "Executing Recovery..."
                : `Execute ${decision.recommended_action}`}
            </button>

            {/* Recovery Result */}
            {actionResult && (
              <div className="mt-4 rounded-xl border p-4">
                <p className="font-semibold">
                  Recovery Status: {actionResult.status}
                </p>

                <p className="mt-2 text-sm opacity-80">
                  {actionResult.message}
                </p>
              </div>
            )}

          </div>
        )}

      </div>
    </main>
  );
}