<script>
  import { goto } from '$app/navigation';
  import { api } from '$lib/api.js';
  import { authToken, currentUser } from '$lib/auth.js';

  let username = '';
  let password = '';
  let error = '';
  let loading = false;

  async function handleLogin() {
    error = '';
    loading = true;
    try {
      const data = await api.login(username, password);
      authToken.set(data.access_token);
      currentUser.set({ username: data.username, role: data.role });
      await goto('/');
    } catch (e) {
      error = e.message || 'Anmeldung fehlgeschlagen';
    } finally {
      loading = false;
    }
  }

  function onKeydown(e) {
    if (e.key === 'Enter') handleLogin();
  }
</script>

<svelte:head>
  <title>Anmeldung – HausManager</title>
</svelte:head>

<div class="min-h-screen bg-gray-100 flex items-center justify-center">
  <div class="bg-white rounded-2xl shadow-lg w-full max-w-sm p-8">
    <!-- Header -->
    <div class="text-center mb-8">
      <div class="text-4xl mb-3">🏡</div>
      <h1 class="text-2xl font-bold text-gray-800">HausManager</h1>
      <p class="text-sm text-gray-500 mt-1">WEG Tulpenstr. 31 · Hilgertshausen-Tandern</p>
    </div>

    <!-- Form -->
    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="username">
          Benutzerkennung
        </label>
        <input
          id="username"
          type="text"
          bind:value={username}
          on:keydown={onKeydown}
          autocomplete="username"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="z.B. admin"
          disabled={loading}
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="password">
          Passwort
        </label>
        <input
          id="password"
          type="password"
          bind:value={password}
          on:keydown={onKeydown}
          autocomplete="current-password"
          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="••••••••"
          disabled={loading}
        />
      </div>

      {#if error}
        <p class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      {/if}

      <button
        on:click={handleLogin}
        disabled={loading || !username || !password}
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
               text-white font-semibold rounded-lg px-4 py-2.5 text-sm transition-colors"
      >
        {loading ? 'Wird angemeldet …' : 'Anmelden'}
      </button>
    </div>
  </div>
</div>
