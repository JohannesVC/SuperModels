/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'selector', 
  content: [
    './src/renderer/**/*.{html,js}', 
  ],
  theme: {
    extend: {
      typography: (theme) => ({
        DEFAULT: {
          css: {
            color: theme('colors.gray.300'),
            a: { color: theme('colors.blue.500'), 
              '&:hover': { color: theme('colors.blue.400'),},
            },
            p: { margin: theme('spacing.2') },
            strong: { color: theme('colors.gray.100') },
            h1: { color: theme('colors.gray.100'), },
            h2: { color: theme('colors.gray.100'), },
            blockquote: { 
              color: theme('colors.gray.100'), 
              fontWeight: 'normal',
              quotes: 'none',
              fontStyle: 'normal'
            },
            'blockquote p': {
              fontStyle: 'normal', 
            },
            pre: { backgroundColor: theme('colors.neutral.800') }, // theme('colors.neutral.800'),
            code: { color: theme('colors.gray.200'), },
            maxWidth: 'none',
          },
        },
      }),
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}