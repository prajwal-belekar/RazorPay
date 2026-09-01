'use client';

import React, { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, Box, Icosahedron } from '@react-three/drei';
import * as THREE from 'three';

function BackgroundFloatingScene() {
  const groupRef = useRef<THREE.Group>(null!);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.08;
      groupRef.current.rotation.x += delta * 0.04;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Central Subtle AI Sphere */}
      <Sphere args={[1.4, 32, 32]} position={[0, 0, -1]}>
        <meshStandardMaterial
          color="#7C3AED"
          wireframe
          transparent
          opacity={0.15}
        />
      </Sphere>

      {/* Floating Low-Poly Geometries */}
      <Icosahedron args={[0.4, 0]} position={[-3, 2, -2]}>
        <meshStandardMaterial color="#8B5CF6" wireframe transparent opacity={0.2} />
      </Icosahedron>

      <Box args={[0.5, 0.5, 0.5]} position={[3.2, -1.8, -2]}>
        <meshStandardMaterial color="#3B82F6" wireframe transparent opacity={0.2} />
      </Box>

      <Sphere args={[0.3, 16, 16]} position={[-2.5, -2, -1.5]}>
        <meshStandardMaterial color="#10B981" transparent opacity={0.25} />
      </Sphere>

      <Box args={[0.4, 0.4, 0.4]} position={[2.8, 2.2, -2.5]}>
        <meshStandardMaterial color="#F59E0B" wireframe transparent opacity={0.2} />
      </Box>
    </group>
  );
}

export function LoginBackground3D() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return (
    <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden opacity-60">
      <Canvas camera={{ position: [0, 0, 5], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 5, 5]} intensity={0.8} />
        <BackgroundFloatingScene />
      </Canvas>
    </div>
  );
}
