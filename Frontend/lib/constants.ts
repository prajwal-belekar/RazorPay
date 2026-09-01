export const APP_NAME = "RecoverAI";
export const APP_TAGLINE = "Turn failed payments into recovered revenue.";

export type AppRoute =
  | '/dashboard'
  | '/recovery'
  | '/transactions'
  | '/revenue-radar'
  | '/simulator'
  | '/agents'
  | '/analytics'
  | '/blockchain'
  | '/policies'
  | '/copilot'
  | '/settings';

export interface NavItem {
  label: string;
  href: AppRoute;
  icon: string;
  badge?: string;
}

export interface NavSection {
  category: string;
  items: NavItem[];
}

export const NAV_ITEMS: NavSection[] = [
  {
    category: "OVERVIEW",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: "LayoutDashboard" },
    ],
  },
  {
    category: "REVENUE",
    items: [
      { label: "Recovery", href: "/recovery", icon: "RotateCcw", badge: "12" },
      { label: "Transactions", href: "/transactions", icon: "Receipt" },
      { label: "Revenue Radar", href: "/revenue-radar", icon: "Radar" },
    ],
  },
  {
    category: "INTELLIGENCE",
    items: [
      { label: "Simulator", href: "/simulator", icon: "Cpu" },
      { label: "AI Agents", href: "/agents", icon: "Bot", badge: "3 Active" },
      { label: "Analytics", href: "/analytics", icon: "BarChart3" },
    ],
  },
  {
    category: "TRUST",
    items: [
      { label: "Blockchain", href: "/blockchain", icon: "ShieldCheck" },
      { label: "Policies", href: "/policies", icon: "Sliders" },
    ],
  },
  {
    category: "AI",
    items: [
      { label: "Copilot", href: "/copilot", icon: "Sparkles" },
    ],
  },
  {
    category: "SYSTEM",
    items: [
      { label: "Settings", href: "/settings", icon: "Settings" },
    ],
  },
];

export const DEMO_WORKFLOW_STEPS = [
  { step: 1, name: "Detect", label: "Payment Failed", detail: "TXN-82931 failed on Razorpay (UPI Timeout)" },
  { step: 2, name: "Predict", label: "Risk Detected", detail: "₹18,500 exposed, ₹16,835 recoverable" },
  { step: 3, name: "Reason", label: "AI Analysis", detail: "Ollama LLM evaluating retry windows" },
  { step: 4, name: "Simulate", label: "Digital Twin", detail: "Simulated 4 strategies (Retry + Payment Link optimal)" },
  { step: 5, name: "Validate", label: "Action Firewall", detail: "Verified limits, cooldown, and policy v2.4" },
  { step: 6, name: "Recover", label: "Executing Action", detail: "Triggering Razorpay recovery flow" },
  { step: 7, name: "Prove", label: "Successful Recovery", detail: "₹18,500 recovered successfully" },
  { step: 8, name: "Verify", label: "Blockchain Proof", detail: "Hashing decision to ledger (0x8a91...72fc)" },
  { step: 9, name: "Learn", label: "Merchant DNA Updated", detail: "Updated UPI retry probability model (+1.4%)" },
];
