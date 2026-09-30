import './globals.css';

export const metadata = {
  title: 'superDOTats',
  description: 'Un Dot per a cada dubte: ajudants intel·ligents que et responen en català.',
};

const themeScript = `try{var t=localStorage.getItem('sd-theme');if(t!=='light'&&t!=='dark'){t=window.matchMedia&&window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'}document.documentElement.setAttribute('data-theme',t)}catch(e){document.documentElement.setAttribute('data-theme','dark')}`;

export default function RootLayout({ children }) {
  return (
    <html lang="ca" className="dark" suppressHydrationWarning={true}>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body className="bg-background text-foreground antialiased select-none" suppressHydrationWarning={true}>
        {children}
      </body>
    </html>
  );
}
