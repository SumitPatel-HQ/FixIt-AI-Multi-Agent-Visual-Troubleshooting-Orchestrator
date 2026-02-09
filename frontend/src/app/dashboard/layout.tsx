"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
   // LayoutDashboardIcon,
   UploadIcon,
   FileTextIcon,
   ClockIcon,
   SettingsIcon,
   Menu,
   X,
} from "lucide-react";
import { DashboardProvider, useDashboard } from "./dashboard-context";

const navigation = [
   { name: "Input Hub", href: "/dashboard", icon: UploadIcon },
   { name: "Results", href: "/dashboard/results", icon: FileTextIcon },
   { name: "History", href: "/dashboard/history", icon: ClockIcon },
   { name: "Settings", href: "/dashboard/settings", icon: SettingsIcon },
];

function DashboardLayoutContent({
   children,
}: {
   children: React.ReactNode;
}) {
   const pathname = usePathname();
   const { isMobileMenuOpen, setIsMobileMenuOpen } = useDashboard();

   return (
      <div className="min-h-screen bg-background selection:bg-accent/30">
         {/* Mobile Header */}
         <div className="md:hidden fixed top-4 left-4 right-4 z-50 flex items-center justify-between px-6 py-3 bg-[#0c0c0c]/90 backdrop-blur-md border border-white/10 rounded-full shadow-lg">
            <Link href="/" className="flex items-center gap-2">
               <span className="font-display text-xl font-bold tracking-tight text-white">
                  Fixit
               </span>
            </Link>
            <button
               onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
               className="p-1 text-muted-foreground hover:text-white transition-colors"
            >
               {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
         </div>

         {/* Backdrop for Mobile */}
         {isMobileMenuOpen && (
            <div
               className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
               onClick={() => setIsMobileMenuOpen(false)}
            />
         )}

         {/* Navigation - Sidebar */}
         <aside
            className={cn(
               "fixed z-50  flex flex-col transition-all duration-300 ease-in-out",
               // Mobile Styles
               "inset-y-0 left-0 top-3 bottom-3 w-80 bg-[#0c0c0c] border-r border-white/10 p-6 shadow-2xl rounded-4xl",
               isMobileMenuOpen ? "translate-x-0" : "-translate-x-full",
               // Desktop Styles
               "md:translate-x-0 md:fixed md:left-4 md:top-4 md:bottom-4 md:w-full md:max-w-2xs md:bg-[#0c0c0c]/60 md:backdrop-blur-2xl md:border md:border-white/[0.05] md:rounded-[2rem] md:shadow-black/50"
            )}
         >
            {/* Logo Section */}
            <div className="mb-10 px-2 flex justify-between items-center">
               <Link
                  href="/"
                  className="flex items-center mt-2 gap-3 group"
                  onClick={() => setIsMobileMenuOpen(false)}
               >
                  <span className="font-display text-3xl font-bold tracking-tight text-white">
                     Fixit
                  </span>
               </Link>
               {/* Mobile Close Button inside sidebar */}
               <button
                  className="md:hidden text-muted-foreground hover:text-white"
                  onClick={() => setIsMobileMenuOpen(false)}
               >
                  <X className="w-5 h-5" />
               </button>
            </div>

            {/* Navigation Links */}
            <nav className="flex-1 space-y-2">
               {navigation.map((item) => {
                  const isActive = pathname === item.href;
                  const Icon = item.icon;

                  return (
                     <Link
                        key={item.name}
                        href={item.href}
                        onClick={() => setIsMobileMenuOpen(false)}
                        className={cn(
                           "relative flex items-center gap-3 px-4 py-3.5 rounded-2xl transition-all duration-300 group font-medium",
                           isActive
                              ? "text-primary bg-primary/10 shadow-lg shadow-primary/5 border border-primary/10"
                              : "text-muted-foreground hover:text-white hover:bg-white/[0.03]"
                        )}
                     >
                        <Icon className={cn(
                           "w-5 h-5 relative z-10 transition-transform duration-300 group-hover:scale-110",
                           isActive ? "text-primary" : "group-hover:text-primary"
                        )} />
                        <span className="relative z-10">{item.name}</span>

                        {isActive && (
                           <div className="absolute right-3 w-1.5 h-1.5 rounded-full bg-primary blur-[1px] shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                        )}
                     </Link>
                  );
               })}
            </nav>

            {/* User Profile Section */}
            <div className="pt-6 border-t border-white/[0.05]">
               <div className="flex items-center gap-3 p-3 rounded-2xl bg-white/[0.03] border border-white/[0.05] group hover:bg-white/[0.05] transition-colors cursor-pointer">
                  <div className="relative">
                     <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center border border-primary/20">
                        <span className="text-primary font-display font-bold text-sm">U</span>
                     </div>
                     <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 border-2 border-[#0c0c0c] rounded-full" />
                  </div>
                  <div className="flex-1 min-w-0">
                     <p className="text-sm font-semibold text-white truncate group-hover:text-primary transition-colors">
                        User
                     </p>
                     <p className="text-[10px] text-muted-foreground truncate uppercase tracking-wider font-bold">
                        Premium Plan
                     </p>
                  </div>
               </div>
            </div>
         </aside>

         {/* Main Content Area */}
         <main className={cn(
            "relative transition-all duration-300",
            "md:ml-76 md:mr-4 md:pt-10 md:mt-2 md:pb-8", // Desktop margins
            "p-4 pt-24 pb-32" // Mobile padding - pt for fixed header, pb for fixed footer
         )}>
            <div className="max-w-8xl mx-auto">{children}</div>
         </main>
      </div>
   );
}

export default function DashboardLayout({
   children,
}: {
   children: React.ReactNode;
}) {
   return (
      <DashboardProvider>
         <DashboardLayoutContent>{children}</DashboardLayoutContent>
      </DashboardProvider>
   );
}