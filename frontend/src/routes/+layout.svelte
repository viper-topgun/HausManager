<script>
  import '../app.css';
  import { page } from '$app/stores';

  const nav = [
    { href: '/', label: 'Dashboard', icon: '🏠' },
    { href: '/owners', label: 'Eigentümer', icon: '👥' },
    { href: '/accounts', label: 'Konten', icon: '🏦' },
    { href: '/transactions', label: 'Buchungen', icon: '📋' },
    { href: '/payments', label: 'Hausgeld', icon: '✅' },
    { href: '/expenses', label: 'Ausgaben', icon: '📊' },
    { href: '/abrechnungen', label: 'Abrechnung', icon: '📄' },
    { href: '/import', label: 'Import', icon: '📥' },
  ];
</script>

<div class="flex h-screen overflow-hidden bg-gray-50">
  <!-- Sidebar -->
  <aside class="w-56 bg-primary-900 text-white flex flex-col">
    <div class="p-5 border-b border-primary-700">
      <h1 class="text-lg font-bold leading-tight">🏡 HausManager</h1>
      <p class="text-xs text-blue-200 mt-1">Tulpenstr. 31</p>
    </div>
    <nav class="flex-1 overflow-y-auto py-3">
      {#each nav as item}
        <a
          href={item.href}
          class="flex items-center gap-3 px-5 py-2.5 text-sm transition-colors
            {$page.url.pathname === item.href
              ? 'bg-primary-600 text-white font-semibold'
              : 'text-blue-200 hover:bg-primary-700 hover:text-white'}"
        >
          <span>{item.icon}</span>
          <span>{item.label}</span>
        </a>
      {/each}
    </nav>
    <div class="p-4 text-xs text-blue-300 border-t border-primary-700">
      WEG Tulpenstr. 31<br />Hilgertshausen-Tandern
    </div>
  </aside>

  <!-- Main content -->
  <main class="flex-1 overflow-y-auto p-6">
    <slot />
  </main>
</div>
