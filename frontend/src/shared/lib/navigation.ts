import type { UserRole } from '@/features/auth/types';

export interface NavItem {
  path: string;
  label: string;
  roles: UserRole[];
}

export const navItems: NavItem[] = [
  {
    path: '/',
    label: 'Dashboard',
    roles: ['alumno', 'docente', 'admin'],
  },
  {
    path: '/courses',
    label: 'Mis Cursos',
    roles: ['alumno'],
  },
  {
    path: '/actividades',
    label: 'Actividades',
    roles: ['alumno'],
  },
  {
    path: '/student/progress',
    label: 'Mi Progreso',
    roles: ['alumno'],
  },
  {
    path: '/courses',
    label: 'Cursos',
    roles: ['docente', 'admin'],
  },
  {
    path: '/settings',
    label: 'Configuracion',
    roles: ['docente', 'admin'],
  },
  {
    path: '/admin/governance',
    label: 'Gobernanza',
    roles: ['admin'],
  },
];

export function getNavItemsForRole(role: UserRole): NavItem[] {
  return navItems.filter((item) => item.roles.includes(role));
}
