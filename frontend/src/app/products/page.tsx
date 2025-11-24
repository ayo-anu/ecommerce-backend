'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { productsAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { formatPrice } from '@/lib/utils';
import { ShoppingCart, User, Search, MapPin, ChevronDown } from 'lucide-react';

export default function ProductsPage() {
  const router = useRouter();
  const { user, isAuthenticated, loadUser, logout } = useAuthStore();
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['products', selectedCategory, searchQuery],
    queryFn: () => productsAPI.getProducts({ 
      category: selectedCategory,
      search: searchQuery 
    }),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    refetch();
  };

  const handleCategoryClick = (category: string) => {
    setSelectedCategory(category);
    setTimeout(() => refetch(), 100);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Bar */}
      <div className="bg-dark-900 text-white text-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            <span>Deliver to Lagos, Nigeria</span>
          </div>
          <div className="flex items-center gap-4">
            {isAuthenticated && user ? (
              <>
                <span className="hidden sm:inline">
                  Hello, <span className="font-semibold">{user.first_name || user.username}</span>
                </span>
                <button 
                  onClick={async () => {
                    await logout();
                    router.refresh();
                  }} 
                  className="hover:underline"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <Link href="/login" className="hover:underline font-semibold">
                Hello, Sign in
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Main Header */}
      <header className="bg-dark-800 shadow-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 gap-4">
            {/* Logo */}
            <Link href="/products" className="flex-shrink-0">
              <h1 className="text-2xl font-bold text-white hover:text-gray-200 transition-colors">
                SiriusXerxes-Shop
              </h1>
            </Link>

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="flex-1 max-w-2xl hidden md:block">
              <div className="relative flex">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search products..."
                  className="w-full px-4 py-2.5 rounded-l-md focus:outline-none text-gray-900"
                />
                <button 
                  type="submit"
                  className="bg-primary-600 hover:bg-primary-700 text-white px-6 rounded-r-md transition-colors"
                >
                  <Search className="h-5 w-5" />
                </button>
              </div>
            </form>

            {/* Actions */}
            <div className="flex items-center gap-2">
              {/* Account */}
              <Link
                href={isAuthenticated ? "/dashboard" : "/login"}
                className="flex items-center gap-2 px-3 py-2 text-white hover:bg-dark-700 rounded-md transition-colors"
              >
                {isAuthenticated && user?.avatar ? (
                  <img
                    src={`${process.env.NEXT_PUBLIC_API_URL}${user.avatar}`}
                    alt={user.username}
                    className="h-8 w-8 rounded-full object-cover border-2 border-primary-500"
                    onError={(e) => {
                      const target = e.currentTarget;
                      target.style.display = 'none';
                    }}
                  />
                ) : (
                  <User className="h-5 w-5" />
                )}
                <div className="text-left hidden lg:block">
                  <div className="text-xs text-gray-300">
                    {isAuthenticated ? 'Hello' : 'Sign in'}
                  </div>
                  <div className="text-sm font-bold">
                    {isAuthenticated && user ? user.first_name || user.username : 'Account'}
                  </div>
                </div>
              </Link>

              {/* Cart */}
              <Link
                href={isAuthenticated ? "/cart" : "/login?redirect=cart"}
                className="flex items-center gap-2 px-3 py-2 text-white hover:bg-dark-700 rounded-md transition-colors relative"
              >
                <ShoppingCart className="h-6 w-6" />
                <span className="absolute -top-1 -right-1 bg-primary-600 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
                  0
                </span>
                <span className="hidden sm:inline font-bold">Cart</span>
              </Link>
            </div>
          </div>
        </div>

        {/* Mobile Search */}
        <div className="md:hidden px-4 pb-3">
          <form onSubmit={handleSearch} className="relative flex">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search products..."
              className="w-full px-4 py-2 rounded-l-md focus:outline-none text-gray-900"
            />
            <button 
              type="submit"
              className="bg-primary-600 text-white px-4 rounded-r-md"
            >
              <Search className="h-5 w-5" />
            </button>
          </form>
        </div>
      </header>

      {/* Categories Bar */}
      <div className="bg-dark-700 text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4 h-12 overflow-x-auto scrollbar-hide">
            <button 
              onClick={() => handleCategoryClick('')}
              className={`flex items-center gap-2 px-4 py-1.5 rounded transition-colors whitespace-nowrap ${
                selectedCategory === '' ? 'bg-primary-600' : 'hover:bg-dark-600'
              }`}
            >
              <ChevronDown className="h-4 w-4" />
              All Products
            </button>
            <button 
              onClick={() => handleCategoryClick('electronics')}
              className={`px-4 py-1.5 rounded transition-colors whitespace-nowrap ${
                selectedCategory === 'electronics' ? 'bg-primary-600' : 'hover:bg-dark-600'
              }`}
            >
              Electronics
            </button>
            <button 
              onClick={() => handleCategoryClick('clothing')}
              className={`px-4 py-1.5 rounded transition-colors whitespace-nowrap ${
                selectedCategory === 'clothing' ? 'bg-primary-600' : 'hover:bg-dark-600'
              }`}
            >
              Clothing
            </button>
            <button 
              onClick={() => handleCategoryClick('books')}
              className={`px-4 py-1.5 rounded transition-colors whitespace-nowrap ${
                selectedCategory === 'books' ? 'bg-primary-600' : 'hover:bg-dark-600'
              }`}
            >
              Books
            </button>
            <button 
              onClick={() => handleCategoryClick('home-garden')}
              className={`px-4 py-1.5 rounded transition-colors whitespace-nowrap ${
                selectedCategory === 'home-garden' ? 'bg-primary-600' : 'hover:bg-dark-600'
              }`}
            >
              Home & Garden
            </button>
            <span className="px-4 py-1.5 text-primary-400 font-semibold whitespace-nowrap cursor-pointer hover:text-primary-300">
              Today's Deals
            </span>
          </div>
        </div>
      </div>

      {/* Products Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Results Info */}
        {!isLoading && data && (
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-900">
              {selectedCategory 
                ? `${selectedCategory.charAt(0).toUpperCase() + selectedCategory.slice(1)} Products` 
                : 'All Products'}
            </h2>
            <p className="text-gray-600">
              {data.count || data.results?.length || 0} results
            </p>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center py-20">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading products...</p>
            </div>
          </div>
        )}

        {/* Products Grid */}
        {!isLoading && data?.results && data.results.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {data.results.map((product) => (
              <Link
                key={product.id}
                href={`/products/${product.slug}`}
                className="bg-white rounded-lg shadow-sm hover:shadow-lg transition-all duration-200 overflow-hidden group"
              >
                <div className="aspect-square bg-gray-100 relative overflow-hidden">
                  {product.primary_image ? (
                    <img
                      src={`${process.env.NEXT_PUBLIC_API_URL}${product.primary_image}`}
                      alt={product.name}
                      className="w-full h-full object-contain p-4 group-hover:scale-105 transition-transform duration-200"
                      onError={(e) => {
                        e.currentTarget.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%23f3f4f6"/></svg>';
                      }}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      <ShoppingCart className="h-12 w-12 opacity-30" />
                    </div>
                  )}
                  {product.is_on_sale && product.discount_percentage && (
                    <span className="absolute top-2 left-2 bg-red-600 text-white px-2 py-1 text-xs font-bold rounded">
                      -{product.discount_percentage}%
                    </span>
                  )}
                </div>
                <div className="p-3">
                  <h3 className="text-sm text-gray-900 mb-2 line-clamp-2 group-hover:text-primary-600 transition-colors">
                    {product.name}
                  </h3>
                  <div className="flex items-baseline gap-2 mb-1">
                    <span className="text-xl font-bold text-gray-900">
                      {formatPrice(product.price)}
                    </span>
                    {product.compare_at_price && parseFloat(product.compare_at_price) > parseFloat(product.price) && (
                      <span className="text-xs text-gray-500 line-through">
                        {formatPrice(product.compare_at_price)}
                      </span>
                    )}
                  </div>
                  {product.is_low_stock && (
                    <p className="text-xs text-orange-600 font-semibold">Only a few left!</p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        ) : !isLoading && (
          <div className="text-center py-20">
            <ShoppingCart className="h-16 w-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              {searchQuery ? 'No results found' : 'No products available'}
            </h3>
            <p className="text-gray-500 mb-4">
              {searchQuery 
                ? `Try searching for something else` 
                : 'Check back soon for new products!'}
            </p>
            {(searchQuery || selectedCategory) && (
              <Button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedCategory('');
                  setTimeout(() => refetch(), 100);
                }}
              >
                Clear Filters
              </Button>
            )}
          </div>
        )}
      </main>
    </div>
  );
}