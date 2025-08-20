import { AuthProvider } from '../../contexts/AuthContext';
import type { ComponentChildren } from 'preact';

interface AuthProviderWrapperProps {
  children: ComponentChildren;
}

export default function AuthProviderWrapper({ children }: AuthProviderWrapperProps) {
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  );
}
