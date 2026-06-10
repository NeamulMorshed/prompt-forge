export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <nav className="flex flex-col gap-2">
        <a href="/settings/profile" className="text-blue-600 underline">Profile</a>
        <a href="/settings/api-keys" className="text-blue-600 underline">API Keys</a>
      </nav>
    </div>
  );
}
