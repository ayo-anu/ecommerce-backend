import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { Toaster } from 'sonner';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'SiriusXerxes-Shop - Modern E-Commerce',
  description: 'Modern e-commerce platform built with Next.js and Django',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster 
            position="top-center"
            richColors 
            expand={true}
            duration={6000}
            closeButton
            toastOptions={{
              style: {
                padding: '16px',
                fontSize: '14px',
              },
              className: 'toast-custom',
            }}
          />
        </Providers>
      </body>
    </html>
  );
}