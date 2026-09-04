'use client';

import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Line, Sphere } from '@react-three/drei';
import * as THREE from 'three';
import { RecoveryStage, getVisualStageIndex, VISUAL_LIFECYCLE_STEPS } from '@/lib/recoveryStages';
import { useHydrated } from '@/hooks/use-hydrated';

const pipelineNodes = [
  { name: 'DETECT', pos: [-4.0, 0.1, 0] as [number, number, number], color: '#F59E0B' },
  { name: 'ANALYZE', pos: [-3.0, -0.2, 0] as [number, number, number], color: '#3B82F6' },
  { name: 'PREDICT', pos: [-2.0, 0.3, 0] as [number, number, number], color: '#8B5CF6' },
  { name: 'SIMULATE', pos: [-1.0, -0.1, 0] as [number, number, number], color: '#A855F7' },
  { name: 'VALIDATE', pos: [0.0, 0.2, 0] as [number, number, number], color: '#10B981' },
  { name: 'EXECUTE', pos: [1.0, -0.2, 0] as [number, number, number], color: '#F59E0B' },
  { name: 'RECOVER', pos: [2.0, 0.3, 0] as [number, number, number], color: '#10B981' },
  { name: 'PROVE', pos: [3.0, -0.1, 0] as [number, number, number], color: '#6366F1' },
  { name: 'LEARN', pos: [4.0, 0.1, 0] as [number, number, number], color: '#10B981' },
];

function TravelingParticle({ activeStep = 0 }: { activeStep?: number }) {
  const particleRef = useRef<THREE.Mesh>(null!);
  const [progress, setProgress] = useState(0);

  useFrame((_, delta) => {
    setProgress((prev) => (prev + delta * 0.5) % 1);
    if (particleRef.current && pipelineNodes.length > 1) {
      const totalSegments = pipelineNodes.length - 1;
      const scaledProgress = progress * totalSegments;
      const currentSegment = Math.floor(scaledProgress);
      const segmentProgress = scaledProgress - currentSegment;

      const p1 = pipelineNodes[currentSegment].pos;
      const p2 = pipelineNodes[Math.min(currentSegment + 1, totalSegments)].pos;

      particleRef.current.position.x = p1[0] + (p2[0] - p1[0]) * segmentProgress;
      particleRef.current.position.y = p1[1] + (p2[1] - p1[1]) * segmentProgress;
      particleRef.current.position.z = p1[2] + (p2[2] - p1[2]) * segmentProgress;
    }
  });

  return (
    <mesh ref={particleRef}>
      <sphereGeometry args={[0.08, 16, 16]} />
      <meshBasicMaterial color="#ffffff" />
    </mesh>
  );
}

function PipelineScene({ activeStep = 0 }: { activeStep?: number }) {
  const points = pipelineNodes.map((n) => n.pos);

  return (
    <group>
      {/* Node Spheres */}
      {pipelineNodes.map((node, idx) => {
        const isActive = idx <= activeStep;
        const isCurrent = idx === activeStep;
        return (
          <group key={idx} position={node.pos}>
            <Sphere args={[isCurrent ? 0.22 : 0.15, 16, 16]}>
              <meshStandardMaterial
                color={node.color}
                emissive={node.color}
                emissiveIntensity={isCurrent ? 0.8 : isActive ? 0.4 : 0.1}
              />
            </Sphere>
          </group>
        );
      })}

      {/* Connecting Line */}
      <Line
        points={points}
        color="#26262B"
        lineWidth={2}
      />

      {/* Traveling Data Packet */}
      <TravelingParticle activeStep={activeStep} />
    </group>
  );
}

export function RevenuePipeline3D({
  activeStep,
  stage,
  className = 'h-28 w-full',
}: {
  activeStep?: number;
  stage?: RecoveryStage;
  className?: string;
}) {
  const mounted = useHydrated();

  const visualStep = stage !== undefined ? getVisualStageIndex(stage) : (activeStep ?? 0);

  if (!mounted) return null;

  return (
    <div className={`relative ${className}`}>
      <Canvas camera={{ position: [0, 0, 5.5], fov: 45 }}>
        <ambientLight intensity={0.8} />
        <pointLight position={[0, 5, 5]} intensity={1.0} />
        <PipelineScene activeStep={visualStep} />
      </Canvas>
    </div>
  );
}
