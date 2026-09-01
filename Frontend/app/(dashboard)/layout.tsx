'use client';

import React, { useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { Topbar } from '@/components/layout/Topbar';
import { LiveDemoModal } from '@/components/demo/LiveDemoModal';
import { RecoveryEngineProvider, useRecoveryEngine } from '@/context/RecoveryEngineContext';

function DashboardLayoutContent({ children }: { children: React.ReactNode }) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const { startDemo } = useRecoveryEngine();

  return (
    <div className="min-h-screen bg-bg text-primaryText flex font-sans antialiased">
      {/* Collapsible / Mobile Navigation Sidebar */}
      <Sidebar
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
        onRunDemo={startDemo}
      />

      {/* Main Container Area */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-64 transition-all duration-300">
        <Topbar
          onMenuClick={() => setIsMobileOpen(true)}
          onRunDemo={startDemo}
        />

        <main className="flex-1 p-4 sm:p-6 md:p-8 max-w-7xl w-full mx-auto space-y-6">
          {children}
        </main>
      </div>

      {/* Global Hackathon Live Demo Flow Modal */}
      <LiveDemoModal />
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RecoveryEngineProvider>
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </RecoveryEngineProvider>
  );
}
