'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { LoginBackground3D } from '@/components/3d/LoginBackground';
import { APP_NAME, APP_TAGLINE } from '@/lib/constants';
import { ShieldAlert, ArrowRight } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('merchant@payrecover.ai');
  const [password, setPassword] = useState('••••••••••••');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      router.push('/dashboard');
    }, 600);
  };

  return (
    <div className="relative min-h-screen bg-bg text-primaryText flex items-center justify-center p-4 overflow-hidden">
      {/* Abstract Floating 3D Scene Background */}
      <LoginBackground3D />

      <div className="relative z-10 w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-ai/20 border border-ai/50 text-ai-light shadow-glow mb-2">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-primaryText">{APP_NAME}</h1>
          <p className="text-xs text-secondaryText font-medium">{APP_TAGLINE}</p>
        </div>

        {/* Login Card */}
        <Card className="p-6 border-border/80 bg-surface-elevated/90 backdrop-blur-md shadow-card">
          <CardHeader className="p-0 pb-4">
            <CardTitle className="text-base text-center">Sign In to Revenue Command Center</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Merchant Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />

              <Input
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full mt-2"
                isLoading={isLoading}
              >
                Sign In
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>

              <div className="text-center pt-2">
                <button
                  type="button"
                  onClick={() => router.push('/onboarding')}
                  className="text-xs text-ai-light hover:underline font-medium"
                >
                  New merchant? Complete Onboarding Wizard →
                </button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
