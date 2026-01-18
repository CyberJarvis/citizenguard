'use client';

import { usePathname, useRouter } from 'next/navigation';
import { Home, FileText, Map, Users, Plus, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import useAuthStore from '@/context/AuthContext';

// Navigation items in order: Home, My Reports, [FAB], Map, Community
const navItems = [
  { href: '/dashboard', icon: Home, label: 'Home' },
  { href: '/my-reports', icon: FileText, label: 'Reports' },
  { href: null, icon: null, label: 'fab' }, // Center FAB placeholder
  { href: '/map', icon: Map, label: 'Map' },
  { href: '/community', icon: Users, label: 'Community' },
];

export function BottomNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuthStore();

  // Only show for citizen role (or if role not set, default to citizen)
  const userRole = user?.role?.toLowerCase();
  const isCitizen = !userRole || userRole === 'citizen' || userRole === 'verified_organizer';

  if (!isCitizen) return null;

  const handleNavClick = (href) => {
    if (href) {
      router.push(href);
    }
  };

  const handleReportClick = () => {
    router.push('/report-hazard');
  };

  // Check if current page is the report page
  const isReportPage = pathname === '/report-hazard';

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 lg:hidden">
      {/* Frosted glass background */}
      <div className="absolute inset-0 bg-white/90 backdrop-blur-xl border-t border-slate-200/80 shadow-[0_-4px_20px_rgba(0,0,0,0.08)]" />

      {/* Safe area padding for iOS */}
      <div className="relative flex items-end justify-around px-1 pt-2 pb-2" style={{ paddingBottom: 'max(8px, env(safe-area-inset-bottom))' }}>
        {navItems.map((item, index) => {
          // Center FAB Button
          if (item.label === 'fab') {
            return (
              <div key="fab" className="relative flex flex-col items-center" style={{ width: '72px' }}>
                {/* FAB Button */}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.92 }}
                  onClick={handleReportClick}
                  className={cn(
                    "relative -mt-7 w-[60px] h-[60px] rounded-full flex items-center justify-center shadow-lg transition-all duration-300",
                    isReportPage
                      ? "bg-gradient-to-br from-[#0d4a6f] to-[#083a57] shadow-[#0d4a6f]/30"
                      : "bg-gradient-to-br from-orange-500 to-red-500 shadow-orange-500/30"
                  )}
                  aria-label="Report Hazard"
                >
                  {/* Pulse ring animation */}
                  <span className={cn(
                    "absolute inset-0 rounded-full animate-ping opacity-20",
                    isReportPage ? "bg-[#0d4a6f]" : "bg-orange-500"
                  )} style={{ animationDuration: '2s' }} />

                  {/* Inner glow */}
                  <span className={cn(
                    "absolute inset-1 rounded-full opacity-30",
                    isReportPage
                      ? "bg-gradient-to-t from-transparent to-white/20"
                      : "bg-gradient-to-t from-transparent to-white/30"
                  )} />

                  {/* Icon */}
                  <Plus className="w-7 h-7 text-white relative z-10" strokeWidth={2.5} />
                </motion.button>

                {/* Label */}
                <span className={cn(
                  "text-[10px] font-semibold mt-1.5 transition-colors",
                  isReportPage ? "text-[#0d4a6f]" : "text-orange-600"
                )}>
                  Report
                </span>
              </div>
            );
          }

          // Regular nav items
          const isActive = pathname === item.href ||
                          (item.href !== '/dashboard' && pathname?.startsWith(item.href + '/'));
          const Icon = item.icon;

          return (
            <motion.button
              key={item.href}
              whileTap={{ scale: 0.92 }}
              onClick={() => handleNavClick(item.href)}
              className="flex flex-col items-center justify-center py-1 px-2 min-w-[64px] transition-all"
            >
              {/* Icon container with active indicator */}
              <div className="relative">
                <motion.div
                  initial={false}
                  animate={{
                    backgroundColor: isActive ? 'rgb(232, 244, 252)' : 'transparent',
                    scale: isActive ? 1 : 1,
                  }}
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  className={cn(
                    'p-2 rounded-2xl transition-all duration-200',
                    isActive && 'shadow-sm'
                  )}
                >
                  <Icon
                    className={cn(
                      'w-[22px] h-[22px] transition-colors duration-200',
                      isActive ? 'text-[#0d4a6f]' : 'text-slate-400'
                    )}
                    strokeWidth={isActive ? 2.2 : 1.8}
                  />
                </motion.div>

                {/* Active dot indicator */}
                <AnimatePresence>
                  {isActive && (
                    <motion.span
                      initial={{ scale: 0, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      exit={{ scale: 0, opacity: 0 }}
                      className="absolute -bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 bg-[#0d4a6f] rounded-full"
                    />
                  )}
                </AnimatePresence>
              </div>

              {/* Label */}
              <span className={cn(
                'text-[10px] font-medium mt-0.5 transition-colors duration-200',
                isActive ? 'text-[#0d4a6f]' : 'text-slate-500'
              )}>
                {item.label}
              </span>
            </motion.button>
          );
        })}
      </div>
    </nav>
  );
}

export default BottomNav;
