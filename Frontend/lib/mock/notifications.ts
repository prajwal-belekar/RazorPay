import { NotificationItem } from '@/types';

export const mockNotifications: NotificationItem[] = [
  {
    id: 'NOTIF-1',
    title: 'Revenue Anomaly Detected',
    message: 'UPI payment failure rate increased by 137% on HDFC gateway. Estimated ₹3.2L at risk.',
    timestamp: '10 minutes ago',
    type: 'anomaly',
    read: false,
    actionUrl: '/revenue-radar',
    actionText: 'Inspect Radar',
  },
  {
    id: 'NOTIF-2',
    title: 'Recovery Successful',
    message: '₹18,500 successfully recovered for TXN-82931 via 15-min delayed retry strategy.',
    timestamp: '15 minutes ago',
    type: 'recovery',
    read: false,
    actionUrl: '/recovery/REC-18291',
    actionText: 'View Case',
  },
  {
    id: 'NOTIF-3',
    title: 'Blockchain Proof Verified',
    message: 'Decision proof 0x8a91...72fc confirmed on Polygon Devnet (Block #18294021).',
    timestamp: '16 minutes ago',
    type: 'blockchain',
    read: true,
    actionUrl: '/blockchain',
    actionText: 'View Proof',
  },
  {
    id: 'NOTIF-4',
    title: 'High-Value Recovery Pending Approval',
    message: 'TXN-82934 (₹1,15,000) requires human sign-off as it exceeds autonomous limit (₹50k).',
    timestamp: '2 hours ago',
    type: 'policy',
    read: true,
    actionUrl: '/recovery/REC-18294',
    actionText: 'Review Action',
  },
];
