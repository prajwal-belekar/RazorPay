'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { fadeIn, slideUp, staggerContainer, pageTransition, scaleIn } from '@/lib/animations';

export function FadeIn({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={fadeIn}
      transition={{ delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function SlideUp({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={slideUp}
      transition={{ delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerContainer({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={staggerContainer}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function PageTransition({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={pageTransition}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StatusPulse({
  color = 'bg-success',
  ping = true,
}: {
  color?: string;
  ping?: boolean;
}) {
  return (
    <span className="relative flex h-2 w-2">
      {ping && (
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${color} opacity-75`} />
      )}
      <span className={`relative inline-flex rounded-full h-2 w-2 ${color}`} />
    </span>
  );
}

export function SuccessAnimation({
  text = '₹18,500 Recovered',
  subtitle = 'Verified on Blockchain',
}: {
  text?: string;
  subtitle?: string;
}) {
  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.35, ease: [0.34, 1.56, 0.64, 1] }}
      className="flex items-center gap-3 p-3.5 rounded-xl bg-success-bg border border-success-border text-success shadow-subtle"
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-success text-black font-bold text-sm">
        ✓
      </div>
      <div>
        <h4 className="font-bold text-sm text-primaryText font-mono">{text}</h4>
        <p className="text-[11px] text-success/90">{subtitle}</p>
      </div>
    </motion.div>
  );
}
