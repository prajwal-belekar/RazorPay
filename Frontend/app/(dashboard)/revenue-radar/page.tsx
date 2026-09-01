'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { formatCurrency } from '@/lib/formatters';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  CartesianGrid
} from 'recharts';
import { Radar, AlertTriangle, ArrowUpRight, Cpu } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function RevenueRadarPage() {
  const router = useRouter();

  const trendData = [
    { time: '00:00', UPI: 4, Cards: 6, NetBanking: 3, Wallet: 2 },
    { time: '04:00', UPI: 5, Cards: 5, NetBanking: 4, Wallet: 2 },
    { time: '08:00', UPI: 19, Cards: 8, NetBanking: 6, Wallet: 3 }, // Spike
    { time: '12:00', UPI: 12, Cards: 11, NetBanking: 7, Wallet: 4 },
    { time: '16:00', UPI: 9, Cards: 7, NetBanking: 5, Wallet: 3 },
    { time: '20:00', UPI: 7, Cards: 6, NetBanking: 4, Wallet: 2 },
  ];

  const distributionData = [
    { name: 'UPI', value: 48, color: '#8B5CF6' },
    { name: 'Cards', value: 31, color: '#3B82F6' },
    { name: 'Net Banking', value: 14, color: '#F59E0B' },
    { name: 'Wallet', value: 7, color: '#10B981' },
  ];

  const heatmap = [
    { method: 'UPI', morning: 'HIGH (19%)', afternoon: 'MEDIUM (12%)', evening: 'LOW (7%)', night: 'LOW (4%)' },
    { method: 'Cards', morning: 'MEDIUM (8%)', afternoon: 'HIGH (14%)', evening: 'MEDIUM (7%)', night: 'LOW (5%)' },
    { method: 'Net Banking', morning: 'MEDIUM (6%)', afternoon: 'MEDIUM (7%)', evening: 'LOW (4%)', night: 'LOW (3%)' },
    { method: 'Wallet', morning: 'LOW (3%)', afternoon: 'LOW (4%)', evening: 'LOW (2%)', night: 'LOW (2%)' },
  ];

  const anomalyTimeline = [
    {
      time: '09:10 AM',
      title: 'UPI Payment Failure Spike',
      change: '+137%',
      risk: 320000,
      confidence: 94,
      method: 'UPI',
      severity: 'HIGH',
      action: 'Apply 15-min delayed retry with dynamic fallback payment link',
    },
    {
      time: '11:42 AM',
      title: 'Card Decline Rate Increase',
      change: '+42%',
      risk: 180000,
      confidence: 88,
      method: 'Cards',
      severity: 'MEDIUM',
      action: 'Switch gateway routing to secondary ICICI acquiring channel',
    },
    {
      time: '01:05 PM',
      title: 'Bank Timeout Anomaly',
      change: '+64%',
      risk: 95000,
      confidence: 91,
      method: 'Net Banking',
      severity: 'MEDIUM',
      action: 'Issue soft push reminder with OTP refresh token',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-primaryText">
              Revenue Leak Radar
            </h1>
            <Badge variant="warning">Anomaly Detection Active</Badge>
          </div>
          <p className="text-xs sm:text-sm text-secondaryText mt-1">
            Real-time pattern recognition identifying abnormal payment drops and gateway outages.
          </p>
        </div>

        <span className="font-mono text-xs text-warning flex items-center gap-1.5">
          <Radar className="h-4 w-4 animate-spin text-warning" />
          3 Active Anomaly Clusters
        </span>
      </div>

      {/* Grid: Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Failure Rate Trend */}
        <Card className="lg:col-span-8 p-5">
          <CardHeader className="p-0 pb-4 border-b border-border/60">
            <CardTitle className="text-sm">Failure Rate Trend by Payment Method</CardTitle>
          </CardHeader>
          <CardContent className="p-0 pt-6">
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#26262B" vertical={false} />
                  <XAxis dataKey="time" stroke="#A1A1AA" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#A1A1AA" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#17171A', borderColor: '#26262B', borderRadius: '8px' }}
                  />
                  <Line type="monotone" dataKey="UPI" stroke="#8B5CF6" strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="Cards" stroke="#3B82F6" strokeWidth={2} />
                  <Line type="monotone" dataKey="NetBanking" stroke="#F59E0B" strokeWidth={2} />
                  <Line type="monotone" dataKey="Wallet" stroke="#10B981" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Payment Method Distribution */}
        <Card className="lg:col-span-4 p-5 flex flex-col justify-between">
          <CardHeader className="p-0 pb-4 border-b border-border/60">
            <CardTitle className="text-sm">Payment Failure Distribution</CardTitle>
          </CardHeader>
          <CardContent className="p-0 pt-4 flex-1 flex flex-col items-center justify-center">
            <div className="h-44 w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={distributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {distributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="grid grid-cols-2 gap-2 w-full pt-2 text-xs font-mono">
              {distributionData.map((d, i) => (
                <div key={i} className="flex items-center justify-between p-1.5 rounded bg-surface-elevated/60">
                  <span className="flex items-center gap-1.5 text-secondaryText">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: d.color }} />
                    {d.name}
                  </span>
                  <span className="font-bold text-primaryText">{d.value}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Failure Heatmap */}
      <Card className="p-5">
        <CardHeader className="p-0 pb-4 border-b border-border/60">
          <CardTitle className="text-sm">Failure Intensity Heatmap (Time of Day vs Gateway)</CardTitle>
        </CardHeader>
        <CardContent className="p-0 pt-4 overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="text-secondaryText font-mono border-b border-border">
              <tr>
                <th className="py-2.5 px-3">Payment Method</th>
                <th className="py-2.5 px-3">Morning (06-12)</th>
                <th className="py-2.5 px-3">Afternoon (12-18)</th>
                <th className="py-2.5 px-3">Evening (18-24)</th>
                <th className="py-2.5 px-3">Night (00-06)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40 font-mono">
              {heatmap.map((row, idx) => (
                <tr key={idx}>
                  <td className="py-3 px-3 font-bold text-primaryText">{row.method}</td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-1 rounded ${row.morning.includes('HIGH') ? 'bg-danger-bg text-danger font-bold border border-danger-border' : 'bg-surface-elevated text-secondaryText'}`}>
                      {row.morning}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-1 rounded ${row.afternoon.includes('HIGH') ? 'bg-danger-bg text-danger font-bold border border-danger-border' : 'bg-surface-elevated text-secondaryText'}`}>
                      {row.afternoon}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-1 rounded bg-surface-elevated text-secondaryText">{row.evening}</span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-1 rounded bg-surface-elevated text-secondaryText">{row.night}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Anomaly Timeline */}
      <Card className="p-0">
        <CardHeader className="flex flex-row items-center justify-between border-b border-border/60 pb-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-warning" />
            <CardTitle>Detected Anomaly Timeline</CardTitle>
          </div>
          <span className="text-xs font-mono text-mutedText">3 Flags Today</span>
        </CardHeader>

        <CardContent className="p-4 space-y-3">
          {anomalyTimeline.map((item, idx) => (
            <div
              key={idx}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-lg border border-warning-border/40 bg-surface-elevated/40 text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-primaryText text-sm">{item.title}</span>
                  <Badge variant="warning">{item.severity}</Badge>
                  <span className="font-mono text-danger font-bold">{item.change}</span>
                </div>
                <p className="text-secondaryText text-xs">
                  <strong>Recommended Action:</strong> {item.action}
                </p>
                <div className="flex items-center gap-4 text-[11px] font-mono text-mutedText pt-1">
                  <span>Detected: {item.time}</span>
                  <span>Method: {item.method}</span>
                  <span>Confidence: {item.confidence}%</span>
                </div>
              </div>

              <div className="flex flex-col sm:items-end gap-2 shrink-0">
                <div className="font-mono text-warning font-bold text-base">
                  {formatCurrency(item.risk)} At Risk
                </div>
                <Button
                  variant="ai"
                  size="sm"
                  onClick={() => router.push(`/simulator?risk=${item.risk}`)}
                >
                  <Cpu className="h-3.5 w-3.5" />
                  Simulate
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
