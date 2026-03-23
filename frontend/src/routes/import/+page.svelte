<script>
  import { onMount } from 'svelte';
  import { api } from '$lib/api.js';

  let seedResult = null;
  let uploadResult = null;
  let loading = { seed: false, upload: false };
  let loadingFile = {};   // { filename: true/false }
  let fileResults = {};   // { filename: result }

  let availableFiles = [];
  let filesLoading = true;

  let uploadFile = null;
  let uploadAccount = '6023543';

  onMount(async () => {
    await refreshFileList();
  });

  async function refreshFileList() {
    filesLoading = true;
    try {
      const res = await api.getAvailableFiles();
      availableFiles = res.files || [];
    } catch (e) {
      availableFiles = [];
    } finally {
      filesLoading = false;
    }
  }

  async function runSeed() {
    loading.seed = true;
    try {
      seedResult = await api.seed();
      await refreshFileList();
    } catch (e) {
      seedResult = { error: e.message };
    } finally {
      loading.seed = false;
    }
  }

  async function importFile(filename) {
    loadingFile = { ...loadingFile, [filename]: true };
    try {
      fileResults = { ...fileResults, [filename]: await api.importSingleFile(filename) };
      await refreshFileList();
    } catch (e) {
      fileResults = { ...fileResults, [filename]: { error: e.message } };
    } finally {
      loadingFile = { ...loadingFile, [filename]: false };
    }
  }

  async function importAllFiles() {
    for (const f of availableFiles) {
      await importFile(f.filename);
    }
  }

  async function runUpload() {
    if (!uploadFile) { alert('Bitte eine Datei auswählen.'); return; }
    loading.upload = true;
    try {
      uploadResult = await api.importFile(uploadFile, uploadAccount);
      await refreshFileList();
    } catch (e) {
      uploadResult = { error: e.message };
    } finally {
      loading.upload = false;
    }
  }

  function handleFileChange(e) {
    uploadFile = e.target.files[0] || null;
  }

  function yearBadgeClass(year) {
    return year === '2024' ? 'bg-amber-100 text-amber-800' :
           year === '2025' ? 'bg-blue-100 text-blue-800' :
           'bg-gray-100 text-gray-600';
  }

  function accountBadgeClass(name) {
    return name?.includes('Betriebs') ? 'bg-green-100 text-green-800' : 'bg-purple-100 text-purple-800';
  }
</script>

<div class="space-y-6 max-w-3xl">
  <h2 class="text-2xl font-bold">Daten-Import</h2>

  <!-- Step 1: Seed base data -->
  <div class="card">
    <h3 class="font-semibold text-gray-700 mb-2">Schritt 1: Stammdaten anlegen</h3>
    <p class="text-sm text-gray-500 mb-3">
      Legt die bekannten Konten und Eigentümer (WE-001 bis WE-004) in der Datenbank an.
      Sicher mehrfach ausführbar – vorhandene Einträge werden übersprungen.
    </p>
    <button class="btn-primary" on:click={runSeed} disabled={loading.seed}>
      {loading.seed ? 'Läuft…' : '🏗️ Stammdaten anlegen'}
    </button>
    {#if seedResult}
      <pre class="mt-3 text-xs bg-gray-50 p-3 rounded-lg overflow-auto">{JSON.stringify(seedResult, null, 2)}</pre>
    {/if}
  </div>

  <!-- Step 2: Import files from /app/data -->
  <div class="card">
    <div class="flex items-center justify-between mb-3">
      <h3 class="font-semibold text-gray-700">Schritt 2: StarMoney-Dateien einlesen</h3>
      <div class="flex gap-2">
        <button class="text-sm text-gray-500 hover:text-gray-700 underline" on:click={refreshFileList}>
          🔄 Aktualisieren
        </button>
        <button class="btn-primary text-sm py-1 px-3" on:click={importAllFiles}
          disabled={availableFiles.length === 0 || filesLoading}>
          📥 Alle importieren
        </button>
      </div>
    </div>
    <p class="text-sm text-gray-500 mb-4">
      Alle <code>.txt</code>-Dateien aus dem gemounteten <code>/app/data</code>-Ordner.
      Bereits vorhandene Transaktionen werden übersprungen (Duplikatschutz).
    </p>

    {#if filesLoading}
      <p class="text-sm text-gray-400 italic">Lade Dateiliste…</p>
    {:else if availableFiles.length === 0}
      <p class="text-sm text-yellow-700 bg-yellow-50 rounded p-3">
        Keine .txt-Dateien in /app/data gefunden.
      </p>
    {:else}
      <div class="space-y-3">
        {#each availableFiles as file}
          {@const res = fileResults[file.filename]}
          <div class="border rounded-lg p-4 flex items-center justify-between gap-4">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap mb-1">
                {#if file.year}
                  <span class="text-xs font-bold px-2 py-0.5 rounded-full {yearBadgeClass(file.year)}">
                    {file.year}
                  </span>
                {/if}
                <span class="text-xs font-medium px-2 py-0.5 rounded-full {accountBadgeClass(file.account_name)}">
                  {file.account_name} ({file.account_number})
                </span>
                {#if file.already_imported > 0}
                  <span class="text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
                    ✓ {file.already_imported} importiert
                  </span>
                {/if}
              </div>
              <p class="text-sm font-mono text-gray-600 truncate">{file.filename}</p>
              <p class="text-xs text-gray-400">{(file.size_bytes / 1024).toFixed(1)} KB</p>
            </div>
            <button
              class="btn-primary text-sm py-1.5 px-4 whitespace-nowrap"
              on:click={() => importFile(file.filename)}
              disabled={loadingFile[file.filename]}
            >
              {loadingFile[file.filename] ? '⏳ Läuft…' : '⬆️ Importieren'}
            </button>
          </div>
          {#if res}
            <div class="ml-4 text-xs rounded p-2 {res.error ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}">
              {#if res.error}
                ❌ Fehler: {res.error}
              {:else}
                ✅ {res.inserted} neu importiert, {res.skipped} übersprungen
              {/if}
            </div>
          {/if}
        {/each}
      </div>
    {/if}
  </div>

  <!-- Step 3: Manual upload -->
  <div class="card">
    <h3 class="font-semibold text-gray-700 mb-2">Schritt 3: Neue StarMoney-Datei hochladen</h3>
    <p class="text-sm text-gray-500 mb-3">
      Laden Sie eine neue StarMoney-Exportdatei (.txt) für ein bestimmtes Konto hoch.
    </p>
    <div class="space-y-3">
      <div>
        <label class="text-sm font-medium text-gray-700">Konto</label>
        <select bind:value={uploadAccount} class="mt-1 block border rounded-lg px-3 py-2 text-sm w-full">
          <option value="6023543">Betriebskonto (6023543)</option>
          <option value="6023550">Rücklagenkonto (6023550)</option>
        </select>
      </div>
      <div>
        <label class="text-sm font-medium text-gray-700">StarMoney TXT-Datei</label>
        <input
          type="file"
          accept=".txt,.csv"
          on:change={handleFileChange}
          class="mt-1 block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-primary-600 file:text-white file:cursor-pointer"
        />
      </div>
      <button class="btn-primary" on:click={runUpload} disabled={loading.upload || !uploadFile}>
        {loading.upload ? 'Hochladen…' : '⬆️ Importieren'}
      </button>
    </div>
    {#if uploadResult}
      <pre class="mt-3 text-xs bg-gray-50 p-3 rounded-lg overflow-auto">{JSON.stringify(uploadResult, null, 2)}</pre>
    {/if}
  </div>

  <div class="card bg-blue-50 border-blue-200">
    <h4 class="font-semibold text-blue-800 mb-2">ℹ️ Workflow</h4>
    <ol class="text-sm text-blue-700 space-y-1 list-decimal list-inside">
      <li>Stammdaten anlegen (Schritt 1) – einmalig</li>
      <li>Einzelne Dateien per Klick importieren (Schritt 2) – für 2024 und 2025</li>
      <li>Neue Exports über Schritt 3 hochladen</li>
      <li>Dashboard und Auswertungen benutzen</li>
    </ol>
  </div>
</div>

