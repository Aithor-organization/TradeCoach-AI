"use client";

import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
}

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}: ButtonProps) {
  const base = "font-semibold rounded-lg transition-all duration-200 cursor-pointer";

  const variants = {
    primary: "bg-gradient-to-r from-[#22D3EE] to-[#06B6D4] text-[#0A0F1C] hover:opacity-90",
    secondary: "bg-[#1E293B] text-white border border-[#22D3EE33] hover:border-[#22D3EE66]",
    ghost: "bg-transparent text-[#94A3B8] hover:text-white",
  };

  const sizes = {
    sm: "px-4 py-2 text-sm",
    md: "px-6 py-3 text-base",
    lg: "px-8 py-4 text-lg",
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
