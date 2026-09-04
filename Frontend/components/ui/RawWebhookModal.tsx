'use client';

import React, { useState } from 'react';
import { Modal } from './Modal';
import { Button } from './Button';
import { Code, Copy, Check } from 'lucide-react';

export function RawWebhookModal({
  isOpen,
  onClose,
  transactionId = 'TXN-82931',
}: {
  isOpen: boolean;
  onClose: () => void;
  transactionId?: string;
}) {
  const [copied, setCopied] = useState(false);
  const [createdAt] = useState(() => Math.floor(Date.now() / 1000) - 300);

  const rawWebhookJson = {
    entity: "event",
    account_id: "acc_recoverai_prod_001",
    event: "payment.failed",
    contains: ["payment"],
    payload: {
      payment: {
        entity: {
          id: transactionId,
          amount: 1850000, // in paise
          currency: "INR",
          status: "failed",
          order_id: "order_Kj981240192",
          invoice_id: null,
          international: false,
          method: "upi",
          amount_refunded: 0,
          refund_status: null,
          captured: false,
          description: "RecoverAI Premium Subscription Charge",
          card_id: null,
          bank: "HDFC",
          wallet: null,
          vpa: "priya.sharma@okaxis",
          email: "priya.sharma@example.com",
          contact: "+919876543210",
          error_code: "GATEWAY_TIMEOUT",
          error_description: "Temporary HDFC UPI gateway response timeout (>15000ms)",
          error_source: "bank",
          error_step: "payment_authentication",
          error_reason: "bank_technical_error",
          created_at: createdAt
        }
      }
    },
    created_at: createdAt
  };

  const jsonString = JSON.stringify(rawWebhookJson, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <Code className="h-4 w-4 text-ai" />
          <span>Raw Razorpay Webhook Payload ({transactionId})</span>
        </div>
      }
      subtitle="Full JSON telemetry payload received from gateway"
      maxWidth="2xl"
    >
      <div className="space-y-4">
        <div className="relative rounded-lg border border-border bg-bg-dark p-4 font-mono text-xs overflow-x-auto max-h-96">
          <button
            onClick={handleCopy}
            className="absolute top-3 right-3 flex items-center gap-1 rounded bg-surface-elevated px-2 py-1 text-[10px] text-secondaryText hover:text-primaryText border border-border"
          >
            {copied ? <Check className="h-3 w-3 text-success" /> : <Copy className="h-3 w-3" />}
            <span>{copied ? 'Copied' : 'Copy JSON'}</span>
          </button>
          <pre className="text-ai-light leading-relaxed">{jsonString}</pre>
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            Close
          </Button>
          <Button variant="ai" size="sm" onClick={handleCopy}>
            <Copy className="h-3.5 w-3.5" />
            Copy Webhook Payload
          </Button>
        </div>
      </div>
    </Modal>
  );
}
