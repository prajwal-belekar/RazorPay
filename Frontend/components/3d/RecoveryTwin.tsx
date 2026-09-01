'use client';

import React, { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, Line } from '@react-three/drei';
import * as THREE from 'three';
import { StrategyType } from '@/types';

interface StrategyNodeData {
  type: StrategyType;
  label: string;
  pos: [number, number, number];
  color: string;
}

const strategyNodes: StrategyNodeData[] = [
  { type: 'Retry', label: 'Retry', pos: [0, 1.4, 0], color: '#3B82F6' },
  { type: 'Payment Link', label: 'Payment Link', pos: [-1.6, -0.4, 0], color: '#F59E0B' },
  { type: 'Reminder', label: 'Reminder', pos: [1.6, -0.4, 0], color: '#60A5FA' },
  { type: 'Retry + Payment Link', label: 'Hybrid Cascade', pos: [0, -1.5, 0], color: '#8B5CF6' },
];

function TwinScene({
  selectedStrategy,
  onSelect,
}: {
  selectedStrategy: StrategyType;
  onSelect?: (strat: StrategyType) => void;
}) {
  const groupRef = useRef<THREE.Group>(null!);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.15;
    }
  });

  const centerPos: [number, number, number] = [0, 0, 0];

  return (
    <group ref={groupRef}>
      {/* Central Transaction Core */}
      <mesh position={centerPos}>
        <sphereGeometry args={[0.3, 32, 32]} />
        <meshStandardMaterial color="#F5F5F5" emissive="#8B5CF6" emissiveIntensity={0.4} />
      </mesh>

      {/* Orbiting Strategy Nodes */}
      {strategyNodes.map((node) => {
        const isSelected = selectedStrategy === node.type;
        return (
          <group key={node.type}>
            {/* Connecting Ray Line */}
            <Line
              points={[centerPos, node.pos]}
              color={isSelected ? '#8B5CF6' : '#26262B'}
              lineWidth={isSelected ? 3 : 1}
            />

            {/* Strategy Mesh Node */}
            <mesh
              position={node.pos}
              onClick={(e) => {
                e.stopPropagation();
                onSelect?.(node.type);
              }}
            >
              <sphereGeometry args={[isSelected ? 0.26 : 0.18, 24, 24]} />
              <meshStandardMaterial
                color={node.color}
                emissive={node.color}
                emissiveIntensity={isSelected ? 0.8 : 0.3}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

export function RecoveryTwin3D({
  selectedStrategy = 'Retry + Payment Link',
  onSelectStrategy,
  className = 'h-52 w-full',
}: {
  selectedStrategy?: StrategyType;
  onSelectStrategy?: (strat: StrategyType) => void;
  className?: string;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return (
    <div className={`relative ${className}`}>
      <Canvas camera={{ position: [0, 0, 4.2], fov: 45 }}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[3, 3, 3]} intensity={1.2} />
        <TwinScene selectedStrategy={selectedStrategy} onSelect={onSelectStrategy} />
      </Canvas>
    </div>
  );
}
