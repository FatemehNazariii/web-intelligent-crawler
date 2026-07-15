// frontend/app/layout.js
import './globals.css';

export const metadata = {
  title: 'Web Crawler - Intelligent Research Assistant',
  description: 'An intelligent web crawler for topic-based search, information extraction, and automated report generation',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" dir="ltr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap" rel="stylesheet" />
      </head>
      <body className="h-screen overflow-hidden bg-[#343541] text-white">
        {children}
      </body>
    </html>
  );
}