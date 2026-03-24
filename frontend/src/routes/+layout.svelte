<script>
  import '../app.css';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { authToken, currentUser, logout } from '$lib/auth.js';
  import { api } from '$lib/api.js';

  const nav = [
    { href: '/', label: 'Dashboard', icon: '🏠' },
    { href: '/owners', label: 'Eigentümer', icon: '👥' },
    { href: '/accounts', label: 'Konten', icon: '🏦' },
    { href: '/transactions', label: 'Buchungen', icon: '📋' },
    { href: '/payments', label: 'Hausgeld', icon: '✅' },
    { href: '/expenses', label: 'Ausgaben', icon: '📊' },
    { href: '/abrechnungen', label: 'Abrechnung', icon: '📄' },
    { href: '/witter', label: 'Witter Formular', icon: '🔥' },
    { href: '/import', label: 'Import', icon: '📥' },
    { href: '/export', label: 'Export', icon: '📤' },
  ];

  $: isLoginPage = $page.url.pathname === '/login';
  $: isAdminPage = $page.url.pathname.startsWith('/admin');

  onMount(async () => {
    if (isLoginPage) return;
    const token = $authToken;
    if (!token) {
      goto('/login');
      return;
    }
    if (!$currentUser) {
      try {
        const user = await api.getMe();
        currentUser.set(user);
      } catch {
        logout();
        goto('/login');
      }
    }
  });

  function handleLogout() {
    logout();
    goto('/login');
  }
</script>

{#if isLoginPage}
  <slot />
{:else}
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

      {#if $currentUser?.role === 'admin'}
        <a
          href="/admin/users"
          class="flex items-center gap-3 px-5 py-2.5 text-sm transition-colors mt-2 border-t border-primary-700 pt-3
            {$page.url.pathname === '/admin/users'
              ? 'bg-primary-600 text-white font-semibold'
              : 'text-blue-200 hover:bg-primary-700 hover:text-white'}"
        >
          <span>⚙️</span>
          <span>Benutzerverwaltung</span>
        </a>
      {/if}
    </nav>

    <!-- Logged-in user + logout -->
    <div class="p-4 border-t border-primary-700">
      {#if $currentUser}
        <div class="text-xs text-blue-200 mb-2 truncate">
          <span class="font-semibold text-white">{$currentUser.display_name || $currentUser.username}</span><br />
          <span class="capitalize">{$currentUser.role}</span>
        </div>
      {/if}
      <button
        on:click={handleLogout}
        class="w-full text-left text-xs text-blue-300 hover:text-white transition-colors"
      >
        🚪 Abmelden
      </button>
      <p class="text-xs text-blue-400 mt-2">WEG Tulpenstr. 31<br />Hilgertshausen-Tandern</p>
    </div>
  </aside>

  <!-- Main content -->
  <main class="flex-1 overflow-y-auto p-6">
    <slot />
  </main>
</div>
{/if}
