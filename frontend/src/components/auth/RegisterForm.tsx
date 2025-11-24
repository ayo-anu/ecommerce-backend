'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import Link from 'next/link';
import { authAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PasswordInput } from '@/components/ui/password-input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  username: z.string().min(3, 'Username must be at least 3 characters'),
  first_name: z.string().min(2, 'First name must be at least 2 characters'),
  last_name: z.string().min(2, 'Last name must be at least 2 characters'),
  phone: z.string().optional(),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number'),
  password2: z.string(),
}).refine((data) => data.password === data.password2, {
  message: "Passwords don't match",
  path: ['password2'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export function RegisterForm() {
  const router = useRouter();
  const { setUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsLoading(true);

    try {
      const response = await authAPI.register(data);
      setUser(response.user);
      toast.success('Account created successfully!');
      router.push('/');
    } catch (error: any) {
      console.error('Registration error:', error);
      
      // Handle API errors properly
      if (error.response?.data) {
        const errorData = error.response.data;
        
        // Handle field-specific errors
        Object.keys(errorData).forEach((field) => {
          const fieldError = errorData[field];
          
          // Convert error to string properly
          let errorMessage: string;
          if (Array.isArray(fieldError)) {
            errorMessage = fieldError.join(', ');
          } else if (typeof fieldError === 'string') {
            errorMessage = fieldError;
          } else if (typeof fieldError === 'object') {
            errorMessage = JSON.stringify(fieldError);
          } else {
            errorMessage = String(fieldError);
          }
          
          // Capitalize field name and show error
          const fieldName = field.charAt(0).toUpperCase() + field.slice(1).replace('_', ' ');
          toast.error(`${fieldName}: ${errorMessage}`);
        });
      } else if (error.message) {
        toast.error(error.message);
      } else {
        toast.error('Registration failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="first_name">First Name</Label>
          <Input
            id="first_name"
            placeholder="John"
            {...register('first_name')}
            error={errors.first_name?.message}
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="last_name">Last Name</Label>
          <Input
            id="last_name"
            placeholder="Doe"
            {...register('last_name')}
            error={errors.last_name?.message}
            disabled={isLoading}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="username">Username</Label>
        <Input
          id="username"
          placeholder="johndoe"
          {...register('username')}
          error={errors.username?.message}
          disabled={isLoading}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          placeholder="john@example.com"
          {...register('email')}
          error={errors.email?.message}
          disabled={isLoading}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="phone">Phone (Optional)</Label>
        <Input
          id="phone"
          type="tel"
          placeholder="+1234567890"
          {...register('phone')}
          error={errors.phone?.message}
          disabled={isLoading}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <PasswordInput
          id="password"
          placeholder="••••••••"
          {...register('password')}
          error={errors.password?.message}
          disabled={isLoading}
        />
        <p className="text-xs text-gray-500">
          Must contain uppercase, lowercase, and number. Min 8 characters.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="password2">Confirm Password</Label>
        <PasswordInput
          id="password2"
          placeholder="••••••••"
          {...register('password2')}
          error={errors.password2?.message}
          disabled={isLoading}
        />
      </div>

      <Button type="submit" className="w-full" isLoading={isLoading}>
        Create Account
      </Button>

      <p className="text-center text-sm text-gray-600">
        Already have an account?{' '}
        <Link href="/login" className="text-blue-600 hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </form>
  );
}