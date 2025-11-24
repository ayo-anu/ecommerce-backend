import Link from 'next/link';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header matching products page */}
      <div className="bg-dark-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/products">
            <h1 className="text-2xl font-bold text-white hover:text-gray-200 transition-colors">
              SiriusXerxes-Shop
            </h1>
          </Link>
          <div className="text-sm">
            <Link href="/products" className="hover:underline">
              Back to Shopping
            </Link>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          {children}
        </div>
      </div>
    </div>
  );
}