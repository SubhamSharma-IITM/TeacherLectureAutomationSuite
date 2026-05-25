export default function HomePage() {
  return (
    <main className="min-h-screen bg-black px-6 py-20 text-white">
      <div className="mx-auto max-w-2xl rounded-xl border border-zinc-700 bg-zinc-900 p-6">
        <h1 className="text-2xl font-semibold">Acadza Upload Backend</h1>
        <p className="mt-3 text-sm text-zinc-300">
          UI is handled by Acadza Studio (OBS). This service only provides auth
          and upload APIs.
        </p>
      </div>
    </main>
  );
}
