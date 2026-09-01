'use client';

import React, { useEffect, useState } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

export function AnimatedNumber({
  value,
  formatter = (v) => v.toFixed(0),
  className,
}: {
  value: number;
  formatter?: (val: number) => string;
  className?: string;
}) {
  const spring = useSpring(value, { mass: 0.8, stiffness: 75, damping: 15 });
  const [displayValue, setDisplayValue] = useState(formatter(value));

  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  useEffect(() => {
    return spring.on('change', (latest) => {
      setDisplayValue(formatter(latest));
    });
  }, [spring, formatter]);

  return <span className={className}>{displayValue}</span>;
}
