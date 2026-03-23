<script>
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { currentUser } from '$lib/auth.js';
  import { api } from '$lib/api.js';

  let users = [];
  let loading = true;
  let error = '';
  let successMsg = '';

  // Modal state
  let showModal = false;
  let editingUser = null;   // null = create new, object = edit existing
  let form = { username: '', password: '', role: 'viewer', display_name: '' };
  let saving = false;
  let modalError = '';

  onMount(async () => {
    if ($currentUser && $currentUser.role !== 'admin') {
      goto('/');
      return;
    }
    await loadUsers();
  });

  async function loadUsers() {
    loading = true;
    error = '';
    try {
      users = await api.getUsers();
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  function openCreate() {
    editingUser = null;
    form = { username: '', password: '', role: 'viewer', display_name: '' };
    modalError = '';
    showModal = true;
  }

  function openEdit(user) {
    editingUser = user;
    form = { username: user.username, password: '', role: user.role, display_name: user.display_name };
    modalError = '';
    showModal = true;
  }

  async function saveUser() {
    saving = true;
    modalError = '';
    successMsg = '';
    try {
      if (editingUser) {
        const payload = { role: form.role, display_name: form.display_name };
        if (form.password) payload.password = form.password;
        await api.updateUser(editingUser.username, payload);
        successMsg = `Benutzer "${editingUser.username}" aktualisiert`;
      } else {
        if (!form.password) { modalError = 'Passwort ist erforderlich'; saving = false; return; }
        await api.createUser({ username: form.username, password: form.password, role: form.role, display_name: form.display_name });
        successMsg = `Benutzer "${form.username}" erstellt`;
      }
      showModal = false;
      await loadUsers();
    } catch (e) {
      modalError = e.message;
    } finally {
      saving = false;
    }
  }

  async function deleteUser(user) {
    if (!confirm(`Benutzer "${user.username}" wirklich löschen?`)) return;
    successMsg = '';
    error = '';
    try {
      await api.deleteUser(user.username);
      successMsg = `Benutzer "${user.username}" gelöscht`;
      await loadUsers();
    } catch (e) {
      error = e.message;
    }
  }

  function closeModal() {
    showModal = false;
  }
</script>

<div class="max-w-3xl mx-auto">
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-2xl font-bold text-gray-800">⚙️ Benutzerverwaltung</h1>
      <p class="text-sm text-gray-500 mt-1">Verwalten Sie die Benutzerkonten der Anwendung</p>
    </div>
    <button
      on:click={openCreate}
      class="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
    >
      + Neuer Benutzer
    </button>
  </div>

  {#if successMsg}
    <div class="mb-4 bg-green-50 border border-green-200 text-green-800 text-sm rounded-lg px-4 py-2">
      ✅ {successMsg}
    </div>
  {/if}

  {#if error}
    <div class="mb-4 bg-red-50 border border-red-200 text-red-800 text-sm rounded-lg px-4 py-2">
      ⚠️ {error}
    </div>
  {/if}

  {#if loading}
    <div class="text-center py-12 text-gray-400">Lade Benutzer …</div>
  {:else}
    <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b border-gray-200">
          <tr>
            <th class="text-left px-5 py-3 font-semibold text-gray-600">Benutzerkennung</th>
            <th class="text-left px-5 py-3 font-semibold text-gray-600">Anzeigename</th>
            <th class="text-left px-5 py-3 font-semibold text-gray-600">Rolle</th>
            <th class="text-left px-5 py-3 font-semibold text-gray-600">Erstellt am</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {#each users as user, i}
            <tr class="{i % 2 === 0 ? '' : 'bg-gray-50'} border-b border-gray-100 last:border-0">
              <td class="px-5 py-3 font-mono font-semibold text-gray-800">{user.username}</td>
              <td class="px-5 py-3 text-gray-600">{user.display_name || '—'}</td>
              <td class="px-5 py-3">
                <span class="inline-block px-2 py-0.5 rounded text-xs font-semibold
                  {user.role === 'admin'
                    ? 'bg-purple-100 text-purple-700'
                    : 'bg-blue-100 text-blue-700'}">
                  {user.role === 'admin' ? 'Admin' : 'Betrachter'}
                </span>
              </td>
              <td class="px-5 py-3 text-gray-400 text-xs">
                {user.created_at ? new Date(user.created_at).toLocaleDateString('de-DE') : '—'}
              </td>
              <td class="px-5 py-3 text-right space-x-2">
                <button
                  on:click={() => openEdit(user)}
                  class="text-blue-600 hover:text-blue-800 text-xs font-medium"
                >Bearbeiten</button>
                {#if user.username !== $currentUser?.username}
                  <button
                    on:click={() => deleteUser(user)}
                    class="text-red-500 hover:text-red-700 text-xs font-medium"
                  >Löschen</button>
                {/if}
              </td>
            </tr>
          {/each}
          {#if users.length === 0}
            <tr><td colspan="5" class="px-5 py-8 text-center text-gray-400">Keine Benutzer vorhanden</td></tr>
          {/if}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<!-- Modal -->
{#if showModal}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
    on:click|self={closeModal}
    role="dialog"
    aria-modal="true"
    aria-labelledby="modal-title"
  >
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
      <h2 id="modal-title" class="text-lg font-bold text-gray-800 mb-5">
        {editingUser ? `Benutzer bearbeiten: ${editingUser.username}` : 'Neuer Benutzer'}
      </h2>

      <div class="space-y-4">
        {#if !editingUser}
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Benutzerkennung *</label>
            <input
              type="text"
              bind:value={form.username}
              autocomplete="off"
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="z.B. jschmidt"
            />
          </div>
        {/if}

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Anzeigename
          </label>
          <input
            type="text"
            bind:value={form.display_name}
            autocomplete="off"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="z.B. Josef Schmidt"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Passwort {editingUser ? '(leer lassen = unverändert)' : '*'}
          </label>
          <input
            type="password"
            bind:value={form.password}
            autocomplete="new-password"
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="••••••••"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Rolle</label>
          <select
            bind:value={form.role}
            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="viewer">Betrachter (viewer)</option>
            <option value="admin">Administrator (admin)</option>
          </select>
        </div>

        {#if modalError}
          <p class="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {modalError}
          </p>
        {/if}
      </div>

      <div class="flex justify-end gap-3 mt-6">
        <button
          on:click={closeModal}
          class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 font-medium"
        >Abbrechen</button>
        <button
          on:click={saveUser}
          disabled={saving}
          class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
        >
          {saving ? 'Speichert …' : (editingUser ? 'Speichern' : 'Erstellen')}
        </button>
      </div>
    </div>
  </div>
{/if}
