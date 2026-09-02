const API_URL = "http://localhost:8000";

export async function checkBackendHealth() {
  const response = await fetch(`${API_URL}/health`);

  if (!response.ok) {
    throw new Error("Backend health check failed");
  }

  return response.json();
}

export interface PaymentAnalysisRequest {
  amount: number;
  failure_reason: string;
  customer_type: string;
}

export async function analyzePayment(
  payment: PaymentAnalysisRequest
) {
  const response = await fetch(`${API_URL}/api/ai/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payment),
  });

  if (!response.ok) {
    throw new Error("AI analysis failed");
  }

  return response.json();
}

export async function executeRecovery(
  paymentId: number,
  action: string
) {
  const response = await fetch(
    "http://127.0.0.1:8000/api/ai/recover",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        payment_id: paymentId,
        action: action,
      }),
    }
  );

  if (!response.ok) {
    throw new Error("Recovery action failed");
  }

  return response.json();
}

export interface Payment {
  id: number;
  amount: number;
  failure_reason: string;
  customer_type: string;
  recommended_action: string;
  reason: string;
  confidence: number;
  decision_source: string | null;
  recovery_status: string;
  retry_count: number;
  created_at: string;
}

export async function getPayments(): Promise<Payment[]> {
  const response = await fetch(
    "http://127.0.0.1:8000/api/ai/payments",
    {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error("Failed to fetch payments");
  }

  return response.json();
}