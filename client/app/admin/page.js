'use client';

import AuthGate from '../../components/AuthGate';
import AdminPanel from '../../components/AdminPanel';

export default function AdminPage() {
  return (
    <AuthGate requireAdmin>
      <AdminPanel />
    </AuthGate>
  );
}
