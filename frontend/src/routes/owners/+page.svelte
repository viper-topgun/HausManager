<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';
  import { formatEur } from '$lib/format.js';

  let owners = [];
  let loading = true;
  let error = null;
  let editing = null;
  let showForm = false;

  const emptyForm = () => ({
    unit_id: '',
    name: '',
    iban: '',
    bic: '',
    email: '',
    phone: '',
    monthly_hausgeld: 0,
    notes: '',
  });
  let form = emptyForm();

  async function load() {
    loading = true;
    try {
      owners = await api.getOwners();
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(load);

  function startEdit(owner) {
    editing = owner;
    form = { ...owner };
    showForm = true;
  }

  function startNew() {
    editing = null;
    form = emptyForm();
    showForm = true;
  }

  async function save() {
    try {
      if (editing) {
        await api.updateOwner(editing.id, form);
      } else {
        await api.createOwner(form);
      }
      showForm = false;
      await load();
    } catch (e) {
      alert('Fehler: ' + e.message);
    }
  }

  async function remove(owner) {
    if (!confirm(`Eigentümer "${owner.name}" wirklich löschen?`)) return;
    try {
      await api.deleteOwner(owner.id);
      await load();
    } catch (e) {
      alert('Fehler: ' + e.message);
    }
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <h2 class="text-2xl font-bold">Eigentümer</h2>
    <button class="btn-primary" on:click={startNew}>+ Neu</button>
  </div>

  {#if loading}
    <div class="text-gray-500 text-center py-12">Lade…</div>
  {:else if error}
    <div class="bg-red-50 text-red-700 rounded-xl p-4">Fehler: {error}</div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {#each owners as owner}
        <div class="card hover:shadow-md transition-shadow">
          <div class="flex justify-between items-start">
            <div>
              <span class="text-xs font-mono font-bold text-primary-600 bg-primary-50 px-2 py-0.5 rounded">
                {owner.unit_id}
              </span>
              <h3 class="text-lg font-semibold mt-2">{owner.name}</h3>
            </div>
            <div class="flex gap-1">
              <button class="btn-secondary text-xs py-1 px-2" on:click={() => startEdit(owner)}>✏️</button>
              <button class="text-red-400 hover:text-red-600 text-xs py-1 px-2 rounded" on:click={() => remove(owner)}>🗑️</button>
            </div>
          </div>
          <dl class="mt-3 space-y-1 text-sm text-gray-600">
            <div class="flex justify-between">
              <dt>Monatliches Hausgeld</dt>
              <dd class="font-semibold text-gray-900">{formatEur(owner.monthly_hausgeld)}</dd>
            </div>
            {#if owner.iban}
              <div class="flex justify-between">
                <dt>IBAN</dt>
                <dd class="font-mono text-xs">{owner.iban}</dd>
              </div>
            {/if}
            {#if owner.email}
              <div class="flex justify-between">
                <dt>E-Mail</dt>
                <dd>{owner.email}</dd>
              </div>
            {/if}
            {#if owner.notes}
              <div class="mt-2 text-xs text-gray-400 italic">{owner.notes}</div>
            {/if}
          </dl>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Modal Form -->
{#if showForm}
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
      <h3 class="text-lg font-bold mb-4">{editing ? 'Eigentümer bearbeiten' : 'Neuer Eigentümer'}</h3>
      <div class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-sm font-medium text-gray-700">Einheit</label>
            <input bind:value={form.unit_id} class="mt-1 w-full border rounded-lg px-3 py-2 text-sm" placeholder="WE-001" />
          </div>
          <div>
            <label class="text-sm font-medium text-gray-700">Hausgeld/Monat</label>
            <input type="number" bind:value={form.monthly_hausgeld} class="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label class="text-sm font-medium text-gray-700">Name</label>
          <input bind:value={form.name} class="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="text-sm font-medium text-gray-700">IBAN</label>
          <input bind:value={form.iban} class="mt-1 w-full border rounded-lg px-3 py-2 text-sm font-mono" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-sm font-medium text-gray-700">E-Mail</label>
            <input type="email" bind:value={form.email} class="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="text-sm font-medium text-gray-700">Telefon</label>
            <input bind:value={form.phone} class="mt-1 w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label class="text-sm font-medium text-gray-700">Notizen</label>
          <textarea bind:value={form.notes} rows="2" class="mt-1 w-full border rounded-lg px-3 py-2 text-sm"></textarea>
        </div>
      </div>
      <div class="flex gap-3 mt-5 justify-end">
        <button class="btn-secondary" on:click={() => (showForm = false)}>Abbrechen</button>
        <button class="btn-primary" on:click={save}>Speichern</button>
      </div>
    </div>
  </div>
{/if}
