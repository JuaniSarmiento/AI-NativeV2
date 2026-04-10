---
name: tailwind-theme-system
description: >
  Impone el sistema de diseño con TailwindCSS 4: tokens como CSS custom properties
  en @theme, dark mode via variante dark:, layouts mobile-first y contenedores
  con overflow-x-hidden. Prohibe valores hex hardcodeados y class toggling manual
  para dark mode. Trigger: al trabajar con estilos TailwindCSS, dark mode, layouts
  responsivos o tokens de diseño en la plataforma AI-Native.
license: Apache-2.0
metadata:
  author: ai-native
  version: "1.0"
---

## Cuándo Usar

- Al crear o modificar componentes con clases de Tailwind
- Al definir colores, tipografía o espaciado del sistema de diseño
- Al implementar dark mode en cualquier componente
- Al construir layouts responsivos (mobile, tablet, desktop)
- Al depurar overflow horizontal en mobile
- Al agregar nuevos tokens de color o escala al tema

## Patrones Críticos

### 1. `@theme` con CSS custom properties para colores

En TailwindCSS 4, los tokens se definen en la capa `@theme` del CSS global.
Tailwind genera automáticamente las utilidades `bg-*`, `text-*`, `border-*`
a partir de las variables `--color-*`.

```css
/* src/styles/globals.css */
@import "tailwindcss";

@theme {
  /* Paleta primaria — plataforma educativa */
  --color-brand-50:  oklch(97% 0.02 250);
  --color-brand-100: oklch(93% 0.05 250);
  --color-brand-200: oklch(86% 0.09 250);
  --color-brand-500: oklch(60% 0.18 250);
  --color-brand-600: oklch(52% 0.20 250);
  --color-brand-700: oklch(44% 0.19 250);
  --color-brand-900: oklch(28% 0.14 250);

  /* Superficies semánticas */
  --color-surface:       oklch(99% 0.005 250);
  --color-surface-muted: oklch(96% 0.01  250);
  --color-surface-dark:  oklch(14% 0.02  250);

  /* Feedback */
  --color-success: oklch(65% 0.20 145);
  --color-warning: oklch(75% 0.18  70);
  --color-danger:  oklch(60% 0.22  25);

  /* Tipografía */
  --font-sans: "Inter Variable", ui-sans-serif, system-ui, sans-serif;

  /* Radios */
  --radius-card: 0.75rem;
  --radius-input: 0.5rem;
}
```

### 2. Componente con dark mode via variante `dark:`

El dark mode se activa con la variante `dark:` de Tailwind (estrategia `class`
o `media`). Nunca se alterna manualmente entre clases de color.

```tsx
// components/ui/EvaluationCard.tsx
interface EvaluationCardProps {
  score: number;
  label: string;
  detail: string;
}

export function EvaluationCard({ score, label, detail }: EvaluationCardProps) {
  return (
    <article
      className={[
        // Base — usa tokens del @theme
        "rounded-[--radius-card] border p-6 shadow-sm",
        "bg-surface border-brand-100",
        "font-sans",
        // Dark mode — variante dark: sobre cada token
        "dark:bg-surface-dark dark:border-brand-700",
      ].join(" ")}
    >
      <p className="text-sm font-medium text-brand-600 dark:text-brand-200">
        {label}
      </p>
      <span className="text-4xl font-bold text-brand-900 dark:text-brand-50">
        {score}
      </span>
      <p className="mt-2 text-sm text-brand-500 dark:text-brand-300">
        {detail}
      </p>
    </article>
  );
}
```

### 3. Layout responsivo mobile-first

Se escribe el estilo base para mobile y se sobreescribe en breakpoints más
grandes (`sm:`, `md:`, `lg:`). Nunca al revés.

```tsx
// components/layouts/TutorLayout.tsx
export function TutorLayout({ sidebar, chat, panel }: TutorLayoutProps) {
  return (
    // Contenedor raíz: mobile stack → desktop grid
    <div className="min-h-screen bg-surface dark:bg-surface-dark">
      <div
        className={[
          // Mobile: columna única
          "mx-auto w-full max-w-full px-4",
          // Tablet: dos columnas
          "sm:px-6",
          // Desktop: tres columnas con sidebar fijo
          "lg:grid lg:max-w-screen-xl lg:grid-cols-[240px_1fr_320px] lg:gap-6 lg:px-8",
        ].join(" ")}
      >
        {/* Sidebar — oculto en mobile, visible desde lg */}
        <aside className="hidden lg:block lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto">
          {sidebar}
        </aside>

        {/* Chat — ocupa todo el ancho en mobile */}
        <main className="w-full min-w-0 py-4 sm:py-6">
          {chat}
        </main>

        {/* Panel lateral — ocupa todo el ancho en mobile, columna en desktop */}
        <aside className="w-full lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto">
          {panel}
        </aside>
      </div>
    </div>
  );
}
```

### 4. Patrón de contenedor mobile: `overflow-x-hidden w-full max-w-full`

Cualquier contenedor raíz que pueda causar scroll horizontal en mobile debe
declarar estas tres clases. Aplica especialmente a layouts con posicionamiento
absoluto o elementos que se salen del viewport.

```tsx
// app/layout.tsx (o RootLayout)
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body
        className={[
          // Previene overflow horizontal en mobile — SIEMPRE en body
          "overflow-x-hidden w-full max-w-full",
          "bg-surface text-brand-900",
          "dark:bg-surface-dark dark:text-brand-50",
          "font-sans antialiased",
        ].join(" ")}
      >
        {/* Wrapper interno también necesita la restricción */}
        <div className="relative w-full max-w-full overflow-x-hidden">
          {children}
        </div>
      </body>
    </html>
  );
}

// Componente con elemento que puede sobresalir — agregar clip
function SocraticBubble({ text }: { text: string }) {
  return (
    <div className="relative w-full max-w-full overflow-x-hidden">
      <div className="rounded-[--radius-card] bg-brand-50 p-4 dark:bg-brand-900">
        <p className="break-words text-sm text-brand-700 dark:text-brand-200">
          {text}
        </p>
      </div>
    </div>
  );
}
```

## Anti-patrones

### Valores hex hardcodeados en lugar de tokens del tema

```tsx
// NO — hardcodea colores, rompe el sistema de diseño y el dark mode
<div className="bg-[#1e3a5f] text-[#f0f4ff]">...</div>

// SI — usa los tokens definidos en @theme
<div className="bg-brand-900 text-brand-50 dark:bg-surface-dark dark:text-brand-100">
  ...
</div>
```

### Toggle manual de clases para dark mode

```tsx
// NO — lógica manual que duplica responsabilidad y se desincroniza
const [dark, setDark] = useState(false);
<div className={dark ? "bg-gray-900 text-white" : "bg-white text-gray-900"}>

// SI — Tailwind maneja el dark mode con la variante dark:
// (activada por la clase "dark" en <html> o por prefers-color-scheme)
<div className="bg-surface text-brand-900 dark:bg-surface-dark dark:text-brand-50">
```

### Breakpoints desktop-first (sobreescribir con sm: lo que lg: definió)

```tsx
// NO — desktop-first, mobile queda sin estilos base o los sobreescribe
<div className="lg:grid lg:grid-cols-3 sm:flex sm:flex-col">

// SI — mobile-first: base para mobile, escalar hacia arriba
<div className="flex flex-col lg:grid lg:grid-cols-3">
```

## Checklist

- [ ] Todos los colores del proyecto están en `@theme` como `--color-*`
- [ ] Ningún componente usa clases con valores hex `bg-[#...]` o `text-[#...]`
- [ ] El dark mode se implementa exclusivamente con la variante `dark:`
- [ ] El body tiene `overflow-x-hidden w-full max-w-full`
- [ ] Los layouts se escriben mobile-first (base sin prefijo, luego `sm:`, `md:`, `lg:`)
- [ ] Las fuentes están declaradas en `@theme` como `--font-*`
- [ ] Los radios de borde reutilizan `--radius-card` / `--radius-input`
- [ ] Elementos con texto largo usan `break-words` o `truncate` para evitar overflow
- [ ] Sidebars y paneles fijos tienen `overflow-y-auto` para scroll interno
