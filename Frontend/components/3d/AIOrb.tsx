'use client';

import React, { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, MeshWobbleMaterial } from '@react-three/drei';
import * as THREE from 'three';
import { RecoveryStage, getStageMetadata } from '@/lib/recoveryStages';

function InnerCore({ stage, prefersReducedMotion }: { stage: RecoveryStage; prefersReducedMotion: boolean }) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const outerWireRef = useRef<THREE.Mesh>(null!);
  const ringRef = useRef<THREE.Mesh>(null!);

  const stageMeta = getStageMetadata(stage);

  useFrame((_, delta) => {
    if (prefersReducedMotion) return;

    if (meshRef.current) {
      let speedMultiplier = 0.6;
      if (stage === 'detecting') speedMultiplier = 2.0;
      if (stage === 'executing') speedMultiplier = 3.2;
      if (stage === 'analyzing' || stage === 'simulating') speedMultiplier = 1.4;

      meshRef.current.rotation.y += delta * 0.4 * speedMultiplier;
      meshRef.current.rotation.x += delta * 0.2 * speedMultiplier;
    }

    if (outerWireRef.current) {
      outerWireRef.current.rotation.y -= delta * 0.2;
      outerWireRef.current.rotation.z += delta * 0.15;
    }

    if (ringRef.current) {
      const ringSpeed = stage === 'validating' ? 2.5 : stage === 'verified' ? 0.3 : 1.2;
      ringRef.current.rotation.z += delta * ringSpeed;
    }
  });

  const getCoreColor = () => {
    switch (stage) {
      case 'detecting':
        return '#F59E0B'; // Amber
      case 'analyzing':
      case 'predicting':
        return '#3B82F6'; // Info blue
      case 'simulating':
      case 'validating':
        return '#8B5CF6'; // Violet
      case 'executing':
        return '#EAB308'; // Warning gold
      case 'recovered':
      case 'learning':
        return '#10B981'; // Emerald
      case 'verified':
        return '#6366F1'; // Indigo
      case 'failed':
        return '#EF4444'; // Red
      default:
        return '#8B5CF6';
    }
  };

  const coreColor = getCoreColor();

  return (
    <group>
      {/* Central AI Sphere */}
      <Sphere ref={meshRef} args={[1, 32, 32]}>
        <MeshWobbleMaterial
          color={coreColor}
          factor={stage === 'analyzing' ? 0.35 : stage === 'simulating' ? 0.25 : 0.1}
          speed={stage === 'analyzing' ? 3 : 1}
          roughness={0.2}
          metalness={0.85}
          wireframe={false}
          emissive={coreColor}
          emissiveIntensity={stage === 'recovered' || stage === 'verified' ? 0.5 : 0.25}
        />
      </Sphere>

      {/* Outer Wireframe Hull */}
      <Sphere ref={outerWireRef} args={[1.2, 16, 16]}>
        <meshBasicMaterial
          color={coreColor}
          wireframe
          transparent
          opacity={0.25}
        />
      </Sphere>

      {/* Verification / Validation Torus Ring */}
      {(stage === 'validating' || stage === 'verified' || stage === 'simulating' || stage === 'learning') && (
        <mesh ref={ringRef} rotation={[Math.PI / 3, 0, 0]}>
          <torusGeometry args={[1.5, 0.03, 16, 64]} />
          <meshStandardMaterial
            color={stage === 'verified' ? '#6366F1' : '#8B5CF6'}
            emissive={stage === 'verified' ? '#6366F1' : '#8B5CF6'}
            emissiveIntensity={0.6}
          />
        </mesh>
      )}
    </group>
  );
}

function OrbitingNodes({ stage, prefersReducedMotion }: { stage: RecoveryStage; prefersReducedMotion: boolean }) {
  const groupRef = useRef<THREE.Group>(null!);

  useFrame((_, delta) => {
    if (prefersReducedMotion) return;
    if (groupRef.current) {
      const orbitSpeed = stage === 'detecting' ? 2.5 : stage === 'executing' ? 3.5 : 1.0;
      groupRef.current.rotation.y += delta * 0.8 * orbitSpeed;
    }
  });

  const nodeCount = stage === 'simulating' ? 5 : stage === 'predicting' ? 4 : 3;

  return (
    <group ref={groupRef}>
      {Array.from({ length: nodeCount }).map((_, idx) => {
        const angle = (idx / nodeCount) * Math.PI * 2;
        const radius = 1.6;
        const x = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius;

        return (
          <mesh key={idx} position={[x, idx % 2 === 0 ? 0.3 : -0.3, z]}>
            <sphereGeometry args={[0.08, 12, 12]} />
            <meshBasicMaterial color={idx === 0 ? '#10B981' : '#A78BFA'} />
          </mesh>
        );
      })}
    </group>
  );
}

export function AIOrb({
  state = 'idle',
  stage,
  className = 'h-36 w-30',
}: {
  state?: string;
  stage?: RecoveryStage;
  className?: string;
}) {
  const [mounted, setMounted] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  const activeStage: RecoveryStage = stage || (state as RecoveryStage) || 'idle';

  useEffect(() => {
    setMounted(true);
    if (typeof window !== 'undefined') {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      setPrefersReducedMotion(mediaQuery.matches);
    }
  }, []);

  if (!mounted) {
    return (
      <div className={`flex items-center justify-center rounded-full bg-ai/10 border border-ai/30 ${className}`}>
        <div className="h-8 w-8 rounded-full bg-ai/30 animate-pulse" />
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <Canvas
        camera={{ position: [0, 0, 4.5], fov: 45 }}
        style={{ background: 'transparent' }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 5, 5]} intensity={1.2} />
        <pointLight position={[-5, -5, -5]} color="#8B5CF6" intensity={0.8} />

        <InnerCore stage={activeStage} prefersReducedMotion={prefersReducedMotion} />
        <OrbitingNodes stage={activeStage} prefersReducedMotion={prefersReducedMotion} />
      </Canvas>
    </div>
  );
}
