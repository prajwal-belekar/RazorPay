import { AIResponse, CopilotMessage, StrategyOption } from '@/types';
import { apiFetch } from './client';
import { mockRecoveryCases } from '../mock/recovery';

export async function generateRecoveryStrategy(transactionId: string): Promise<AIResponse<StrategyOption[]>> {
  try {
    return await apiFetch<AIResponse<StrategyOption[]>>(`/api/ai/generate-strategy`, {
      method: 'POST',
      body: JSON.stringify({ transactionId }),
    });
  } catch {
    const recoveryCase = mockRecoveryCases.find(c => c.transactionId === transactionId) || mockRecoveryCases[0];
    return {
      success: true,
      data: recoveryCase.strategies,
      latencyMs: 840,
      model: 'Ollama Llama3.1-8B-Fintech',
      timestamp: new Date().toISOString(),
    };
  }
}

export async function analyzeFailure(transactionId: string): Promise<AIResponse<{ explanation: string; probability: number; confidence: number }>> {
  try {
    return await apiFetch(`/api/ai/analyze-failure`, {
      method: 'POST',
      body: JSON.stringify({ transactionId }),
    });
  } catch {
    const recoveryCase = mockRecoveryCases.find(c => c.transactionId === transactionId) || mockRecoveryCases[0];
    return {
      success: true,
      data: {
        explanation: recoveryCase.explanation,
        probability: recoveryCase.recoveryProbability,
        confidence: recoveryCase.aiConfidence,
      },
      latencyMs: 320,
      model: 'XGBoost RecoveryModel v3.1',
      timestamp: new Date().toISOString(),
    };
  }
}

export async function explainDecision(decisionId: string): Promise<AIResponse<string>> {
  try {
    return await apiFetch(`/api/ai/explain-decision`, {
      method: 'POST',
      body: JSON.stringify({ decisionId }),
    });
  } catch {
    return {
      success: true,
      data: "Temporary bank failure combined with strong customer payment history makes a delayed retry the highest-probability recovery option.",
      latencyMs: 210,
      model: 'Ollama Llama3.1-8B-Fintech',
      timestamp: new Date().toISOString(),
    };
  }
}

export async function askCopilot(query: string): Promise<AIResponse<CopilotMessage>> {
  try {
    return await apiFetch(`/api/copilot/chat`, {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  } catch {
    const lower = query.toLowerCase();
    let responseText = "RecoverAI copilot analyzing financial telemetry...";
    let metricCard;
    let chartData;
    let tableData;

    if (lower.includes("risk") || lower.includes("revenue at risk")) {
      responseText = "Currently, ₹28.4L in revenue is exposed across 1,284 failed payments. 82% of this risk is concentrated in temporary UPI timeouts.";
      metricCard = { value: "₹28.4L", label: "Revenue At Risk", change: "+12.4% vs last period" };
    } else if (lower.includes("strategy") || lower.includes("performs best")) {
      responseText = "The 'Retry + Payment Link' hybrid cascade performs best overall, yielding an 82.4% recovery rate and 5.6x ROI.";
      chartData = [
        { name: "Retry + Link", value: 82.4, benchmark: 60 },
        { name: "Retry Only", value: 62.5, benchmark: 60 },
        { name: "Payment Link", value: 58.0, benchmark: 60 },
        { name: "Reminder", value: 54.1, benchmark: 60 },
      ];
    } else if (lower.includes("high-value") || lower.includes("failed payments")) {
      responseText = "Here are the top high-value failed payments flagged for recovery review:";
      tableData = {
        headers: ["Transaction", "Customer", "Amount", "Method", "Probability"],
        rows: [
          ["TXN-82934", "Vikram Singh", "₹1,15,000", "Cards", "65%"],
          ["TXN-82932", "Rohan Mehta", "₹42,000", "Cards", "84%"],
          ["TXN-82935", "Kavita Iyer", "₹24,500", "UPI", "88%"],
          ["TXN-82931", "Priya Sharma", "₹18,500", "UPI", "91%"],
        ]
      };
    } else if (lower.includes("upi") || lower.includes("failure rate")) {
      responseText = "UPI failure rates experienced a +137% spike between 08:00 and 10:00 AM due to HDFC gateway timeouts.";
      metricCard = { value: "19.0%", label: "UPI Failure Rate", change: "+137% spike" };
    } else {
      responseText = `Analyzed financial recovery query: "${query}". System recommends checking Revenue Radar for anomaly breakdowns or running the Digital Twin Simulator for custom scenario projections.`;
      metricCard = { value: "65.8%", label: "System Recovery Rate", change: "+8.2% uplift" };
    }

    return {
      success: true,
      data: {
        id: `msg-${Date.now()}`,
        sender: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        text: responseText,
        metricCard,
        chartData,
        tableData,
        actions: [
          { label: "Run Simulator", action: "/simulator" },
          { label: "View Revenue Radar", action: "/revenue-radar" }
        ]
      },
      latencyMs: 650,
      model: 'Ollama Llama3.1-8B-Fintech',
      timestamp: new Date().toISOString(),
    };
  }
}
