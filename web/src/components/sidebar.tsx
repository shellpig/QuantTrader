"use client";

// Sidebar component (Phase 10-B)
// PC (lg+): fixed left sidebar 240px
// Mobile (<lg): fixed bottom tab bar with 5 icons

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  TrendingUp,
  FolderOpen,
  Bot,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useCommandPaletteEntry } from "@/hooks/use-command-palette";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "個股分析", href: "/dashboard", icon: BarChart3 },
  { label: "回測研究", href: "/backtest", icon: TrendingUp },
  { label: "資料管理", href: "/data",     icon: FolderOpen },
  { label: "AI 問答",  href: "/ai",       icon: Bot,      badge: "後續開放" },
  { label: "設定",     href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  useCommandPaletteEntry({
    id: "nav-dashboard",
    group: "pages",
    label: "個股分析",
    action: () => router.push("/dashboard"),
  });
  useCommandPaletteEntry({
    id: "nav-data",
    group: "pages",
    label: "資料管理",
    action: () => router.push("/data"),
  });
  useCommandPaletteEntry({
    id: "nav-backtest",
    group: "pages",
    label: "回測研究",
    action: () => router.push("/backtest"),
  });
  useCommandPaletteEntry({
    id: "nav-ai",
    group: "pages",
    label: "AI 問答",
    action: () => router.push("/ai"),
  });
  useCommandPaletteEntry({
    id: "nav-settings",
    group: "pages",
    label: "設定",
    action: () => router.push("/settings"),
  });

  return (
    <>
      {/* ── PC: left fixed sidebar ── */}
      <aside className="hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 lg:left-0 lg:w-32 lg:border-r lg:border-border lg:bg-card lg:z-40">
        {/* Logo */}
        <div className="flex h-16 items-center px-3 border-b border-border">
          <span className="text-base font-bold text-foreground tracking-tight">
            QuantTrader
          </span>
        </div>

        {/* Nav */}
        <nav className="flex flex-col gap-1 p-2 flex-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => (
            <SidebarLink key={item.href} item={item} active={pathname === item.href} />
          ))}
        </nav>
      </aside>

      {/* ── Mobile: bottom tab bar ── */}
      <nav
        className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-card border-t border-border"
        aria-label="モバイルナビ"
      >
        <div className="flex items-center justify-around h-16 px-2">
          {NAV_ITEMS.map((item) => (
            <MobileTabItem key={item.href} item={item} active={pathname === item.href} />
          ))}
        </div>
      </nav>
    </>
  );
}

function SidebarLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={cn(
        "flex flex-col rounded-lg px-2 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-muted hover:text-foreground",
      )}
      aria-current={active ? "page" : undefined}
      data-testid={`sidebar-nav-${item.href.slice(1)}`}
    >
      <span className="flex items-center gap-2">
        <Icon className="h-5 w-5 shrink-0" />
        {item.label}
      </span>
      {item.badge && (
        <span
          className="mt-0.5 self-start rounded-full bg-slate-700/40 px-1.5 py-px text-[10px] font-normal text-slate-400"
          data-testid={`sidebar-badge-${item.href.slice(1)}`}
        >
          {item.badge}
        </span>
      )}
    </Link>
  );
}

function MobileTabItem({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      className={cn(
        "flex flex-col items-center gap-0.5 px-2 py-1 text-xs font-medium transition-colors",
        active ? "text-primary" : "text-muted-foreground",
      )}
      aria-current={active ? "page" : undefined}
      data-testid={`mobile-nav-${item.href.slice(1)}`}
    >
      <Icon className="h-6 w-6" />
      <span>{item.label}</span>
    </Link>
  );
}
