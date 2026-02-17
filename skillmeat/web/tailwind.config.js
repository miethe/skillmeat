/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: '',
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      fontFamily: {
        sans: [
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI"',
          'Roboto',
          'Helvetica Neue"',
          'Arial',
          'Noto Sans"',
          'sans-serif',
          'Apple Color Emoji"',
          'Segoe UI Emoji"',
          'Segoe UI Symbol"',
          'Noto Color Emoji"',
        ],
      },
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      keyframes: {
        'accordion-down': {
          from: {
            height: '0',
          },
          to: {
            height: 'var(--radix-accordion-content-height)',
          },
        },
        'accordion-up': {
          from: {
            height: 'var(--radix-accordion-content-height)',
          },
          to: {
            height: '0',
          },
        },
        'collapsible-down': {
          from: {
            height: '0',
            opacity: '0',
          },
          to: {
            height: 'var(--radix-collapsible-content-height)',
            opacity: '1',
          },
        },
        'collapsible-up': {
          from: {
            height: 'var(--radix-collapsible-content-height)',
            opacity: '1',
          },
          to: {
            height: '0',
            opacity: '0',
          },
        },
        'notification-pulse': {
          '0%, 100%': {
            transform: 'scale(1)',
          },
          '50%': {
            transform: 'scale(1.1)',
          },
        },
        'dnd-pickup': {
          '0%': {
            transform: 'scale(1) rotate(0deg)',
            opacity: '1',
            boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)',
          },
          '100%': {
            transform: 'scale(0.6) rotate(2.5deg)',
            opacity: '0.7',
            boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
          },
        },
        'dnd-drop-into': {
          '0%': {
            transform: 'scale(0.6)',
            opacity: '0.7',
          },
          '100%': {
            transform: 'scale(0.3)',
            opacity: '0',
          },
        },
        'dnd-success-check': {
          '0%': {
            transform: 'scale(0)',
            opacity: '0',
          },
          '50%': {
            transform: 'scale(1.2)',
            opacity: '1',
          },
          '75%': {
            transform: 'scale(0.9)',
          },
          '100%': {
            transform: 'scale(1)',
            opacity: '1',
          },
        },
        'dnd-success-check-out': {
          '0%': {
            transform: 'scale(1)',
            opacity: '1',
          },
          '100%': {
            transform: 'scale(0.8)',
            opacity: '0',
          },
        },
        'dnd-badge-pop': {
          '0%': {
            transform: 'scale(1)',
          },
          '50%': {
            transform: 'scale(1.2)',
          },
          '100%': {
            transform: 'scale(1)',
          },
        },
        'dnd-badge-shrink': {
          '0%': {
            transform: 'scale(1)',
          },
          '50%': {
            transform: 'scale(0.9)',
          },
          '100%': {
            transform: 'scale(1)',
          },
        },
        'dnd-poof': {
          '0%': {
            transform: 'scale(0.6)',
            opacity: '0.7',
          },
          '15%': {
            transform: 'scale(0.66)',
            opacity: '0.6',
          },
          '100%': {
            transform: 'scale(0)',
            opacity: '0',
          },
        },
        'dnd-particle': {
          '0%': {
            transform: 'translate(0, 0) scale(1)',
            opacity: '1',
          },
          '100%': {
            transform: 'translate(var(--particle-x), var(--particle-y)) scale(0)',
            opacity: '0',
          },
        },
        // -- New DnD polish keyframes --
        'dnd-drop-target-pulse': {
          '0%, 100%': {
            boxShadow: '0 0 0 0 hsl(var(--primary) / 0.2)',
          },
          '50%': {
            boxShadow: '0 0 0 4px hsl(var(--primary) / 0.15)',
          },
        },
        'dnd-remove-zone-breathe': {
          '0%, 100%': {
            borderColor: 'hsl(var(--destructive) / 0.3)',
            backgroundColor: 'hsl(var(--destructive) / 0.03)',
          },
          '50%': {
            borderColor: 'hsl(var(--destructive) / 0.5)',
            backgroundColor: 'hsl(var(--destructive) / 0.06)',
          },
        },
        'dnd-ghost-pulse': {
          '0%, 100%': {
            borderColor: 'hsl(var(--primary) / 0.2)',
          },
          '50%': {
            borderColor: 'hsl(var(--primary) / 0.4)',
          },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'collapsible-down': 'collapsible-down 0.2s ease-out',
        'collapsible-up': 'collapsible-up 0.2s ease-out',
        'notification-pulse': 'notification-pulse 0.5s ease-in-out',
        'dnd-pickup': 'dnd-pickup 200ms cubic-bezier(0.2, 0, 0.13, 1.5) forwards',
        'dnd-drop-into': 'dnd-drop-into 300ms cubic-bezier(0.55, 0, 1, 0.45) forwards',
        'dnd-success-check': 'dnd-success-check 350ms cubic-bezier(0.34, 1.56, 0.64, 1) forwards',
        'dnd-success-check-out': 'dnd-success-check-out 200ms cubic-bezier(0.55, 0, 1, 0.45) forwards',
        'dnd-badge-pop': 'dnd-badge-pop 300ms cubic-bezier(0.34, 1.56, 0.64, 1)',
        'dnd-badge-shrink': 'dnd-badge-shrink 300ms cubic-bezier(0.34, 1.56, 0.64, 1)',
        'dnd-poof': 'dnd-poof 350ms cubic-bezier(0.55, 0, 1, 0.45) forwards',
        'dnd-particle': 'dnd-particle 400ms cubic-bezier(0.2, 0, 0, 1) forwards',
        // -- New DnD polish animations --
        'dnd-drop-target-pulse': 'dnd-drop-target-pulse 1.5s ease-in-out infinite',
        'dnd-remove-zone-breathe': 'dnd-remove-zone-breathe 5s ease-in-out infinite',
        'dnd-ghost-pulse': 'dnd-ghost-pulse 1.5s ease-in-out infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate'), require('@tailwindcss/typography')],
};
