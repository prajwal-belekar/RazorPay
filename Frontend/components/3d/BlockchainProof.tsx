'use client';

import React, { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Box, Line } from '@react-three/drei';
import * as THREE from 'three';

const blocks = [
  { name: 'Decision', pos: [-2.4, 0, 0] as [number, number, number], color: '#8B5CF6' },
  { name: 'Policy', pos: [-1.2, 0, 0] as [number, number, number], color: '#3B82F6' },
  { name: 'Action', pos: [0, 0, 0] as [number, number, number], color: '#F59E0B' },
  { name: 'Result', pos: [1.2, 0, 0] as [number, number, number], color: '#10B981' },
  { name: 'Proof', pos: [2.4, 0, 0] as [number, number, number], color: '#10B981' },
];

function BlockChainScene() {
  const groupRef = useRef<THREE.Group>(null!);
  const [pulsePos, setPulsePos] = useState(-2.4);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.2;
    }
    setPulsePos((prev) => (prev > 2.4 ? -2.4 : prev + delta * 2.5));
  });

  return (
    <group ref={groupRef}>
      {/* Block Sequence Cubes */}
      {blocks.map((block, idx) => (
        <group key={idx} position={block.pos}>
          <Box args={[0.45, 0.45, 0.45]}>
            <meshStandardMaterial
              color={block.color}
              wireframe={false}
              metalness={0.7}
              roughness={0.2}
              emissive={block.color}
              emissiveIntensity={0.3}
            />
          </Box>
        </group>
      ))}

      {/* Connecting Chain Axis */}
      <Line
        points={[[-2.4, 0, 0], [2.4, 0, 0]]}
        color="#3A3A42"
        lineWidth={2}
      />

      {/* Verification Pulse Signal */}
      <mesh position={[pulsePos, 0, 0]}>
        <sphereGeometry args={[0.1, 16, 16]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
    </group>
  );
}

export function BlockchainProof3D({
  className = 'h-36 w-full',
}: {
  className?: string;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return (
    <div className={`relative ${className}`}>
      <Canvas camera={{ position: [0, 0, 4.0], fov: 45 }}>
        <ambientLight intensity={0.8} />
        <directionalLight position={[2, 4, 3]} intensity={1.2} />
        <BlockChainScene />
      </Canvas>
    </div>
  );
}
